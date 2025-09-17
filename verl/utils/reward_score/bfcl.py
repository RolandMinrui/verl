import re
import json
from typing import List

from mcp.server.fastmcp.tools import tool_manager

TOOL_CALL_PATTERN = re.compile(r'<tool_call>\s*({.*?})\s*</tool_call>', re.DOTALL)

def extract_tool_calls(text: str) -> List[str]:
    """
    从文本中提取tool_call,只支持格式: <tool_call>{"name": "func", "arguments": {...}}</tool_call>
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
                
                # 标准化为 function(arg1='value1', arg2='value2') 格式
                sorted_args = []
                for key in sorted(args.keys()):
                    value = args[key]
                    sorted_args.append(f"{key}='{value}'")
                
                args_str = ', '.join(sorted_args)
                normalized_call = f"{name}({args_str})"
                tool_calls.append(normalized_call)
        except json.JSONDecodeError:
            continue
    
    return tool_calls

def parse_ground_truth(ground_truth: str) -> List[str]:
    """
    parse the ground_truth, support JSON list format
    """
    try:
        if ground_truth.strip().startswith('['):
            return json.loads(ground_truth)
        else:
            return [line.strip() for line in ground_truth.strip().split('\n') if line.strip()]
    except json.JSONDecodeError:
        return [line.strip() for line in ground_truth.strip().split('\n') if line.strip()]

def compute_score(solution_str: str, ground_truth: str, format_score: float = 0.1, extra_info=None) -> float:
    """
    calculate the score of solution relative to ground_truth, only return the numerical value
    
    Args:
        solution_str: the solution text containing tool_calls
        ground_truth: the correct answer tool_call sequence
        format_score: the base score when the format is correct
        extra_info: extra information
    
    Returns:
        float: solution==grouth_truch - length_penalty + format_score
    """
    try:
        # 1. extract the tool_calls from solution
        solution_calls = extract_tool_calls(solution_str)
        
        # 2. parse the ground_truth
        ground_truth_calls = parse_ground_truth(ground_truth)
        
        # 3. if no tool_calls are extracted, return 0
        if not solution_calls:
            return 0.0
        
        # 4. if the ground_truth is empty, return 1
        if not ground_truth_calls:
            return 1.0
        
        # 5. check if the ground_truth is a subsequence of solution
        gt_idx = 0
        for sol_call in solution_calls:
            if gt_idx < len(ground_truth_calls) and sol_call == ground_truth_calls[gt_idx]:
                gt_idx += 1
        
        if gt_idx == len(ground_truth_calls):
            total_score = 1.0
        else:
            total_score = 0.0
        
        # 6. calculate the length penalty
        length_ratio = len(solution_calls) / len(ground_truth_calls)
        length_penalty = 0.0
        
        if length_ratio > 2.0:
            length_penalty = min(0.3, (length_ratio - 2.0) * 0.1)
        elif length_ratio > 1.5:
            length_penalty = min(0.1, (length_ratio - 1.5) * 0.2)
        
        # 7. calculate the final content score(0-1)
        total_score = max(0.0, min(1.0, total_score - length_penalty + format_score))

        return round(total_score, 1)
        
    except Exception:
        return 0.0
