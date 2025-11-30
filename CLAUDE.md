# CLAUDE.md - Technical Notes for LLM Council

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

LLM Council is a **production-ready, highly sophisticated multi-round deliberation system** where multiple LLMs collaboratively answer user questions through iterative discussion phases. The system uses advanced convergence detection, real-time streaming, and structured analysis to achieve high-quality consensus answers.

**Current Status**: Fully functional with extensive optimizations for chairman evaluation and convergent phase analysis. Includes real-time streaming, modern React UI, and comprehensive testing suite.

## Architecture

### Backend Structure (`backend/`)

**`config.py`**
- Contains `COUNCIL_MODELS` (list of OpenRouter model identifiers)
- Contains `CHAIRMAN_MODEL` (model that synthesizes final answer)
- Uses environment variable `OPENROUTER_API_KEY` from `.env`
- Backend runs on **port 8001** (NOT 8000 - user had another app on 8000)
- **Current Models (Free Tier)**:
  - `z-ai/glm-4.5-air:free` (Council + Chairman)
  - `x-ai/grok-4.1-fast:free`
  - `tngtech/deepseek-r1t2-chimera:free`
  - `kwaipilot/kat-coder-pro:free`

**`openrouter.py`**
- `query_model()`: Single async model query
- `query_models_parallel()`: Parallel queries using `asyncio.gather()`
- Returns dict with 'content' and optional 'reasoning_details'
- Graceful degradation: returns None on failure, continues with successful responses

**`council.py`** - The Core Logic (**HEAVILY OPTIMIZED**)
- `divergent_phase_responses()`: Sequential responses where each model sees all previous responses
- `evaluate_convergence()`: **OPTIMIZED** - Chairman assesses convergence with systematic round-by-round comparison analysis
- `run_convergent_phase()`: **ENHANCED** - Deep analysis requirements with structured JSON output
- `build_divergent_prompt()`: Builds prompt for divergent phase with accumulated context
- `build_convergent_prompt()`: **COMPLETELY REWRITTEN** - Forces deep analysis of consensus/conflict points
- `run_full_council_stream()`: **ADVANCED** - Real-time streaming with Server-Sent Events

**Recent Major Optimizations:**
1. **Chairman Evaluation Enhancement** (`CHAIRMAN_OPTIMIZATION_SUMMARY.md`):
   - Systematic comparison between rounds with 4-dimension evaluation
   - Detailed previous-round context with structured analysis requirements
   - Clear distinction between "converged" and "consistent" states
   - Convergence detection threshold: ≥0.8 (converged), ≤0.7 (continue discussion)

2. **Convergent Phase Deep Analysis** (`CONVERGENT_OPTIMIZATION_SUMMARY.md`):
   - Mandatory deep analysis of each consensus point (agreement, supplements, conditions, insights)
   - Mandatory deep analysis of each conflict point (position, reconciliation, root cause, impact)
   - New JSON fields: `consensus_analysis[]`, `conflict_analysis[]`
   - Integration requirements: analysis must combine with question answering

**`storage.py`**
- JSON-based conversation storage in `data/conversations/`
- Each conversation: `{id, created_at, messages[]}`
- Assistant messages contain: `{role, all_rounds, final_result}`
- Note: metadata (converged_round) is persisted to storage

**`main.py`** - **ADVANCED API LAYER**
- FastAPI app with CORS enabled for localhost:5173 and localhost:3000
- **Streaming API**: `/api/conversations/{id}/message/stream` with Server-Sent Events
- **Batch API**: `/api/conversations/{id}/message` for traditional request/response
- **Conversation Management**: Full CRUD with automatic title generation (Gemini-2.5-flash)
- DELETE `/api/conversations/{id}` deletes a conversation with modern UI confirmation
- **Metadata Persistence**: Complete conversation state including convergence round
- **Real-time Events**: Individual model completion, round updates, final results streaming
- **Error Handling**: Graceful degradation with proper error events and partial success handling

