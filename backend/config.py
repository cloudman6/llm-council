"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    # "openai/gpt-5.1",
    # "deepseek/deepseek-v3.2-exp",
    "z-ai/glm-4.5-air:free",
    "x-ai/grok-4.1-fast:free",
    "tngtech/deepseek-r1t2-chimera:free",
    "kwaipilot/kat-coder-pro:free",
    # "google/gemini-3-pro-preview",
    # "anthropic/claude-sonnet-4.5",
    # "x-ai/grok-4",
]

# Chairman model - synthesizes final response
# CHAIRMAN_MODEL = "deepseek/deepseek-v3.2-exp"
CHAIRMAN_MODEL = "z-ai/glm-4.5-air:free"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# Convergence threshold for chairman evaluation
# Chairman can only set is_converged=true when convergence_score >= this threshold
CONVERGENCE_THRESHOLD = 0.85
