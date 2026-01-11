# Copyright 2025 Bytedance Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Tool Agent Reward Model using Generative Reward Model (GenRM).

This module provides async reward computation for tool calling agents by:
1. Extracting tool calls from solution and ground truth
2. Computing diff between final configurations
3. Sending prompt to GenRM for evaluation
4. Parsing GenRM output to get binary reward (0 or 1)
"""

import re
import json
import difflib
import logging
import os

import requests
from openai import OpenAI

logger = logging.getLogger()
logger.setLevel(os.getenv("VERL_LOGGING_LEVEL", "WARN"))

# ============== Global Configuration ==============
# Configure these variables for your GenRM deployment
OPENAI_API_KEY = os.getenv("GENRM_API_KEY", "EMPTY")
OPENAI_API_BASE = os.getenv("GENRM_API_BASE", "http://127.0.0.1:55222/v1")
GENRM_MODEL_NAME = os.getenv("GENRM_MODEL_NAME", "")

# Initialize OpenAI client
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE,
)

# Model name: use specified name or auto-detect on first use
EVAL_MODEL_NAME = GENRM_MODEL_NAME if GENRM_MODEL_NAME else ""

# Pattern to extract tool calls from text
TOOL_CALL_PATTERN = re.compile(r'<tool_call>\s*({.*?})\s*</tool_call>', re.DOTALL)

# GenRM prompt template for tool agent evaluation
GENRM_PROMPT_TEMPLATE = """You are evaluating whether a tool-calling agent successfully completed a task.

## Ground Truth Tool Calls
The following are the reference tool calls that represent one correct solution:
```json
{ground_truth_calls}
```

## Agent's Tool Calls
The following are the actual tool calls made by the agent:
```json
{solution_calls}
```

## Configuration Diff
The difference between the expected final state and the agent's final state:
```diff
{config_diff}
```

## Evaluation Criteria
Evaluate whether the agent successfully completed the task. Focus on:
1. **Task Completion**: Did the agent achieve the intended goal? The exact sequence of tool calls does not need to match exactly.
2. **Reasonable Attempts**: The agent is allowed to explore and try different approaches. Extra exploratory calls are acceptable.
3. **Final State**: Is the final configuration correct or close to the expected state?

Note: The agent does NOT need to match the ground truth exactly. Alternative valid solutions and exploratory attempts should be considered successful as long as the task goal is achieved.

## Output
Provide a brief analysis, then output your final verdict.
Put your final answer ('1' for task completed successfully, '0' for task failed) inside <judge></judge> tags.

