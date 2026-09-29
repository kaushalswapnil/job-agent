"""
Test matching agent — scores jobs against candidate profile using LLM.
Run: python test_matching.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

USER_ID = "5e851791-6d3a-4c12-832c-c5e4abb61082"

from app.agents.matching.runner import run_matching

print("Starting job matching (first batch of 30 jobs)...")
print("Using OpenAI gpt-4o-mini — this takes ~1-2 minutes")
print("=" * 60)

result = run_matching(USER_ID, batch_size=30)

print("=" * 60)
print(f"Jobs evaluated:  {result.get('evaluated', 0)}")
print(f"High matches:    {result.get('high_matches', 0)}")
if result.get('error'):
    print(f"Error: {result['error']}")
