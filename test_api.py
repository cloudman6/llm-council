#!/usr/bin/env python3
"""Quick test for OpenRouter API connectivity."""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.openrouter import query_model
import json

async def test_api():
    messages = [{'role': 'user', 'content': 'Hello, respond with just OK'}]
    print('Testing OpenRouter API with simple request...')
    try:
        response = await query_model('z-ai/glm-4.5-air:free', messages, timeout=30.0)
        if response:
            print('✓ API Response received:')
            print(f"Length: {len(response.get('content', ''))} characters")
            print(f"Content: {response.get('content', '')[:200]}...")
        else:
            print('✗ No response received')
    except Exception as e:
        print(f'✗ Error: {e}')

if __name__ == "__main__":
    asyncio.run(test_api())