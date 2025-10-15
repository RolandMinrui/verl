import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

existing = os.environ.get("PYTHONPATH")
os.environ["PYTHONPATH"] = (
    str(ROOT)
    if not existing
    else str(ROOT) + os.pathsep + existing
)

from tools.mcp_managers.client_manager import MCPClientManager

DOMAINS = ["airline", "mock", "retail", "telecom"]
SAMPLE_CALLS = {
    "airline": ("airline-get_flight_status", {"flight_number": "HAT001", "date": "2024-05-16"}),
    "mock"   : ("mock-get_users", {}),
    "retail" : ("retail-get_order_details", {"order_id": "#W2611340"}),
    "telecom": ("telecom-get_customer_by_id", {"customer_id": "C1001"}),
    "telecom": ("telecom-save_scenario", {}),
}


def build_temp_config() -> str:
    config = {
        "mcpServers": {
            domain: {
                "local_path": f"tools/mcp_tools/{domain}.py",
                "stateless": False,
            }
            for domain in DOMAINS
        }
    }
    handle = tempfile.NamedTemporaryFile("w", delete=False, suffix=".json")
    json.dump(config, handle, indent=2)
    handle.flush()
    handle.close()
    return handle.name


def main() -> None:
    manager = MCPClientManager()
    temp_config_path = build_temp_config()

    try:
        manager.init_config(temp_config_path)
        print(manager.list_tools(include_schema=True))
        summary: dict[str, dict[str, str]] = {}
        for domain in DOMAINS:
            client_id = f"{domain}-sanity"
            load_result = manager.call_tool(f"{domain}-load_scenario", {}, client_id)
            tool_name, args = SAMPLE_CALLS[domain]
            sample_result = manager.call_tool(tool_name, args, client_id)
            if len(sample_result) > 200:
                sample_preview = sample_result[:200] + "..."
            else:
                sample_preview = sample_result
            summary[domain] = {
                "load_scenario": load_result,
                "sample_tool": tool_name,
                "sample_result": sample_preview,
            }
    finally:
        manager.shutdown()
        if 'temp_config_path' in locals():
            temp_path = Path(temp_config_path)
            if temp_path.exists():
                temp_path.unlink()

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
