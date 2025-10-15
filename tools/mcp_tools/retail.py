from mcp.server.fastmcp import FastMCP

from tools.mcp_tools.func_source_code.retail.data_model import RetailDB
from tools.mcp_tools.func_source_code.retail.tools import RetailTools
from tools.mcp_tools.func_source_code.retail.utils import RETAIL_DB_PATH
from tools.mcp_tools.utils import register_mcp_tools

retail = RetailTools(RetailDB.load(RETAIL_DB_PATH))

mcp = FastMCP("Airline")
register_mcp_tools(RetailTools, mcp, retail)

if __name__ == "__main__":
    mcp.run(transport="stdio")
