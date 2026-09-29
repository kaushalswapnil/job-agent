import structlog
from datetime import datetime, timezone
from app.db.queries import (
    get_high_match_jobs, create_application, create_approval_request,
    update_application, get_candidate_config, get_profile, log_action
)
from app.agents.resume.runner import tailor_resume, generate_cover_letter

logger = structlog.get_logger()


def process_high_match_jobs(user_id: str) -> dict:
    """
    For every HIGH/MEDIUM match job not yet applied to:
    1. Generate tailored resume
    2. Determine if human approval needed
    3. Create application record
    """
    profile = get_profile(user_id)
    config = get_candidate_config(user_id)
    if not profile or not config:
        return {"error": "Complete onboarding first"}

    combined = {**profile, **config}
    matches = get_high_match_jobs(user_id, limit=10)
    processed = 0
    approvals_created = 0

    for match in matches:
        job = match.get("jobs") or {}
        if not job:
            continue
        try:
            # Tailor resume
            resume_record = tailor_resume(user_id, job, combined)

            # Generate cover letter
            cover_letter = generate_cover_letter(user_id, job, combined)

            # Create application record
            app = create_application(user_id, {
                "job_id": job["id"],
                "company": job["company"],
                "role": job["title"],
                "job_url": job["url"],
                "country": job.get("country"),
                "location": job.get("location"),
                "job_match_score": match.get("overall_score"),
                "ai_score": match.get("ai_score"),
                "java_score": match.get("java_score"),
                "fullstack_score": match.get("frontend_score"),
                "visa_status": job.get("visa_sponsorship", "UNKNOWN"),
                "remote_status": job.get("remote_type", "UNKNOWN"),
                "resume_id": resume_record["id"],
                "cover_letter_text": cover_letter,
                "status": "RESUME_GENERATED",
            })

            # Check if approval needed
            approval_questions = _check_approval_needed(job, match, combined)
            if approval_questions:
                create_approval_request(user_id, {
                    "application_id": app["id"],
                    "company": job["company"],
                    "role": job["title"],
                    "country": job.get("country"),
                    "job_url": job["url"],
                    "match_score": match.get("overall_score"),
                    "resume_id": resume_record["id"],
                    "questions": approval_questions,
                    "reason": "Human review required before submission",
                })
                update_application(app["id"], {"status": "PENDING_APPROVAL"})
                approvals_created += 1
            else:
                update_application(app["id"], {"status": "PENDING_APPROVAL", "next_action": "Ready to submit — awaiting your approval"})
                approvals_created += 1  # Always ask for approval in MVP

            log_action(user_id, "APPLICATION_PREPARED", f"{job['title']} at {job['company']}", application_id=app["id"], agent="application")
            processed += 1

        except Exception as e:
            logger.error("application_prep_failed", job_id=job.get("id"), error=str(e))

    return {"processed": processed, "approvals_created": approvals_created}


def _check_approval_needed(job: dict, match: dict, config: dict) -> list[dict]:
    """Returns questions requiring human input. Always returns at least one in MVP."""
    questions = []
    country = (job.get("country") or "").lower()
    work_auth = config.get("work_authorization") or {}

    auth_status = work_auth.get(country, work_auth.get("remote", "authorized"))
    if auth_status == "requires_sponsorship":
        visa = job.get("visa_sponsorship", "UNKNOWN")
        if visa in ("UNKNOWN", "NOT_SUPPORTED"):
            questions.append({
                "question": f"This job is in {job.get('country')}. Visa sponsorship status is '{visa}'. Do you want to apply?",
                "type": "visa_decision",
                "recommended": "Apply only if sponsorship is available — verify on company website",
            })

    score = match.get("overall_score", 0)
    auto_threshold = (config.get("job_prefs") or {}).get("auto_apply_threshold", 80)
    if score < auto_threshold:
        questions.append({
            "question": f"Match score is {score:.0f}% (below your {auto_threshold}% auto-apply threshold). Confirm application?",
            "type": "score_confirmation",
            "recommended": f"Score: {score:.0f}% — review job description before applying",
        })

    if not questions:
        questions.append({
            "question": f"Ready to apply to {job['title']} at {job['company']} ({score:.0f}% match). Confirm?",
            "type": "final_confirmation",
            "recommended": "Apply",
        })

    return questions
