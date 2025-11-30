# LLM Council

![llmcouncil](header.jpg)

A sophisticated multi-LLM collaborative deliberation system that enables multiple large language models to engage in structured discussions, debate perspectives, and converge on high-quality consensus answers through iterative reasoning.

Instead of querying a single LLM provider, LLM Council creates a "council" of diverse AI models that collaborate through a structured multi-round process. Each model contributes unique perspectives, identifies conflicts and consensus points, and works together under the guidance of a Chairman model to produce comprehensive, well-reasoned responses.

## How It Works

The system uses a sophisticated **divergent → convergent** discussion process:

### 🌱 **Round 1: Divergent Phase**
- Models respond sequentially, building on previous responses
- Each model sees all preceding responses, creating a chain of evolving perspectives
- Goal: Maximize viewpoint diversity and uncover different angles

### 🔍 **Chairman Assessment**
- After each round, the Chairman analyzes responses for:
  - **Consensus Points**: Areas of agreement and shared understanding
  - **Conflict Points**: Disagreements requiring further exploration
  - **Convergence Score**: 0.0-1.0 rating of discussion stability
- **Configurable Threshold**: Chairman can only declare convergence when score ≥ 0.85 (configurable)
- **Automatic Enforcement**: System validates threshold compliance and corrects violations
- Generates targeted questions for the next round if needed

### 🎯 **Round 2+: Convergent Phase**
- Models respond independently to Chairman's questions
- Deep analysis of previous consensus and conflict points
- Structured evaluation across multiple dimensions
- Goal: Resolve conflicts, strengthen consensus, and stabilize discussion framework

### ✅ **Final Integration**
- When convergence is achieved (score ≥CONVERGENCE_THRESHOLD, default 0.85), the Chairman synthesizes:
  - Integrated conclusion incorporating all perspectives
  - Acknowledgment of remaining disagreements
  - Comprehensive answer with reasoning transparency
- **Threshold Enforcement**: System automatically ensures convergence threshold is met before final integration

## Key Features

- **Multi-round Deliberation**: Iterative refinement until consensus is reached
- **Intelligent Convergence Detection**: Sophisticated assessment of discussion stability
- **Complete Transparency**: Inspect all model responses, and reasoning
- **Robust Error Handling**: Continues even if some models fail

## Current Configuration

The system is currently configured with free-tier models for accessibility:

**Council Members:**
- `z-ai/glm-4.5-air:free` - General reasoning and analysis
- `x-ai/grok-4.1-fast:free` - Fast responses with diverse perspectives
- `tngtech/deepseek-r1t2-chimera:free` - Deep reasoning capabilities
- `kwaipilot/kat-coder-pro:free` - Technical and analytical insights

**Chairman:** `z-ai/glm-4.5-air:free` - Manages discussion flow and synthesizes final answers

**Convergence Threshold:** `0.85` - Chairman can only declare convergence when convergence_score ≥ 0.85 (configurable in `backend/config.py`)

## Setup

### 1. Install Dependencies

The project uses [uv](https://docs.astral.sh/uv/) for Python dependency management.

**Backend:**
```bash
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 2. Configure API Key

Create a `.env` file in the project root:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

Get your API key at [openrouter.ai](https://openrouter.ai/). Purchase credits or set up automatic top-up.

### 3. Configure Models (Optional)

Edit `backend/config.py` to customize the council:

```python
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4",
]

CHAIRMAN_MODEL = "google/gemini-3-pro-preview"

# Configure convergence threshold (default: 0.85)
# Chairman can only declare convergence when convergence_score >= this threshold
CONVERGENCE_THRESHOLD = 0.85
```

## Running the Application

**Option 1: Use the start script**
```bash
./start.sh
```

**Option 2: Run manually**

Terminal 1 (Backend):
```bash
uv run python -m backend.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

## Architecture & Tech Stack

### Backend (Port 8001)
- **Framework:** FastAPI with async support
- **Core Logic:** Sophisticated multi-round discussion management
- **API Client:** Robust HTTPX-based OpenRouter integration
- **Streaming:** Server-Sent Events for real-time progress updates
- **Storage:** JSON-based conversation persistence
- **Error Handling:** Graceful degradation with partial failures
- **Package Management:** uv for Python dependencies

### Frontend (Port 5173)
- **Framework:** React 19.2.0 with modern hooks
- **Build Tool:** Vite 7.2.4 for fast development
- **UI Features:**
  - Real-time streaming interface with progress tracking
  - Tab-based multi-round discussion navigation
  - Interactive model selection and response inspection
  - Conversation management with delete functionality
  - Modern confirmation dialogs with keyboard shortcuts
- **Rendering:** ReactMarkdown for structured content display
- **Styling:** Modern CSS with responsive design

### Advanced Features
- **Intelligent Convergence Detection:** 4-dimension evaluation system
- **Deep Analysis Requirements:** Structured consensus and conflict analysis
- **Chairman Optimization:** Systematic round-by-round comparison analysis
- **Real-time Updates:** Live streaming of discussion progress
- **Robust Persistence:** Complete conversation history with metadata
