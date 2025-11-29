"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any
import json
from .openrouter import query_models_parallel, query_model
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL





async def divergent_phase_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Divergent Phase: Sequential responses where each model sees all previous responses.

    Args:
        user_query: The user's question

    Returns:
        List of dicts with 'model', 'response', and 'parsed_json' keys
    """
    divergent_results = []
    accumulated_responses = []

    # Process models sequentially
    for i, model in enumerate(COUNCIL_MODELS):
        # Build prompt with accumulated context
        prompt = build_divergent_prompt(user_query, accumulated_responses)
        messages = [{"role": "user", "content": prompt}]

        # Log prompt for debugging
        print(f"\n=== Divergent Phase - Model {i+1}: {model} ===", flush=True)
        print(f"Prompt length: {len(prompt)} characters", flush=True)
        print("Prompt content:", flush=True)
        print("-" * 80, flush=True)
        print(prompt, flush=True)
        print("-" * 80, flush=True)

        # Query the model
        response = await query_model(model, messages)

        if response is not None:
            response_text = response.get('content', '')

            # Log response for debugging
            print(f"\n=== Response from {model} ===", flush=True)
            print(f"Response length: {len(response_text)} characters", flush=True)
            print("Response content:", flush=True)
            print("-" * 80, flush=True)
            print(response_text, flush=True)
            print("-" * 80, flush=True)

            # Validate and parse JSON
            parsed_json = validate_and_parse_json(response_text, model)

            result = {
                "model": model,
                "response": response_text,
                "parsed_json": parsed_json
            }

            divergent_results.append(result)
            accumulated_responses.append(result)
        else:
            # If model fails, continue with next model
            print(f"Warning: Model {model} failed to respond in divergent phase")

    return divergent_results












async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use gemini-2.5-flash for title generation (fast and cheap)
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


def build_divergent_prompt(user_query: str, previous_responses: List[Dict[str, Any]]) -> str:
    """
    Build prompt for divergent phase based on accumulated context.

    Args:
        user_query: The user's question
        previous_responses: List of previous model responses

    Returns:
        Formatted prompt string
    """
    # Optimized divergent phase prompt with clear structure
    system_prompt = """# 角色与任务

## 角色定义
你是多智能体协作系统的 AI 模型，参与发散阶段的讨论。

## 核心任务
- 围绕用户问题提供你的观点
- 基于已有讨论内容进行推理和反思
- 使用结构化 JSON 格式输出

---

# 输出格式

## 必须严格遵守以下 JSON 格式：

```json
{
  "summary": "本轮你的思考简述",
  "viewpoints": [
    "你的主要观点1",
    "你的主要观点2"
  ],
  "conflicts": [
    "你与其他观点的主要不同点（若有）"
  ],
  "suggestions": [
    "基于讨论你认为应该增加或修正的内容"
  ],
  "final_answer_candidate": "如果你需要提供最终答案，请放在这里"
}
```

## 输出要求
1. 必须使用 JSON 格式，不得包含解释性文字
2. 不得重复他人观点的原文，使用自己的语言表达
3. 保持逻辑清晰、结构化表达

---

