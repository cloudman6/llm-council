"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Optional
import json
from .openrouter import query_models_parallel, query_model
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL


async def divergent_phase_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Divergent Phase: responses where each model provides their own perspective without seeing others' responses.

    Args:
        user_query: The user's question

    Returns:
        List of dicts with 'model', 'response', and 'parsed_json' keys
    """
    divergent_results = []

    # Build prompt for responses (no accumulated context)
    prompt = build_divergent_prompt(user_query)

    # Query all models in parallel for responses
    responses = await query_models_parallel(COUNCIL_MODELS, [{"role": "user", "content": prompt}])

    # Process responses
    for model, response in responses.items():
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


def build_divergent_prompt(user_query: str) -> str:
    """
    Build prompt for divergent phase where each model responds without seeing others' responses.

    Args:
        user_query: The user's question

    Returns:
        Formatted prompt string
    """
    # Optimized divergent phase prompt for responses
    system_prompt = """# 角色与任务

## 角色定义
你是多智能体协作系统的 AI 模型，参与发散阶段的讨论。你将独立提供观点，看不到其他模型的想法。

## 核心任务
- 围绕用户问题提供你独特的观点
- 从你的角度分析问题，独立思考
- 使用结构化 JSON 格式输出

---

# 输出格式

必须严格遵守以下 JSON 格式：

```json
{{
  "summary": "你对问题的思考简述",
  "viewpoints": ["你的主要观点1", "你的主要观点2", "你的主要观点3", ...],
  "final_answer_candidate": "基于你的独立分析给出的初步答案"
}}
```

---

# 用户原始问题
{user_query}

---

