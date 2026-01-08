import asyncio
import json
import threading
import os
import jsonlines
from pathlib import Path
from tqdm import tqdm
from fastmcp import Client
from fastmcp.exceptions import ToolError


class MCPClientManager:
    _instance = None  # Private class variable to store the unique instance

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MCPClientManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):  # The singleton should only be initialized once
            self.clients = {}  # {client_id: {"client": client, "status": bool}}
            self.stateless_clients = {}  # {server_name: client}
            self.server_to_path_mapping = {} # {server_name: tool_path}
            self.log_info = {}
            self.tool_schemas = []
            self.tools = {}

            # Set up a new event loop in a separate thread for async operations
            self.loop = asyncio.new_event_loop()
            self.loop_thread = threading.Thread(target=self.start_loop, daemon=True)
            self.loop_thread.start()

            self._initialized = False

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    # TODO
    def is_valid_mcp_servers(self, config: dict) -> bool:
        return True

    def is_valid_client_id(self, client_id: str) -> bool:
        """A valid client_id must follow "str-str" where substring str contains hyphens."""
        if not isinstance(client_id, str):
            return False

        parts = client_id.split("-")
        return len(parts) == 2 and all(parts) and client_id.count("-") == 1

    async def init_config_async(self, config: dict, overwrite: bool = False):
        """
        Initialize the MCP client manager from JSON config file.

        Args:
            config_path: Path to the MCP server config file
            overwrite: Whether to overwrite existing configuration
        """
        if getattr(self, "_initialized", False) and not overwrite:
            return

        self.tool_schemas = []
        self.tools = {} # {tool_name: tool_schema}

        mcp_servers = config["mcpServers"]
        for server_name, server in tqdm(
            mcp_servers.items(), desc="Loading MCP Clients..."
        ):
            self.server_to_path_mapping[server_name] = server["tool_path"]
            await self.register_MCP_server_async(
                server_name = server_name,
                tool_path = server["tool_path"],
                is_stateless = server["stateless"],
            )

        self._initialized = True

    def init_config(self, config_path: str, overwrite: bool = False):
        """Synchronous wrapper for init_config_async"""
        if getattr(self, "_initialized", False) and not overwrite:
            return
        
        config_path_obj = Path(config_path)
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    config = {"mcpServers": {}}
                else:
                    config = json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {"mcpServers": {}}
            config_path_obj.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path_obj, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

        if not self.is_valid_mcp_servers(config):
            raise ValueError("MCP servers config is not valid")

        future = asyncio.run_coroutine_threadsafe(
            self.init_config_async(config, overwrite), self.loop
        )
        try:
            result = future.result()
            return result
        except Exception as e:
            raise e

    async def register_MCP_server_async(self, server_name: str, tool_path: str, is_stateless: bool = False) -> None:
        """
        Register a new MCP server into the manager.

        Args:
            server_name: Name of the MCP server
            tool_path: Path to the tool file
            is_stateless: Whether the server is stateless
        """
        async def add_tool_schema(server_name: str, client: Client):
            tools = await client.list_tools()
            for tool in tools:
                tool_schema = {
                    "type": "function",
                    "function": {
                        "name": f"{server_name}-{tool.name}",
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                }
                tool_name = f"{server_name}-{tool.name}"
                if tool_name not in self.tools:
                    self.tool_schemas.append(tool_schema)
                    self.tools.update({tool_name: tool_schema})

        self.server_to_path_mapping[server_name] = tool_path
        client = Client(tool_path)

        # For stateless clients, create a new client instance and keep it alive
        if is_stateless:
            await client._connect()
            await add_tool_schema(server_name, client)
            self.stateless_clients[server_name] = client
        # For stateful clients, create a new client instance and delete it afterwards
        else:
            async with client:
                await add_tool_schema(server_name, client)
            await client.close()

    def register_MCP_server(self, server_name: str, tool_path: str, is_stateless: bool = False) -> None:
        """Synchronous wrapper for register_MCP_server_async"""
        future = asyncio.run_coroutine_threadsafe(
            self.register_MCP_server_async(server_name, tool_path, is_stateless),
            self.loop,
        )
        try:
            future.result()
        except Exception as e:
            raise e

    async def reload_MCP_server_async(self, server_name: str, tool_path: str, is_stateless: bool = False) -> None:
        """
        Reload an existing MCP server from the manager.
        
        Args:
            server_name: Name of the MCP server
            tool_path: Path to the updated tool file
            is_stateless: Whether the server is stateless
        """
        # 1. Close all related stateful clients
        clients_to_close = [
            cid for cid in list(self.clients.keys())
            if cid.startswith(f"{server_name}-")
        ]
        for client_id in clients_to_close:
            await self.close_client_async(client_id)

        # 2. Close all related stateless clients
        if server_name in self.stateless_clients:
            try:
                await self.stateless_clients[server_name].close()
            except Exception as e:
                print(f"Warning: Failed to close stateless client: {e}")
            del self.stateless_clients[server_name]

        # 3. Remove original tool schemas
        self.tool_schemas = [
            schema for schema in self.tool_schemas
            if not schema['function']['name'].startswith(f"{server_name}-")
        ]
        self.tools = {
            name: schema for name, schema in self.tools.items()
            if not name.startswith(f"{server_name}-")
        }

        # 4. Re-register the tool server
        await self.register_MCP_server_async(server_name, tool_path, is_stateless)
        print(f"[MCPClientManager] Successfully reloaded tool server: {server_name}")

    def reload_MCP_server(self, server_name: str, tool_path: str, is_stateless: bool = False) -> None:
        """Synchronous wrapper for reload_MCP_server_async"""
        future = asyncio.run_coroutine_threadsafe(
            self.reload_MCP_server_async(server_name, tool_path, is_stateless),
            self.loop
        )
        try:
            future.result()
        except Exception as e:
            print(f"Error reloading MCP server: {e}")
            raise e

    def filter_tools(self, servers: list[str] | None) -> list[dict]:
        if servers is None:
            return self.tool_schemas

        filtered_tool_schemas = []

        # Only keep the tools that belongs to the given mcp_servers
        # Remove the load_scenario and save_scenario tools
        for mcp_server in servers:
            for tool_name, tool_schema in self.tools.items():
                if (
                    mcp_server in tool_name
                    and "load_scenario" not in tool_name
                    and "save_scenario" not in tool_name
                ):
                    filtered_tool_schemas.append(tool_schema)

        return filtered_tool_schemas

    def dump_log(self, client_id, log_dump_path="log/log.jsonl") -> None:
        os.makedirs(os.path.dirname(log_dump_path), exist_ok=True)

        if client_id in self.log_info:
            with jsonlines.open(log_dump_path, mode="a") as writer:
                writer.write({client_id: self.log_info[client_id]})

            del self.log_info[client_id]  # delete log after dumping

    def add_log(self, client_id, info: dict) -> None:
        no_class_client_id = client_id.split("-")[-1]  # remove tool class from client id
        if no_class_client_id not in self.log_info:
            self.log_info[no_class_client_id] = []

        if info:
            self.log_info[no_class_client_id].append(info)

    def set_status(self, client_id):
        client_info = self.clients.get(client_id)
        if client_info:
            self.clients[client_id]["status"] = True

    def get_client(self, client_id: str) -> tuple[Client, bool]:
        """
        Get a client from a given client id or create a new client if not exist.
        """
        assert self.is_valid_client_id(
            client_id
        ), "The client_id should follow pattern {mcp_server}-{request_id} or {mcp_server}-{request_id}_test_{test_case_id}!"

        if client_id in self.clients:
            return self.clients[client_id]["client"], self.clients[client_id]["status"]

        tool_class = client_id.split("-")[0]
        if tool_class in self.stateless_clients:
            return self.stateless_clients[tool_class], True

        new_client = Client(self.server_to_path_mapping[tool_class])
        self.clients[client_id] = {
            "client": new_client,
            "status": False,  # not initialized
        }
        return new_client, False

    async def close_client_async(self, client_id: str = None, server_name: str = None):
        """
        Close and remove a client from the manager.

        Args:
            client_id: Client ID of the stateful client to close
            server_name: Server name of the stateless client to close
        """
        if client_id:
            client_info = self.clients.get(client_id, {})
            client_to_close = client_info.get("client")
            if client_to_close:
                try:
                    await client_to_close.close()
                    print(f"Client {client_id} closed and removed")
                except Exception as e:
                    print(f"Error closing client {client_id}: {e}")
                del self.clients[client_id]

        if server_name:
            client_to_close = self.stateless_clients.get(server_name)
            if client_to_close:
                try:
                    await client_to_close.close()
                    print(f"Server {server_name} closed and removed")
                except Exception as e:
                    print(f"Error closing server {server_name}: {e}")
                del self.stateless_clients[server_name]

    def close_client(self, client_id: str = None, server_name: str = None):
        """Synchronous wrapper for the async close_client method"""
        future = asyncio.run_coroutine_threadsafe(
            self.close_client_async(client_id, server_name), self.loop
        )
        try:
            future.result()
        except Exception as e:
            print(f"Error closing clients: {e}")

    def close_all_clients(self):
        """Close all clients."""
        futures = []
        # Close stateful clients
        for client_id in list(self.clients.keys()):
            future = asyncio.run_coroutine_threadsafe(
                self.close_client_async(client_id = client_id), self.loop
            )
            futures.append(future)

        # Close stateless clients
        for server_name in list(self.stateless_clients.keys()):
            future = asyncio.run_coroutine_threadsafe(
                self.close_client_async(server_name = server_name), self.loop
            )
            futures.append(future)

        for future in futures:
            try:
                future.result()
            except Exception as e:
                print(f"Error closing client: {e}")

    def load_scenario(
        self, client_id: str, scenario: dict | None = None, check: bool = False
    ):
        """Synchronous wrapper for the async call_tool method"""
        client, status = self.get_client(client_id)
        if not status and scenario:
            tool_args = {"scenario": scenario}
            future = asyncio.run_coroutine_threadsafe(
                self._call_tool_async("load_scenario", tool_args, client, client_id),
                self.loop,
            )
            try:
                result = future.result()
                if (
                    check
                ):  # TODO: we need to handle the case where the scenario fails to load
                    saved_scenario = self.call_tool(
                        client_id=client_id,
                        tool_name="save_scenario",
                        tool_args={},
                    )
                    try:
                        scenario_normalized = json.loads(json.dumps(scenario))
                        if scenario_normalized == json.loads(saved_scenario):
                            self.set_status(client_id)
                            print(f"Load scenario succeeded with checking: {result}")
                        else:
                            print(f"scenario: {json.dumps(scenario, indent=2, ensure_ascii=False)}")
                            print(f"saved_scenario: {json.dumps(json.loads(saved_scenario), indent=2, ensure_ascii=False)}")
                            print(
                                f"Load scenario failed. The loaded scenario mismatch with saved scenario."
                            )
                    except Exception as e:
                        print(
                            f"Load scenario failed. Error during comparison: {e}"
                        )
                else:
                    self.set_status(client_id)
                    print(f"Load scenario succeeded without checking: {result}")
                return result
            except Exception as e:
                print(f"Load scenario failed: {e}")
                raise e
        return "This client is already initialized. Skipping..."

    def call_tool(self, tool_name: str, tool_args: dict | str, client_id: str):
        """Synchronous wrapper for the async call_tool method"""
        assert self.is_valid_client_id(
            client_id
        ), "The client_id should follow pattern {mcp_server}-{request_id} or {mcp_server}-{request_id}_test_{test_case_id}!"

        if "load_scenario" in tool_name:
            # Parse tool_args if it's a JSON string (from execute_mcp_tool wrapper)
            if isinstance(tool_args, str):
                try:
                    parsed_args = json.loads(tool_args)
                    if isinstance(parsed_args, dict) and "scenario" in parsed_args:
                        scenario = parsed_args["scenario"]
                    elif isinstance(parsed_args, dict):
                        scenario = parsed_args
                    else:
                        scenario = parsed_args
                except json.JSONDecodeError as e:
                    return f"{tool_name} fail: Invalid JSON in tool_args - {str(e)}"
            elif isinstance(tool_args, dict):
                scenario = tool_args.get("scenario", tool_args)

            return self.load_scenario(client_id=client_id, scenario=scenario)

        client, status = self.get_client(client_id)
        future = asyncio.run_coroutine_threadsafe(
            self._call_tool_async(tool_name, tool_args, client, client_id), self.loop
        )
        try:
            result = future.result()
            print(f"{tool_name} execute: {result}")
            return result
        except ToolError as e:
            print(f"{tool_name} fail before execution: {e}")
            return f"{tool_name} fail before execution: {e}"
        except Exception as e:
            print(f"{tool_name} raise an unexpected error: {e}")
            return f"{tool_name} raise an unexpected error: {e}"

    async def _call_tool_async(
        self, tool_name: str, tool_args: dict | str, client: Client, client_id: str
    ) -> str:
        assert self.is_valid_client_id(
            client_id
        ), "The client_id should follow pattern {mcp_server}-{request_id} or {mcp_server}-{request_id}_test_{test_case_id}!"

        tool_name = tool_name.split("-", 1)[-1]
        async with client:
            if isinstance(tool_args, str):
                tool_args = json.loads(tool_args)
            result = await client.call_tool(tool_name, tool_args)
        print('result:', result)
        
        all_texts = [item.text for item in result.content if hasattr(item, 'text')]
        tool_result = ','.join(all_texts) if all_texts else ''
        
        self.add_log(
            client_id=client_id,
            info={
                "tool": {
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "tool_result": tool_result,
                }
            },
        )

        return tool_result

    def save_all_scenario(self, client_id_list) -> dict:
        saved_all_scenario = {}
        for client_id in client_id_list:
            tool_class = client_id.split("-")[0]
            try:
                saved_scenario = self.call_tool(
                    client_id=client_id,
                    tool_name="save_scenario",
                    tool_args={},
                )
                saved_scenario = json.loads(saved_scenario)
            except Exception as e:
                saved_scenario = None
            saved_all_scenario.update({tool_class: saved_scenario})
        return saved_all_scenario

    def shutdown(self, timeout=5):
        """Cleanup and shutdown the manager"""
        # Close all clients
        self.close_all_clients()

        # Stop the event loop
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.loop_thread.join(timeout=timeout)

        # Handle case where thread doesn't join within timeout
        if self.loop_thread.is_alive():
            print(f"Warning: Event loop thread did not terminate within {timeout} seconds")

    def __del__(self):
        self.shutdown()


MCPManager = MCPClientManager()
if not os.environ.get("SKIP_MCP_AUTO_INIT"):
    MCPManager.init_config("configs/mcp_server.json")