# 讨论上下文
"""

    # Add previous responses context
    if previous_responses:
        system_prompt += "\n## 已有讨论内容\n\n"
        for i, prev_response in enumerate(previous_responses, 1):
            system_prompt += f"### 模型 {i} 的观点\n\n"
            # Show the parsed JSON directly if available, otherwise show raw response
            if prev_response.get('parsed_json'):
                parsed = prev_response['parsed_json']
                system_prompt += f"```json\n{json.dumps(parsed, ensure_ascii=False, indent=2)}\n```\n\n"
            else:
                system_prompt += f"{prev_response['response']}\n\n"

    system_prompt += "---\n\n# 本轮任务\n\n"
    system_prompt += f"## 用户原始问题\n{user_query}\n\n"

    system_prompt += "## 你的任务\n"
    if previous_responses:
        system_prompt += "基于上述讨论内容，提供你的观点：\n"
        system_prompt += "- 考虑与之前观点的异同\n"
        system_prompt += "- 补充新的见解或角度\n"
    else:
        system_prompt += "作为第一个发言者，请提供你的初步观点：\n"
        system_prompt += "- 从多个角度分析问题\n"
        system_prompt += "- 为后续讨论奠定基础\n"

    system_prompt += "\n---\n\n# 开始回答\n请严格按照指定 JSON 格式输出你的观点。"

    return system_prompt


def validate_and_parse_json(response_text: str, model_name: str) -> Dict[str, Any]:
    """
    Validate and parse JSON response with retry logic.

    Args:
        response_text: The raw response text from the model
        model_name: Name of the model for error reporting

    Returns:
        Parsed JSON dict or empty dict if validation fails
    """
    # Try to parse JSON
    try:
        # Remove any markdown code block markers
        cleaned_text = response_text.strip()
        if cleaned_text.startswith('```json'):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith('```'):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith('```'):
            cleaned_text = cleaned_text[:-3]

        parsed = json.loads(cleaned_text.strip())

        # Validate required fields
        required_fields = ['summary', 'viewpoints', 'conflicts', 'suggestions', 'final_answer_candidate']
        for field in required_fields:
            if field not in parsed:
                print(f"Warning: Model {model_name} missing required field '{field}' in JSON")
                return {}

        return parsed

    except json.JSONDecodeError as e:
        print(f"Warning: Model {model_name} returned invalid JSON: {e}")
        print(f"Response text: {response_text}")
        return {}


async def evaluate_convergence(
    user_query: str,
    round_responses: List[Dict[str, Any]],
    round_number: int
) -> Dict[str, Any]:
    """
    Evaluate convergence and generate chairman's assessment.

    Args:
        user_query: The user's question
        round_responses: List of model responses for this round
        round_number: Current round number (1 for divergent, 2+ for convergent)

    Returns:
        Chairman's assessment in JSON format
    """
    # Build responses text for chairman
    responses_text = "\n\n".join([
        f"{result['model']}:\n{result['response']}"
        for result in round_responses
    ])

    # Build optimized chairman prompt with clear structure
    chairman_prompt = f"""# 角色定义
你是多智能体协作系统的 Chairman LLM（主持人模型），负责引导讨论进程并评估收敛状态。

---

# 核心任务

## 1. 内容分析
- 分析各 LLM 的最新回复内容
- 提炼共识观点（共同认可的核心内容）
- 识别冲突观点（存在分歧的关键问题）

## 2. 收敛评估
判断本轮讨论是否"趋于收敛"（稳定化）。

**收敛定义**（注意：收敛 ≠ 全体同意）：
- 各模型不再提出显著新的关键观点
- 剩余分歧稳定且清晰，不再扩散
- 讨论形成稳定框架（明确共识点 + 明确分歧点）
- 现有信息足够生成高质量综合答案

## 3. 决策输出
- **若已收敛**：输出最终综合结论
- **若未收敛**：生成下一轮讨论的具体问题

---

# 评估标准

## 收敛评估维度（主观评分 0-1 分）

1. **新观点减少程度**
   - 本轮是否基本停止出现新的关键观点？

2. **分歧稳定性**
   - 分歧是否稳定、清晰，而非不断扩散？

3. **结构化一致性**
   - 讨论是否形成稳定的框架？

4. **信息充分性**
   - 当前内容是否足以写出高质量综合结论？

**注意**：基于整体语义主观判断，无需严格数学计算。

---

# 输出格式

## 必须严格遵守以下 JSON 格式：

```json
{{
  "convergence_score": 0.0-1.0,
  "is_converged": true/false,
  "consensus_points": ["共识点1", "共识点2", ...],
  "conflict_points": ["冲突点1", "冲突点2", ...],
  "explanation": "为什么你判断已/未收敛",
  "questions_for_next_round": [
    "问题1",
    "问题2",
    "问题3"
  ],
  "final_integrated_conclusion": "如果需要停止讨论，请给出最终综合答案"
}}
```

## 输出规则
- 若 `is_converged = true` → 必须输出 `final_integrated_conclusion`
- 若 `is_converged = false` → 必须输出 `questions_for_next_round`

---

# 待分析内容

## 用户原始问题
{user_query}

## 本轮 LLM 回复内容
{responses_text}

---

