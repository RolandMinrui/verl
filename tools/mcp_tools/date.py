from datetime import datetime, timezone
import pytz
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Date")

@mcp.tool()
def get_today_date() -> str:
    """
    Get today's date in YYYY-MM-DD format.
    
    Returns:
        Today's date as a string in YYYY-MM-DD format
    """
    today = datetime.now().date()
    return today.strftime("%Y-%m-%d")

@mcp.tool()
def get_current_datetime() -> str:
    """
    Get the current date and time in ISO format.
    
    Returns:
        Current datetime as a string in ISO format
    """
    now = datetime.now()
    return now.isoformat()

@mcp.tool()
def get_current_datetime_utc() -> str:
    """
    Get the current date and time in UTC timezone.
    
    Returns:
        Current UTC datetime as a string in ISO format
    """
    now_utc = datetime.now(timezone.utc)
    return now_utc.isoformat()

@mcp.tool()
def get_date_in_timezone(timezone_name: str) -> str:
    """
    Get the current date and time in a specific timezone.
    
    Args:
        timezone_name: Timezone name (e.g., 'America/New_York', 'Europe/London', 'Asia/Tokyo')
        
    Returns:
        Current datetime in the specified timezone as a string
    """
    try:
        tz = pytz.timezone(timezone_name)
        now_in_tz = datetime.now(tz)
        return f"{now_in_tz.strftime('%Y-%m-%d %H:%M:%S %Z')} ({timezone_name})"
    except pytz.exceptions.UnknownTimeZoneError:
        return (f"Error: Unknown timezone '{timezone_name}'. "
                f"Please use a valid timezone name like 'America/New_York' or 'Europe/London'.")

@mcp.tool()
def get_timestamp() -> str:
    """
    Get the current Unix timestamp.
    
    Returns:
        Current Unix timestamp as a string
    """
    timestamp = datetime.now().timestamp()
    return str(int(timestamp))

if __name__ == "__main__":
    mcp.run(transport='stdio')