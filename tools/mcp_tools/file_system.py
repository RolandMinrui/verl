from mcp.server.fastmcp import FastMCP
from tools.mcp_tools.func_source_code.gorilla_file_system import GorillaFileSystem
from tools.mcp_tools.utils import register_mcp_tools

mcp = FastMCP("FileSystem")
register_mcp_tools(GorillaFileSystem, mcp)

if __name__ == "__main__":
    print("\nStarting MCP File System Management Server...")
    mcp.run(transport='stdio')