# 开始分析
请基于以上信息，严格按照指定格式输出你的分析结果。"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Log chairman prompt for debugging
    print(f"\n=== Chairman Prompt (Round {round_number}) ===", flush=True)
    print(f"Prompt length: {len(chairman_prompt)} characters", flush=True)
    print("Prompt content:", flush=True)
    print("-" * 80, flush=True)
    print(chairman_prompt, flush=True)
    print("-" * 80, flush=True)

    # Query the chairman model
    response = await query_model(CHAIRMAN_MODEL, messages)

    # Log chairman response for debugging
    if response is not None:
        response_text = response.get('content', '')
        print(f"\n=== Chairman Response (Round {round_number}) ===", flush=True)
        print(f"Response length: {len(response_text)} characters", flush=True)
        print("Response content:", flush=True)
        print("-" * 80, flush=True)
        print(response_text, flush=True)
        print("-" * 80, flush=True)
    else:
        print(f"\n=== Chairman Response (Round {round_number}) ===")
        print("Chairman failed to respond")

    if response is None:
        # Fallback if chairman fails
        return {
            "convergence_score": 0.0,
            "is_converged": False,
            "consensus_points": [],
            "conflict_points": [],
            "explanation": "Chairman failed to respond",
            "questions_for_next_round": ["Please continue the discussion"],
            "final_integrated_conclusion": ""
        }

    response_text = response.get('content', '')

    # Parse chairman's JSON response
    try:
        # Remove any markdown code block markers
        cleaned_text = response_text.strip()
        if cleaned_text.startswith('```json'):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith('```'):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith('```'):
            cleaned_text = cleaned_text[:-3]

        chairman_assessment = json.loads(cleaned_text.strip())

        # Log parsed assessment for debugging
        print(f"\n=== Parsed Chairman Assessment (Round {round_number}) ===")
        print(f"Convergence Score: {chairman_assessment.get('convergence_score', 'N/A')}")
        print(f"Converged: {chairman_assessment.get('is_converged', 'N/A')}")
        print(f"Consensus Points: {chairman_assessment.get('consensus_points', [])}")
        print(f"Conflict Points: {chairman_assessment.get('conflict_points', [])}")
        print(f"Explanation: {chairman_assessment.get('explanation', 'N/A')}")
        print(f"Questions for Next Round: {chairman_assessment.get('questions_for_next_round', [])}")
        print(f"Final Conclusion: {chairman_assessment.get('final_integrated_conclusion', 'N/A')}")

        # Validate required fields
        required_fields = [
            'convergence_score', 'is_converged', 'consensus_points',
            'conflict_points', 'explanation', 'questions_for_next_round',
            'final_integrated_conclusion'
        ]
        for field in required_fields:
            if field not in chairman_assessment:
                print(f"Warning: Chairman missing required field '{field}' in JSON")
                chairman_assessment[field] = "" if field == "final_integrated_conclusion" else []

        return chairman_assessment

    except json.JSONDecodeError as e:
        print(f"Warning: Chairman returned invalid JSON: {e}")
        print(f"Response text: {response_text}")
        return {
            "convergence_score": 0.0,
            "is_converged": False,
            "consensus_points": [],
            "conflict_points": [],
            "explanation": "Invalid JSON response from chairman",
            "questions_for_next_round": ["Please continue the discussion"],
            "final_integrated_conclusion": ""
        }


def build_convergent_prompt(
    user_query: str,
    consensus_points: List[str],
    conflict_points: List[str],
    questions: List[str]
) -> str:
    """
    Build prompt for convergent phase based on chairman's assessment.

    Args:
        user_query: The user's question
        consensus_points: List of consensus points from chairman
        conflict_points: List of conflict points from chairman
        questions: List of questions for next round

    Returns:
        Formatted prompt string for convergent phase
    """
    # Optimized convergent phase prompt with clear structure
    system_prompt = """# 角色与任务

## 角色定义
你是多智能体协作系统的 AI 模型，参与收敛阶段的讨论。

## 核心任务
- 基于讨论上下文和本轮指定问题，提供你的观点
- 促进共识形成，帮助讨论收敛
- 使用结构化 JSON 格式输出

---

# 输出格式

## 必须严格遵守以下 JSON 格式：

```json
{
  "summary": "本轮你的思考简述",
  "viewpoints": [
    "你的主要观点1",
    "你的主要观点2"
  ],
  "conflicts": [
    "你与其他观点的主要不同点（若有）"
  ],
  "suggestions": [
    "基于讨论你认为应该增加或修正的内容"
  ],
  "final_answer_candidate": "如果你需要提供最终答案，请放在这里"
}
```

## 输出要求
1. 必须使用 JSON 格式，不得包含解释性文字
2. 不得重复他人观点的原文，使用自己的语言表达
3. 保持逻辑清晰、结构化表达

---

# 讨论上下文

## Chairman 总结

### 共识点
"""

    # Add consensus points
    for point in consensus_points:
        system_prompt += f"- {point}\n"

    system_prompt += "\n### 冲突点\n"
    for point in conflict_points:
        system_prompt += f"- {point}\n"

    system_prompt += "\n---\n\n# 本轮任务\n\n## 用户原始问题\n"
    system_prompt += f"{user_query}\n\n"

    system_prompt += "## 本轮必须回答的问题\n"
    for i, question in enumerate(questions, 1):
        system_prompt += f"{i}. {question}\n"

    system_prompt += "\n---\n\n# 开始回答\n请基于以上信息，严格按照指定 JSON 格式输出你的观点。"

    return system_prompt