### Frontend Structure (`frontend/src/`) - **MODERN REACT 19.2.0**

**`App.jsx`** - **SOPHISTICATED STATE MANAGEMENT**
- Advanced streaming event handling with Server-Sent Events
- Real-time UI updates during multi-round discussions
- Optimistic UI updates with graceful error handling
- Conversation state management with comprehensive loading indicators
- Automatic conversation title updates from backend

**`components/ChatInterface.jsx`** - **ENHANCED USER EXPERIENCE**
- Clean, modern interface with proper markdown rendering
- Real-time loading states with round-by-round progress tracking
- Support for both streaming and non-streaming responses
- Responsive design with proper error state handling

**`components/MultiRoundDiscussion.jsx`** - **HIGHLY SOPHISTICATED**
- **Advanced tab-based navigation** for discussion rounds
- **Interactive model selection** within each round with response inspection
- **Real-time convergence visualization** with scoring and status updates
- **Chairman assessment display** with consensus/conflict point breakdown
- **Final integrated conclusion** with comprehensive result presentation
- **Metadata tracking** showing convergence round and total rounds completed

**`components/Sidebar.jsx`** - **MODERN CONVERSATION MANAGEMENT**
- Clean conversation list with sophisticated delete functionality
- Custom SVG icons with animated confirmation dialogs
- Responsive layout with proper accessibility and event handling

**`components/ConfirmDialog.jsx`** - **PROFESSIONAL UI COMPONENT**
- Modern confirmation dialog with backdrop click handling
- Keyboard shortcuts (ESC to cancel, Enter to confirm)
- Smooth animations and proper accessibility features
- Reusable component for various confirmation scenarios

**Technology Stack:**
- **React 19.2.0** with modern hooks and patterns
- **Vite 7.2.4** for fast development and building
- **ReactMarkdown 10.1.0** for structured content rendering
- **Modern CSS** with responsive design and animations

**Styling (`*.css`)**
- Light mode theme (not dark mode)
- Primary color: #4a90e2 (blue)
- Global markdown styling in `index.css` with `.markdown-content` class
- 12px padding on all markdown content to prevent cluttered appearance

## Key Design Decisions

### Multi-Round Discussion Process
- **Divergent Phase**: Models respond sequentially, building on previous responses to explore diverse perspectives
- **Convergent Phase**: **ENHANCED** - Models perform deep analysis of consensus/conflict points with structured requirements
- **Chairman Assessment**: **OPTIMIZED** - Systematic round-by-round comparison with 4-dimension evaluation
- **Iterative Process**: Continues until convergence (≥0.8) is achieved or maximum rounds reached

### Role-Free Implementation
- Models don't have predefined roles (innovator, critic, etc.)
- Each model contributes naturally based on the accumulated discussion context
- This allows more organic and emergent discussion dynamics
- Models build on each other's insights without artificial constraints

## Recent Major Optimizations (2024)

### 1. Chairman Evaluation Enhancement
**File**: `CHAIRMAN_OPTIMIZATION_SUMMARY.md`
**Impact**: Dramatically improved convergence detection accuracy

**Key Improvements:**
- **Systematic Round Comparison**: Chairman now explicitly compares current round vs previous round
- **4-Dimension Evaluation**: Stability, conflict management, structure, quality (25% each)
- **Structured Previous Context**: Detailed breakdown of last round's consensus, conflicts, and questions
- **Clear Convergence Criteria**: Distinguishes "converged" from "consistent" with precise thresholds

**Technical Implementation:**
- Enhanced `evaluate_convergence()` with detailed `previous_chairman_context`
- Structured comparison requirements with 4-step analysis process
- Improved convergence scoring with actionable decision thresholds

### 2. Convergent Phase Deep Analysis
**File**: `CONVERGENT_OPTIMIZATION_SUMMARY.md`
**Impact**: Significantly deeper analysis quality and faster convergence

