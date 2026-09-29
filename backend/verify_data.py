"""
Verify all data saved in Supabase for the user.
Run: python verify_data.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

USER_ID = "5e851791-6d3a-4c12-832c-c5e4abb61082"

from app.db.queries import get_profile, get_candidate_config, get_master_resume
from app.core.supabase import get_supabase

db = get_supabase()

print("=" * 60)
print("VERIFYING DATA IN SUPABASE")
print("=" * 60)

# Profile
profile = get_profile(USER_ID)
print("\n[1] PROFILE:")
if profile:
    print(f"  Name:     {profile.get('full_name')}")
    print(f"  Email:    {profile.get('email')}")
    print(f"  Phone:    {profile.get('phone')}")
    print(f"  City:     {profile.get('current_city')}")
    print(f"  LinkedIn: {profile.get('linkedin_url')}")
    print(f"  Naukri:   {profile.get('naukri_url')}")
    print(f"  GitHub:   {profile.get('github_url')}")
else:
    print("  NOT FOUND")

# Candidate config
config = get_candidate_config(USER_ID)
print("\n[2] CANDIDATE CONFIG:")
if config:
    print(f"  Experience: {config.get('experience_years')} yrs total | AI: {config.get('ai_years')}y | Java: {config.get('java_years')}y")
    print(f"  Target Roles: {config.get('target_roles')}")
    print(f"  Skills ({len(config.get('skills') or [])}): {', '.join((config.get('skills') or [])[:5])}...")
    print(f"  Summary: {(config.get('professional_summary') or '')[:80]}...")
else:
    print("  NOT FOUND")

# Resume
resume = get_master_resume(USER_ID)
print("\n[3] MASTER RESUME:")
if resume:
    print(f"  ID:      {resume.get('id')}")
    print(f"  Version: {resume.get('version')}")
    print(f"  Path:    {resume.get('storage_path')}")
    print(f"  Text length: {len(resume.get('raw_text') or '')} characters")
    print(f"  Preview: {(resume.get('raw_text') or '')[:200]}...")
else:
    print("  NOT FOUND — resume not uploaded yet")

# Jobs
jobs_count = db.table("ja_jobs").select("id", count="exact").execute()
print(f"\n[4] JOBS IN DATABASE: {jobs_count.count}")

# Matches
matches = db.table("ja_job_matches").select("match_level").eq("user_id", USER_ID).execute()
if matches.data:
    from collections import Counter
    counts = Counter(m["match_level"] for m in matches.data)
    print(f"\n[5] JOB MATCHES: {len(matches.data)} total")
    for level, count in counts.most_common():
        print(f"  {level}: {count}")
else:
    print("\n[5] JOB MATCHES: 0 (run matching agent next)")

print("\n" + "=" * 60)
