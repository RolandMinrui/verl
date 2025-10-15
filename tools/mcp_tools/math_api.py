from mcp.server.fastmcp import FastMCP
from tools.mcp_tools.func_source_code.math_api import MathAPI
from tools.mcp_tools.utils import register_mcp_tools

mcp = FastMCP("Math")
register_mcp_tools(MathAPI, mcp)

if __name__ == "__main__":
    mcp.run(transport='stdio')