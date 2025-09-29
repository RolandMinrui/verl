from mcp.server.fastmcp import FastMCP
from tools.mcp_tools.func_source_code.posting_api import TwitterAPI
from tools.mcp_tools.utils import register_mcp_tools

mcp = FastMCP("Posting")
register_mcp_tools(TwitterAPI, mcp)

if __name__ == "__main__":
    print("\nStarting MCP Twitter Posting Server...")
    mcp.run(transport='stdio')