from typing import Any, Dict, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound=BaseModel)


class BaseModelNoExtra(BaseModel):
    """BaseModel that forbids unexpected fields."""

    model_config = ConfigDict(extra="forbid")


def update_pydantic_model_with_dict(model_instance: T, update_data: Dict[str, Any]) -> T:
    """Recursively merge update_data into model_instance and return a new model."""

    def _merge(target: Dict[str, Any], updates: Dict[str, Any]) -> None:
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                _merge(target[key], value)
            else:
                target[key] = value

    base_data = model_instance.model_dump()
    _merge(base_data, update_data)
    return type(model_instance).model_validate(base_data)