**Key Improvements:**
- **Mandatory Consensus Analysis**: 4-dimension analysis for each consensus point (agreement, supplements, conditions, insights)
- **Mandatory Conflict Analysis**: 4-dimension analysis for each conflict point (position, reconciliation, root cause, impact)
- **New JSON Structure**: Added `consensus_analysis[]` and `conflict_analysis[]` fields
- **Integration Requirements**: Analysis must combine with question answering

**Technical Implementation:**
- Complete rewrite of `build_convergent_prompt()` function (lines 499-611)
- Enhanced `validate_and_parse_json()` with new field support and graceful fallback
- Structured analysis requirements with clear dimension specifications

### 3. Advanced Streaming Architecture
**Impact**: Real-time user experience with comprehensive progress tracking

**Features:**
- **Server-Sent Events**: Real-time streaming of multi-round discussion progress
- **Individual Model Completion**: Live updates as each model finishes responding
- **Round-by-Round Updates**: Real-time convergence scoring and assessment
- **Error Event Handling**: Graceful degradation with partial success reporting
- **Final Result Streaming**: Complete discussion data with metadata

### Error Handling Philosophy
- Continue with successful responses if some models fail (graceful degradation)
- Never fail the entire request due to single model failure
- Log errors but don't expose to user unless all models fail

### UI/UX Transparency
- All raw outputs are inspectable via tabs
- Parsed rankings shown below raw text for validation
- Users can verify system's interpretation of model outputs
- This builds trust and allows debugging of edge cases

## Important Implementation Details

### Relative Imports
All backend modules use relative imports (e.g., `from .config import ...`) not absolute imports. This is critical for Python's module system to work correctly when running as `python -m backend.main`.

### Port Configuration
- Backend: 8001 (changed from 8000 to avoid conflict)
- Frontend: 5173 (Vite default)
- Update both `backend/main.py` and `frontend/src/api.js` if changing

### Markdown Rendering
All ReactMarkdown components must be wrapped in `<div className="markdown-content">` for proper spacing. This class is defined globally in `index.css`.

### Model Configuration
Models are hardcoded in `backend/config.py`. Chairman can be same or different from council members. The current default is Gemini as chairman per user preference.

## Common Gotchas

1. **Module Import Errors**: Always run backend as `python -m backend.main` from project root, not from backend directory
2. **CORS Issues**: Frontend must match allowed origins in `main.py` CORS middleware
3. **JSON Parsing Failures**: If models don't follow JSON format, fallback to raw response display
4. **Streaming Data Persistence**: Ensure streaming API properly saves all discussion data to storage
5. **Convergence Detection**: Chairman model must be reliable for convergence assessment

## Future Enhancement Ideas

- Configurable council/chairman via UI instead of config file
- Streaming responses instead of batch loading
- Export conversations to markdown/PDF
- Model performance analytics over time
- Custom ranking criteria (not just accuracy/insight)
- Support for reasoning models (o1, etc.) with special handling

## Comprehensive Testing Suite

### Test Files Overview
The codebase includes extensive testing to verify optimizations and ensure reliability:

**`test_chairman_optimization.py`**
- Tests optimized chairman evaluation with systematic round comparison
- Validates 4-dimension convergence assessment
- Simulates multi-round scenarios to verify convergence detection accuracy

**`test_convergent_optimization.py`**
- Tests enhanced convergent phase with deep analysis requirements
- Validates new JSON structure (`consensus_analysis`, `conflict_analysis`)
- Ensures proper integration of analysis with question answering

**`test_optimized_integration.py`**
- End-to-end integration tests for complete council process
- Tests streaming vs non-streaming modes
- Validates error handling and graceful degradation

**`test_openrouter.py`**
- Basic API connectivity testing
- Model identifier validation
- Streaming and non-streaming mode verification

### Key Testing Scenarios

