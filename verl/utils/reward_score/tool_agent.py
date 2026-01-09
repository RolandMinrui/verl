import re
import json
from typing import List
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("VERL_LOGGING_LEVEL", "WARN"))

TOOL_CALL_PATTERN = re.compile(r'<tool_call>\s*({.*?})\s*</tool_call>', re.DOTALL)

def normalize_function_call(name: str, args: dict) -> str:
    """
    Normalize function call format to ensure consistent parameter ordering
    """
    # Method 1: Sort parameters alphabetically (recommended)
    sorted_args = []
    for key in sorted(args.keys()):
        value = args[key]
        sorted_args.append(f"{key}='{value}'")
    
    args_str = ', '.join(sorted_args)
    return f"{name}({args_str})"

def extract_tool_calls(text: str) -> List[str]:
    """
    Extract tool_call from text, only supports format: <tool_call>{"name": "func", "arguments": {...}}</tool_call>
    """
    tool_calls = []

    try:
        matches = TOOL_CALL_PATTERN.findall(text)
    except Exception as e:
        print(f"Debug: regex error: {e}")
        return tool_calls

    for match in matches:
        try:
            call_data = json.loads(match)
            if 'name' in call_data:
                name = call_data['name']
                args = call_data.get('arguments', {})
                
                # Use unified normalization function
                normalized_call = normalize_function_call(name, args)
                tool_calls.append(normalized_call)
        except json.JSONDecodeError:
            continue
    
    return tool_calls

def extract_involved_classes(ground_truth_calls: List[str]) -> List[str]:
    involved_classes = set()
    for call in ground_truth_calls:
        tool_name = call.split("(")[0]  
        tool_class = tool_name.split("-")[0]  
        involved_classes.add(tool_class)
    return list(involved_classes)

def normalize_ground_truth_calls(ground_truth_calls: List[str]) -> List[str]:
    """
    Normalize function calls in ground truth
    """
    normalized_calls = []
    
    for call in ground_truth_calls:
        # Parse function call format: func_name(arg1='val1', arg2='val2')
        match = re.match(r'([^(]+)\((.*)\)', call.strip())
        if match:
            func_name = match.group(1)
            args_str = match.group(2)
            
            # Parse parameters
            args = {}
            if args_str.strip():
                # Simple parameter parsing (assuming parameter format is key='value')
                arg_pattern = re.compile(r"(\w+)='([^']*)'")
                for arg_match in arg_pattern.finditer(args_str):
                    key = arg_match.group(1)
                    value = arg_match.group(2)
                    args[key] = value
            
            # Use the same normalization function
            normalized_call = normalize_function_call(func_name, args)
            normalized_calls.append(normalized_call)
        else:
            # If unable to parse, keep as is
            normalized_calls.append(call)
    
    return normalized_calls

def mask_calls(gt_calls: list[dict], sol_calls: list[dict]) -> tuple:
    pass

def parse_ground_truth(ground_truth: str | list[dict]) -> List[str]:
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

def _compute_trace_score(solution: str, ground_truth: str) -> float:
    """
    Compute trace reward score.
    Return 1.0 if ground truth tool calls is a subset of any permutation of solution tool calls.
    """
    # 1. Extract solution tool calls
    sol_calls = extract_tool_calls(solution)
    
    # 2. Parse ground truth tool calls
    gt_calls = parse_ground_truth(ground_truth)

    # 3. If no sol_calls, return 0
    if not sol_calls:
        return 0.0
    
    # 4. If no gt_calls, return 1
    if not gt_calls:
        return 1.0

    # 5. Normalize calls
    gt_calls, sol_calls = mask_calls(gt_calls, sol_calls)
    
    # 6. Check if ground truth is a subset of any permutation of solution
    for gt in gt_calls:
        if gt not in sol_calls:
            return 0.0
    return 1.0

def _compute_length_penalty(solution, ground_truth) -> float:
    length_ratio = len(solution) / len(ground_truth) if len(ground_truth) > 0 else 1.0
    length_penalty = 0.0
    
    if length_ratio > 2.0:
        length_penalty = min(0.3, (length_ratio - 2.0) * 0.1)
    elif length_ratio > 1.5:
        length_penalty = min(0.1, (length_ratio - 1.5) * 0.2)
    return length_penalty

def _compute_state_score(solution: str | dict, ground_truth: str | dict, involved_classes: List[str] | None = None) -> float:
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

    if involved_classes is None:
        involved_classes = list(ground_truth.keys())

    filtered_gt = {k: v for k, v in ground_truth.items() if k in involved_classes}
    
    matches = sum(1 for tool_class, final_config in filtered_gt.items()
                  if solution.get(tool_class) == final_config)

    return matches / len(filtered_gt) if filtered_gt else 0.0

def _compute_answer_score(solution: str | dict, ground_truth: str | dict) -> float:
    """
    Calculate the answer score based on exact match.
    
    Args:
        solution: The solution answer (string or dict)
        ground_truth: The ground truth answer (string or dict)
    
    Returns:
        float: 1.0 if exact match, 0.0 otherwise
    """
    if isinstance(ground_truth, dict):
        if isinstance(solution, str):
            try:
                import json
                solution = json.loads(solution)
            except Exception:
                return 0.0

    if solution == ground_truth:
        return 1.0
    else:
        return 0.0

def compute_score(solution: str, ground_truth: str, extra_info=None) -> float:
    """
    calculate the reward for tool calling agent,.
    
    Args:
        solution: the solution text containing tool_calls
        ground_truth: the correct answer tool_call sequence
        extra_info: extra information
    
    Returns:
        reward (str) = w1 * trace_score + w2 * state_score
    """
    try:
        trace_score = _compute_trace_score(
            solution=solution,
            ground_truth=ground_truth,
        )

        gt_calls = parse_ground_truth(ground_truth)
        involved_classes = extract_involved_classes(gt_calls)

        state_score = _compute_state_score(
            solution=extra_info['sol_final_config'],
            ground_truth=extra_info['gts_final_config'],
            involved_classes=involved_classes,
        )
        return {
            "score": 0.5 * trace_score + 0.5 * state_score,
            "trace_score": trace_score,
            "state_score": state_score,
        }
        
    except Exception as e:
        logger.warning(f"Debug: Error in compute_score: {e}")
        return {
            "score": 0.0,
            "trace_score": 0.0,
            "state_score": 0.0,
        }
