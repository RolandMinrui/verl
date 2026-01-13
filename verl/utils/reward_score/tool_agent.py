import re
import json
import logging
import os
import math

logger = logging.getLogger()
logger.setLevel(os.getenv("VERL_LOGGING_LEVEL", "WARN"))

TOOL_CALL_PATTERN = re.compile(r'<tool_call>\s*({.*?})\s*</tool_call>', re.DOTALL)


def _values_match(v1, v2) -> bool:
    """
    Compare two values with number sensitivity handling.
    Returns True if values are effectively equal (1 == 1.0).
    """
    if v1 == v2:
        return True
    
    if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
        return math.isclose(v1, v2, rel_tol=1e-9)

    return False
    
def parse_ground_truth(ground_truth: str | list[dict]) -> list[dict]:
    """
    Parse ground truth tool calls into JSON dict list.
    Ensures masked_arguments are preserved.
    """
    try:
        if isinstance(ground_truth, str):
            ground_truth_calls = json.loads(ground_truth)
        elif isinstance(ground_truth, list):
            ground_truth_calls = ground_truth
        else:
            ground_truth_calls = []
    except Exception:
        ground_truth_calls = []
        
    return ground_truth_calls

def extract_tool_calls(text: str) -> list[str]:
    """Extract tool_call from text"""
    tool_calls = []
    
    matches = TOOL_CALL_PATTERN.findall(text)
    for match in matches:
        try:
            tool_call = json.loads(match)
            if "name" in tool_call and "arguments" in tool_call:
                tool_calls.append(tool_call)
        except Exception as e:
            continue

    return tool_calls

def extract_mcp_servers(gt_calls: list[str]) -> list[str]:
    mcp_servers = set()
    for gt_call in gt_calls:
        mcp_server = gt_call["name"].split("-")[0]
        mcp_servers.add(mcp_server)
    return list(mcp_servers)


def _check_tool_call_match(sol_call: dict, gt_call: dict) -> bool:
    """
    Check if a solution call matches a ground truth call, respecting masked_arguments.
    """
    # 1. Check Name
    if sol_call.get("name") != gt_call.get("name"):
        return False

    sol_args = sol_call.get("arguments", {})
    gt_args = gt_call.get("arguments", {})
    masked_keys = set(gt_call.get("masked_arguments", [])) 

    # 2. Iterate through GT arguments constraints
    for key, gt_val in gt_args.items():
        # if key in masked_arguments, skip value comparison
        if key in masked_keys:
            continue
        
        # if gt has key but sol not, return False
        if key not in sol_args:
            return False
        
        sol_val = sol_args[key]
        
        # if not in masked, must compare value (include number type handling)
        if not _values_match(sol_val, gt_val):
            return False
    return True

def _compute_trace_score(solution: list[dict], ground_truth: list[dict]) -> float:
    """
    Compute trace reward score with support for masked arguments and number tolerance.
    Return 1.0 if ground truth tool calls is a subset of solution tool calls (order independent).
    """
    # If no solution, return 0
    if not solution:
        return 0.0
    
    # If no ground_truth, return 1
    if not ground_truth:
        return 1.0

    # create a solution index list to mark which call has been matched
    # avoid two same call in GT matching to the same call in Solution
    solution_matched_indices = set()

    # Check if EVERY call in ground truth has a corresponding match in solution
    for gt_call in ground_truth:
        match_found = False

        for idx, sol_call in enumerate(solution):
            # if this solution call has been matched by previous GT call, skip
            if idx in solution_matched_indices:
                continue
            
            # check if match
            if _check_tool_call_match(sol_call, gt_call):
                solution_matched_indices.add(idx)
                match_found = True
                break # found match, break inner loop, process next GT call
        
        # if current GT call not found any match in solution, return 0
        if not match_found:
            return 0.0

    return 1.0


def _compute_state_score(solution: str | dict, ground_truth: str | dict, mcp_servers: list[str]) -> float:
    def _ensure_dict(obj: str | dict) -> dict | None:
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, str):
            try:
                return json.loads(obj)
            except Exception:
                return {}
        return {}

    ground_truth = _ensure_dict(ground_truth)
    solution = _ensure_dict(solution)

    filtered_gt = {k: v for k, v in ground_truth.items() if k in mcp_servers}
    
    matches = sum(1 for tool_class, final_config in filtered_gt.items()
                  if solution.get(tool_class) == final_config)

    return matches / len(filtered_gt) if filtered_gt else 0.0

def _compute_length_penalty(solution: list[dict], ground_truth: list[dict]) -> float:
    """
    Compute the length penalty.
    """
    if not ground_truth:
        return 0.0
    
    if not solution:
        return 0.0
    
    ratio = len(solution) / len(ground_truth)
    if ratio > 2.0:
        return min(0.3, (ratio - 2.0) * 0.1)
    elif ratio > 1.5:
        return min(0.1, (ratio - 1.5) * 0.2)
    return 0.0


def compute_score(data_source=None, solution_str: str = None, ground_truth: str = None, extra_info: dict = None, solution: str = None, **kwargs) -> dict:
    """
    Calculate the reward for tool calling agent,.
    
    Args:
        data_source: the data source identifier (optional, for compatibility with framework)
        solution_str: the solution text containing tool_calls (preferred parameter name)
        ground_truth: the correct answer tool_call sequence (JSON string)
        extra_info: extra information containing:
            - sol_final_config: solution's final MCP server configuration
            - gts_final_config: ground truth's final MCP server configuration
        solution: deprecated, use solution_str instead (for backward compatibility)
    
    Returns:
        dict containing:
            - score: total weighted score = w1 * trace_score + w2 * state_score - length_penalty
            - trace_score: score for correct tool call sequence
            - state_score: score for correct final state
            - length_penalty: penalty for overly long sequences
    """
    # Handle backward compatibility: if solution is provided but solution_str is not, use solution
    if solution_str is None and solution is not None:
        solution_str = solution
    
    if solution_str is None:
        logger.warning("compute_score: solution_str is None")
        return {
            "score": 0.0,
            "trace_score": 0.0,
            "state_score": 0.0,
            "length_penalty": 0.0,
        }
    
    if ground_truth is None:
        ground_truth = ""
    
    if extra_info is None:
        extra_info = {}
    
    try:
        sol_calls = extract_tool_calls(solution_str)
        gt_calls = parse_ground_truth(ground_truth)
        mcp_servers = extract_mcp_servers(gt_calls)

        # Compute trace score
        trace_score = _compute_trace_score(
            solution=sol_calls,
            ground_truth=gt_calls,
        )

        # Compute state score
        state_score = _compute_state_score(
            solution=extra_info.get('sol_final_config'),
            ground_truth=extra_info.get('gts_final_config'),
            mcp_servers=mcp_servers,
        )

        # Compute length penalty
        length_penalty = _compute_length_penalty(
            solution=sol_calls,
            ground_truth=gt_calls,
        )

        return {
            "score": 0.5 * trace_score + 0.5 * state_score - length_penalty,
            "trace_score": trace_score,
            "state_score": state_score,
            "length_penalty": length_penalty,
        }
        
    except Exception as e:
        logger.warning(f"Debug: Error in compute_score: {e}")
        return {
            "score": 0.0,
            "trace_score": 0.0,
            "state_score": 0.0,
            "length_penalty": 0.0,
        }
