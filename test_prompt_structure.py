#!/usr/bin/env python3
"""
Test script to verify the improved prompt structure.
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from backend.council import build_divergent_prompt, assign_roles_to_models
from backend.config import COUNCIL_MODELS

def test_prompt_structure():
    """Test the improved prompt structure."""
    print("=== Testing Improved Prompt Structure ===")

    # Test query
    test_query = "What are the key factors for successful AI project implementation?"

    # Get role assignments
    model_roles = assign_roles_to_models()

    # Test for first model (no previous responses)
    print("\n--- Test Case 1: First Model (No Previous Responses) ---")
    first_model = COUNCIL_MODELS[0]
    role_info = model_roles[first_model]

    prompt = build_divergent_prompt(test_query, [], role_info)
    print(f"Model: {first_model}")
    print(f"Role: {role_info['role_name']}")
    print(f"Prompt length: {len(prompt)} characters")
    print("\nPrompt structure preview:")
    print("-" * 80)
    lines = prompt.split('\n')
    for i, line in enumerate(lines[:30]):  # Show first 30 lines
        print(f"{i+1:3d}: {line}")
    print("...")

    # Test for second model (with one previous response)
    print("\n--- Test Case 2: Second Model (With Previous Response) ---")
    second_model = COUNCIL_MODELS[1]
    role_info = model_roles[second_model]

    # Create a mock previous response
    previous_responses = [
        {
            'model': first_model,
            'role_name': role_info['role_name'],
            'response': '{"summary": "Test summary", "viewpoints": ["Test viewpoint 1", "Test viewpoint 2"], "conflicts": [], "suggestions": [], "final_answer_candidate": ""}',
            'parsed_json': {
                'summary': 'Test summary',
                'viewpoints': ['Test viewpoint 1', 'Test viewpoint 2'],
                'conflicts': [],
                'suggestions': [],
                'final_answer_candidate': ''
            }
        }
    ]

    prompt = build_divergent_prompt(test_query, previous_responses, role_info)
    print(f"Model: {second_model}")
    print(f"Role: {role_info['role_name']}")
    print(f"Prompt length: {len(prompt)} characters")
    print("\nPrompt structure preview:")
    print("-" * 80)
    lines = prompt.split('\n')
    for i, line in enumerate(lines[:40]):  # Show first 40 lines
        print(f"{i+1:3d}: {line}")
    print("...")

    # Analyze prompt sections
    print("\n--- Prompt Structure Analysis ---")
    sections = prompt.split('---')
    print(f"Number of sections (separated by '---'): {len(sections)}")

    # Check for clear section headers
    section_headers = [line for line in prompt.split('\n') if line.startswith('# ')]
    print(f"Section headers found: {len(section_headers)}")
    for header in section_headers:
        print(f"  - {header}")

if __name__ == "__main__":
    test_prompt_structure()
    print("\n=== Test Complete ===")