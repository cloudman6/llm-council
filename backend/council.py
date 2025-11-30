"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Optional
import json
from .openrouter import query_models_parallel, query_model
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL, CONVERGENCE_THRESHOLD


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

**IMPORTANT**: The title must be in the same language as the question. If the question is in Chinese, the title should be in Chinese. If the question is in English, the title should be in English, etc.

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
    system_prompt = """# Role and Task

## Role Definition
You are an AI model in a multi-agent collaboration system, participating in the divergent phase discussion. You will provide independent viewpoints and cannot see other models' thoughts.

## Core Task
- Provide your unique perspectives on the user's question
- Analyze the question from your angle, think independently
- Use structured JSON format for output

## Language Consistency Requirement
**IMPORTANT**: The language of your response MUST match the language of the user's question:
- If the user asks in English, respond in English
- If the user asks in Chinese (中文), respond in Chinese (中文)
- If the user asks in any other language, respond in the same language
- Maintain language consistency throughout your entire response

---

# Output Format

Must strictly adhere to the following JSON format:

```json
{{
  "summary": "Brief description of your thinking on the question",
  "viewpoints": ["Your main viewpoint 1", "Your main viewpoint 2", "Your main viewpoint 3", ...],
  "final_answer_candidate": "Preliminary answer based on your independent analysis"
}}
```

---

# User's Original Question
{user_query}

---

# Start Answering
Please output your independent viewpoints strictly according to the specified JSON format."""

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

## Previous Round Discussion Status Review (Round {round_number-1})

### Previous Round Key Metrics
- **Convergence Score**: {prev_score}/1.0
- **Convergence Status**: {prev_converged}

### Previous Round Identified Consensus Points
{chr(10).join([f"- {point}" for point in prev_consensus]) if prev_consensus else "- No clear consensus points"}

### Previous Round Identified Main Conflict Points
{chr(10).join([f"- {point}" for point in prev_conflicts]) if prev_conflicts else "- No significant conflict points"}

### Previous Round Proposed Guiding Questions
{chr(10).join([f"{i+1}. {q}" for i, q in enumerate(prev_questions)]) if prev_questions else "- No specific guiding questions"}

### Previous Round Convergence Analysis
{prev_explanation}

## 🔍 This Round Comparative Analysis Requirements

**When evaluating this round's discussion, you must perform the following comparative analysis:**

### 1. Viewpoint Evolution Comparison
- **Compare with previous round consensus points**: Has this round reinforced these consensus points? Have there been modifications?
- **Compare with previous round conflict points**: Has this round resolved these conflicts? Have new conflicts emerged?
- **New viewpoint identification**: What new viewpoints or angles have appeared in this round that were not in the previous round?

### 2. Discussion Progress Assessment
- **Question responsiveness**: Have the responses in this round effectively addressed the guiding questions proposed in the previous round?
- **Convergence trajectory**: Is the discussion moving toward convergence or have new divergences appeared?
- **Depth change**: Compared to the previous round, has the depth and breadth of the discussion improved?

### 3. Decision Basis
- **Stability judgment**: Is this round more stable compared to the previous round (viewpoints no longer changing significantly)?
- **Sufficiency assessment**: Are the existing consensus points and resolved conflict points sufficient to form a high-quality answer?
- **Remaining divergence value**: Do the remaining divergence points have a substantial impact on the quality of the final answer?

**Special Note**: Convergence does not mean complete agreement, but rather that the discussion framework is stable, divergences are clear and manageable, and a comprehensive high-quality answer can be formed.
"""

    # Build optimized chairman prompt with clear structure and configurable threshold
    chairman_prompt = f"""# Role Definition
You are the Chairman LLM (facilitator model) of a multi-agent collaboration system, responsible for guiding the discussion process and assessing convergence status.

## Language Consistency Requirement
**IMPORTANT**: The language of your response MUST match the language of the user's question:
- If the user asks in English, respond in English
- If the user asks in Chinese (中文), respond in Chinese (中文)
- If the user asks in any other language, respond in the same language
- Maintain language consistency throughout your entire response, including all JSON values

---

# Core Tasks

