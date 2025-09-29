from mcp.server.fastmcp import FastMCP
from tools.mcp_tools.func_source_code.vehicle_control import VehicleControlAPI
from tools.mcp_tools.utils import register_mcp_tools

mcp = FastMCP("Vehicle")
register_mcp_tools(VehicleControlAPI, mcp)

if __name__ == "__main__":
    print("\nStarting MCP Vehicle Control Server...")
    mcp.run(transport='stdio')