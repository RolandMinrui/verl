from enum import Enum
from typing import Callable, Dict


class ToolType(str, Enum):
    READ = "read"
    WRITE = "write"
    THINK = "think"
    GENERIC = "generic"


def is_tool(tool_type: ToolType = ToolType.READ):
    """Decorator marker used by the original TauBench toolkits."""

    def decorator(func: Callable) -> Callable:
        setattr(func, "__tool_type__", tool_type)
        return func

    return decorator


class ToolKitBase:
    """Minimal base to keep ported toolkits working."""

    def __init__(self, db=None) -> None:
        self.db = db

    def get_statistics(self) -> dict[str, int]:
        tools = self._collect_tools()
        counts = {tool_type: 0 for tool_type in ToolType}
        for func in tools.values():
            tool_type = getattr(func, "__tool_type__", ToolType.READ)
            counts[tool_type] += 1
        return {
            "num_tools": len(tools),
            "num_read_tools": counts[ToolType.READ],
            "num_write_tools": counts[ToolType.WRITE],
            "num_think_tools": counts[ToolType.THINK],
            "num_generic_tools": counts[ToolType.GENERIC],
        }

    def _collect_tools(self) -> Dict[str, Callable]:
        tools: Dict[str, Callable] = {}
        for attr in dir(self):
            if attr.startswith("_"):
                continue
            value = getattr(self, attr)
            if callable(value) and hasattr(value, "__tool_type__"):
                tools[attr] = value
        return tools