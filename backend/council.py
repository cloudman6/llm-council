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
    # System prompt with clear structure
    system_prompt = """# 系统指令

## 任务描述
你是一名参与多智能体协同讨论系统的 AI 模型。
你的任务是围绕用户提出的问题进行讨论，基于你收到的材料进行推理、反思和表达观点。

## 输出格式要求（必须严格遵守）
1. 你的输出必须始终使用 JSON 格式，不得包含解释性文字
2. JSON 格式必须严格遵循以下结构：

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

3. 不得重复他人观点的原文，应使用你自己的语言表达
4. 不得绕开 JSON 输出
5. 保持逻辑清晰、结构化表达

---
"""


    # Context section with clear boundaries
    context_prompt = ""
    if previous_responses:
        context_prompt = """# 讨论上下文

以下是之前其他模型的讨论内容：

"""
        for i, prev_response in enumerate(previous_responses, 1):
            context_prompt += f"## 模型 {i}\n\n"
            # Show the parsed JSON directly if available, otherwise show raw response
            if prev_response.get('parsed_json'):
                parsed = prev_response['parsed_json']
                context_prompt += f"```json\n{json.dumps(parsed, ensure_ascii=False, indent=2)}\n```\n\n"
            else:
                context_prompt += f"{prev_response['response']}\n\n"
        context_prompt += "---\n"

    # Main question with clear task
    question_prompt = f"""# 任务执行

## 用户问题
{user_query}

## 你的任务
请基于上述讨论内容，提供你的观点。

**重要提示：**
- 请严格按照指定的 JSON 格式输出
- 不要包含任何额外的解释性文字
- 考虑与之前观点的异同

请开始你的回答："""

    return system_prompt + context_prompt + question_prompt


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


async def run_full_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (divergent_results, stage2_results, stage3_result, metadata)
    """
    # Divergent Phase: Sequential responses with role assignments
    divergent_results = await divergent_phase_responses(user_query)

    # If no models responded successfully, return error
    if not divergent_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # DEBUG MODE: Stop after divergent phase for debugging
    print("\n=== DEBUG MODE: Stopping after divergent phase ===")
    print(f"Returning {len(divergent_results)} divergent results")

    # Return empty stage2 and stage3 results for debugging
    return divergent_results, [], {
        "model": "debug",
        "response": "Stopped after divergent phase for debugging"
    }, {}

    # TODO: Uncomment below to re-enable full 3-stage process
    # # Stage 2: Collect rankings (using divergent phase responses as input)
    # stage2_results, label_to_model = await stage2_collect_rankings(user_query, divergent_results)
    #
    # # Calculate aggregate rankings
    # aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
    #
    # # Stage 3: Synthesize final answer
    # stage3_result = await stage3_synthesize_final(
    #     user_query,
    #     divergent_results,
    #     stage2_results
    # )
    #
    # # Prepare metadata
    # metadata = {
    #     "label_to_model": label_to_model,
    #     "aggregate_rankings": aggregate_rankings
    # }
    #
    # return divergent_results, stage2_results, stage3_result, metadata
