"""Validate dataset scenarios by replaying tool trajectories with MCP clients."""

from __future__ import annotations
import traceback
import argparse
import ast
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import numpy as np
import pandas as pd

from tools.mcp_managers.client_manager import MCPClientManager


def parse_tool_call(call: str) -> Tuple[str, Dict[str, Any]]:
    call = call.strip()
    if "(" not in call:
        return call, {}

    name, rest = call.split("(", 1)
    args_str = rest.rsplit(")", 1)[0].strip()
    if not args_str:
        return name, {}

    try:
        expr = ast.parse(f"f({args_str})", mode="eval").body  # type: ignore[attr-defined]
    except SyntaxError as exc:  # pragma: no cover - defensive logging
        raise ValueError(f"Failed to parse arguments for call '{call}': {exc}") from exc

    kwargs: Dict[str, Any] = {}
    for keyword in expr.keywords:
        kwargs[keyword.arg] = ast.literal_eval(keyword.value)

    if expr.args:
        positional_values = [ast.literal_eval(arg) for arg in expr.args]
        kwargs["__args__"] = positional_values

    return name, kwargs


def load_dataframe(dataset_path: Path) -> pd.DataFrame:
    try:
        return pd.read_parquet(dataset_path)
    except Exception as exc:  # pragma: no cover - propagate informative error
        raise RuntimeError(f"Failed to read parquet dataset at {dataset_path}: {exc}") from exc


def ensure_iterable_strings(values: Any) -> Iterable[str]:
    if isinstance(values, np.ndarray):
        return [str(item) for item in values.tolist()]
    if isinstance(values, list):
        return [str(item) for item in values]
    if isinstance(values, tuple):
        return [str(item) for item in values]
    return [str(values)]


def parse_config(value: Any) -> Dict[str, Any]:
    if value in (None, "", {}):
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    raise TypeError(f"Unsupported config type: {type(value)!r}")


def create_client_mapping(manager: MCPClientManager, initial_config: Dict[str, Any]) -> Dict[str, str]:
    client_ids: Dict[str, str] = {}
    for class_name, scenario in initial_config.items():
        client_id = f"{class_name}-{uuid.uuid4().hex}"
        client_ids[class_name] = client_id
        if class_name == "math":
            continue
        manager.load_scenario(client_id=client_id, scenario=scenario, check=False)
    return client_ids


# def execute_tool_sequence(
#     manager: MCPClientManager, client_ids: Dict[str, str], calls: Iterable[str]
# ) -> None:
#     for call in calls:
#         tool_name, params = parse_tool_call(call)
#         tool_prefix = tool_name.split("-", 1)[0]
#         client_id = client_ids.get(tool_prefix)
#         if client_id is None:
#             raise RuntimeError(f"Client for class '{tool_prefix}' is not initialized")

#         if "__args__" in params:
#             positional = params.pop("__args__")
#             if positional:
#                 raise ValueError(
#                     f"Positional arguments are not supported for tool call '{call}'"
#                 )

#         manager.call_tool(tool_name=tool_name, tool_args=params, client_id=client_id)
def execute_tool_sequence(manager: MCPClientManager, client_ids: Dict[str, str], calls: Iterable[str]) -> None:
    for call in calls:
        tool_name, params = parse_tool_call(call)
        tool_prefix = tool_name.split("-", 1)[0]
        client_id = client_ids.get(tool_prefix)
        if client_id is None:
            raise RuntimeError(f"Client for class '{tool_prefix}' is not initialized")

        if "__args__" in params:
            positional = params.pop("__args__")
            if positional:
                raise ValueError(f"Positional arguments are not supported for tool call '{call}'")

        raw = manager.call_tool(tool_name=tool_name, tool_args=params, client_id=client_id)
        if raw is None:
            raise RuntimeError(f"{tool_name} returned no result")

        # 统一解析，检查错误
        parsed = None
        try:
            parsed = json.loads(raw)
        except Exception:
            # 可能是纯文本；按你的服务端约定自行判断
            pass

        # 典型错误形态的兜底检查
        if isinstance(parsed, dict):
            if parsed.get("error"):
                raise RuntimeError(f"{tool_name} failed: {parsed['error']}")
            if parsed.get("success") is False:
                raise RuntimeError(f"{tool_name} failed: {parsed}")

def capture_final_scenarios(manager: MCPClientManager, client_ids: Dict[str, str]) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    for class_name, client_id in client_ids.items():
        if class_name == "math":
            continue
        raw = manager.call_tool(tool_name="save_scenario", tool_args={}, client_id=client_id)
        if raw is None:
            raise RuntimeError(f"save_scenario returned no data for class '{class_name}'")
        results[class_name] = json.loads(raw)
    return results


