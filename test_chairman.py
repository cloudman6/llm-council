#!/usr/bin/env python3
"""
Test script for the new chairman functionality.
"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from backend.council import run_full_council


async def test_chairman():
    """Test the chairman functionality with a simple question."""

    test_question = "What are the main benefits of renewable energy?"

    print(f"Testing chairman functionality with question: {test_question}")
    print("=" * 80)

    try:
        # Run the multi-round council process
        all_rounds_results, final_result, metadata = await run_full_council(test_question)

        print(f"\nTotal rounds completed: {len(all_rounds_results)}")
        print(f"Converged in round: {metadata.get('converged_round', 'Not converged')}")

        # Display results for each round
        for round_data in all_rounds_results:
            round_num = round_data['round']
            round_type = round_data['type']
            print(f"\n--- Round {round_num} ({round_type}) ---")

            # Show chairman assessment
            if 'chairman_assessment' in round_data:
                assessment = round_data['chairman_assessment']
                print(f"Convergence Score: {assessment.get('convergence_score', 'N/A')}")
                print(f"Converged: {assessment.get('is_converged', 'N/A')}")
                print(f"Explanation: {assessment.get('explanation', 'N/A')}")

                if assessment.get('is_converged', False):
                    print(f"Final Conclusion: {assessment.get('final_integrated_conclusion', 'N/A')}")
                else:
                    print(f"Next Round Questions: {assessment.get('questions_for_next_round', [])}")

        print(f"\nFinal Result: {final_result.get('response', 'N/A')}")

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_chairman())