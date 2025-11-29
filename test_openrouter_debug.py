#!/usr/bin/env python3
"""Test script to debug OpenRouter API issues."""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.openrouter import query_model
from backend.config import COUNCIL_MODELS, CHAIRMAN_MODEL

async def test_models():
    print("Testing OpenRouter API connection...")
    print(f"Models to test: {COUNCIL_MODELS}")
    print(f"Chairman model: {CHAIRMAN_MODEL}")
    print()

    messages = [{"role": "user", "content": "Hello, please respond with a simple greeting."}]

    for i, model in enumerate(COUNCIL_MODELS):
        print(f"Testing model {i+1}: {model}")
        try:
            response = await query_model(model, messages, timeout=30.0)
            if response is not None:
                content = response.get('content', '')
                print(f"✅ SUCCESS: Response length {len(content)} chars")
                print(f"First 100 chars: {content[:100]}...")
            else:
                print("❌ FAILED: No response received")
        except Exception as e:
            print(f"❌ ERROR: {e}")
        print()

    print("Testing chairman model...")
    try:
        response = await query_model(CHAIRMAN_MODEL, messages, timeout=30.0)
        if response is not None:
            content = response.get('content', '')
            print(f"✅ Chairman SUCCESS: Response length {len(content)} chars")
            print(f"First 100 chars: {content[:100]}...")
        else:
            print("❌ Chairman FAILED: No response received")
    except Exception as e:
        print(f"❌ Chairman ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_models())