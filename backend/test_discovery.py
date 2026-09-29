"""
Test discovery directly — run and see exact output + errors.
Run: python test_discovery.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.discovery.runner import run_discovery

print("Starting job discovery...")
print("This will fetch from Remotive, Arbeitnow, Greenhouse, Lever")
print("=" * 60)

result = run_discovery()

print("=" * 60)
print(f"New jobs found:  {result.get('new', 0)}")
print(f"Already seen:    {result.get('seen', 0)}")
print(f"Errors:          {len(result.get('errors', []))}")
if result.get('errors'):
    print("\nErrors:")
    for e in result['errors']:
        print(f"  - {e}")
