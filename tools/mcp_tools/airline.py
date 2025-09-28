from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import date, datetime
from enum import Enum
from functools import wraps
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from tools.mcp_tools.func_source_code.airline.data_model import FlightDB
from tools.mcp_tools.func_source_code.airline.tools import AirlineTools
from tools.mcp_tools.func_source_code.airline.utils import AIRLINE_DB_PATH

mcp = FastMCP("Airline")

_TOOLKIT: Dict[str, AirlineTools] = {
    "instance": AirlineTools(FlightDB.load(AIRLINE_DB_PATH))
}


def _get_toolkit() -> AirlineTools:
    return _TOOLKIT["instance"]


def _serialize_output(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _serialize_output(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_output(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


@mcp.tool()
def load_scenario(scenario: dict | None = None):
    """Load a database snapshot for the airline toolkit."""
    try:
        if scenario and isinstance(scenario, dict) and "db" in scenario:
            db = FlightDB.model_validate(scenario["db"])
        else:
            db = FlightDB.load(AIRLINE_DB_PATH)
        _TOOLKIT["instance"] = AirlineTools(db)
        return "Successfully loaded airline scenario."
    except Exception as error:
        return f"Error: {error}"


@mcp.tool()
def save_scenario():
    """Serialize the current airline database to a dictionary."""
    toolkit = _get_toolkit()
    if toolkit.db is None:
        return {"error": "Airline database is not initialized."}
    return {"db": _serialize_output(toolkit.db)}


def _register_tool_methods():
    toolkit = _get_toolkit()
    toolkit_type = type(toolkit)

    for name, func in inspect.getmembers(toolkit_type, predicate=callable):
        if name.startswith("_"):
            continue
        if not hasattr(func, "__tool_type__"):
            continue

        bound_method = getattr(toolkit, name)
        signature = inspect.signature(bound_method)

        @wraps(bound_method)
        def wrapper(*args, _method_name=name, **kwargs):
            try:
                method = getattr(_get_toolkit(), _method_name)
                result = method(*args, **kwargs)
                return _serialize_output(result)
            except Exception as error:
                return f"Error: {error}"

        wrapper.__signature__ = signature  # type: ignore[attr-defined]
        decorated = mcp.tool()(wrapper)
        try:
            decorated.__signature__ = signature  # type: ignore[attr-defined]
        except AttributeError:
            pass
        globals()[name] = decorated


_register_tool_methods()


if __name__ == "__main__":
    mcp.run(transport="stdio")
