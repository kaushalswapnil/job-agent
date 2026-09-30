import time
import structlog
from app.core.llm import LLMClient
from app.db.queries import get_unmatched_jobs, save_match, log_action

logger = structlog.get_logger()

SYSTEM = "You are an expert technical recruiter. Score candidate-job fit. Return ONLY valid JSON."

BATCH_PROMPT = """
Score how well this candidate matches each job below. Be honest — do NOT inflate scores.

CANDIDATE:
Name: {name} | Location: {location}
Experience: {total_years} yrs | AI/ML: {ai_years}y | Java: {java_years}y | Frontend: {frontend_years}y | Cloud: {cloud_years}y
Skills: {skills}
Target Roles: {target_roles}
Work Authorization: {work_auth}

JOBS TO SCORE:
{jobs_text}

Match levels: HIGH_MATCH (>=80), MEDIUM_MATCH (60-79), LOW_MATCH (40-59), DO_NOT_APPLY (<40 or missing fundamentals).

Return ONLY a JSON array — one object per job in the same order:
[
  {{
    "job_index": 0,
    "overall_score": <0-100>,
    "match_level": "<HIGH_MATCH|MEDIUM_MATCH|LOW_MATCH|DO_NOT_APPLY>",
    "technical_score": <0-100>,
    "ai_score": <0-100>,
    "java_score": <0-100>,
    "frontend_score": <0-100>,
    "cloud_score": <0-100>,
    "location_score": <0-100>,
    "visa_score": <0-100>,
    "explanation": {{
      "summary": "<1 sentence>",
      "strengths": ["<s1>"],
      "gaps": ["<g1>"],
      "recommendation": "<apply|skip|needs_review>"
    }}
  }},
  ...
]
"""


def run_matching(user_id: str, batch_size: int = 50) -> dict:
    config = _get_user_config(user_id)
    if not config:
        return {"error": "No candidate config found. Complete onboarding first."}

    jobs = get_unmatched_jobs(user_id, limit=batch_size)
    if not jobs:
        return {"evaluated": 0, "message": "No new jobs to evaluate"}

    llm = LLMClient(use_fast=True)
    evaluated = 0
    high_matches = 0
    chunk_size = 5  # 5 jobs per LLM call — stays under free tier 3 RPM limit

    candidate_summary = {
        "name": config.get("full_name", "Candidate"),
        "location": f"{config.get('current_city')}, {config.get('current_country')}",
        "total_years": config.get("experience_years", 0),
        "ai_years": config.get("ai_years", 0),
        "java_years": config.get("java_years", 0),
        "frontend_years": config.get("frontend_years", 0),
        "cloud_years": config.get("cloud_years", 0),
        "skills": ", ".join((config.get("skills") or [])[:25]),
        "target_roles": ", ".join((config.get("target_roles") or [])[:8]),
        "work_auth": str(config.get("work_authorization") or {}),
    }

    total_batches = (len(jobs) + chunk_size - 1) // chunk_size
    for i in range(0, len(jobs), chunk_size):
        chunk = jobs[i:i + chunk_size]
        try:
            results = _score_batch(llm, chunk, candidate_summary)
            for j, result in enumerate(results):
                job = chunk[j]
                try:
                    save_match(user_id, {
                        "job_id": job["id"],
                        "match_level": result["match_level"],
                        "overall_score": float(result["overall_score"]),
                        "technical_score": float(result.get("technical_score", 0)),
                        "ai_score": float(result.get("ai_score", 0)),
                        "java_score": float(result.get("java_score", 0)),
                        "frontend_score": float(result.get("frontend_score", 0)),
                        "cloud_score": float(result.get("cloud_score", 0)),
                        "location_score": float(result.get("location_score", 0)),
                        "visa_score": float(result.get("visa_score", 0)),
                        "explanation": result.get("explanation", {}),
                    })
                    if result["match_level"] == "HIGH_MATCH":
                        high_matches += 1
                    evaluated += 1
                except Exception as e:
                    logger.error("save_match_failed", job_id=job["id"], error=str(e))

            logger.info("batch_matched", batch=i // chunk_size + 1,
                        total_batches=total_batches, evaluated=evaluated, high_matches=high_matches)

            if i + chunk_size < len(jobs):
                time.sleep(20)  # 20s between calls = ~3 RPM, safe for free tier

        except Exception as e:
            logger.error("batch_match_failed", batch_start=i, error=str(e))
            time.sleep(60)  # back off 60s on rate limit error

    return {"evaluated": evaluated, "high_matches": high_matches}


def _score_batch(llm: LLMClient, jobs: list[dict], candidate: dict) -> list[dict]:
    """Score a batch of jobs in a single LLM call."""
    jobs_text = "\n\n".join(
        f"JOB {j}:\nTitle: {job['title']}\nCompany: {job['company']}\n"
        f"Location: {job.get('location', 'Unknown')}\n"
        f"Remote: {job.get('remote_type', 'UNKNOWN')} | Visa: {job.get('visa_sponsorship', 'UNKNOWN')}\n"
        f"Description (first 150 chars): {job['description'][:150]}"
        for j, job in enumerate(jobs)
    )

    prompt = BATCH_PROMPT.format(**candidate, jobs_text=jobs_text)
    results = llm.invoke_json(prompt, SYSTEM)

    # Handle both array response and wrapped response
    if isinstance(results, dict) and "results" in results:
        results = results["results"]
    if not isinstance(results, list):
        raise ValueError(f"Expected list, got {type(results)}")
    if len(results) != len(jobs):
        raise ValueError(f"Expected {len(jobs)} results, got {len(results)}")

    return results


def _get_user_config(user_id: str) -> dict | None:
    from app.db.queries import get_candidate_config, get_profile
    config = get_candidate_config(user_id)
    profile = get_profile(user_id)
    if not config or not profile:
        return None
    return {**profile, **config}