# 开始回答
请严格按照指定 JSON 格式输出你的独立观点。"""

    return system_prompt.format(user_query=user_query)


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

        # Validate required fields for convergent phase
        required_fields = ['summary', 'viewpoints', 'final_answer_candidate']

        # Optional fields for convergent phase analysis
        optional_fields = ['consensus_analysis', 'conflict_analysis', 'conflicts', 'suggestions']

        for field in required_fields:
            if field not in parsed:
                print(f"Warning: Model {model_name} missing required field '{field}' in JSON")
                # Try to create missing field from available data
                if field == 'viewpoints' and 'summary' in parsed:
                    parsed['viewpoints'] = [parsed['summary']]
                elif field == 'summary' and 'viewpoints' in parsed:
                    parsed['summary'] = ' '.join(parsed['viewpoints'][:2]) if parsed['viewpoints'] else "No summary provided"
                else:
                    parsed[field] = "" if field == 'final_answer_candidate' else []

        # Ensure optional fields exist with appropriate defaults
        for field in optional_fields:
            if field not in parsed:
                if field in ['consensus_analysis', 'conflict_analysis']:
                    parsed[field] = []  # These should be arrays of objects
                else:
                    parsed[field] = []  # conflicts and suggestions should be arrays

        return parsed

    except json.JSONDecodeError as e:
        print(f"Warning: Model {model_name} returned invalid JSON: {e}")
        print(f"Response text: {response_text}")
        return {}


async def evaluate_convergence(
    user_query: str,
    round_responses: List[Dict[str, Any]],
    round_number: int,
    previous_chairman_response: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluate convergence and generate chairman's assessment.

    Args:
        user_query: The user's question
        round_responses: List of model responses for this round
        round_number: Current round number (1 for divergent, 2+ for convergent)
        previous_chairman_response: Previous round's chairman assessment for context

    Returns:
        Chairman's assessment in JSON format
    """
    # Build responses text for chairman
    responses_text = "\n\n".join([
        f"{result['model']}:\n{result['response']}"
        for result in round_responses
    ])

    # Build previous chairman context section if available
    previous_chairman_context = ""
    if previous_chairman_response and round_number > 1:
        # Format the detailed previous round context for better comparison
        prev_consensus = previous_chairman_response.get('consensus_points', [])
        prev_conflicts = previous_chairman_response.get('conflict_points', [])
        prev_questions = previous_chairman_response.get('questions_for_next_round', [])
        prev_score = previous_chairman_response.get('convergence_score', 'N/A')
        prev_converged = previous_chairman_response.get('is_converged', 'N/A')
        prev_explanation = previous_chairman_response.get('explanation', 'N/A')

        previous_chairman_context = f"""

## 上一轮讨论状态回顾 (第{round_number-1}轮)

### 上一轮关键指标
- **收敛评分**: {prev_score}/1.0
- **收敛状态**: {prev_converged}

### 上一轮识别的共识点
{chr(10).join([f"- {point}" for point in prev_consensus]) if prev_consensus else "- 无明确共识点"}

### 上一轮识别的主要冲突点
{chr(10).join([f"- {point}" for point in prev_conflicts]) if prev_conflicts else "- 无显著冲突点"}

### 上一轮提出的引导问题
{chr(10).join([f"{i+1}. {q}" for i, q in enumerate(prev_questions)]) if prev_questions else "- 无特定引导问题"}

### 上一轮收敛分析
{prev_explanation}

## 🔍 本轮对比分析要求

**在评估本轮讨论时，你必须进行以下对比分析：**

### 1. 观点演进对比
- **对比上一轮共识点**: 本轮是否强化了这些共识？是否有所修正？
- **对比上一轮冲突点**: 本轮是否解决了这些冲突？是否产生了新的冲突？
- **新观点识别**: 本轮出现了哪些上一轮没有的新观点或新角度？

### 2. 讨论进展评估
- **问题响应度**: 本轮回复是否有效回应了上一轮提出的引导问题？
- **收敛轨迹**: 讨论是朝着收敛方向发展还是出现了新的分歧？
- **深度变化**: 相比上一轮，讨论的深度和广度是否有提升？

### 3. 决策依据
- **稳定性判断**: 本轮相比上一轮是否更加稳定（观点不再大幅变化）？
- **充分性评估**: 现有的共识点和已解决的冲突点是否足以形成高质量答案？
- **剩余分歧价值**: 剩余的分歧点是否对最终答案质量有实质性影响？

**特别注意**: 收敛不等于完全一致，而是指讨论框架稳定、分歧明确且可控，能够形成综合性的高质量答案。
"""

    # Build optimized chairman prompt with clear structure
    chairman_prompt = f"""# 角色定义
你是多智能体协作系统的 Chairman LLM（主持人模型），负责引导讨论进程并评估收敛状态。

---

# 核心任务

## 1. 内容分析
- **深度分析**: 分析各 LLM 的最新回复内容，提取核心观点和论证逻辑
- **对比分析**: 对比上一轮的共识点和冲突点，识别观点演进轨迹
- **收敛评估**: 判断本轮讨论是否真正"趋于收敛"（稳定化）

## 2. 收敛评估标准

### 收敛的关键指标（注意：收敛 ≠ 全体同意）
- **观点稳定性**: 各模型不再提出显著新的关键观点，讨论框架趋于稳定
- **分歧清晰性**: 剩余分歧具体、明确且可管理，不再扩散到新的领域
- **结构完整性**: 讨论形成了稳定的知识框架（明确共识点 + 清晰分歧点）
- **答案充分性**: 现有信息足以生成高质量、综合性的答案

### 收敛评估的具体维度（综合评分 0-1）

#### 维度1：观点演进稳定性 (25%)
- **对比上一轮**: 本轮相比上一轮是否出现显著的新观点？
- **创新度**: 新出现的观点是实质性创新还是边际补充？
- **收敛迹象**: 观点变化是否趋于平缓？

#### 维度2：分歧管理效果 (25%)
- **冲突解决**: 本轮是否有效解决了上一轮识别的关键冲突点？
- **新冲突涌现**: 是否出现了重要的新分歧领域？
- **分歧质量**: 剩余分歧是否具有实质性价值，还是细节差异？

#### 维度3：讨论结构化程度 (25%)
- **框架稳定性**: 讨论是否形成了相对稳定的分析框架？
- **逻辑完整性**: 关键议题是否都得到了充分讨论？
- **层次清晰度**: 共识点和分歧点的层次关系是否明确？

#### 维度4：综合答案质量 (25%)
- **信息充分性**: 当前讨论内容是否足以支撑高质量答案？
- **平衡性**: 是否涵盖了问题的主要方面和不同角度？
- **实用性**: 基于现有讨论能否提供有价值的指导或结论？

## 3. 决策输出机制
- **若已收敛**: 必须输出最终综合结论，整合共识点并客观反映分歧点
- **若未收敛**: 必须生成针对下一轮的具体引导问题，聚焦于未解决的关键分歧

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
  "questions_for_next_round": ["问题1", "问题2", "问题3", ...],
  "final_integrated_conclusion": "如果需要停止讨论，请给出最终综合答案"
}}
```

## 输出规则
- 若 `is_converged = true` → 必须输出高质量的 `final_integrated_conclusion`
- 若 `is_converged = false` → 必须输出精准的 `questions_for_next_round`

---

# 分析方法论

## 对比分析流程
**必须按照以下步骤进行系统性对比分析：**

### Step 1: 上一轮状态回顾（如果有）
- 重新审视上一轮的共识点、冲突点和引导问题
- 评估上一轮的收敛评分和判断依据

### Step 2: 本轮内容解析
- 提取每个模型的核心观点和论证逻辑
- 识别本轮新出现的观点、证据或角度

### Step 3: 演进轨迹分析
- **共识演进**: 上一轮的共识点在本轮是否得到强化、修正或挑战？
- **冲突管理**: 上一轮的冲突点是否得到解决、深化或转化？
- **新贡献评估**: 本轮的新观点是否具有实质性价值？

### Step 4: 收敛状态判断
- **稳定性评估**: 相比上一轮，讨论是否更加稳定？
- **充分性判断**: 现有讨论是否足以支撑高质量答案？
- **分歧价值评估**: 剩余分歧是否对答案质量有实质性影响？

## 收敛判断准则

### 明确收敛的情况（建议评分≥0.85）
- 观点演进趋于平缓，不再有实质性的新角度出现
- 主要冲突点已得到充分讨论和有效管理
- 讨论框架稳定，共识和分歧层次清晰
- 基于现有内容能够生成综合性、高质量的答案

### 继续讨论的情况（建议评分<0.85）
- 仍有重要的新观点或证据可以引入
- 关键冲突点尚未得到充分探讨或有效解决
- 讨论框架仍在演变，不够稳定
- 现有信息不足以生成全面、平衡的答案

---

# 待分析内容

## 用户原始问题
{user_query}

{previous_chairman_context}

## 本轮 LLM 回复内容
{responses_text}

---

# 开始分析
**严格按照上述对比分析流程，基于所有信息进行深度分析，并按照指定格式输出你的评估结果。**

**特别注意**:
- 必须充分对比本轮与上一轮的观点演进
- 收敛判断要基于讨论质量，而非观点一致性
- 最终答案要客观反映共识点和分歧点
"""

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
    # Optimized convergent phase prompt with enhanced consensus/conflict analysis
    system_prompt = """# 角色与任务

## 角色定义
你是多智能体协作系统的 AI 模型，参与收敛阶段的讨论。你的任务不仅仅是回答问题，还要深度分析上一轮的讨论结果。

## 核心任务

### 🔍 深度分析上一轮讨论结果

#### 1. 共识点深度分析
**对每个共识点，你必须思考并回答：**
- **同意程度**: 你完全同意、部分同意还是不同意这个共识点？
- **补充说明**: 你是否能为这个共识点提供额外的证据、例子或细节？
- **限制条件**: 这个共识点在什么条件下成立？有什么例外情况？
- **深化理解**: 你能从什么新的角度或更深层次来解释这个共识点？

#### 2. 冲突点深度分析
**对每个冲突点，你必须思考并回答：**
- **立场选择**: 你在这个冲突点上倾向于哪种观点？为什么？
- **调和方案**: 你能提出什么方式来调和或解决这个冲突？
- **根本原因**: 这个冲突点的根本原因是什么？是价值观差异、事实争议还是方法论分歧？
- **影响评估**: 这个冲突点对最终答案的实质影响有多大？是否是关键分歧？

### 🎯 回答Chairman问题
- 基于上述深度分析，回答本轮Chairman提出的问题
- 将你的分析结论与问题回答有机结合
- 推进讨论向收敛方向发展

### 📋 结构化输出
- 使用结构化 JSON 格式输出你的分析结果
- 确保分析深度和逻辑清晰性

---

# 输出格式

## 必须严格遵守以下 JSON 格式：

```json
{
  "summary": "本轮你的思考简述，重点说明对共识点和冲突点的深度分析",
  "viewpoints": ["你的主要观点1", "你的主要观点2", "你的主要观点3", ...],
  "consensus_analysis": [
    {
      "consensus_point": "对应的共识点",
      "agreement_level": "完全同意/部分同意/不同意",
      "supplement": "你的补充说明或新证据",
      "conditions": "成立条件或例外情况",
      "deeper_insight": "更深层次的理解或角度"
    }
  ],
  "conflict_analysis": [
    {
      "conflict_point": "对应的冲突点",
      "your_position": "你的立场和理由",
      "reconciliation_approach": "调和或解决冲突的建议",
      "root_cause": "冲突的根本原因分析",
      "impact_assessment": "对最终答案的影响程度"
    }
  ],
  "conflicts": [
    "你与其他模型的主要不同点（基于上述分析）"
  ],
  "suggestions": [
    "基于你的深度分析，讨论应该增加或修正的内容"
  ],
  "final_answer_candidate": "如果你需要提供最终答案，请放在这里"
}
```

## 输出要求
1. **必须使用 JSON 格式**，不得包含解释性文字
2. **深度分析要求**: 对每个共识点和冲突点都要进行深入分析，不得简单重复
3. **逻辑清晰**: 分析要有明确的逻辑链条和证据支持
4. **建设性导向**: 不仅要分析问题，还要提出解决方案

---

# 讨论上下文

## 📊 上一轮 Chairman 评估结果

### 🎯 已识别的共识点（要求深度分析）
"""

    # Add consensus points with analysis guidance
    system_prompt += "**请对以下每个共识点进行深度分析（必须包含：同意程度、补充说明、限制条件、深化理解）：**\n"
    for i, point in enumerate(consensus_points, 1):
        system_prompt += f"{i}. **{point}**\n   - *你的分析要求：同意程度？补充证据？成立条件？深层理解？*\n"

    system_prompt += "\n### ⚡ 已识别的冲突点（要求深度分析）\n"
    system_prompt += "**请对以下每个冲突点进行深度分析（必须包含：立场选择、调和方案、根本原因、影响评估）：**\n"
    for i, point in enumerate(conflict_points, 1):
        system_prompt += f"{i}. **{point}**\n   - *你的分析要求：你的立场？解决建议？根本原因？影响程度？*\n"

    system_prompt += "\n---\n\n# 🎯 本轮核心任务\n\n## 📋 用户原始问题\n"
    system_prompt += f"{user_query}\n\n"

    system_prompt += "## ❓ 本轮必须回答的问题\n"
    for i, question in enumerate(questions, 1):
        system_prompt += f"{i}. **{question}**\n   - *回答要求：请结合上述对共识点和冲突点的深度分析来回答这个问题*\n"

    system_prompt += "\n## 🔗 整合要求\n"
    system_prompt += "**你的回答必须体现以下整合能力：**\n"
    system_prompt += "1. **分析整合**: 将你对共识点和冲突点的深度分析与问题回答有机结合\n"
    system_prompt += "2. **演进视角**: 说明你的分析如何帮助讨论从分歧走向共识\n"
    system_prompt += "3. **解决方案**: 针对冲突点提出具体的调和或解决方案\n"
    system_prompt += "4. **收敛导向**: 你的观点如何促进整个讨论的收敛\n"

    system_prompt += "\n---\n\n# 🚀 开始回答\n**请严格基于以上深度分析要求，按照指定 JSON 格式输出你的观点。你的分析深度将直接影响讨论的收敛质量。**"

    return system_prompt


