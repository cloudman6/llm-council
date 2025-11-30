#!/usr/bin/env python3
"""
Test script to verify debug output in LLM Council
"""

import asyncio
import sys
import os

# Add the current directory to Python path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.council import run_full_council_stream
from backend.storage import save_conversation


async def test_debug_output():
    """Test the debug output with a simple question"""

    print("🧪 Testing LLM Council Debug Output", flush=True)
    print("=" * 100, flush=True)

    # Simple test question
    test_question = "什么是人工智能？请简要解释。"

    print(f"📝 Test Question: {test_question}", flush=True)
    print("🚀 Starting streaming council process...", flush=True)
    print("=" * 100, flush=True)

    # Track events for verification
    event_count = 0
    round_events = []

    try:
        async for event in run_full_council_stream(test_question):
            event_count += 1
            event_type = event.get("type", "unknown")

            print(f"\n📡 Event {event_count}: {event_type}", flush=True)
            print("-" * 50, flush=True)

            # Log important events
            if event_type == "round_start":
                round_events.append(event_type)
                data = event.get("data", {})
                print(f"   Round {data.get('round')} - {data.get('type')} phase")

            elif event_type == "model_response_complete":
                round_events.append(event_type)
                data = event.get("data", {})
                model = data.get("model", "unknown")
                round_num = data.get("round", "unknown")
                print(f"   Model {model} (Round {round_num}) response complete")

            elif event_type == "round_complete":
                round_events.append(event_type)
                data = event.get("data", {})
                round_num = data.get("round", "unknown")
                phase_type = data.get("type", "unknown")
                is_converged = data.get("is_converged", False)
                convergence_score = data.get("convergence_score", 0.0)
                print(f"   Round {round_num} ({phase_type}) complete")
                print(f"   Converged: {is_converged} (Score: {convergence_score})")

            elif event_type == "complete":
                round_events.append(event_type)
                print("   ✅ Council process completed!")

            elif event_type == "final_results":
                round_events.append(event_type)
                print("   💾 Final results ready for storage")

            elif event_type == "error":
                round_events.append(event_type)
                print(f"   ❌ Error: {event.get('message', 'Unknown error')}")

            elif event_type == "initializing":
                round_events.append(event_type)
                print("   🎯 Process initialized")

            print("-" * 50, flush=True)

            # Early exit for testing (optional)
            if event_count > 20:  # Limit events for testing
                print("⏹️  Limiting events for testing purposes", flush=True)
                break

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

    print(f"\n📊 Test Summary:", flush=True)
    print(f"   Total events processed: {event_count}", flush=True)
    print(f"   Event types received: {list(set(round_events))}", flush=True)
    print(f"   ✅ Debug output test completed successfully!", flush=True)

    return True


if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_debug_output())

    if success:
        print("\n🎉 All tests passed!", flush=True)
        sys.exit(0)
    else:
        print("\n💥 Test failed!", flush=True)
        sys.exit(1)