**Medical AI Diagnosis Scenario:**
- **Round 1**: Divergent phase identifying AI medical diagnosis advantages/challenges
- **Round 2**: Convergent phase addressing specific application standards, evaluation mechanisms, collaboration models
- **Validation**: Systematic comparison analysis between rounds, convergence scoring accuracy

**Optimization Validation Points:**
1. **Comparison Analysis Completeness**: Chairman explicitly compares current vs previous rounds
2. **Evaluation Dimension Precision**: 4-dimension assessment with specific criteria
3. **Deep Analysis Requirements**: Consensus and conflict point analysis with all required dimensions
4. **Integration Quality**: Analysis combines effectively with question answering
5. **Convergence Detection**: Accurate distinction between "converged" and "consistent" states

### Performance Metrics

**Convergence Detection:**
- **Optimized Accuracy**: Significant improvement in convergence assessment
- **Threshold Optimization**: ≥0.85 for converged, <0.85 for continue discussion
- **Round Reduction**: Faster convergence through deeper analysis requirements

**Quality Assurance:**
- **Prompt Length**: Optimized to stay within model limits (2000-4000 characters)
- **JSON Parsing**: Robust validation with graceful fallback for malformed responses
- **Error Recovery**: Continues with successful responses even when some models fail

### Continuous Monitoring

**Real-time Performance Tracking:**
- Convergence score accuracy over multiple discussion topics
- Analysis depth vs convergence speed optimization
- Error rates and graceful degradation effectiveness
- User feedback on final answer quality

**Usage Analytics:**
- Average rounds to convergence by topic complexity
- Model performance comparison across different discussion types
- Streaming performance and user engagement metrics

## Data Flow Summary

```
User Query
    ↓
Round 1: Divergent Phase (sequential responses with accumulated context)
    ↓
Chairman Assessment: OPTIMIZED systematic evaluation with round comparison
    ↓
If not converged: Round 2+ Convergent Phase (ENHANCED deep analysis with structured requirements)
    ↓
Repeat until convergence (≥0.85) or max rounds
    ↓
Final Integrated Conclusion from chairman with comprehensive reasoning
    ↓
Return: {all_rounds, final_result, metadata, convergence_analysis}
    ↓
Frontend: ADVANCED streaming interface with real-time progress and tab navigation
```

## Enhanced Data Structure (Post-Optimization)

```json
{
  "all_rounds": [
    {
      "round": 1,
      "type": "divergent",
      "responses": [
        {
          "model": "model-id",
          "response": "raw-response",
          "parsed_json": {
            "summary": "...",
            "viewpoints": [...],
            "consensus_analysis": [...],  // NEW: Enhanced convergent phase
            "conflict_analysis": [...],  // NEW: Enhanced convergent phase
            "conflicts": [...],
            "suggestions": [...],
            "final_answer_candidate": "..."
          }
        }
      ],
      "chairman_assessment": {
        "convergence_score": 0.0-1.0,
        "is_converged": true/false,
        "consensus_points": [...],
        "conflict_points": [...],
        "explanation": "...",
        "questions_for_next_round": [...],
        "final_integrated_conclusion": "...",
        "previous_round_comparison": "..."  // NEW: Optimized chairman evaluation
      }
    }
  ],
  "final_result": {
    "model": "chairman-model",
    "response": "integrated-conclusion",
    "convergence_analysis": {
      "total_rounds": number,
      "converged_round": number,
      "final_convergence_score": number,
      "consensus_summary": [...],
      "remaining_conflicts": [...]
    }
  },
  "metadata": {
    "converged_round": round_number,
    "optimization_version": "2024-enhanced",
    "streaming_completed": true
  }
}
```

The entire flow is **fully async/parallel** with **real-time streaming**, **advanced error handling**, and **graceful degradation**. The system maintains **complete transparency** while providing **sophisticated analysis** and **high-quality consensus answers**.
