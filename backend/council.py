"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple
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
        print(f"\n=== Divergent Phase - Model {i+1}: {model} ===")
        print(f"Prompt length: {len(prompt)} characters")
        print("Prompt content:")
        print("-" * 80)
        print(prompt)
        print("-" * 80)

        # Query the model
        response = await query_model(model, messages)

        if response is not None:
            response_text = response.get('content', '')

            # Log response for debugging
            print(f"\n=== Response from {model} ===")
            print(f"Response length: {len(response_text)} characters")
            print("Response content:")
            print("-" * 80)
            print(response_text)
            print("-" * 80)

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


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    messages = [{"role": "user", "content": user_query}]

    # Query all models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage1_results = []
    for model, response in responses.items():
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "model": model,
                "response": response.get('content', '')
            })

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model
    response = await query_model(CHAIRMAN_MODEL, messages)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": CHAIRMAN_MODEL,
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": CHAIRMAN_MODEL,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


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
    print(f"\n=== Chairman Prompt (Round {round_number}) ===")
    print(f"Prompt length: {len(chairman_prompt)} characters")
    print("Prompt content:")
    print("-" * 80)
    print(chairman_prompt)
    print("-" * 80)

    # Query the chairman model
    response = await query_model(CHAIRMAN_MODEL, messages)

    # Log chairman response for debugging
    if response is not None:
        response_text = response.get('content', '')
        print(f"\n=== Chairman Response (Round {round_number}) ===")
        print(f"Response length: {len(response_text)} characters")
        print("Response content:")
        print("-" * 80)
        print(response_text)
        print("-" * 80)
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


async def run_full_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete multi-round council process.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (all_rounds_results, stage2_results, final_result, metadata)
    """
    all_rounds_results = []
    max_rounds = 5  # Maximum rounds including divergent phase

    # Round 1: Divergent Phase
    print(f"\n=== Round 1: Divergent Phase ===")
    divergent_results = await divergent_phase_responses(user_query)

    # If no models responded successfully, return error
    if not divergent_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    all_rounds_results.append({
        "round": 1,
        "type": "divergent",
        "responses": divergent_results
    })

    # Evaluate convergence after divergent phase
    chairman_assessment = await evaluate_convergence(user_query, divergent_results, 1)

    # Add chairman assessment to results
    all_rounds_results[-1]["chairman_assessment"] = chairman_assessment

    # Check if converged after divergent phase
    if chairman_assessment.get("is_converged", False):
        print(f"\n=== Converged after divergent phase ===")
        return all_rounds_results, [], {
            "model": CHAIRMAN_MODEL,
            "response": chairman_assessment.get("final_integrated_conclusion", "")
        }, {"converged_round": 1}

    # Continue with convergent phases
    current_round = 2
    while current_round <= max_rounds:
        print(f"\n=== Round {current_round}: Convergent Phase ===")

        # Run convergent phase
        convergent_results = await run_convergent_phase(
            user_query,
            chairman_assessment["consensus_points"],
            chairman_assessment["conflict_points"],
            chairman_assessment["questions_for_next_round"]
        )

        all_rounds_results.append({
            "round": current_round,
            "type": "convergent",
            "responses": convergent_results
        })

        # Evaluate convergence
        chairman_assessment = await evaluate_convergence(user_query, convergent_results, current_round)

        # Add chairman assessment to results
        all_rounds_results[-1]["chairman_assessment"] = chairman_assessment

        # Check if converged
        if chairman_assessment.get("is_converged", False):
            print(f"\n=== Converged after round {current_round} ===")
            return all_rounds_results, [], {
                "model": CHAIRMAN_MODEL,
                "response": chairman_assessment.get("final_integrated_conclusion", "")
            }, {"converged_round": current_round}

        current_round += 1

    # If reached max rounds without convergence
    print(f"\n=== Reached maximum rounds ({max_rounds}) without convergence ===")
    return all_rounds_results, [], {
        "model": CHAIRMAN_MODEL,
        "response": chairman_assessment.get("final_integrated_conclusion", "Maximum rounds reached without convergence")
    }, {"converged_round": None}