## 1. Content Analysis
- **Deep Analysis**: Analyze the latest response content from each LLM, extract core viewpoints and argumentation logic
- **Comparative Analysis**: Compare with previous round's consensus points and conflict points, identify viewpoint evolution trajectories
- **Convergence Assessment**: Determine whether this round's discussion is truly "converging" (stabilizing)

## 2. Convergence Assessment Standards

### Key Indicators of Convergence (Note: Convergence ≠ Complete Agreement)
- **Viewpoint Stability**: Models no longer propose significant new key viewpoints, discussion framework tends toward stability
- **Divergence Clarity**: Remaining divergences are specific, clear and manageable, no longer spreading to new areas
- **Structural Integrity**: Discussion has formed a stable knowledge framework (clear consensus points + clear divergence points)
- **Answer Sufficiency**: Existing information is sufficient to generate high-quality, comprehensive answers

### Specific Dimensions for Convergence Assessment (Comprehensive Score 0-1)

#### Dimension 1: Viewpoint Evolution Stability (25%)
- **Compare with previous round**: Have significant new viewpoints appeared in this round compared to the previous round?
- **Innovation degree**: Are new viewpoints substantive innovations or marginal supplements?
- **Convergence signs**: Are viewpoint changes becoming gradual?

#### Dimension 2: Divergence Management Effectiveness (25%)
- **Conflict resolution**: Has this round effectively resolved the key conflict points identified in the previous round?
- **New conflict emergence**: Have important new areas of divergence appeared?
- **Divergence quality**: Do remaining divergences have substantive value, or are they detailed differences?

#### Dimension 3: Discussion Structuring Level (25%)
- **Framework stability**: Has the discussion formed a relatively stable analytical framework?
- **Logical completeness**: Have key topics been adequately discussed?
- **Hierarchical clarity**: Are the hierarchical relationships between consensus points and divergence points clear?

#### Dimension 4: Comprehensive Answer Quality (25%)
- **Information sufficiency**: Is current discussion content sufficient to support a high-quality answer?
- **Balance**: Does it cover the main aspects and different angles of the question?
- **Practicality**: Can valuable guidance or conclusions be provided based on existing discussion?

## 3. Decision Output Mechanism
- **If converged**: Must output final comprehensive conclusion, integrate consensus points and objectively reflect divergence points
- **If not converged**: Must generate specific guiding questions for the next round, focusing on unresolved key divergences

---

# Output Format

## Must strictly adhere to the following JSON format:

```json
{{
  "convergence_score": 0.0-1.0,
  "is_converged": true/false,
  "consensus_points": ["Consensus point 1", "Consensus point 2", ...],
  "conflict_points": ["Conflict point 1", "Conflict point 2", ...],
  "explanation": "Why you judge it as converged/not converged",
  "questions_for_next_round": ["Question 1", "Question 2", "Question 3", ...],
  "final_integrated_conclusion": "If discussion needs to stop, provide final comprehensive answer"
}}
```

## Output Rules
- If `is_converged = true` → Must output high-quality `final_integrated_conclusion`
- If `is_converged = false` → Must output precise `questions_for_next_round`

---

# Analysis Methodology

## Comparative Analysis Process
**Must perform systematic comparative analysis following these steps:**

### Step 1: Previous Round Status Review (if available)
- Re-examine the previous round's consensus points, conflict points, and guiding questions
- Evaluate the previous round's convergence score and judgment basis

### Step 2: Current Round Content Analysis
- Extract each model's core viewpoints and argumentation logic
- Identify new viewpoints, evidence, or angles that appeared in this round

### Step 3: Evolution Trajectory Analysis
- **Consensus evolution**: Have the previous round's consensus points been reinforced, modified, or challenged in this round?
- **Conflict management**: Have the previous round's conflict points been resolved, deepened, or transformed?
- **New contribution assessment**: Do the new viewpoints in this round have substantive value?

### Step 4: Convergence State Judgment
- **Stability assessment**: Compared to the previous round, is the discussion more stable?
- **Sufficiency judgment**: Is the existing discussion sufficient to support a high-quality answer?
- **Divergence value assessment**: Do the remaining divergences have a substantive impact on answer quality?

## Convergence Judgment Criteria