async def run_convergent_phase(
    user_query: str,
    consensus_points: List[str],
    conflict_points: List[str],
    questions: List[str]
) -> List[Dict[str, Any]]:
    """
    Run convergent phase where models respond independently to chairman's questions.

    Args:
        user_query: The user's question
        consensus_points: List of consensus points from chairman
        conflict_points: List of conflict points from chairman
        questions: List of questions for next round

    Returns:
        List of convergent phase responses
    """
    convergent_results = []

    # Build convergent prompt
    prompt = build_convergent_prompt(user_query, consensus_points, conflict_points, questions)
    messages = [{"role": "user", "content": prompt}]

    # Log convergent phase prompt for debugging
    print(f"\n=== Convergent Phase Prompt ===")
    print(f"Prompt length: {len(prompt)} characters")
    print("Prompt content:")
    print("-" * 80)
    print(prompt)
    print("-" * 80)

    # Query all models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    for model, response in responses.items():
        if response is not None:
            response_text = response.get('content', '')
            parsed_json = validate_and_parse_json(response_text, model)

            # Log convergent phase response for debugging
            print(f"\n=== Convergent Phase - Response from {model} ===")
            print(f"Response length: {len(response_text)} characters")
            print("Response content:")
            print("-" * 80)
            print(response_text)
            print("-" * 80)

            convergent_results.append({
                "model": model,
                "response": response_text,
                "parsed_json": parsed_json
            })

    return convergent_results




