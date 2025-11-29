# CLAUDE.md - Technical Notes for LLM Council

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

LLM Council is a multi-round deliberation system where multiple LLMs collaboratively answer user questions through iterative discussion phases. The system uses a chairman model to assess convergence and guide the discussion process.

## Architecture

### Backend Structure (`backend/`)

**`config.py`**
- Contains `COUNCIL_MODELS` (list of OpenRouter model identifiers)
- Contains `CHAIRMAN_MODEL` (model that synthesizes final answer)
- Uses environment variable `OPENROUTER_API_KEY` from `.env`
- Backend runs on **port 8001** (NOT 8000 - user had another app on 8000)

**`openrouter.py`**
- `query_model()`: Single async model query
- `query_models_parallel()`: Parallel queries using `asyncio.gather()`
- Returns dict with 'content' and optional 'reasoning_details'
- Graceful degradation: returns None on failure, continues with successful responses

**`council.py`** - The Core Logic
- `divergent_phase_responses()`: Sequential responses where each model sees all previous responses
- `evaluate_convergence()`: Chairman assesses convergence and generates questions for next round
- `run_convergent_phase()`: Parallel responses to chairman's questions
- `build_divergent_prompt()`: Builds prompt for divergent phase with accumulated context
- `build_convergent_prompt()`: Builds prompt for convergent phase based on chairman's assessment
- `run_full_council()`: Runs complete multi-round council process (batch mode)
- `run_full_council_stream()`: Runs complete multi-round council process with streaming output

**`storage.py`**
- JSON-based conversation storage in `data/conversations/`
- Each conversation: `{id, created_at, messages[]}`
- Assistant messages contain: `{role, all_rounds, final_result}`
- Note: metadata (converged_round) is persisted to storage

**`main.py`**
- FastAPI app with CORS enabled for localhost:5173 and localhost:3000
- POST `/api/conversations/{id}/message` returns all rounds and final result
- POST `/api/conversations/{id}/message/stream` streams multi-round process with real-time updates
- Metadata includes: converged_round indicating which round achieved convergence

### Frontend Structure (`frontend/src/`)

**`App.jsx`**
- Main orchestration: manages conversations list and current conversation
- Handles message sending and metadata storage
- Important: metadata is stored in the UI state for display but not persisted to backend JSON

**`components/ChatInterface.jsx`**
- Multiline textarea (3 rows, resizable)
- Enter to send, Shift+Enter for new line
- User messages wrapped in markdown-content class for padding

**`components/MultiRoundDiscussion.jsx`**
- Tab-based UI showing all discussion rounds
- Each round displays model responses and chairman assessment
- Real-time convergence status and scores
- Interactive model selection within each round
- Final integrated conclusion when converged

**`components/DivergentPhase.jsx`**
- Displays divergent phase responses with structured JSON parsing
- Shows summary, viewpoints, conflicts, and suggestions
- Final answer candidate with markdown rendering

**Styling (`*.css`)**
- Light mode theme (not dark mode)
- Primary color: #4a90e2 (blue)
- Global markdown styling in `index.css` with `.markdown-content` class
- 12px padding on all markdown content to prevent cluttered appearance

## Key Design Decisions

### Multi-Round Discussion Process
- **Divergent Phase**: Models respond sequentially, building on previous responses to explore diverse perspectives
- **Convergent Phase**: Models respond in parallel to chairman's questions to resolve conflicts and reach consensus
- **Chairman Assessment**: After each round, chairman evaluates convergence and guides next steps
- **Iterative Process**: Continues until convergence is achieved or maximum rounds reached

### Role-Free Implementation
- Models don't have predefined roles (innovator, critic, etc.)
- Each model contributes naturally based on the accumulated discussion context
- This allows more organic and emergent discussion dynamics
- Models build on each other's insights without artificial constraints

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

## Testing Notes

Use `test_openrouter.py` to verify API connectivity and test different model identifiers before adding to council. The script tests both streaming and non-streaming modes.

## Data Flow Summary

```
User Query
    ↓
Round 1: Divergent Phase (sequential responses with accumulated context)
    ↓
Chairman Assessment: Evaluate convergence and generate questions
    ↓
If not converged: Round 2+ Convergent Phase (parallel responses to questions)
    ↓
Repeat until convergence or max rounds
    ↓
Final Integrated Conclusion from chairman
    ↓
Return: {all_rounds, final_result, metadata}
    ↓
Frontend: Multi-round tabbed interface with real-time progress
```

The entire flow is async/parallel where possible to minimize latency.
