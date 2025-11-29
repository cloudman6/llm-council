#!/usr/bin/env python3
"""
Test script to verify the divergent phase implementation with debug mode.
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from backend.council import run_full_council, assign_roles_to_models, ROLES
from backend.config import COUNCIL_MODELS

async def test_role_assignment():
    """Test that role assignment works correctly with circular allocation."""
    print("=== Testing Role Assignment ===")
    model_roles = assign_roles_to_models()

    print(f"Number of models: {len(COUNCIL_MODELS)}")
    print(f"Number of roles: {len(ROLES)}")

    for model, role_info in model_roles.items():
        print(f"{model}: {role_info['role_name']}")

    print()

async def test_divergent_debug():
    """Test the divergent phase with debug mode enabled."""
    print("=== Testing Divergent Phase (Debug Mode) ===")

    # Test query
    test_query = "What are the key factors for successful AI project implementation?"

    print(f"Test query: {test_query}")
    print("Running divergent phase...")

    # Run the council process (should stop after divergent phase)
    all_rounds_results, final_result, metadata = await run_full_council(test_query)

    print(f"\nResults:")
    print(f"- Total rounds: {len(all_rounds_results)}")
    print(f"- Final result: {final_result['model']} - {final_result['response'][:50]}...")

    # Show divergent phase details
    if all_rounds_results and len(all_rounds_results) > 0:
        divergent_results = all_rounds_results[0]['responses']
        print("\nDivergent Phase Details:")
        for i, result in enumerate(divergent_results, 1):
            print(f"\nModel {i}: {result['model']}")
            print(f"Response length: {len(result['response'])} chars")
            if result.get('parsed_json'):
                print("✓ JSON parsed successfully")
            else:
                print("✗ JSON parsing failed")

if __name__ == "__main__":
    print("Testing Divergent Phase Implementation with Debug Mode")
    print("=" * 60)

    asyncio.run(test_role_assignment())
    asyncio.run(test_divergent_debug())

    print("\n=== Test Complete ===")
    print("Note: The system should stop after divergent phase for debugging.")