async def run_full_council_stream(user_query: str):
    """
    Run the complete multi-round council process with streaming output.

    Args:
        user_query: The user's question

    Yields:
        Dict events for each stage of completion
    """
    # IMMEDIATE YIELD to avoid timeout - let frontend know we're starting
    yield {
        "type": "initializing",
        "data": {
            "message": "Initializing multi-round council process...",
            "user_query": user_query
        }
    }

    all_rounds_results = []
    max_rounds = 5  # Maximum rounds including divergent phase

    # Round 1: Divergent Phase
    print(f"\n=== Round 1: Divergent Phase ===")

    # Yield round start event
    yield {
        "type": "round_start",
        "data": {
            "round": 1,
            "type": "divergent",
            "message": "Starting divergent phase - gathering initial perspectives..."
        }
    }

    # Process models one by one for streaming individual responses
    accumulated_responses = []
    divergent_results = []

    for i, model in enumerate(COUNCIL_MODELS):
        # Build prompt with accumulated context
        prompt = build_divergent_prompt(user_query, accumulated_responses)
        messages = [{"role": "user", "content": prompt}]

        # Query the model
        response = await query_model(model, messages)

        if response is not None:
            response_text = response.get('content', '')
            parsed_json = validate_and_parse_json(response_text, model)

            result = {
                "model": model,
                "response": response_text,
                "parsed_json": parsed_json
            }

            divergent_results.append(result)
            accumulated_responses.append(result)

            # Yield individual model response
            yield {
                "type": "model_response_complete",
                "data": {
                    "round": 1,
                    "model": model,
                    "response": response_text,
                    "parsed_json": parsed_json,
                    "completed_models": i + 1,
                    "total_models": len(COUNCIL_MODELS)
                }
            }

    # If no models responded successfully, send error
    if not divergent_results:
        yield {
            "type": "error",
            "message": "All models failed to respond. Please try again."
        }
        return

    # Add round to results
    round_data = {
        "round": 1,
        "type": "divergent",
        "responses": divergent_results
    }
    all_rounds_results.append(round_data)

    # Evaluate convergence after divergent phase
    chairman_assessment = await evaluate_convergence(user_query, divergent_results, 1)

    # Add chairman assessment to results
    round_data["chairman_assessment"] = chairman_assessment

    # Yield round complete event
    yield {
        "type": "round_complete",
        "data": {
            "round": 1,
            "type": "divergent",
            "responses": divergent_results,
            "chairman_assessment": chairman_assessment,
            "is_converged": chairman_assessment.get("is_converged", False),
            "convergence_score": chairman_assessment.get("convergence_score", 0.0)
        }
    }

    # Check if converged after divergent phase
    if chairman_assessment.get("is_converged", False):
        print(f"\n=== Converged after divergent phase ===")
        final_result = {
            "model": CHAIRMAN_MODEL,
            "response": chairman_assessment.get("final_integrated_conclusion", "")
        }

        yield {
            "type": "complete",
            "data": {
                "all_rounds": all_rounds_results,
                "stage2": [],  # No stage2 in multi-round format
                "final_result": final_result,
                "metadata": {"converged_round": 1}
            }
        }

        # Yield final results for storage
        yield {
            "type": "final_results",
            "data": {
                "all_rounds": all_rounds_results,
                "stage2": [],  # No stage2 in multi-round format
                "final_result": final_result,
                "metadata": {"converged_round": 1}
            }
        }
        return

    # Continue with convergent phases
    current_round = 2
    while current_round <= max_rounds:
        print(f"\n=== Round {current_round}: Convergent Phase ===")

        # Yield round start event
        yield {
            "type": "round_start",
            "data": {
                "round": current_round,
                "type": "convergent",
                "message": f"Starting convergent phase round {current_round}..."
            }
        }

        # Run convergent phase with streaming
        convergent_results = []
        prompt = build_convergent_prompt(
            user_query,
            chairman_assessment["consensus_points"],
            chairman_assessment["conflict_points"],
            chairman_assessment["questions_for_next_round"]
        )
        messages = [{"role": "user", "content": prompt}]

        # Query models in parallel but stream individual results
        responses = await query_models_parallel(COUNCIL_MODELS, messages)

        for i, (model, response) in enumerate(responses.items()):
            if response is not None:
                response_text = response.get('content', '')
                parsed_json = validate_and_parse_json(response_text, model)

                result = {
                    "model": model,
                    "response": response_text,
                    "parsed_json": parsed_json
                }

                convergent_results.append(result)

                # Yield individual model response
                yield {
                    "type": "model_response_complete",
                    "data": {
                        "round": current_round,
                        "model": model,
                        "response": response_text,
                        "parsed_json": parsed_json,
                        "completed_models": i + 1,
                        "total_models": len([r for r in responses.values() if r is not None])
                    }
                }

        # Add round to results
        round_data = {
            "round": current_round,
            "type": "convergent",
            "responses": convergent_results
        }
        all_rounds_results.append(round_data)

        # Evaluate convergence
        chairman_assessment = await evaluate_convergence(user_query, convergent_results, current_round)

        # Add chairman assessment to results
        round_data["chairman_assessment"] = chairman_assessment

        # Yield round complete event
        yield {
            "type": "round_complete",
            "data": {
                "round": current_round,
                "type": "convergent",
                "responses": convergent_results,
                "chairman_assessment": chairman_assessment,
                "is_converged": chairman_assessment.get("is_converged", False),
                "convergence_score": chairman_assessment.get("convergence_score", 0.0)
            }
        }

        # Check if converged
        if chairman_assessment.get("is_converged", False):
            print(f"\n=== Converged after round {current_round} ===")
            final_result = {
                "model": CHAIRMAN_MODEL,
                "response": chairman_assessment.get("final_integrated_conclusion", "")
            }

            yield {
                "type": "complete",
                "data": {
                    "all_rounds": all_rounds_results,
                    "stage2": [],  # No stage2 in multi-round format
                    "final_result": final_result,
                    "metadata": {"converged_round": current_round}
                }
            }

            # Yield final results for storage
            yield {
                "type": "final_results",
                "data": {
                    "all_rounds": all_rounds_results,
                    "stage2": [],  # No stage2 in multi-round format
                    "final_result": final_result,
                    "metadata": {"converged_round": current_round}
                }
            }
            return

        current_round += 1

    # If reached max rounds without convergence
    print(f"\n=== Reached maximum rounds ({max_rounds}) without convergence ===")
    final_result = {
        "model": CHAIRMAN_MODEL,
        "response": chairman_assessment.get("final_integrated_conclusion", "Maximum rounds reached without convergence")
    }

    yield {
        "type": "complete",
        "data": {
            "all_rounds": all_rounds_results,
            "stage2": [],  # No stage2 in multi-round format
            "final_result": final_result,
            "metadata": {"converged_round": None}
        }
    }

    # Yield final results for storage
    yield {
        "type": "final_results",
        "data": {
            "all_rounds": all_rounds_results,
            "stage2": [],  # No stage2 in multi-round format
            "final_result": final_result,
            "metadata": {"converged_round": None}
        }
    }
