from mcp.server.fastmcp import FastMCP
from tools.mcp_tools.func_source_code.trading_bot import TradingBot
from tools.mcp_tools.utils import register_mcp_tools

mcp = FastMCP("TradingBot")
register_mcp_tools(TradingBot, mcp)

if __name__ == "__main__":
    mcp.run(transport='stdio')