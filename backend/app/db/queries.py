"""
Supabase database helpers — all queries use ja_ prefixed tables
to coexist with the existing Roulette app on the same project.
"""
from app.core.supabase import get_supabase
import structlog

logger = structlog.get_logger()


def _db():
    return get_supabase()


# ── Profile ──────────────────────────────────────────────────

def get_profile(user_id: str) -> dict | None:
    try:
        r = _db().table("ja_profiles").select("*").eq("id", user_id).maybe_single().execute()
        return r.data if r else None
    except Exception:
        return None


def upsert_profile(user_id: str, data: dict) -> dict:
    r = _db().table("ja_profiles").upsert({"id": user_id, **data}, on_conflict="id").execute()
    return r.data[0] if r.data else {}


def get_candidate_config(user_id: str) -> dict | None:
    try:
        r = _db().table("ja_candidate_configs").select("*").eq("user_id", user_id).maybe_single().execute()
        return r.data if r else None
    except Exception:
        return None


def upsert_candidate_config(user_id: str, data: dict) -> dict:
    existing = get_candidate_config(user_id)
    if existing:
        r = _db().table("ja_candidate_configs").update(data).eq("user_id", user_id).execute()
    else:
        r = _db().table("ja_candidate_configs").insert({"user_id": user_id, **data}).execute()
    return r.data[0]


# ── Jobs ─────────────────────────────────────────────────────

def upsert_job(job: dict) -> tuple[dict, bool]:
    try:
        existing = (
            _db().table("ja_jobs")
            .select("id")
            .eq("source", job["source"])
            .eq("source_job_id", job["source_job_id"])
            .maybe_single()
            .execute()
        )
        if existing and existing.data:
            return existing.data, False
    except Exception:
        pass
    r = _db().table("ja_jobs").insert(job).execute()
    return r.data[0], True


def get_unmatched_jobs(user_id: str, limit: int = 50) -> list[dict]:
    try:
        matched = (
            _db().table("ja_job_matches")
            .select("job_id")
            .eq("user_id", user_id)
            .execute()
        )
        matched_ids = [m["job_id"] for m in (matched.data or [])] if matched else []
        query = _db().table("ja_jobs").select("*").order("discovered_at", desc=True).limit(limit)
        if matched_ids:
            query = query.not_.in_("id", matched_ids)
        r = query.execute()
        return r.data if r and r.data else []
    except Exception:
        return []


def get_high_match_jobs(user_id: str, limit: int = 20) -> list[dict]:
    applied = (
        _db().table("ja_applications")
        .select("job_id")
        .eq("user_id", user_id)
        .execute()
    )
    applied_ids = [a["job_id"] for a in (applied.data or []) if a.get("job_id")]

    rows = (
        _db().table("ja_job_matches")
        .select("*, ja_jobs(*)")
        .eq("user_id", user_id)
        .in_("match_level", ["HIGH_MATCH", "MEDIUM_MATCH"])
        .order("overall_score", desc=True)
        .limit(limit)
        .execute()
    ).data or []

    if applied_ids:
        rows = [r for r in rows if r["job_id"] not in applied_ids]
    return rows


# ── Matches ───────────────────────────────────────────────────

def save_match(user_id: str, match: dict) -> dict:
    r = (
        _db().table("ja_job_matches")
        .upsert({"user_id": user_id, **match}, on_conflict="user_id,job_id")
        .execute()
    )
    return r.data[0]


def get_matches(user_id: str, level: str = None, limit: int = 50) -> list[dict]:
    q = (
        _db().table("ja_job_matches")
        .select("*, ja_jobs(*)")
        .eq("user_id", user_id)
        .order("overall_score", desc=True)
        .limit(limit)
    )
    if level:
        q = q.eq("match_level", level)
    return q.execute().data or []


# ── Resumes ───────────────────────────────────────────────────

def save_resume_record(user_id: str, data: dict) -> dict:
    r = _db().table("ja_resumes").insert({"user_id": user_id, **data}).execute()
    return r.data[0]


def get_master_resume(user_id: str) -> dict | None:
    try:
        r = (
            _db().table("ja_resumes")
            .select("*")
            .eq("user_id", user_id)
            .eq("resume_type", "MASTER")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return r.data[0] if r and r.data else None
    except Exception:
        return None


# ── Applications ──────────────────────────────────────────────

def create_application(user_id: str, data: dict) -> dict:
    r = _db().table("ja_applications").insert({"user_id": user_id, **data}).execute()
    return r.data[0]


def update_application(app_id: str, data: dict) -> dict:
    r = _db().table("ja_applications").update(data).eq("id", app_id).execute()
    return r.data[0]


def get_applications(user_id: str, status: str = None, limit: int = 100) -> list[dict]:
    q = (
        _db().table("ja_applications")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status:
        q = q.eq("status", status)
    return q.execute().data or []


# ── Approvals ─────────────────────────────────────────────────

def create_approval_request(user_id: str, data: dict) -> dict:
    r = _db().table("ja_approval_requests").insert({"user_id": user_id, **data}).execute()
    return r.data[0]


def get_pending_approvals(user_id: str) -> list[dict]:
    r = (
        _db().table("ja_approval_requests")
        .select("*")
        .eq("user_id", user_id)
        .eq("resolved", False)
        .order("created_at", desc=True)
        .execute()
    )
    return r.data or []


def resolve_approval(approval_id: str, resolution: str) -> dict:
    from datetime import datetime, timezone
    r = (
        _db().table("ja_approval_requests")
        .update({
            "resolved": True,
            "resolution": resolution,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", approval_id)
        .execute()
    )
    return r.data[0]


# ── Audit log ─────────────────────────────────────────────────

def log_action(user_id: str, action: str, detail: str = None,
               application_id: str = None, agent: str = None, model: str = None):
    _db().table("ja_audit_log").insert({
        "user_id": user_id,
        "application_id": application_id,
        "action": action,
        "detail": detail,
        "agent_name": agent,
        "llm_model": model,
    }).execute()


# ── Dashboard stats ───────────────────────────────────────────

def get_dashboard_stats(user_id: str) -> dict:
    apps = get_applications(user_id, limit=1000)
    matches = get_matches(user_id, limit=1000)
    approvals = get_pending_approvals(user_id)

    status_counts: dict[str, int] = {}
    for a in apps:
        s = a.get("status", "UNKNOWN")
        status_counts[s] = status_counts.get(s, 0) + 1

    total_jobs = _db().table("ja_jobs").select("id", count="exact").execute()

    return {
        "total_jobs_discovered": total_jobs.count or 0,
        "jobs_evaluated": len(matches),
        "high_match_jobs": sum(1 for m in matches if m.get("match_level") == "HIGH_MATCH"),
        "applications_submitted": status_counts.get("APPLICATION_SUBMITTED", 0),
        "pending_approval": len(approvals),
        "recruiter_responses": status_counts.get("RECRUITER_CONTACTED", 0),
        "interviews": (
            status_counts.get("INTERVIEW_REQUESTED", 0) +
            status_counts.get("INTERVIEW_SCHEDULED", 0)
        ),
        "rejections": status_counts.get("REJECTED", 0),
        "offers": status_counts.get("OFFER", 0),
    }
