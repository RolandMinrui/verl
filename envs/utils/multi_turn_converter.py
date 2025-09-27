"""Enhanced multi-turn conversation converter using MCPClientManager.

This module converts BFCL multi-turn data into single-turn records while
replaying the ground-truth tool trajectories via the MCP client manager.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import ast
import pandas as pd

from tools.mcp_managers.client_manager import MCPClientManager


class EnhancedMultiTurnConverter:
    """Convert multi-turn BFCL data with real tool execution."""

    def __init__(self, config_path: Path) -> None:
        self.class_map: Dict[str, str] = {
            "GorillaFileSystem": "file_system",
            "TwitterAPI": "posting",
            "TicketAPI": "ticket",
            "TravelAPI": "travel",
            "TradingBot": "trading",
            "VehicleControlAPI": "vehicle",
            "MathAPI": "math",
            "MessageAPI": "message",
        }

        self.function_mapping = {
            "ls": "file_system-ls",
            "pwd": "file_system-pwd",
            "cd": "file_system-cd",
            "mkdir": "file_system-mkdir",
            "touch": "file_system-touch",
            "echo": "file_system-echo",
            "cat": "file_system-cat",
            "rm": "file_system-rm",
            "mv": "file_system-mv",
            "cp": "file_system-cp",
            "find": "file_system-find",
            "grep": "file_system-grep",
            "tail": "file_system-tail",
            "diff": "file_system-diff",
            "wc": "file_system-wc",
            "sort": "file_system-sort",
            "du": "file_system-du",
            "rmdir": "file_system-rmdir",
            "load_scenario": "file_system-load_scenario",
            "save_scenario": "file_system-save_scenario",
            "logarithm": "math-logarithm",
            "mean": "math-mean",
            "standard_deviation": "math-standard_deviation",
            "si_unit_conversion": "math-si_unit_conversion",
            "imperial_si_conversion": "math-imperial_si_conversion",
            "add": "math-add",
            "subtract": "math-subtract",
            "multiply": "math-multiply",
            "divide": "math-divide",
            "power": "math-power",
            "square_root": "math-square_root",
            "absolute_value": "math-absolute_value",
            "round_number": "math-round_number",
            "percentage": "math-percentage",
            "min_value": "math-min_value",
            "max_value": "math-max_value",
            "sum_values": "math-sum_values",
            "authenticate_twitter": "posting-authenticate_twitter",
            "posting_get_login_status": "posting-posting_get_login_status",
            "post_tweet": "posting-post_tweet",
            "retweet": "posting-retweet",
            "comment": "posting-comment",
            "mention": "posting-mention",
            "follow_user": "posting-follow_user",
            "list_all_following": "posting-list_all_following",
            "unfollow_user": "posting-unfollow_user",
            "get_tweet": "posting-get_tweet",
            "get_user_tweets": "posting-get_user_tweets",
            "search_tweets": "posting-search_tweets",
            "get_tweet_comments": "posting-get_tweet_comments",
            "get_user_stats": "posting-get_user_stats",
            "create_ticket": "ticket-create_ticket",
            "get_ticket": "ticket-get_ticket",
            "close_ticket": "ticket-close_ticket",
            "resolve_ticket": "ticket-resolve_ticket",
            "edit_ticket": "ticket-edit_ticket",
            "ticket_login": "ticket-ticket_login",
            "ticket_get_login_status": "ticket-ticket_get_login_status",
            "logout": "ticket-logout",
            "get_user_tickets": "ticket-get_user_tickets",
            "get_current_time": "trading-get_current_time",
            "update_market_status": "trading-update_market_status",
            "get_symbol_by_name": "trading-get_symbol_by_name",
            "get_stock_info": "trading-get_stock_info",
            "get_order_details": "trading-get_order_details",
            "cancel_order": "trading-cancel_order",
            "place_order": "trading-place_order",
            "make_transaction": "trading-make_transaction",
            "get_account_info": "trading-get_account_info",
            "trading_login": "trading-trading_login",
            "trading_get_login_status": "trading-trading_get_login_status",
            "trading_logout": "trading-trading_logout",
            "fund_account": "trading-fund_account",
            "remove_stock_from_watchlist": "trading-remove_stock_from_watchlist",
            "get_watchlist": "trading-get_watchlist",
            "get_order_history": "trading-get_order_history",
            "get_transaction_history": "trading-get_transaction_history",
            "update_stock_price": "trading-update_stock_price",
            "get_available_stocks": "trading-get_available_stocks",
            "filter_stocks_by_price": "trading-filter_stocks_by_price",
            "add_to_watchlist": "trading-add_to_watchlist",
            "notify_price_change": "trading-notify_price_change",
            "authenticate_travel": "travel-authenticate_travel",
            "travel_get_login_status": "travel-travel_get_login_status",
            "get_budget_fiscal_year": "travel-get_budget_fiscal_year",
            "register_credit_card": "travel-register_credit_card",
            "get_flight_cost": "travel-get_flight_cost",
            "get_credit_card_balance": "travel-get_credit_card_balance",
            "book_flight": "travel-book_flight",
            "retrieve_invoice": "travel-retrieve_invoice",
            "list_all_airports": "travel-list_all_airports",
            "cancel_booking": "travel-cancel_booking",
            "compute_exchange_rate": "travel-compute_exchange_rate",
            "verify_traveler_information": "travel-verify_traveler_information",
            "set_budget_limit": "travel-set_budget_limit",
            "get_nearest_airport_by_city": "travel-get_nearest_airport_by_city",
            "purchase_insurance": "travel-purchase_insurance",
            "contact_customer_support": "travel-contact_customer_support",
            "get_all_credit_cards": "travel-get_all_credit_cards",
            "startEngine": "vehicle-startEngine",
            "fillFuelTank": "vehicle-fillFuelTank",
            "lockDoors": "vehicle-lockDoors",
            "adjustClimateControl": "vehicle-adjustClimateControl",
            "get_outside_temperature_from_google": "vehicle-get_outside_temperature_from_google",
            "get_outside_temperature_from_weather_com": "vehicle-get_outside_temperature_from_weather_com",
            "setHeadlights": "vehicle-setHeadlights",
            "displayCarStatus": "vehicle-displayCarStatus",
            "activateParkingBrake": "vehicle-activateParkingBrake",
            "pressBrakePedal": "vehicle-pressBrakePedal",
            "releaseBrakePedal": "vehicle-releaseBrakePedal",
            "setCruiseControl": "vehicle-setCruiseControl",
            "get_current_speed": "vehicle-get_current_speed",
            "estimate_drive_feasibility_by_mileage": "vehicle-estimate_drive_feasibility_by_mileage",
            "liter_to_gallon": "vehicle-liter_to_gallon",
            "gallon_to_liter": "vehicle-gallon_to_liter",
            "estimate_distance": "vehicle-estimate_distance",
            "get_zipcode_based_on_city": "vehicle-get_zipcode_based_on_city",
            "set_navigation": "vehicle-set_navigation",
            "check_tire_pressure": "vehicle-check_tire_pressure",
            "find_nearest_tire_shop": "vehicle-find_nearest_tire_shop",
            "list_users": "message-list_users",
            "get_user_id": "message-get_user_id",
            "message_login": "message-message_login",
            "message_get_login_status": "message-message_get_login_status",
            "send_message": "message-send_message",
            "delete_message": "message-delete_message",
            "view_messages_sent": "message-view_messages_sent",
            "add_contact": "message-add_contact",
            "search_messages": "message-search_messages",
            "get_message_stats": "message-get_message_stats",
        }

        self.param_mapping: Dict[str, Dict[str, str]] = {
            "ls": {"show_hidden": "show_hidden"},
            "cd": {"folder": "folder"},
            "mkdir": {"dir_name": "dir_name"},
            "touch": {"file_name": "file_name"},
            "echo": {"content": "content", "file_name": "file_name"},
            "cat": {"file_name": "file_name"},
            "rm": {"file_name": "file_name"},
            "mv": {"source": "source", "destination": "destination"},
            "cp": {"source": "source", "destination": "destination"},
            "find": {"path": "path", "name": "name"},
            "grep": {"file_name": "file_name", "pattern": "pattern"},
            "tail": {"file_name": "file_name", "lines": "lines"},
            "diff": {"file_name1": "file_name1", "file_name2": "file_name2"},
            "wc": {"file_name": "file_name", "mode": "mode"},
            "sort": {"file_name": "file_name"},
            "du": {"human_readable": "human_readable"},
            "rmdir": {"dir_name": "dir_name"},
            "load_scenario": {"scenario": "scenario", "long_context": "long_context"},
            "save_scenario": {},
            "logarithm": {"value": "value", "base": "base", "precision": "precision"},
            "mean": {"numbers": "numbers"},
            "standard_deviation": {"numbers": "numbers"},
            "si_unit_conversion": {"value": "value", "unit_in": "unit_in", "unit_out": "unit_out"},
            "imperial_si_conversion": {"value": "value", "unit_in": "unit_in", "unit_out": "unit_out"},
            "add": {"a": "a", "b": "b"},
            "subtract": {"a": "a", "b": "b"},
            "multiply": {"a": "a", "b": "b"},
            "divide": {"a": "a", "b": "b"},
            "power": {"base": "base", "exponent": "exponent"},
            "square_root": {"number": "number", "precision": "precision"},
            "absolute_value": {"number": "number"},
            "round_number": {"number": "number", "decimal_places": "decimal_places"},
            "percentage": {"part": "part", "whole": "whole"},
            "min_value": {"numbers": "numbers"},
            "max_value": {"numbers": "numbers"},
            "sum_values": {"numbers": "numbers"},
            "authenticate_twitter": {"username": "username", "password": "password"},
            "posting_get_login_status": {},
            "post_tweet": {"content": "content", "tags": "tags", "mentions": "mentions"},
            "retweet": {"tweet_id": "tweet_id"},
            "comment": {"tweet_id": "tweet_id", "comment_content": "comment_content"},
            "mention": {"tweet_id": "tweet_id", "mentioned_usernames": "mentioned_usernames"},
            "follow_user": {"username_to_follow": "username_to_follow"},
            "list_all_following": {},
            "unfollow_user": {"username_to_unfollow": "username_to_unfollow"},
            "get_tweet": {"tweet_id": "tweet_id"},
            "get_user_tweets": {"username": "username"},
            "search_tweets": {"keyword": "keyword"},
            "get_tweet_comments": {"tweet_id": "tweet_id"},
            "get_user_stats": {"username": "username"},
            "create_ticket": {"title": "title", "description": "description", "priority": "priority"},
            "get_ticket": {"ticket_id": "ticket_id"},
            "close_ticket": {"ticket_id": "ticket_id"},
            "resolve_ticket": {"ticket_id": "ticket_id", "resolution": "resolution"},
            "edit_ticket": {
                "ticket_id": "ticket_id",
                "title": "title",
                "description": "description",
                "status": "status",
                "priority": "priority",
            },
            "ticket_login": {"username": "username", "password": "password"},
            "ticket_get_login_status": {},
            "logout": {},
            "get_user_tickets": {"status": "status"},
            "get_current_time": {},
            "update_market_status": {"current_time_str": "current_time_str"},
            "get_symbol_by_name": {"name": "name"},
            "get_stock_info": {"symbol": "symbol"},
            "get_order_details": {"order_id": "order_id"},
            "cancel_order": {"order_id": "order_id"},
            "place_order": {"order_type": "order_type", "symbol": "symbol", "price": "price", "amount": "amount"},
            "make_transaction": {"account_id": "account_id", "xact_type": "xact_type", "amount": "amount"},
            "get_account_info": {},
            "trading_login": {"username": "username", "password": "password"},
            "trading_get_login_status": {},
            "trading_logout": {},
            "fund_account": {"amount": "amount"},
            "remove_stock_from_watchlist": {"symbol": "symbol"},
            "get_watchlist": {},
            "get_order_history": {},
            "get_transaction_history": {"start_date": "start_date", "end_date": "end_date"},
            "update_stock_price": {"symbol": "symbol", "new_price": "new_price"},
            "get_available_stocks": {"sector": "sector"},
            "filter_stocks_by_price": {"stocks": "stocks", "min_price": "min_price", "max_price": "max_price"},
            "add_to_watchlist": {"stock": "stock"},
            "notify_price_change": {"stocks": "stocks", "threshold": "threshold"},
            "authenticate_travel": {
                "client_id": "client_id",
                "client_secret": "client_secret",
                "refresh_token": "refresh_token",
                "grant_type": "grant_type",
                "user_first_name": "user_first_name",
                "user_last_name": "user_last_name",
            },
            "travel_get_login_status": {},
            "get_budget_fiscal_year": {"lastModifiedAfter": "lastModifiedAfter", "includeRemoved": "includeRemoved"},
            "register_credit_card": {
                "access_token": "access_token",
                "card_number": "card_number",
                "expiration_date": "expiration_date",
                "cardholder_name": "cardholder_name",
                "card_verification_number": "card_verification_number",
            },
            "get_flight_cost": {
                "travel_from": "travel_from",
                "travel_to": "travel_to",
                "travel_date": "travel_date",
                "travel_class": "travel_class",
            },
            "get_credit_card_balance": {"access_token": "access_token", "card_id": "card_id"},
            "book_flight": {
                "access_token": "access_token",
                "card_id": "card_id",
                "travel_date": "travel_date",
                "travel_from": "travel_from",
                "travel_to": "travel_to",
                "travel_class": "travel_class",
            },
            "retrieve_invoice": {"access_token": "access_token", "booking_id": "booking_id", "insurance_id": "insurance_id"},
            "list_all_airports": {},
            "cancel_booking": {"access_token": "access_token", "booking_id": "booking_id"},
            "compute_exchange_rate": {
                "base_currency": "base_currency",
                "target_currency": "target_currency",
                "value": "value",
            },
            "verify_traveler_information": {
                "first_name": "first_name",
                "last_name": "last_name",
                "date_of_birth": "date_of_birth",
                "passport_number": "passport_number",
            },
            "set_budget_limit": {"access_token": "access_token", "budget_limit": "budget_limit"},
            "get_nearest_airport_by_city": {"location": "location"},
            "purchase_insurance": {
                "access_token": "access_token",
                "insurance_type": "insurance_type",
                "booking_id": "booking_id",
                "insurance_cost": "insurance_cost",
                "card_id": "card_id",
            },
            "contact_customer_support": {"booking_id": "booking_id", "message": "message"},
            "get_all_credit_cards": {},
            "startEngine": {"ignitionMode": "ignitionMode"},
            "fillFuelTank": {"fuelAmount": "fuelAmount"},
            "lockDoors": {"unlock": "unlock", "door": "door"},
            "adjustClimateControl": {"temperature": "temperature", "unit": "unit", "fanSpeed": "fanSpeed", "mode": "mode"},
            "get_outside_temperature_from_google": {},
            "get_outside_temperature_from_weather_com": {},
            "setHeadlights": {"mode": "mode"},
            "displayCarStatus": {"option": "option"},
            "activateParkingBrake": {"mode": "mode"},
            "pressBrakePedal": {"pedalPosition": "pedalPosition"},
            "releaseBrakePedal": {},
            "setCruiseControl": {"speed": "speed", "activate": "activate", "distanceToNextVehicle": "distanceToNextVehicle"},
            "get_current_speed": {},
            "estimate_drive_feasibility_by_mileage": {"distance": "distance"},
            "liter_to_gallon": {"liter": "liter"},
            "gallon_to_liter": {"gallon": "gallon"},
            "estimate_distance": {"cityA": "cityA", "cityB": "cityB"},
            "get_zipcode_based_on_city": {"city": "city"},
            "set_navigation": {"destination": "destination"},
            "check_tire_pressure": {},
            "find_nearest_tire_shop": {},
            "list_users": {},
            "get_user_id": {"user": "user"},
            "message_login": {"user_id": "user_id"},
            "message_get_login_status": {},
            "send_message": {"receiver_id": "receiver_id", "message": "message"},
            "delete_message": {"receiver_id": "receiver_id"},
            "view_messages_sent": {},
            "add_contact": {"user_name": "user_name"},
            "search_messages": {"keyword": "keyword"},
            "get_message_stats": {},
        }

        self.manager: Optional[MCPClientManager] = None
        self.manager_config_path = config_path
        self.client_ids: Dict[str, str] = {}

    def create_client_manager(self) -> MCPClientManager:
        if self.manager is None:
            self.manager = MCPClientManager()
            self.manager.init_config(str(self.manager_config_path))
        return self.manager

    def load_data(self, original_file: Path, golden_answer_file: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        with open(original_file, "r", encoding="utf-8") as f:
            original_data = [json.loads(line) for line in f if line.strip()]

        with open(golden_answer_file, "r", encoding="utf-8") as f:
            golden_data = [json.loads(line) for line in f if line.strip()]

        return original_data, golden_data

    @staticmethod
    def parse_list_string(value: str) -> Any:
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            try:
                import ast

                return ast.literal_eval(value)
            except (ValueError, SyntaxError):
                pass
        return value

    def parse_function_call(self, call_str: str) -> Tuple[str, Dict[str, Any]]:
        call = call_str.strip()
        if "(" not in call or ")" not in call:
            return call, {}

        name = call.split("(", 1)[0].strip()
        args_str = call[call.find("(") + 1 : call.rfind(")")].strip()
        if not args_str:
            return name, {}

        # 用 AST 解析以正确处理转义序列、数字、布尔、列表/字典等
        try:
            expr = ast.parse(f"f({args_str})", mode="eval").body  # type: ignore[attr-defined]
        except SyntaxError as exc:
            raise ValueError(f"Failed to parse arguments for call '{call}': {exc}") from exc

        params: Dict[str, Any] = {}
        for kw in expr.keywords:
            params[kw.arg] = ast.literal_eval(kw.value)

        # 如有位置参数，统一不支持（和验证脚本一致）；需要的话可放入 __args__
        if expr.args:
            params["__args__"] = [ast.literal_eval(a) for a in expr.args]

        return name, params

    def convert_function_call(self, old_call: str) -> Tuple[str, Dict[str, Any]]:
        # 先解析出原始函数名和参数（可能包含 __args__）
        func_name, params = self.parse_function_call(old_call)

        # 计算新的函数名（带前缀）
        new_func_name = self.function_mapping.get(func_name, func_name)
        if new_func_name == func_name and "-" not in new_func_name:
            inferred = self.infer_tool_name(func_name)
            if inferred:
                new_func_name = inferred

        # —— 关键修复：对位置参数做“位置→命名”的映射 ——
        # param_mapping 用的是“基础名”（不含前缀），比如 "sort"、"grep"
        def _pick_param_map() -> Dict[str, str]:
            # 依次尝试：原始名去前缀、新名去前缀、原始名（兼容极少数键）
            base_candidates = [
                func_name.split("-", 1)[-1],
                new_func_name.split("-", 1)[-1],
                func_name,
            ]
            for cand in base_candidates:
                if cand in self.param_mapping:
                    return self.param_mapping[cand]
            return {}

        param_map = _pick_param_map()

        new_params: Dict[str, Any] = {}

        # 1) 先把位置参数（__args__）按 param_map 的参数顺序依次填充
        if "__args__" in params:
            args = params.pop("__args__") or []
            if param_map:
                ordered_keys = list(param_map.keys())
                for i, arg in enumerate(args):
                    if i < len(ordered_keys) and ordered_keys[i] not in new_params:
                        new_params[ordered_keys[i]] = arg
            else:
                # 没有映射表就原样保留，避免信息丢失
                if args:
                    new_params["__args__"] = args

        # 2) 再处理命名参数：根据 param_map 做键名映射
        if param_map:
            for key, value in params.items():
                mapped_key = param_map.get(key, key)
                new_params[mapped_key] = value
        else:
            new_params.update(params)

        return new_func_name, new_params

    def infer_tool_name(self, func_name: str) -> Optional[str]:
        lower = func_name.lower()
        if any(token in lower for token in ["add", "subtract", "multiply", "divide", "power", "sqrt", "abs", "round", "log", "mean", "std"]):
            return f"math-{func_name}"
        if any(token in lower for token in ["tweet", "post", "follow", "unfollow", "retweet", "comment", "mention"]):
            return f"posting-{func_name}"
        if any(token in lower for token in ["ticket", "create_ticket", "close_ticket", "resolve"]):
            return f"ticket-{func_name}"
        if any(token in lower for token in ["order", "trade", "stock", "buy", "sell", "watchlist", "account"]):
            return f"trading-{func_name}"
        if any(token in lower for token in ["flight", "book", "travel", "airport", "credit_card", "budget"]):
            return f"travel-{func_name}"
        if any(token in lower for token in ["engine", "fuel", "door", "brake", "tire", "headlight", "climate"]):
            return f"vehicle-{func_name}"
        if any(token in lower for token in ["message", "send", "delete", "contact", "user"]):
            return f"message-{func_name}"
        return None

    def prepare_scenario_for_loading(self, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        if not scenario_data:
            return {}
        prepared: Dict[str, Any] = {}
        for key, value in scenario_data.items():
            mapped_key = self.class_map.get(key, key)
            prepared[mapped_key] = value
        return prepared

    def _create_client_id(self, class_name: str) -> str:
        return f"{class_name}-{uuid.uuid4().hex}"

    def _load_initial_scenarios(self, scenario_data: Dict[str, Any]) -> List[Tuple[str, bool, str]]:
        manager = self.create_client_manager()
        manager.close_all_clients()
        self.client_ids = {}

        prepared_scenario = self.prepare_scenario_for_loading(scenario_data)
        load_results: List[Tuple[str, bool, str]] = []

        for class_name in [
            "file_system",
            "math",
            "posting",
            "ticket",
            "trading",
            "travel",
            "vehicle",
            "message",
        ]:
            if class_name not in prepared_scenario:
                continue

            scenario = prepared_scenario[class_name]
            if class_name == "math":
                self.client_ids[class_name] = self._create_client_id(class_name)
                load_results.append((class_name, True, "math tools ready"))
                continue

            client_id = self._create_client_id(class_name)
            try:
                manager.load_scenario(client_id=client_id, scenario=scenario, check=False)
                self.client_ids[class_name] = client_id
                load_results.append((class_name, True, "loaded"))
            except Exception as exc:  # pylint: disable=broad-except
                load_results.append((class_name, False, str(exc)))

        return load_results

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        tool_prefix = tool_name.split("-", 1)[0]
        client_id = self.client_ids.get(tool_prefix)
        if client_id is None:
            return {"success": False, "error": f"Client for {tool_prefix} not initialized"}

        try:
            raw_result = self.manager.call_tool(tool_name=tool_name, tool_args=args, client_id=client_id)  # type: ignore[union-attr]
            if raw_result is None:
                return {"success": False, "error": "Tool call returned no result"}
            parsed_result: Any
            try:
                parsed_result = json.loads(raw_result)
            except (TypeError, json.JSONDecodeError):
                parsed_result = raw_result
            return {"success": True, "result": parsed_result, "raw_result": raw_result}
        except Exception as exc:  # pylint: disable=broad-except
            return {"success": False, "error": str(exc)}

    def save_all_scenarios(self) -> Optional[Dict[str, Any]]:
        if not self.client_ids or self.manager is None:
            return None

        saved: Dict[str, Any] = {}
        for class_name, client_id in self.client_ids.items():
            if class_name == "math":
                continue

            try:
                raw = self.manager.call_tool(tool_name="save_scenario", tool_args={}, client_id=client_id)  # type: ignore[union-attr]
                try:
                    saved[class_name] = json.loads(raw)
                except json.JSONDecodeError:
                    saved[class_name] = raw
            except Exception as exc:  # pylint: disable=broad-except
                saved[class_name] = {"error": str(exc)}

        return saved

    def extract_scenario_from_save_result(self, save_result: Any) -> Any:
        return save_result

    def simulate_multi_turn_execution(
        self, scenario_data: Dict[str, Any], golden_answers: List[List[str]]
    ) -> List[Dict[str, Any]]:
        load_results = self._load_initial_scenarios(scenario_data)
        successful = [result for result in load_results if result[1]]
        if not successful:
            return []

        execution_history: List[Dict[str, Any]] = []

        for turn_idx, turn_actions in enumerate(golden_answers):
            scenario_before = self.save_all_scenarios()
            turn_history: Dict[str, Any] = {
                "turn_index": turn_idx,
                "actions": [],
                "scenario_before": scenario_before,
                "scenario_after": None,
            }

            for action_str in turn_actions:
                new_func_name, new_params = self.convert_function_call(action_str)
                result = self.execute_tool(new_func_name, new_params)
                turn_history["actions"].append(
                    {
                        "original_call": action_str,
                        "converted_call": f"{new_func_name}({new_params})",
                        "function_name": new_func_name,
                        "parameters": new_params,
                        "execution_result": result,
                        "success": result.get("success", False),
                    }
                )

            turn_history["scenario_after"] = self.save_all_scenarios()
            execution_history.append(turn_history)

        if self.manager is not None:
            self.manager.close_all_clients()
        self.client_ids = {}
        return execution_history

    def generate_conversation_history(
        self, questions: List[List[Dict[str, Any]]], execution_history: List[Dict[str, Any]], current_turn: int
    ) -> List[Dict[str, Any]]:
        conversation: List[Dict[str, Any]] = []
        for turn_idx in range(current_turn):
            if turn_idx < len(questions):
                for msg in questions[turn_idx]:
                    if msg.get("role") == "user":
                        conversation.append({"role": "user", "content": msg["content"]})

            if turn_idx < len(execution_history):
                turn_data = execution_history[turn_idx]
                for action in turn_data.get("actions", []):
                    func_name = action.get("function_name", "")
                    params = action.get("parameters", {})
                    tool_call = {
                        "role": "assistant",
                        "content": f'<tool_call>{{"name": "{func_name}", "arguments": {json.dumps(params, ensure_ascii=False)}}}</tool_call>',
                    }
                    conversation.append(tool_call)

                    result = action.get("execution_result", {})
                    if result.get("success"):
                        raw_result = result.get("raw_result")
                        result_text = raw_result if isinstance(raw_result, str) else json.dumps(result.get("result"), ensure_ascii=False)
                        if isinstance(result_text, str) and len(result_text) > 500:
                            result_text = result_text[:500] + "..."
                        conversation.append({"role": "tool", "content": result_text})
                    else:
                        conversation.append({"role": "tool", "content": f'Error: {result.get("error", "Unknown error")}'})

        return conversation

    def map_involved_classes(self, involved_classes: List[str]) -> List[str]:
        return [self.class_map.get(cls, cls) for cls in involved_classes]

    def map_initial_config_classes(self, initial_config: Dict[str, Any]) -> Dict[str, Any]:
        mapped: Dict[str, Any] = {}
        for key, value in initial_config.items():
            mapped[self.class_map.get(key, key)] = value
        return mapped

    def convert_golden_answers(self, golden_answers: List[str]) -> List[str]:
        converted: List[str] = []
        for call in golden_answers:
            new_func_name, new_params = self.convert_function_call(call)
            if new_params:
                param_parts = []
                for key, value in new_params.items():
                    if isinstance(value, str):
                        param_parts.append(f"{key}='{value}'")
                    else:
                        param_parts.append(f"{key}={value}")
                converted_call = f"{new_func_name}({', '.join(param_parts)})"
            else:
                converted_call = f"{new_func_name}()"
            converted.append(converted_call)
        return converted

    def split_train_test(self, data: List[Dict[str, Any]], test_nums: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if test_nums >= len(data):
            return [], data
        if test_nums <= 0:
            return data, []
        return data[:-test_nums], data[-test_nums:]

    def convert_to_enhanced_single_turn(
        self,
        original_data: List[Dict[str, Any]],
        golden_data: List[Dict[str, Any]],
        split_type: str,
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        golden_map = {item["id"]: item for item in golden_data}

        for idx, original_item in enumerate(original_data):
            item_id = original_item["id"]
            questions = original_item.get("question", [])
            initial_config = original_item.get("initial_config", {})
            involved_classes = original_item.get("involved_classes", [])

            golden_item = golden_map.get(item_id)
            if not golden_item:
                continue

            golden_answers = golden_item.get("ground_truth", [])
            execution_history = self.simulate_multi_turn_execution(initial_config, golden_answers) if initial_config else []

            for turn_idx, turn_questions in enumerate(questions):
                for q_idx, question_msg in enumerate(turn_questions):
                    if question_msg.get("role") != "user":
                        continue

                    conversation_history = self.generate_conversation_history(questions, execution_history, turn_idx)
                    prompt_content = conversation_history + [{"content": question_msg["content"], "role": "user"}] if conversation_history else [{"content": question_msg["content"], "role": "user"}]

                    current_golden = golden_answers[turn_idx] if turn_idx < len(golden_answers) else []
                    current_golden = self.convert_golden_answers(current_golden)

                    current_scenario = execution_history[turn_idx]["scenario_before"] if turn_idx < len(execution_history) and execution_history[turn_idx].get("scenario_before") else initial_config
                    mapped_initial_config = self.map_initial_config_classes(current_scenario)

                    if turn_idx < len(execution_history) and execution_history[turn_idx].get("scenario_after"):
                        final_config = execution_history[turn_idx]["scenario_after"]
                    elif turn_idx < len(execution_history) and execution_history[turn_idx].get("scenario_before"):
                        final_config = execution_history[turn_idx]["scenario_before"]
                    else:
                        final_config = initial_config

                    mapped_final_config = self.map_initial_config_classes(final_config)

                    single_turn_item = {
                        "id": f"{item_id}_turn_{turn_idx}_{q_idx}",
                        "question": question_msg["content"],
                        "golden_answers": current_golden,
                        "data_source": "BFCL_multi_turn_base",
                        "prompt": prompt_content,
                        "agent_name": "tool_agent",
                        "ability": "tool_use",
                        "reward_model": {
                            "ground_truth": json.dumps(current_golden, ensure_ascii=False),
                            "style": "rule",
                        },
                        "extra_info": {
                            "index": len(result),
                            "split": split_type,
                            "involved_class": self.map_involved_classes(involved_classes),
                            "initial_config": mapped_initial_config,
                            "final_config": mapped_final_config,
                        },
                    }

                    result.append(single_turn_item)

        return result

    @staticmethod
    def save_to_json(data: List[Dict[str, Any]], output_file: Path) -> None:
        with open(output_file, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    @staticmethod
    def save_to_csv(data: List[Dict[str, Any]], output_file: Path) -> None:
        if not data:
            return

        fieldnames = [
            "id",
            "question",
            "golden_answers",
            "data_source",
            "prompt",
            "ability",
            "reward_model",
            "extra_info",
            "agent_name",
        ]

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in data:
                writer.writerow({
                    "id": item["id"],
                    "question": item["question"],
                    "golden_answers": item["golden_answers"],
                    "data_source": item["data_source"],
                    "prompt": item["prompt"],
                    "ability": item["ability"],
                    "reward_model": item["reward_model"],
                    "extra_info": item["extra_info"],
                    "agent_name": item["agent_name"],
                })

    def save_to_parquet(self, data: List[Dict[str, Any]], output_file: Path) -> None:
        if not data:
            return

        df_rows: List[Dict[str, Any]] = []
        for item in data:
            df_rows.append(
                {
                    "id": item["id"],
                    "question": item["question"],
                    "golden_answers": json.dumps(item["golden_answers"], ensure_ascii=False),
                    "data_source": item["data_source"],
                    "agent_name": item["agent_name"],
                    "prompt": json.dumps(item["prompt"], ensure_ascii=False),
                    "ability": item["ability"],
                    "reward_model": json.dumps(item["reward_model"], ensure_ascii=False),
                    "extra_info": json.dumps(item["extra_info"], ensure_ascii=False),
                }
            )

        df = pd.DataFrame(df_rows)
        df.to_parquet(output_file, index=False)

    def save_to_parquet_with_native_types(self, data: List[Dict[str, Any]], output_file: Path) -> None:
        if not data:
            return

        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            self.save_to_parquet(data, output_file)
            return

        cleaned_data: List[Dict[str, Any]] = []
        for item in data:
            cleaned = dict(item)
            golden_answers = cleaned.get("golden_answers")
            if not golden_answers:
                cleaned["golden_answers"] = [""]

            prompt = cleaned.get("prompt")
            if not prompt:
                cleaned["prompt"] = [{"content": "", "role": "user"}]

            reward_model = cleaned.get("reward_model")
            if not isinstance(reward_model, dict):
                cleaned["reward_model"] = {"ground_truth": "", "style": "rule"}

            extra_info = cleaned.get("extra_info", {})
            if not isinstance(extra_info, dict):
                cleaned["extra_info"] = {
                    "index": 0,
                    "split": "unknown",
                    "involved_class": [],
                    "initial_config": "{}",
                    "final_config": "{}",
                }
            else:
                initial_config = extra_info.get("initial_config", {})
                final_config = extra_info.get("final_config", {})
                cleaned["extra_info"] = {
                    "index": extra_info.get("index", 0),
                    "split": extra_info.get("split", "unknown"),
                    "involved_class": extra_info.get("involved_class", []),
                    "initial_config": json.dumps(initial_config, ensure_ascii=False) if isinstance(initial_config, dict) else str(initial_config),
                    "final_config": json.dumps(final_config, ensure_ascii=False) if isinstance(final_config, dict) else str(final_config),
                }

            cleaned_data.append(cleaned)

        df = pd.DataFrame(cleaned_data)
        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, output_file)

    def save_train_test_separately(
        self, train_data: List[Dict[str, Any]], test_data: List[Dict[str, Any]], output_dir: Path
    ) -> None:
        if train_data:
            self.save_to_parquet_with_native_types(train_data, output_dir / "train.parquet")
        if test_data:
            self.save_to_parquet_with_native_types(test_data, output_dir / "test.parquet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enhanced multi-turn converter with MCP execution")
    parser.add_argument("--config", type=Path, default=Path("tools/mcp_configs/bfcl_mcp_server.json"))
    parser.add_argument("--original-file", type=Path, default=Path("data/BFCL/multi-turn-original/BFCL_v3_multi_turn_base.json"))
    parser.add_argument("--golden-file", type=Path, default=Path("data/BFCL/possible_answer/BFCL_v3_multi_turn_base.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/BFCL/multi-turn-test"))
    parser.add_argument("--num-items", type=int, default=200)
    parser.add_argument("--test-nums", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    converter = EnhancedMultiTurnConverter(args.config)
    original_data, golden_data = converter.load_data(args.original_file, args.golden_file)

    original_subset = original_data[: args.num_items]
    train_data, test_data = converter.split_train_test(original_subset, args.test_nums)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    train_single_turn: List[Dict[str, Any]] = []
    test_single_turn: List[Dict[str, Any]] = []

    if train_data:
        train_single_turn = converter.convert_to_enhanced_single_turn(train_data, golden_data, "train")

    if test_data:
        test_single_turn = converter.convert_to_enhanced_single_turn(test_data, golden_data, "test")

    all_data = train_single_turn + test_single_turn

    if all_data:
        converter.save_to_json(all_data, output_dir / "enhanced_single_turn_data.json")
        converter.save_to_csv(all_data, output_dir / "enhanced_single_turn_data.csv")

    converter.save_train_test_separately(train_single_turn, test_single_turn, output_dir)


if __name__ == "__main__":
    main()