### Clear Convergence Cases (score ≥ {CONVERGENCE_THRESHOLD})
- Viewpoint evolution tends to be gradual, with no substantial new angles appearing
- Main conflict points have been fully discussed and effectively managed
- Discussion framework is stable, with clear hierarchy of consensus and divergences
- Comprehensive, high-quality answers can be generated based on existing content

### Continue Discussion Cases (score < {CONVERGENCE_THRESHOLD})
- There are still important new viewpoints or evidence that can be introduced
- Key conflict points have not yet been fully explored or effectively resolved
- Discussion framework is still evolving and not stable enough
- Existing information is insufficient to generate comprehensive, balanced answers

**IMPORTANT**: You can only set `is_converged = true` when your `convergence_score` is **greater than or equal to {CONVERGENCE_THRESHOLD}**. If your score is below this threshold, you must set `is_converged = false` and provide questions for the next round.

---

# Content to Analyze

## User's Original Question
{user_query}

{previous_chairman_context}

## This Round's LLM Response Content
{responses_text}

---

# Start Analysis
**Strictly follow the above comparative analysis process, conduct deep analysis based on all information, and output your assessment results according to the specified format.**

**Special Attention**:
- Must fully compare viewpoint evolution between current and previous rounds
- Convergence judgment should be based on discussion quality, not viewpoint consistency
- Final answers should objectively reflect consensus points and divergence points
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

        # Enforce convergence threshold validation
        convergence_score = chairman_assessment.get('convergence_score', 0.0)
        is_converged = chairman_assessment.get('is_converged', False)

        # Validate convergence score is a number
        try:
            convergence_score = float(convergence_score)
        except (ValueError, TypeError):
            print(f"Warning: Chairman convergence_score '{convergence_score}' is not a number, defaulting to 0.0")
            convergence_score = 0.0
            chairman_assessment['convergence_score'] = 0.0

        # Enforce threshold: if score < threshold, force is_converged to False
        if convergence_score < CONVERGENCE_THRESHOLD and is_converged:
            print(f"Warning: Chairman set is_converged=true with score {convergence_score} < threshold {CONVERGENCE_THRESHOLD}")
            print(f"Force: Setting is_converged=false and requiring questions for next round")
            chairman_assessment['is_converged'] = False

            # Ensure we have questions for next round when not converged
            if not chairman_assessment.get('questions_for_next_round'):
                chairman_assessment['questions_for_next_round'] = [
                    f"Please continue discussion to reach convergence threshold of {CONVERGENCE_THRESHOLD}"
                ]

            # Clear final integrated conclusion when not converged
            chairman_assessment['final_integrated_conclusion'] = ""

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
    system_prompt = """# Role and Task

## Role Definition
You are an AI model in a multi-agent collaboration system, participating in the convergent phase discussion. Your task is not only to answer questions but also to deeply analyze the previous round's discussion results.

## Language Consistency Requirement
**IMPORTANT**: The language of your response MUST match the language of the user's question:
- If the user asks in English, respond in English
- If the user asks in Chinese (中文), respond in Chinese (中文)
- If the user asks in any other language, respond in the same language
- Maintain language consistency throughout your entire response, including all JSON values

## Core Tasks

### 🔍 Deep Analysis of Previous Round Discussion Results

#### 1. Deep Analysis of Consensus Points
**For each consensus point, you must think and answer:**
- **Agreement Level**: Do you completely agree, partially agree, or disagree with this consensus point?
- **Supplementary Explanation**: Can you provide additional evidence, examples, or details for this consensus point?
- **Limiting Conditions**: Under what conditions does this consensus point hold? Are there exceptions?
- **Deeper Understanding**: Can you explain this consensus point from new angles or deeper levels?

#### 2. Deep Analysis of Conflict Points
**For each conflict point, you must think and answer:**
- **Position Choice**: Which viewpoint do you tend to take on this conflict point? Why?
- **Reconciliation Approach**: What methods can you propose to reconcile or resolve this conflict?
- **Root Cause**: What is the fundamental cause of this conflict point? Is it value differences, factual disputes, or methodological disagreements?
- **Impact Assessment**: How much substantive impact does this conflict point have on the final answer? Is it a key divergence?

### 🎯 Answer Chairman Questions
- Answer the questions raised by this round's Chairman based on the above deep analysis
- Organically integrate your analysis conclusions with question answers
- Promote discussion toward convergence

### 📋 Structured Output
- Use structured JSON format to output your analysis results
- Ensure analysis depth and logical clarity

---

# Output Format

## Must strictly adhere to the following JSON format:

```json
{
  "summary": "Brief description of your thinking this round, focusing on deep analysis of consensus points and conflict points",
  "viewpoints": ["Your main viewpoint 1", "Your main viewpoint 2", "Your main viewpoint 3", ...],
  "consensus_analysis": [
    {
      "consensus_point": "Corresponding consensus point",
      "agreement_level": "Completely agree/Partially agree/Disagree",
      "supplement": "Your supplementary explanations or new evidence",
      "conditions": "Established conditions or exceptions",
      "deeper_insight": "Deeper understanding or perspective"
    }
  ],
  "conflict_analysis": [
    {
      "conflict_point": "Corresponding conflict point",
      "your_position": "Your position and reasons",
      "reconciliation_approach": "Suggestions for reconciling or resolving conflicts",
      "root_cause": "Analysis of the root cause of the conflict",
      "impact_assessment": "Degree of impact on the final answer"
    }
  ],
  "conflicts": [
    "Main differences with other models (based on above analysis)"
  ],
  "suggestions": [
    "Content that should be added or modified based on your deep analysis"
  ],
  "final_answer_candidate": "If you need to provide a final answer, put it here"
}
```

## Output Requirements
1. **Must use JSON format**, no explanatory text allowed
2. **Deep Analysis Requirements**: Conduct in-depth analysis of each consensus point and conflict point, no simple repetition
3. **Logical Clarity**: Analysis should have clear logical chains and evidence support
4. **Constructive Orientation**: Not only analyze problems but also propose solutions

---

# Discussion Context

## 📊 Previous Round Chairman Assessment Results

### 🎯 Identified Consensus Points (requiring deep analysis)
"""

    # Add consensus points with analysis guidance
    system_prompt += "**Please conduct deep analysis for each of the following consensus points (must include: agreement level, supplementary explanation, limiting conditions, deeper understanding):**\n"
    for i, point in enumerate(consensus_points, 1):
        system_prompt += f"{i}. **{point}**\n   - *Your analysis requirements: agreement level? supplementary evidence? established conditions? deeper understanding?*\n"

    system_prompt += "\n### ⚡ Identified Conflict Points (requiring deep analysis)\n"
    system_prompt += "**Please conduct deep analysis for each of the following conflict points (must include: position choice, reconciliation approach, root cause, impact assessment):**\n"
    for i, point in enumerate(conflict_points, 1):
        system_prompt += f"{i}. **{point}**\n   - *Your analysis requirements: your position? resolution suggestions? root cause? impact degree?*\n"

    system_prompt += "\n---\n\n# 🎯 This Round's Core Tasks\n\n## 📋 User's Original Question\n"
    system_prompt += f"{user_query}\n\n"

    system_prompt += "## ❓ Questions That Must Be Answered This Round\n"
    for i, question in enumerate(questions, 1):
        system_prompt += f"{i}. **{question}**\n   - *Answer requirements: Please answer this question combining the above deep analysis of consensus points and conflict points*\n"

    system_prompt += "\n## 🔗 Integration Requirements\n"
    system_prompt += "**Your answers must demonstrate the following integration capabilities:**\n"
    system_prompt += "1. **Analysis Integration**: Organically integrate your deep analysis of consensus points and conflict points with question answers\n"
    system_prompt += "2. **Evolution Perspective**: Explain how your analysis helps discussion move from divergence to consensus\n"
    system_prompt += "3. **Solution Approach**: Propose specific reconciliation or solution approaches for conflict points\n"
    system_prompt += "4. **Convergence Orientation**: How your viewpoints promote the convergence of the entire discussion\n"

    system_prompt += "\n---\n\n# 🚀 Start Answering\n**Please output your viewpoints according to the specified JSON format, strictly based on the above deep analysis requirements. Your analysis depth will directly affect the convergence quality of the discussion.**"

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
