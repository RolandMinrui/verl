from mcp.server.fastmcp import FastMCP

from tools.mcp_tools.func_source_code.mock.data_model import MockDB
from tools.mcp_tools.func_source_code.mock.tools import MockTools
from tools.mcp_tools.func_source_code.mock.utils import MOCK_DB_PATH
from tools.mcp_tools.utils import register_mcp_tools

mock = MockTools(MockDB.load(MOCK_DB_PATH))

mcp = FastMCP("Airline")
register_mcp_tools(MockTools, mcp, mock)

if __name__ == "__main__":
    mcp.run(transport="stdio")
