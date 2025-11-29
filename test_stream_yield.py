#!/usr/bin/env python3
"""简单测试流式yield机制"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.council import run_full_council_stream

async def test_stream():
    print("=== Testing Stream Yield Mechanism ===")

    event_count = 0

    async for event in run_full_council_stream("What is 1+1?"):
        event_count += 1
        print(f"\n=== Event {event_count}: {event['type']} ===")
        if event['type'] == 'model_response_complete':
            print(f"Model: {event['data']['model']}")
            print(f"Response length: {len(event['data']['response'])}")
        elif event['type'] == 'round_complete':
            print(f"Round {event['data']['round']} completed")
            print(f"Converged: {event['data']['is_converged']}")
        elif event['type'] == 'complete':
            print("=== PROCESSING COMPLETE ===")
            break

if __name__ == "__main__":
    asyncio.run(test_stream())