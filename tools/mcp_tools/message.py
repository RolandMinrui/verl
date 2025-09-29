from mcp.server.fastmcp import FastMCP
from tools.mcp_tools.func_source_code.message_api import MessageAPI
from tools.mcp_tools.utils import register_mcp_tools

mcp = FastMCP("Message")
register_mcp_tools(MessageAPI, mcp)

if __name__ == "__main__":
    print("\nStarting MCP Message Management Server...")
    mcp.run(transport='stdio')