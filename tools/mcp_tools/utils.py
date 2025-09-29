import inspect
from functools import wraps
from typing import Any, Callable, Type
from mcp.server.fastmcp import FastMCP

def register_mcp_tools(tool_class: Type, mcp: FastMCP, tool_instance: Any = None):
    """Register all public methods of a class as MCP tools."""
    if tool_instance is None:
        tool_instance = tool_class()
    
    for name, method in inspect.getmembers(tool_instance, predicate=inspect.ismethod):
        if name.startswith("_"):
            continue
            
        signature = inspect.signature(method)
        
        @wraps(method)
        def wrapper(*args, _method_name: str = name, **kwargs):
            try:
                method_to_call = getattr(tool_instance, _method_name)
                result = method_to_call(*args, **kwargs)
                return result
            except Exception as error:
                return f"Error: {error}"
        
        wrapper.__signature__ = signature
        mcp.tool()(wrapper)