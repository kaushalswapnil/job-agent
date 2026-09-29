import uuid
import structlog
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from common.aws_clients import get_db_url
from common.models import Job, JobMatch, Application, ApplicationStatus, ApprovalRequest

logger = structlog.get_logger()

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(get_db_url(), pool_pre_ping=True, pool_size=5)
    return _engine


def get_session() -> Session:
    return sessionmaker(bind=get_engine())()


# ---------------------------------------------------------------------------
# Job operations
# ---------------------------------------------------------------------------

def upsert_job(session: Session, job: Job) -> bool:
    """Insert job if not exists. Returns True if new."""
    existing = session.execute(
        text("SELECT job_id FROM jobs WHERE source = :src AND source_job_id = :sid"),
        {"src": job.source, "sid": job.source_job_id},
    ).fetchone()

    if existing:
        return False

    session.execute(
        text("""
            INSERT INTO jobs (
                job_id, source, source_job_id, company, title, description, url,
                location, country, remote_type, employment_type,
                salary_min, salary_max, salary_currency,
                visa_sponsorship, relocation_support,
                required_skills, preferred_skills,
                years_experience_required, seniority_level,
                status, discovered_at, raw_data
            ) VALUES (
                :job_id, :source, :source_job_id, :company, :title, :description, :url,
                :location, :country, :remote_type, :employment_type,
                :salary_min, :salary_max, :salary_currency,
                :visa_sponsorship, :relocation_support,
                :required_skills, :preferred_skills,
                :years_experience_required, :seniority_level,
                'DISCOVERED', :discovered_at, :raw_data
            )
        """),
        {
            "job_id": job.job_id,
            "source": job.source,
            "source_job_id": job.source_job_id,
            "company": job.company,
            "title": job.title,
            "description": job.description,
            "url": job.url,
            "location": job.location,
            "country": job.country,
            "remote_type": job.remote_type.value,
            "employment_type": job.employment_type.value if job.employment_type else None,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_currency": job.salary_currency,
            "visa_sponsorship": job.visa_sponsorship.value,
            "relocation_support": job.relocation_support,
            "required_skills": ",".join(job.required_skills),
            "preferred_skills": ",".join(job.preferred_skills),
            "years_experience_required": job.years_experience_required,
            "seniority_level": job.seniority_level,
            "discovered_at": job.discovered_at,
            "raw_data": str(job.raw_data) if job.raw_data else None,
        },
    )
    session.commit()
    return True


def save_job_match(session: Session, match: JobMatch):
    session.execute(
        text("""
            INSERT INTO job_matches (
                job_id, match_level, overall_score, technical_score,
                ai_score, java_score, frontend_score, cloud_score,
                location_score, visa_score, seniority_score,
                explanation, evaluated_at
            ) VALUES (
                :job_id, :match_level, :overall_score, :technical_score,
                :ai_score, :java_score, :frontend_score, :cloud_score,
                :location_score, :visa_score, :seniority_score,
                :explanation, :evaluated_at
            )
            ON CONFLICT (job_id) DO UPDATE SET
                match_level = EXCLUDED.match_level,
                overall_score = EXCLUDED.overall_score,
                evaluated_at = EXCLUDED.evaluated_at
        """),
        {**match.model_dump(), "match_level": match.match_level.value,
         "explanation": str(match.explanation)},
    )
    session.execute(
        text("UPDATE jobs SET status = 'EVALUATED' WHERE job_id = :jid"),
        {"jid": match.job_id},
    )
    session.commit()


def get_unmatched_jobs(session: Session, limit: int = 50) -> list[dict]:
    rows = session.execute(
        text("""
            SELECT j.* FROM jobs j
            LEFT JOIN job_matches m ON j.job_id = m.job_id
            WHERE m.job_id IS NULL
            ORDER BY j.discovered_at DESC
            LIMIT :limit
        """),
        {"limit": limit},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def save_application(session: Session, app: Application):
    session.execute(
        text("""
            INSERT INTO applications (
                application_id, job_id, company, role, job_url, country, location,
                job_description, job_match_score, ai_relevance_score,
                java_relevance_score, fullstack_relevance_score,
                visa_status, remote_status, salary,
                resume_version, cover_letter_version,
                application_date, status, last_checked,
                recruiter_name, recruiter_email, recruiter_message,
                interview_status, interview_date, notes, next_action
            ) VALUES (
                :application_id, :job_id, :company, :role, :job_url, :country, :location,
                :job_description, :job_match_score, :ai_relevance_score,
                :java_relevance_score, :fullstack_relevance_score,
                :visa_status, :remote_status, :salary,
                :resume_version, :cover_letter_version,
                :application_date, :status, :last_checked,
                :recruiter_name, :recruiter_email, :recruiter_message,
                :interview_status, :interview_date, :notes, :next_action
            )
            ON CONFLICT (application_id) DO UPDATE SET
                status = EXCLUDED.status,
                last_checked = EXCLUDED.last_checked,
                resume_version = EXCLUDED.resume_version,
                notes = EXCLUDED.notes,
                next_action = EXCLUDED.next_action
        """),
        {
            **app.model_dump(exclude={"audit_log"}),
            "status": app.status.value,
            "visa_status": app.visa_status.value,
            "remote_status": app.remote_status.value,
        },
    )
    session.commit()


def update_application_status(session: Session, application_id: str, status: ApplicationStatus, notes: str = None):
    session.execute(
        text("""
            UPDATE applications
            SET status = :status, last_checked = :now, notes = COALESCE(:notes, notes)
            WHERE application_id = :aid
        """),
        {"status": status.value, "now": datetime.now(timezone.utc), "notes": notes, "aid": application_id},
    )
    session.execute(
        text("""
            INSERT INTO audit_log (log_id, application_id, action, detail, created_at)
            VALUES (:lid, :aid, :action, :detail, :now)
        """),
        {"lid": str(uuid.uuid4()), "aid": application_id, "action": status.value,
         "detail": notes, "now": datetime.now(timezone.utc)},
    )
    session.commit()


def save_approval_request(session: Session, req: ApprovalRequest):
    import json
    session.execute(
        text("""
            INSERT INTO approval_requests (
                request_id, application_id, company, role, country,
                job_url, match_score, resume_used, questions, reason, created_at, resolved
            ) VALUES (
                :request_id, :application_id, :company, :role, :country,
                :job_url, :match_score, :resume_used, :questions, :reason, :created_at, false
            )
        """),
        {**req.model_dump(), "questions": json.dumps(req.questions)},
    )
    session.commit()
