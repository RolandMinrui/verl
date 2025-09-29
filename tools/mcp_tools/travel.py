from mcp.server.fastmcp import FastMCP
from tools.mcp_tools.func_source_code.travel_booking import TravelAPI
from tools.mcp_tools.utils import register_mcp_tools

mcp = FastMCP("Travel")
register_mcp_tools(TravelAPI, mcp)

if __name__ == "__main__":
    print("\nStarting MCP Travel Booking Server...")
    mcp.run(transport='stdio')