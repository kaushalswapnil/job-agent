import structlog
from common.llm_client import LLMClient
from common.config_loader import load_candidate_profile

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are a professional cover letter writer for software engineering and AI roles.
Write concise, genuine, non-generic cover letters. Avoid AI-sounding filler phrases.
Return ONLY valid JSON."""

COVER_LETTER_PROMPT = """
Write a cover letter for this job application.

## JOB DETAILS
Title: {title}
Company: {company}
Description:
{description}

## CANDIDATE SUMMARY
{candidate_summary}

## INSTRUCTIONS
- 3 short paragraphs maximum
- Opening: specific reason for interest in this company/role (not generic)
- Middle: 2-3 most relevant technical achievements that match the JD
- Closing: brief, confident, professional
- Avoid: "I am excited to apply", "I am passionate about", "leverage my skills", "synergy"
- Tone: direct, confident, professional
- Length: 200-280 words

Return this exact JSON:
{{
  "cover_letter": "<full cover letter text>",
  "word_count": <number>,
  "key_points_highlighted": ["<point1>", "<point2>"]
}}
"""


class CoverLetterAgent:
    """Generates a concise, tailored cover letter for a specific job."""

    def __init__(self):
        self._llm = LLMClient(task="cover_letter")
        self._profile = load_candidate_profile()

    def generate(self, job: dict) -> dict:
        prompt = COVER_LETTER_PROMPT.format(
            title=job["title"],
            company=job["company"],
            description=job["description"][:3000],
            candidate_summary=self._build_summary(),
        )

        result = self._llm.invoke_json(prompt, SYSTEM_PROMPT)
        logger.info("cover_letter_generated", job_id=job["job_id"], company=job["company"])
        return result

    def _build_summary(self) -> str:
        p = self._profile
        info = p.get("personal_information", {})
        exp = p.get("experience", {})
        summary = p.get("professional_summary", "")
        return (
            f"{info.get('full_name')} — {exp.get('total_years')} years experience.\n"
            f"{summary}"
        )