Example format:
<judge>1</judge>
""".strip()


def _get_model_name() -> str:
    """Get the model name, using specified name or auto-detecting if not set."""
    global EVAL_MODEL_NAME  # pylint: disable=global-statement
    # If model name was specified via environment variable, use it directly
    if EVAL_MODEL_NAME:
        return EVAL_MODEL_NAME
    
    # Otherwise, try to auto-detect from server
    try:
        resp = requests.get(f"{OPENAI_API_BASE}/models", timeout=10)
        resp.raise_for_status()
        model_list = resp.json()
        if model_list.get("data"):
            EVAL_MODEL_NAME = model_list["data"][0]["id"]
            return EVAL_MODEL_NAME
    except (requests.exceptions.RequestException, KeyError, IndexError) as e:
        logger.warning("Failed to auto-detect model name: %s", e)
    
    # Fallback to default if auto-detection fails
    EVAL_MODEL_NAME = "default"
    return EVAL_MODEL_NAME


def parse_ground_truth(ground_truth: str | list[dict]) -> list[dict]:
    """
    Parse ground truth tool calls into JSON dict.
    - name (str): tool name
    - arguments (dict): tool arguments
    """
    try:
        ground_truth_calls = json.loads(ground_truth) if isinstance(ground_truth, str) else ground_truth
    except (json.JSONDecodeError, TypeError):
        ground_truth_calls = []
    return ground_truth_calls


def extract_tool_calls(text: str) -> list[dict]:
    """Extract tool_call from text."""
    tool_calls = []
    
    matches = TOOL_CALL_PATTERN.findall(text)
    for match in matches:
        try:
            tool_call = json.loads(match)
            if "name" in tool_call and "arguments" in tool_call:
                tool_calls.append(tool_call)
        except (json.JSONDecodeError, TypeError):
            continue

    return tool_calls


def compute_config_diff(sol_config: str | dict, gt_config: str | dict) -> str:
    """
    Compute unified diff between solution config and ground truth config.
    
    Args:
        sol_config: Solution's final MCP server configuration
        gt_config: Ground truth's final MCP server configuration
    
    Returns:
        Unified diff string
    """
    def _ensure_dict(obj: str | dict) -> dict:
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, str):
            try:
                return json.loads(obj)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    sol_dict = _ensure_dict(sol_config)
    gt_dict = _ensure_dict(gt_config)
    
    # Convert to sorted JSON strings for consistent diff
    sol_json = json.dumps(sol_dict, indent=2, sort_keys=True).splitlines()
    gt_json = json.dumps(gt_dict, indent=2, sort_keys=True).splitlines()
    
    # Compute unified diff
    diff = difflib.unified_diff(
        gt_json,
        sol_json,
        fromfile='ground_truth_config',
        tofile='solution_config',
        lineterm=''
    )
    
    return '\n'.join(diff)


def build_genrm_prompt(
    solution_calls: list[dict],
    ground_truth_calls: list[dict],
    config_diff: str
) -> str:
    """
    Build the prompt for GenRM evaluation.
    
    Args:
        solution_calls: Extracted tool calls from solution
        ground_truth_calls: Parsed ground truth tool calls
        config_diff: Unified diff between configs
    
    Returns:
        Formatted prompt string
    """
    return GENRM_PROMPT_TEMPLATE.format(
        ground_truth_calls=json.dumps(ground_truth_calls, indent=2, ensure_ascii=False),
        solution_calls=json.dumps(solution_calls, indent=2, ensure_ascii=False),
        config_diff=config_diff if config_diff else "(No difference - configurations match)"
    )


def parse_genrm_response(response_text: str) -> int:
    """
    Parse GenRM response to extract binary reward score.
    
    Args:
        response_text: Raw response from GenRM
    
    Returns:
        Binary score (0 or 1)
    """
    try:
        # First, try to extract from <judge></judge> tags
        judge_match = re.search(r'<judge>\s*([01])\s*</judge>', response_text, re.IGNORECASE)
        if judge_match:
            return int(judge_match.group(1))
        
        # Fallback: Get the last non-empty line
        lines = [line.strip() for line in response_text.strip().split('\n') if line.strip()]
        if not lines:
            return 0
        
        last_line = lines[-1]
        
        # Try to extract number from the last line
        # Handle cases like "1", "0", "Score: 1", etc.
        numbers = re.findall(r'\b([01])\b', last_line)
        if numbers:
            return int(numbers[-1])
        
        # Fallback: check for keywords
        lower_line = last_line.lower()
        if any(word in lower_line for word in ['correct', 'success', 'true', 'yes', 'completed']):
            return 1
        if any(word in lower_line for word in ['incorrect', 'fail', 'false', 'no', 'failed']):
            return 0
            
    except (ValueError, IndexError) as e:
        logger.warning("Failed to parse GenRM response: %s", e)
    
    return 0


def get_genrm_response(
    genrm_prompt: str,
    temperature: float = 0.7,
    top_p: float = 0.8,
    max_tokens: int = 4096,
) -> str:
    """
    Send request to GenRM and get response.
    
    Args:
        genrm_prompt: The evaluation prompt
        temperature: Sampling temperature
        top_p: Top-p sampling parameter
        max_tokens: Maximum tokens to generate
    
    Returns:
        GenRM response text
    """
    model_name = _get_model_name()
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": genrm_prompt}],
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except (requests.exceptions.RequestException, KeyError, IndexError) as e:
        logger.warning("GenRM request failed: %s", e)
        raise


async def compute_score(
    solution: str,
    ground_truth: str,
    extra_info: dict = None,
) -> dict:
    """
    Compute the reward score using Generative Reward Model.
    
    Args:
        solution: The solution text containing tool_calls
        ground_truth: The correct answer tool_call sequence (JSON string)
        extra_info: Extra information containing:
            - sol_final_config: solution's final MCP server configuration
            - gts_final_config: ground truth's final MCP server configuration
    
    Returns:
        dict containing:
            - score: Binary reward (0 or 1)
            - genrm_response: Raw response from GenRM (for debugging)
    """
    if extra_info is None:
        extra_info = {}
    
    try:
        # Step 1: Extract and parse tool calls
        sol_calls = extract_tool_calls(solution)
        gt_calls = parse_ground_truth(ground_truth)
        
        # Step 2: Compute config diff
        config_diff = compute_config_diff(
            sol_config=extra_info.get('sol_final_config', {}),
            gt_config=extra_info.get('gts_final_config', {})
        )
        
        # Step 3: Build GenRM prompt
        genrm_prompt = build_genrm_prompt(
            solution_calls=sol_calls,
            ground_truth_calls=gt_calls,
            config_diff=config_diff
        )
        
        # Step 4: Get GenRM response
        genrm_response = get_genrm_response(genrm_prompt)
        
        # Step 5: Parse response and extract score
        score = parse_genrm_response(genrm_response)
        
        return {
            "score": score,
            "genrm_response": genrm_response,
        }
        
    except (ValueError, KeyError, requests.exceptions.RequestException) as e:
        logger.warning("Error in compute_score: %s", e)
        return {
            "score": 0,
            "genrm_response": str(e),
        }


def compute_score_sync(
    solution: str,
    ground_truth: str,
    extra_info: dict = None,
) -> dict:
    """
    Synchronous version of compute_score.
    
    Args:
        solution: The solution text containing tool_calls
        ground_truth: The correct answer tool_call sequence (JSON string)
        extra_info: Extra information containing:
            - sol_final_config: solution's final MCP server configuration
            - gts_final_config: ground truth's final MCP server configuration
    
    Returns:
        dict containing:
            - score: Binary reward (0 or 1)
            - genrm_response: Raw response from GenRM (for debugging)
    """
    if extra_info is None:
        extra_info = {}
    
    try:
        # Step 1: Extract and parse tool calls
        sol_calls = extract_tool_calls(solution)
        gt_calls = parse_ground_truth(ground_truth)
        
        # Step 2: Compute config diff
        config_diff = compute_config_diff(
            sol_config=extra_info.get('sol_final_config', {}),
            gt_config=extra_info.get('gts_final_config', {})
        )
        
        # Step 3: Build GenRM prompt
        genrm_prompt = build_genrm_prompt(
            solution_calls=sol_calls,
            ground_truth_calls=gt_calls,
            config_diff=config_diff
        )
        
        # Step 4: Get GenRM response
        genrm_response = get_genrm_response(genrm_prompt)
        
        # Step 5: Parse response and extract score
        score = parse_genrm_response(genrm_response)
        
        return {
            "score": score,
            "genrm_response": genrm_response,
        }
        
    except (ValueError, KeyError, requests.exceptions.RequestException) as e:
        logger.warning("Error in compute_score_sync: %s", e)
        return {
            "score": 0,
            "genrm_response": str(e),
        }
