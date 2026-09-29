import httpx
import structlog
from datetime import datetime, timezone
from app.db.queries import upsert_job

logger = structlog.get_logger()

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"

# Curated tech companies with public Greenhouse boards
GREENHOUSE_COMPANIES = [
    "airbnb", "stripe", "notion", "figma", "databricks", "snowflake",
    "hashicorp", "confluent", "mongodb", "elastic", "cloudflare", "datadog",
    "scale-ai", "cohere", "huggingface", "anthropic",
]

# Curated tech companies with public Lever boards
LEVER_COMPANIES = [
    "netflix", "reddit", "coinbase", "robinhood", "plaid", "chime",
    "affirm", "carta", "nerdwallet", "opendoor", "zendesk", "asana",
]

ROLE_KEYWORDS = [
    "ai engineer", "ml engineer", "machine learning", "generative ai", "llm",
    "rag", "ai agent", "java", "spring boot", "full stack", "fullstack",
    "backend engineer", "software engineer", "python developer",
    "react", "angular", "node.js", "devops", "cloud engineer",
]

COUNTRY_MAP = {
    "usa": "USA", "united states": "USA", "us only": "USA",
    "new york": "USA", "san francisco": "USA", "seattle": "USA",
    "uk": "UK", "united kingdom": "UK", "london": "UK",
    "germany": "Germany", "berlin": "Germany", "munich": "Germany",
    "india": "India", "bangalore": "India", "hyderabad": "India",
    "canada": "Canada", "toronto": "Canada",
    "australia": "Australia", "sydney": "Australia",
    "singapore": "Singapore",
    "netherlands": "Netherlands", "amsterdam": "Netherlands",
    "ireland": "Ireland", "dublin": "Ireland",
    "uae": "UAE", "dubai": "UAE",
}


def _extract_country(text: str) -> str | None:
    t = text.lower()
    for key, val in COUNTRY_MAP.items():
        if key in t:
            return val
    return None


def _is_relevant(title: str, description: str) -> bool:
    combined = (title + " " + description[:500]).lower()
    return any(kw in combined for kw in ROLE_KEYWORDS)


def _detect_remote(text: str) -> str:
    t = text.lower()
    if "remote" in t:
        return "REMOTE"
    if "hybrid" in t:
        return "HYBRID"
    return "ONSITE"


def run_discovery() -> dict:
    """Fetch jobs from all enabled sources and upsert into Supabase."""
    total_new = 0
    total_seen = 0
    errors = []

    # ── Remotive ─────────────────────────────────────────────
    for category in ["software-dev", "devops", "data"]:
        try:
            resp = httpx.get(REMOTIVE_URL, params={"category": category, "limit": 100}, timeout=30)
            resp.raise_for_status()
            for item in resp.json().get("jobs", []):
                if not _is_relevant(item.get("title", ""), item.get("description", "")):
                    continue
                job = {
                    "source": "remotive",
                    "source_job_id": str(item["id"]),
                    "company": item.get("company_name", ""),
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "url": item.get("url", ""),
                    "location": item.get("candidate_required_location", "Worldwide"),
                    "country": _extract_country(item.get("candidate_required_location", "")),
                    "remote_type": "REMOTE",
                    "visa_sponsorship": "UNKNOWN",
                    "required_skills": [t.get("name", t) if isinstance(t, dict) else t for t in item.get("tags", [])],
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                }
                _, is_new = upsert_job(job)
                if is_new:
                    total_new += 1
                else:
                    total_seen += 1
        except Exception as e:
            errors.append(f"remotive/{category}: {e}")

    # ── Arbeitnow ─────────────────────────────────────────────
    try:
        page = 1
        while page <= 5:
            resp = httpx.get(ARBEITNOW_URL, params={"page": page}, timeout=30)
            resp.raise_for_status()
            items = resp.json().get("data", [])
            if not items:
                break
            for item in items:
                if not _is_relevant(item.get("title", ""), item.get("description", "")):
                    page += 1
                    continue
                job = {
                    "source": "arbeitnow",
                    "source_job_id": item["slug"],
                    "company": item.get("company_name", ""),
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "url": item.get("url", ""),
                    "location": item.get("location", ""),
                    "country": _extract_country(item.get("location", "")),
                    "remote_type": "REMOTE" if item.get("remote") else "ONSITE",
                    "visa_sponsorship": "CONFIRMED" if item.get("visa_sponsorship") else "UNKNOWN",
                    "required_skills": item.get("tags", []),
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                }
                _, is_new = upsert_job(job)
                if is_new:
                    total_new += 1
                else:
                    total_seen += 1
            page += 1
    except Exception as e:
        errors.append(f"arbeitnow: {e}")

    # ── Greenhouse ────────────────────────────────────────────
    for token in GREENHOUSE_COMPANIES:
        try:
            resp = httpx.get(
                f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
                params={"content": "true"}, timeout=20,
            )
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            for item in resp.json().get("jobs", []):
                if not _is_relevant(item.get("title", ""), item.get("content", "")):
                    continue
                loc = item.get("location", {}).get("name", "")
                job = {
                    "source": "greenhouse",
                    "source_job_id": str(item["id"]),
                    "company": token,
                    "title": item.get("title", ""),
                    "description": item.get("content", ""),
                    "url": item.get("absolute_url", ""),
                    "location": loc,
                    "country": _extract_country(loc),
                    "remote_type": _detect_remote(loc + " " + item.get("title", "")),
                    "visa_sponsorship": "UNKNOWN",
                    "required_skills": [],
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                }
                _, is_new = upsert_job(job)
                if is_new:
                    total_new += 1
                else:
                    total_seen += 1
        except Exception as e:
            errors.append(f"greenhouse/{token}: {e}")

    # ── Lever ─────────────────────────────────────────────────
    for slug in LEVER_COMPANIES:
        try:
            resp = httpx.get(f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=20)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            for item in resp.json():
                if not _is_relevant(item.get("text", ""), item.get("descriptionPlain", "")):
                    continue
                loc = item.get("categories", {}).get("location", "")
                job = {
                    "source": "lever",
                    "source_job_id": item["id"],
                    "company": item.get("company", slug),
                    "title": item.get("text", ""),
                    "description": item.get("descriptionPlain", ""),
                    "url": item.get("hostedUrl", ""),
                    "location": loc,
                    "country": _extract_country(loc),
                    "remote_type": _detect_remote(loc + " " + item.get("text", "")),
                    "visa_sponsorship": "UNKNOWN",
                    "required_skills": [],
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                }
                _, is_new = upsert_job(job)
                if is_new:
                    total_new += 1
                else:
                    total_seen += 1
        except Exception as e:
            errors.append(f"lever/{slug}: {e}")

    result = {"new": total_new, "seen": total_seen, "errors": errors}
    logger.info("discovery_complete", **result)
    return result
