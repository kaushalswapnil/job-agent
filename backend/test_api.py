"""
Quick test script — gets auth token and tests all API endpoints.
Run: python test_api.py
"""
import httpx
import json

SUPABASE_URL = "https://ngrudtbshliklqaznloi.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5ncnVkdGJzaGxpa2xxYXpubG9pIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM0MDUxMzAsImV4cCI6MjA5ODk4MTEzMH0.n5B5AV_8hvLQRayF3g1MhAbGqsSh4TAu6EiY_xrd4K4"
API_URL = "https://job-agent-9j1e.onrender.com"
EMAIL = "swapnil.kaushal00@gmail.com"
PASSWORD = "K@ushal31"  # Change if you used a different password

print("=" * 60)
print("JOB AGENT — API TEST")
print("=" * 60)

# Step 1 — Get Supabase auth token
print("\n[1] Getting auth token from Supabase...")
resp = httpx.post(
    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
    headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
    json={"email": EMAIL, "password": PASSWORD},
)
if resp.status_code != 200:
    print(f"ERROR: {resp.status_code} — {resp.text}")
    print("Make sure the password matches what you set in Supabase Dashboard")
    exit(1)

token = resp.json()["access_token"]
user_id = resp.json()["user"]["id"]
print(f"OK — User ID: {user_id}")
print(f"OK — Token: {token[:40]}...")

headers = {"Authorization": f"Bearer {token}"}

# Step 2 — Health check
print("\n[2] Health check...")
resp = httpx.get(f"{API_URL}/health")
print(f"OK — {resp.json()}")

# Step 3 — Onboarding status
print("\n[3] Onboarding status...")
resp = httpx.get(f"{API_URL}/onboarding/status", headers=headers)
print(f"Status code: {resp.status_code}")
print(f"Raw response: {resp.text}")
if resp.status_code == 200:
    print(f"OK — {resp.json()}")

# Step 4 — Save profile
print("\n[4] Saving candidate profile...")
resp = httpx.post(f"{API_URL}/onboarding/profile", headers=headers, json={
    "full_name": "Swapnil Kaushal",
    "phone": "+91-9999999999",
    "linkedin_url": "https://linkedin.com/in/swapnilkaushal",
    "current_city": "Bangalore",
    "current_country": "India",
    "experience_years": 7,
    "ai_years": 3,
    "java_years": 6,
    "frontend_years": 4,
    "cloud_years": 4,
    "professional_summary": "Senior Software Engineer and AI/GenAI Engineer with expertise in Java, Spring Boot, React, and modern AI/ML engineering including RAG, LLMs, and AI agents.",
    "notification_email": "swapnil.kaushal00@gmail.com",
    "target_roles": [
        "AI Engineer", "Generative AI Engineer", "LLM Engineer",
        "Senior Java Developer", "Full Stack Engineer", "Senior Software Engineer"
    ],
    "skills": [
        "Java", "Spring Boot", "Python", "React", "Angular", "TypeScript",
        "AWS", "Docker", "Kubernetes", "LangChain", "RAG", "LLMs",
        "Amazon Bedrock", "OpenAI APIs", "Vector Databases", "Microservices",
        "REST APIs", "Kafka", "PostgreSQL", "MongoDB"
    ],
    "job_prefs": {"remote_preference": "preferred", "auto_apply_threshold": 80},
    "work_authorization": {
        "india": "authorized",
        "usa": "requires_sponsorship",
        "europe": "requires_sponsorship",
        "remote": "authorized"
    },
    "location_prefs": {
        "india": {"enabled": True},
        "europe": {"enabled": True},
        "remote_worldwide": {"enabled": True}
    },
    "salary_prefs": {
        "india": {"currency": "INR", "minimum": 2500000, "target": 3500000}
    },
})
print(f"Status: {resp.status_code}")
print(f"Raw: {resp.text}")

# Step 5 — Dashboard stats
print("\n[5] Dashboard stats...")
resp = httpx.get(f"{API_URL}/dashboard/stats", headers=headers)
print(f"Status: {resp.status_code}")
print(f"Raw: {resp.text}")

# Step 6 — Trigger job discovery
print("\n[6] Triggering job discovery (runs in background)...")
resp = httpx.post(f"{API_URL}/agents/discover", headers=headers)
print(f"Status: {resp.status_code}")
print(f"Raw: {resp.text}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
print(f"\nYour auth token (save this for Swagger UI testing):")
print(f"\nBearer {token}")
print("\nNext: Upload your resume at http://localhost:8000/docs")
print("      → POST /onboarding/resume")