async def run_convergent_phase(
    user_query: str,
    consensus_points: List[str],
    conflict_points: List[str],
    questions: List[str]
) -> List[Dict[str, Any]]:
    """
    Run convergent phase where models respond to chairman's questions.

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
    previous_chairman_assessment = None  # Track previous chairman response

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

    # Build prompt for all models (no accumulated context)
    prompt = build_divergent_prompt(user_query)
    messages = [{"role": "user", "content": prompt}]

    # Enhanced debugging for streaming divergent phase
    print(f"\n{'='*100}", flush=True)
    print(f"🚀 STREAMING - Round 1 Divergent Phase - Parallel Query", flush=True)
    print(f"📝 Prompt length: {len(prompt)} characters", flush=True)
    print(f"📤 Sending prompt to all {len(COUNCIL_MODELS)} models in parallel...", flush=True)
    print("─" * 80, flush=True)
    print(prompt, flush=True)
    print("─" * 80, flush=True)

    # Query all models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Process and stream individual results
    divergent_results = []
    completed_models = 0

    for i, (model, response) in enumerate(responses.items()):
        if response is not None:
            response_text = response.get('content', '')
            parsed_json = validate_and_parse_json(response_text, model)

            # Enhanced debugging for response
            print(f"📥 Parallel response {i+1}/{len(responses)} from {model}", flush=True)
            print(f"📊 Response length: {len(response_text)} characters", flush=True)
            print("─" * 80, flush=True)
            print(response_text, flush=True)
            print("─" * 80, flush=True)

            if parsed_json:
                print(f"✅ JSON parsing successful for {model}", flush=True)
                print(f"📋 Parsed structure: {list(parsed_json.keys())}", flush=True)
            else:
                print(f"⚠️  JSON parsing failed for {model}", flush=True)

            result = {
                "model": model,
                "response": response_text,
                "parsed_json": parsed_json
            }

            divergent_results.append(result)
            completed_models += 1

            # Yield individual model response
            yield {
                "type": "model_response_complete",
                "data": {
                    "round": 1,
                    "model": model,
                    "response": response_text,
                    "parsed_json": parsed_json,
                    "completed_models": completed_models,
                    "total_models": len(COUNCIL_MODELS)
                }
            }

            print(f"✅ Model {model} response completed and yielded", flush=True)
        else:
            print(f"❌ Model {model} failed to respond", flush=True)

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

    # Enhanced debugging for chairman evaluation after divergent phase
    print(f"\n{'='*100}", flush=True)
    print(f"🔍 STREAMING - Round 1 Divergent Phase Complete - Chairman Evaluation", flush=True)
    print(f"📊 Total divergent responses: {len(divergent_results)}", flush=True)
    print(f"📤 Sending divergent responses to chairman: {CHAIRMAN_MODEL}", flush=True)
    print("─" * 80, flush=True)

    # Evaluate convergence after divergent phase
    chairman_assessment = await evaluate_convergence(user_query, divergent_results, 1, previous_chairman_assessment)

    # Add chairman assessment to results
    round_data["chairman_assessment"] = chairman_assessment

    # Enhanced debugging for chairman assessment
    convergence_score = chairman_assessment.get("convergence_score", 0.0)
    is_converged = chairman_assessment.get("is_converged", False)
    print(f"📋 Chairman assessment complete:", flush=True)
    print(f"   🎯 Convergence Score: {convergence_score}/1.0", flush=True)
    print(f"   ✅ Is Converged: {is_converged}", flush=True)
    print(f"   💭 Consensus Points: {len(chairman_assessment.get('consensus_points', []))}", flush=True)
    print(f"   ⚡ Conflict Points: {len(chairman_assessment.get('conflict_points', []))}", flush=True)
    print("─" * 80, flush=True)

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

    # Update previous chairman assessment for next round
    previous_chairman_assessment = chairman_assessment

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

        # Enhanced debugging for streaming convergent phase
        print(f"\n{'='*100}", flush=True)
        print(f"🚀 STREAMING - Round {current_round} Convergent Phase - Parallel Query", flush=True)
        print(f"📝 Prompt length: {len(prompt)} characters", flush=True)
        print(f"📤 Sending prompt to all models in parallel...", flush=True)
        print("─" * 80, flush=True)
        print(prompt, flush=True)
        print("─" * 80, flush=True)

        # Query models in parallel but stream individual results
        responses = await query_models_parallel(COUNCIL_MODELS, messages)

        successful_responses = len([r for r in responses.values() if r is not None])
        print(f"📊 Parallel query completed: {successful_responses}/{len(COUNCIL_MODELS)} models responded", flush=True)

        for i, (model, response) in enumerate(responses.items()):
            if response is not None:
                response_text = response.get('content', '')
                parsed_json = validate_and_parse_json(response_text, model)

                # Enhanced debugging for each model response
                print(f"\n📥 Parallel response {i+1}/{successful_responses} from {model}", flush=True)
                print(f"📊 Response length: {len(response_text)} characters", flush=True)
                print("─" * 60, flush=True)
                print(response_text, flush=True)
                print("─" * 60, flush=True)

                if parsed_json:
                    print(f"✅ JSON parsing successful for {model}", flush=True)
                    print(f"📋 Parsed structure: {list(parsed_json.keys())}", flush=True)
                else:
                    print(f"⚠️  JSON parsing failed for {model}", flush=True)

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
                        "total_models": successful_responses
                    }
                }

                print(f"✅ Model {model} convergent response completed and yielded", flush=True)
            else:
                print(f"❌ Model {model} failed to respond in convergent phase", flush=True)

        # Add round to results
        round_data = {
            "round": current_round,
            "type": "convergent",
            "responses": convergent_results
        }
        all_rounds_results.append(round_data)

        # Enhanced debugging for chairman evaluation after convergent phase
        print(f"\n{'='*100}", flush=True)
        print(f"🔍 STREAMING - Round {current_round} Convergent Phase Complete - Chairman Evaluation", flush=True)
        print(f"📊 Total convergent responses: {len(convergent_results)}", flush=True)
        print(f"📤 Sending convergent responses to chairman: {CHAIRMAN_MODEL}", flush=True)
        print("─" * 80, flush=True)

        # Evaluate convergence
        chairman_assessment = await evaluate_convergence(user_query, convergent_results, current_round, previous_chairman_assessment)

        # Add chairman assessment to results
        round_data["chairman_assessment"] = chairman_assessment

        # Enhanced debugging for chairman assessment
        convergence_score = chairman_assessment.get("convergence_score", 0.0)
        is_converged = chairman_assessment.get("is_converged", False)
        print(f"📋 Chairman assessment complete:", flush=True)
        print(f"   🎯 Convergence Score: {convergence_score}/1.0", flush=True)
        print(f"   ✅ Is Converged: {is_converged}", flush=True)
        print(f"   💭 Consensus Points: {len(chairman_assessment.get('consensus_points', []))}", flush=True)
        print(f"   ⚡ Conflict Points: {len(chairman_assessment.get('conflict_points', []))}", flush=True)
        print("─" * 80, flush=True)

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

        # Update previous chairman assessment for next round
        previous_chairman_assessment = chairman_assessment

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
