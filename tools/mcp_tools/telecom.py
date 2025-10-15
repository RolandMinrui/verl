from mcp.server.fastmcp import FastMCP

from tools.mcp_tools.func_source_code.telecom.data_model import TelecomDB
from tools.mcp_tools.func_source_code.telecom.tools import TelecomTools
from tools.mcp_tools.func_source_code.telecom.utils import TELECOM_DB_PATH
from tools.mcp_tools.utils import register_mcp_tools

telecom = TelecomTools(TelecomDB.load(TELECOM_DB_PATH))

mcp = FastMCP("Airline")
register_mcp_tools(TelecomTools, mcp, telecom)

if __name__ == "__main__":
    mcp.run(transport="stdio")
