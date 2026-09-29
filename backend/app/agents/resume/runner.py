import io
import structlog
import PyPDF2
import docx
from app.core.llm import LLMClient
from app.core.supabase import get_supabase
from app.db.queries import save_resume_record, get_master_resume, log_action
from datetime import datetime, timezone

logger = structlog.get_logger()

TAILOR_SYSTEM = """You are an expert technical resume writer.
NEVER fabricate employment, companies, job titles, degrees, certifications, years of experience,
projects, technologies, achievements, metrics, or responsibilities.
You may reorder, emphasize, and rephrase — all facts must remain truthful.
Return ONLY valid JSON."""

TAILOR_PROMPT = """
Tailor this resume for the job below.

JOB: {title} at {company}
DESCRIPTION (first 2500 chars):
{description}

MASTER RESUME:
{master_resume}

CANDIDATE: {total_years} yrs total | AI: {ai_years}y | Java: {java_years}y | Frontend: {frontend_years}y

Return ONLY this JSON:
{{
  "professional_summary": "<tailored 3-4 sentence summary>",
  "skills_reordered": ["<most relevant first>"],
  "key_requirements_matched": ["<req1>", "<req2>"],
  "tailoring_notes": "<what was changed and why>",
  "full_resume_text": "<complete tailored resume in clean plain text>"
}}
"""

COVER_SYSTEM = "Write concise, genuine cover letters. Avoid clichés. Return ONLY valid JSON."

COVER_PROMPT = """
Write a cover letter. 3 paragraphs, 200-280 words.
AVOID: "excited to apply", "passionate about", "leverage my skills", "synergy"

JOB: {title} at {company}
DESCRIPTION (first 1500 chars): {description}
CANDIDATE: {name}, {total_years} years experience
SUMMARY: {summary}

Return ONLY this JSON:
{{
  "cover_letter": "<full cover letter text>",
  "word_count": <number>
}}
"""


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif filename.lower().endswith(".docx"):
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)
    return file_bytes.decode("utf-8", errors="ignore")


def upload_master_resume(user_id: str, file_bytes: bytes, filename: str) -> dict:
    supabase = get_supabase()
    storage_path = f"{user_id}/master/{filename}"

    supabase.storage.from_("resumes").upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": "application/octet-stream", "upsert": "true"},
    )

    raw_text = extract_text_from_file(file_bytes, filename)
    record = save_resume_record(user_id, {
        "resume_type": "MASTER",
        "storage_path": storage_path,
        "version": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        "raw_text": raw_text,
    })

    log_action(user_id, "MASTER_RESUME_UPLOADED", f"File: {filename}", agent="resume")
    return record


def tailor_resume(user_id: str, job: dict, config: dict) -> dict:
    master = get_master_resume(user_id)
    if not master or not master.get("raw_text"):
        raise ValueError("No master resume found. Please upload your resume first.")

    # gpt-4o for resume quality — this matters
    llm = LLMClient(use_fast=False)
    prompt = TAILOR_PROMPT.format(
        title=job["title"],
        company=job["company"],
        description=job["description"][:2500],
        master_resume=master["raw_text"][:3000],
        total_years=config.get("experience_years", 0),
        ai_years=config.get("ai_years", 0),
        java_years=config.get("java_years", 0),
        frontend_years=config.get("frontend_years", 0),
    )

    result = llm.invoke_json(prompt, TAILOR_SYSTEM)

    supabase = get_supabase()
    version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    storage_path = f"{user_id}/tailored/{job['id']}_{version}.txt"

    supabase.storage.from_("resumes").upload(
        path=storage_path,
        file=result["full_resume_text"].encode("utf-8"),
        file_options={"content-type": "text/plain", "upsert": "true"},
    )

    record = save_resume_record(user_id, {
        "resume_type": "TAILORED",
        "job_id": job["id"],
        "storage_path": storage_path,
        "version": version,
        "raw_text": result["full_resume_text"],
    })

    log_action(user_id, "RESUME_TAILORED", f"{job['title']} at {job['company']}",
               agent="resume", model="gpt-4o")
    return {
        **record,
        "tailoring_notes": result.get("tailoring_notes"),
        "key_requirements_matched": result.get("key_requirements_matched", []),
    }


def generate_cover_letter(user_id: str, job: dict, config: dict) -> str:
    llm = LLMClient(use_fast=False)
    prompt = COVER_PROMPT.format(
        title=job["title"],
        company=job["company"],
        description=job["description"][:1500],
        name=config.get("full_name", ""),
        total_years=config.get("experience_years", 0),
        summary=(config.get("professional_summary") or "")[:500],
    )
    result = llm.invoke_json(prompt, COVER_SYSTEM)
    return result.get("cover_letter", "")