def log_mismatch(log_file: Path, record_id: str, actual_final: Dict[str, Any], 
                expected_final: Dict[str, Any], golden_calls: Iterable[str]) -> None:
    """记录mismatch到日志文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    mismatch_data = {
        "timestamp": timestamp,
        "record_id": record_id,
        "golden_calls": list(golden_calls),
        "actual_final": actual_final,
        "expected_final": expected_final
    }
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"时间: {timestamp}\n")
        f.write(f"记录ID: {record_id}\n")
        f.write(f"工具调用序列: {list(golden_calls)}\n")
        f.write(f"\n实际最终配置:\n")
        f.write(json.dumps(actual_final, ensure_ascii=False, indent=2))
        f.write(f"\n\n期望最终配置:\n")
        f.write(json.dumps(expected_final, ensure_ascii=False, indent=2))
        f.write(f"\n{'='*80}\n")


def save_mismatch_config(config_file: Path, record_id: str, actual_final: Dict[str, Any], 
                        expected_final: Dict[str, Any]) -> None:
    """保存mismatch配置到JSON文件"""
    mismatch_entry = {
        "record_id": record_id,
        "timestamp": datetime.now().isoformat(),
        "actual_final": actual_final,
        "expected_final": expected_final
    }
    
    # 如果文件不存在，创建新文件
    if not config_file.exists():
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    
    # 读取现有数据
    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 添加新的mismatch记录
    data.append(mismatch_entry)
    
    # 写回文件
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _normalize_value(val):
    if isinstance(val, np.ndarray):
        # tolist() 可能返回标量或嵌套，统一递归
        lst = val.tolist()
        if isinstance(lst, list):
            return [_normalize_value(x) for x in lst]
        return lst
    if isinstance(val, dict):
        return {k: _normalize_value(v) for k, v in val.items()}
    return val

def normalize_row(row: pd.Series | dict) -> dict:
    if isinstance(row, pd.Series):
        row = row.to_dict()
    return {k: _normalize_value(v) for k, v in row.items()}

def validate_dataset(
    dataset_path: Path, config_path: Path, limit: int | None = None,
    log_file: Path | None = None, config_file: Path | None = None
) -> Tuple[int, Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]], int]:
    df = load_dataframe(dataset_path)
    manager = MCPClientManager()
    manager.init_config(str(config_path))

    mismatches: Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]] = {}
    processed = 0
    error = 0
    
    # 创建日志文件路径
    if log_file is None:
        log_file = Path("validation_mismatches.log")
    if config_file is None:
        config_file = Path("validation_mismatches.json")
    
    print(f"日志文件: {log_file}")
    print(f"配置文件: {config_file}")
    
    try:
        for _, _row in df.iterrows():
            try:
                if limit is not None and processed >= limit:
                    break
                row = normalize_row(_row) 
                record_id = str(row["id"])
                extra_info = row.get("extra_info", {}) or {}
                initial_config = parse_config(extra_info.get("initial_config"))
                expected_final = parse_config(extra_info.get("final_config"))

                reward_model = row.get("reward_model", {})
                if isinstance(reward_model, str):
                    try:
                        reward_model = json.loads(reward_model)
                    except Exception:
                        reward_model = {}

                ground_truth = reward_model.get("ground_truth", [])
                if isinstance(ground_truth, str):
                    try:
                        golden_calls = json.loads(ground_truth)
                    except Exception:
                        golden_calls = ensure_iterable_strings(ground_truth)
                else:
                    golden_calls = ensure_iterable_strings(ground_truth)
                manager.close_all_clients()

                client_ids = create_client_mapping(manager, initial_config)
                execute_tool_sequence(manager, client_ids, golden_calls)
                actual_final = capture_final_scenarios(manager, client_ids)

                if actual_final != expected_final:
                    mismatches[record_id] = (actual_final, expected_final)
                    
                    # 实时保存mismatch
                    print(f"发现mismatch - 记录ID: {record_id}")
                    log_mismatch(log_file, record_id, actual_final, expected_final, golden_calls)
                    save_mismatch_config(config_file, record_id, actual_final, expected_final)

                processed += 1
                
                # 每处理100条记录打印一次进度
                if processed % 100 == 0:
                    print(f"已处理 {processed} 条记录，发现 {len(mismatches)} 个mismatch")
                    
            except Exception as e:
                error_msg = f"处理记录 {row.get('id', 'unknown')} 时出错: {e}"
                print(error_msg)
                tb = traceback.format_exc()
                # 记录错误到日志文件
                if log_file:
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(f"\n[ERROR] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {error_msg}\n")
                        f.write(f"行数据: {dict(row)}\n")
                        f.write(f"错误追踪: {tb}\n")
                error += 1
                continue
    finally:
        manager.shutdown()

    return processed, mismatches, error


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate BFCL dataset scenarios")
    parser.add_argument(
        "--dataset-path",
        type=Path,
        default=Path("data/BFCL/multi-turn/train.parquet"),
        help="Path to the train.parquet dataset",
    )
    parser.add_argument(
        "--config-path",
        type=Path,
        default=Path("tools/mcp_configs/bfcl_mcp_server.json"),
        help="Path to the MCP server configuration file",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Validate only the first N records",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("validation_mismatches2.log"),
        help="Path to the log file for mismatches",
    )
    parser.add_argument(
        "--config-file",
        type=Path,
        default=Path("validation_mismatches.json"),
        help="Path to the JSON file for mismatch configurations",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    processed, mismatches, error = validate_dataset(
        dataset_path=args.dataset_path, 
        config_path=args.config_path, 
        limit=args.limit,
        log_file=args.log_file,
        config_file=args.config_file
    )

    print(f"\n验证完成!")
    print(f"总处理记录数: {processed}")
    print(f"发现mismatch数: {len(mismatches)}")
    print(f"错误数: {error}")
    print(f"日志文件: {args.log_file}")
    print(f"配置文件: {args.config_file}")

    if mismatches:
        print(f"\n发现 {len(mismatches)} 个mismatch，详细信息已保存到:")
        print(f"- 日志文件: {args.log_file}")
        print(f"- 配置文件: {args.config_file}")
        return 1

    print(f"\n验证成功！所有 {processed} 条记录都通过了验证。")
    return 0


if __name__ == "__main__":
    sys.exit(main())