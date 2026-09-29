import uuid
import structlog
from common.models import JobMatch, MatchLevel
from common.llm_client import LLMClient
from common.config_loader import load_candidate_profile
from common.database import get_session, get_unmatched_jobs, save_job_match

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are an expert technical recruiter and job-fit analyst.
Evaluate how well a candidate matches a job posting. Be precise and honest.
Return ONLY valid JSON — no markdown, no explanation outside the JSON."""

MATCH_PROMPT = """
Evaluate this candidate against the job posting below.

## CANDIDATE PROFILE
{candidate_summary}

## JOB POSTING
Title: {title}
Company: {company}
Location: {location}
Description:
{description}

## SCORING INSTRUCTIONS
Score each dimension 0-100 based on genuine alignment. Do NOT inflate scores.

Return this exact JSON:
{{
  "overall_score": <0-100>,
  "match_level": "<HIGH_MATCH|MEDIUM_MATCH|LOW_MATCH|DO_NOT_APPLY>",
  "technical_score": <0-100>,
  "ai_score": <0-100>,
  "java_score": <0-100>,
  "frontend_score": <0-100>,
  "cloud_score": <0-100>,
  "location_score": <0-100>,
  "visa_score": <0-100>,
  "seniority_score": <0-100>,
  "explanation": {{
    "technical_match": "<brief reason>",
    "ai_match": "<brief reason>",
    "java_match": "<brief reason>",
    "frontend_match": "<brief reason>",
    "location_match": "<brief reason>",
    "visa_match": "<CONFIRMED|LIKELY|UNKNOWN|NOT_SUPPORTED>",
    "recommendation": "<apply|skip|needs_review>",
    "key_gaps": ["<gap1>", "<gap2>"]
  }}
}}

Match level rules:
- HIGH_MATCH: overall >= 80
- MEDIUM_MATCH: overall 60-79
- LOW_MATCH: overall 40-59
- DO_NOT_APPLY: overall < 40 OR candidate clearly lacks fundamental requirements
"""


class JobMatchingAgent:
    """
    Scores every unmatched job against the candidate profile using Bedrock LLM.
    Uses semantic analysis, not keyword matching.
    """

    def __init__(self):
        self._llm = LLMClient(task="job_matching")
        self._profile = load_candidate_profile()
        self._candidate_summary = self._build_candidate_summary()

    def run(self, batch_size: int = 50) -> dict:
        session = get_session()
        try:
            jobs = get_unmatched_jobs(session, limit=batch_size)
            if not jobs:
                logger.info("no_unmatched_jobs")
                return {"evaluated": 0}

            evaluated = 0
            for job in jobs:
                try:
                    match = self._evaluate(job)
                    save_job_match(session, match)
                    evaluated += 1
                    logger.info(
                        "job_evaluated",
                        job_id=job["job_id"],
                        company=job["company"],
                        score=match.overall_score,
                        level=match.match_level.value,
                    )
                except Exception as e:
                    logger.error("job_evaluation_failed", job_id=job["job_id"], error=str(e))

            return {"evaluated": evaluated, "total_available": len(jobs)}
        finally:
            session.close()

    def _evaluate(self, job: dict) -> JobMatch:
        prompt = MATCH_PROMPT.format(
            candidate_summary=self._candidate_summary,
            title=job["title"],
            company=job["company"],
            location=job.get("location", "Unknown"),
            description=job["description"][:4000],  # Truncate to stay within token limits
        )

        result = self._llm.invoke_json(prompt, SYSTEM_PROMPT)

        return JobMatch(
            job_id=job["job_id"],
            match_level=MatchLevel(result["match_level"]),
            overall_score=float(result["overall_score"]),
            technical_score=float(result.get("technical_score", 0)),
            ai_score=float(result.get("ai_score", 0)),
            java_score=float(result.get("java_score", 0)),
            frontend_score=float(result.get("frontend_score", 0)),
            cloud_score=float(result.get("cloud_score", 0)),
            location_score=float(result.get("location_score", 0)),
            visa_score=float(result.get("visa_score", 0)),
            seniority_score=float(result.get("seniority_score", 0)),
            explanation=result.get("explanation", {}),
        )

    def _build_candidate_summary(self) -> str:
        p = self._profile
        info = p.get("personal_information", {})
        exp = p.get("experience", {})
        skills = p.get("skills", {})

        skill_names = []
        for category in skills.values():
            for s in category:
                skill_names.append(f"{s['name']} ({s['proficiency']}, {s['years']}y)")

        roles = []
        for category in p.get("target_roles", {}).values():
            roles.extend(category)

        loc_prefs = p.get("location_preferences", {})
        work_auth = p.get("work_authorization", {})

        return f"""
Name: {info.get('full_name')}
Current Location: {info.get('current_city')}, {info.get('current_location')}
Total Experience: {exp.get('total_years')} years
AI/ML Experience: {exp.get('ai_years')} years
Java Experience: {exp.get('java_years')} years
Frontend Experience: {exp.get('frontend_years')} years
Cloud Experience: {exp.get('cloud_years')} years

Target Roles: {', '.join(roles[:10])}

Skills: {', '.join(skill_names)}

Work Authorization:
- India: {work_auth.get('india')}
- USA: {work_auth.get('usa')}
- Europe: {work_auth.get('europe')}
- UK: {work_auth.get('uk')}
- Remote: {work_auth.get('remote')}

Location Preferences: India (preferred), Europe (with visa sponsorship), USA/UK/Canada/Australia/Singapore/UAE (with sponsorship), Remote (worldwide)
""".strip()
