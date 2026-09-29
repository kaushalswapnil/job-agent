import uuid
import boto3
import structlog
from datetime import datetime
from common.llm_client import LLMClient
from common.config_loader import load_candidate_profile, load_system_config
from common.aws_clients import get_s3_client

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are an expert technical resume writer specializing in software engineering and AI/ML roles.
Your task is to tailor a master resume for a specific job posting.

CRITICAL RULES — NEVER VIOLATE:
1. Never fabricate employment, companies, job titles, degrees, certifications, or years of experience.
2. Never invent projects, technologies, achievements, metrics, or responsibilities.
3. You may reorder, emphasize, rephrase, and restructure — but all facts must remain truthful.
4. The resume must remain ATS-friendly and professional.
Return ONLY valid JSON."""

TAILOR_PROMPT = """
Tailor the candidate's master resume for the job posting below.

## JOB POSTING
Title: {title}
Company: {company}
Description:
{description}

## MASTER RESUME
{master_resume}

## CANDIDATE PROFILE SUMMARY
{profile_summary}

## INSTRUCTIONS
1. Extract the top 10 requirements from the JD.
2. Identify which candidate experiences best match those requirements.
3. Reorder skills section to put most relevant skills first.
4. Rewrite the professional summary (3-4 sentences) to align with this specific role.
5. Adjust experience bullet points to emphasize relevant work — do NOT invent new bullets.
6. Highlight AI/GenAI/RAG/LLM experience if the role requires it.
7. Highlight Java/Spring Boot if the role requires it.
8. Highlight React/Angular/React Native if the role requires it.
9. Highlight AWS/cloud if the role requires it.

Return this exact JSON:
{{
  "professional_summary": "<tailored 3-4 sentence summary>",
  "skills_ordered": ["<most relevant skill>", "..."],
  "key_requirements_matched": ["<req1>", "..."],
  "experience_highlights": ["<highlight1>", "..."],
  "tailoring_notes": "<brief explanation of changes made>",
  "full_resume_text": "<complete tailored resume in plain text, ready to use>"
}}
"""


class ResumeTailoringAgent:
    """
    Generates a tailored resume for HIGH_MATCH jobs using Bedrock LLM.
    Stores both master and tailored versions in S3.
    """

    def __init__(self):
        self._llm = LLMClient(task="resume_tailoring")
        self._s3 = get_s3_client()
        self._config = load_system_config()
        self._profile = load_candidate_profile()
        self._bucket = self._config["s3"]["resumes_bucket"]

    def tailor_for_job(self, job: dict, master_resume_text: str) -> dict:
        """
        Generate a tailored resume for a specific job.
        Returns resume metadata including S3 key and version ID.
        """
        prompt = TAILOR_PROMPT.format(
            title=job["title"],
            company=job["company"],
            description=job["description"][:5000],
            master_resume=master_resume_text[:3000],
            profile_summary=self._build_profile_summary(),
        )

        result = self._llm.invoke_json(prompt, SYSTEM_PROMPT)

        resume_id = str(uuid.uuid4())
        version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        s3_key = f"tailored/{job['job_id']}/{version}_{resume_id}.txt"

        self._s3.put_object(
            Bucket=self._bucket,
            Key=s3_key,
            Body=result["full_resume_text"].encode("utf-8"),
            ContentType="text/plain",
            Metadata={
                "job_id": job["job_id"],
                "company": job["company"],
                "role": job["title"],
                "version": version,
            },
        )

        logger.info(
            "resume_tailored",
            job_id=job["job_id"],
            company=job["company"],
            s3_key=s3_key,
            requirements_matched=len(result.get("key_requirements_matched", [])),
        )

        return {
            "resume_id": resume_id,
            "s3_key": s3_key,
            "version": version,
            "resume_type": "TAILORED",
            "job_id": job["job_id"],
            "tailoring_notes": result.get("tailoring_notes"),
            "key_requirements_matched": result.get("key_requirements_matched", []),
        }

    def upload_master_resume(self, resume_text: str) -> str:
        """Upload or replace the master resume in S3. Returns S3 key."""
        s3_key = "master/master_resume.txt"
        self._s3.put_object(
            Bucket=self._bucket,
            Key=s3_key,
            Body=resume_text.encode("utf-8"),
            ContentType="text/plain",
        )
        logger.info("master_resume_uploaded", s3_key=s3_key)
        return s3_key

    def get_master_resume(self) -> str:
        """Fetch master resume text from S3."""
        s3_key = "master/master_resume.txt"
        try:
            obj = self._s3.get_object(Bucket=self._bucket, Key=s3_key)
            return obj["Body"].read().decode("utf-8")
        except self._s3.exceptions.NoSuchKey:
            raise FileNotFoundError("Master resume not found in S3. Upload it first via the API.")

    def _build_profile_summary(self) -> str:
        p = self._profile
        exp = p.get("experience", {})
        return (
            f"Total experience: {exp.get('total_years')} years. "
            f"AI/ML: {exp.get('ai_years')} years. "
            f"Java: {exp.get('java_years')} years. "
            f"Frontend: {exp.get('frontend_years')} years. "
            f"Cloud: {exp.get('cloud_years')} years."
        )
