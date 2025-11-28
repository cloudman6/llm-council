#!/usr/bin/env python3
"""
Test script to verify the role-free implementation.
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from backend.council import run_full_council, build_divergent_prompt
from backend.config import COUNCIL_MODELS

async def test_role_free():
    """Test the role-free implementation."""
    print("=== Testing Role-Free Implementation ===")

    # Test query
    test_query = "What are the key factors for successful AI project implementation?"

    print(f"Test query: {test_query}")
    print("Running divergent phase without roles...")

    # Test prompt building for first model (no previous responses)
    print("\n--- Testing Prompt Structure (First Model) ---")
    prompt = build_divergent_prompt(test_query, [])
    print(f"Prompt length: {len(prompt)} characters")
    print("\nPrompt structure preview:")
    print("-" * 80)
    lines = prompt.split('\n')
    for i, line in enumerate(lines[:25]):  # Show first 25 lines
        print(f"{i+1:3d}: {line}")
    print("...")

    # Check for role-related content
    role_keywords = ['角色', 'role', 'innovator', 'critic', 'structured', 'conservative']
    found_role_content = any(keyword in prompt.lower() for keyword in role_keywords)
    print(f"\nRole-related content found: {found_role_content}")

    # Run the council process
    print("\n--- Running Divergent Phase ---")
    divergent_results, stage2_results, stage3_result, metadata = await run_full_council(test_query)

    print(f"\nResults:")
    print(f"- Divergent phase results: {len(divergent_results)} responses")
    print(f"- Stage 2 results: {len(stage2_results)} rankings")
    print(f"- Stage 3 result: {stage3_result['model']} - {stage3_result['response'][:50]}...")

    # Show divergent phase details
    if divergent_results:
        print("\nDivergent Phase Details:")
        for i, result in enumerate(divergent_results, 1):
            print(f"\nModel {i}: {result['model']}")
            print(f"Response length: {len(result['response'])} chars")
            if result.get('parsed_json'):
                print("✓ JSON parsed successfully")
                # Check if response contains role-related content
                response_text = result['response'].lower()
                has_role_content = any(keyword in response_text for keyword in role_keywords)
                print(f"Response contains role-related content: {has_role_content}")
            else:
                print("✗ JSON parsing failed")

if __name__ == "__main__":
    print("Testing Role-Free Implementation")
    print("=" * 60)

    asyncio.run(test_role_free())

    print("\n=== Test Complete ===")
    print("Note: The system should work without role assignments.")