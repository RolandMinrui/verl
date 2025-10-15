from mcp.server.fastmcp import FastMCP
from tools.mcp_tools.func_source_code.ticket_api import TicketAPI
from tools.mcp_tools.utils import register_mcp_tools

mcp = FastMCP("Ticket")
register_mcp_tools(TicketAPI, mcp)

if __name__ == "__main__":
    mcp.run(transport='stdio')