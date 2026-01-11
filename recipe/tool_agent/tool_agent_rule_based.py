import re
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("VERL_LOGGING_LEVEL", "WARN"))

TOOL_CALL_PATTERN = re.compile(r'<tool_call>\s*({.*?})\s*</tool_call>', re.DOTALL)

def parse_ground_truth(ground_truth: str | list[dict]) -> list[str]:
    """
    Parse ground truth tool calls into JSON dict.
    - name (str): 
    - arguments (dict): 
    - masked_arguments (list): 
    """
    try:
        ground_truth_calls = json.loads(ground_truth)
    except:
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
        mcp_server = gt_call.split("-")[0]  
        mcp_servers.add(mcp_server)
    return list(mcp_servers)

def mask_tool_calls(solution: list[dict], ground_truth: list[dict]) -> tuple:
    # Todo
    masked_ground_truth = []
    for gt in ground_truth:
        masked_gt = {
            "name": gt.get("name"),
            "arguments": gt.get("arguments")
        }
        masked_ground_truth.append(masked_gt)

    masked_solution = []
    for sol in solution:
        masked_sol = {
            "name": sol.get("name"),
            "arguments": sol.get("arguments")
        }
        masked_solution.append(masked_sol)
    
    return masked_solution, masked_ground_truth

def _compute_trace_score(solution: list[dict], ground_truth: list[dict]) -> float:
    """
    Compute trace reward score.
    Return 1.0 if ground truth tool calls is a subset of any permutation of solution tool calls.
    """
    # If no solution, return 0
    if not solution:
        return 0.0
    
    # If no ground_truth, return 1
    if not ground_truth:
        return 1.0

    # Mask tool calls
    solution, ground_truth = mask_tool_calls(solution, ground_truth)
    
    # Check if ground truth is a subset of any permutation of solution
    for gt in ground_truth:
        if gt not in solution:
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


def compute_score(solution: str, ground_truth: str, extra_info: dict = None) -> dict:
    """
    Calculate the reward for tool calling agent,.
    
    Args:
        solution: the solution text containing tool_calls
        ground_truth: the correct answer tool_call sequence (JSON string)
        extra_info: extra information containing:
            - sol_final_config: solution's final MCP server configuration
            - gts_final_config: ground truth's final MCP server configuration
    
    Returns:
        dict containing:
            - score: total weighted score = w1 * trace_score + w2 * state_score - length_penalty
            - trace_score: score for correct tool call sequence
            - state_score: score for correct final state
            - length_penalty: penalty for overly long sequences
    """
    try:
        sol_calls = extract_tool_calls(solution)
        gt_calls = parse_ground_truth(ground_truth)
        mcp_servers = extract_mcp_servers(gt_calls)

        # Compute trace score
        trace_score = _compute_trace_score(
            solution=sol_calls,
            ground_truth=gt_calls,
        )

        # Compute state score
        state_score = _compute_state_score(
            solution=extra_info['sol_final_config'],
            ground_truth=extra_info['gts_final_config'],
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
