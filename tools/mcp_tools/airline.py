from mcp.server.fastmcp import FastMCP

from tools.mcp_tools.func_source_code.airline.data_model import FlightDB
from tools.mcp_tools.func_source_code.airline.tools import AirlineTools
from tools.mcp_tools.func_source_code.airline.utils import AIRLINE_DB_PATH
from tools.mcp_tools.utils import register_mcp_tools

airline = AirlineTools(FlightDB.load(AIRLINE_DB_PATH))

mcp = FastMCP("Airline")
register_mcp_tools(AirlineTools, mcp, airline)

if __name__ == "__main__":
    print("\nStarting MCP Airline Booking Server...")
    mcp.run(transport='stdio')