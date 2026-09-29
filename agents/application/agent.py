import uuid
import json
import structlog
from datetime import datetime, timezone
from common.models import Application, ApplicationStatus, ApprovalRequest, MatchLevel
from common.database import get_session, save_application, save_approval_request, update_application_status
from common.config_loader import load_candidate_profile, load_system_config
from common.aws_clients import get_sqs_client
from resume.agent import ResumeTailoringAgent
from cover_letter.agent import CoverLetterAgent

logger = structlog.get_logger()


class ApplicationAgent:
    """
    Processes HIGH_MATCH jobs: generates resume, determines if auto-apply or
    human approval is needed, queues accordingly.

    Auto-apply is disabled by default. Enable in system_config.yaml only after
    thorough testing and legal review for each target platform.
    """

    def __init__(self):
        self._profile = load_candidate_profile()
        self._config = load_system_config()
        self._resume_agent = ResumeTailoringAgent()
        self._cover_letter_agent = CoverLetterAgent()
        self._sqs = get_sqs_client()
        self._approval_queue = self._config["sqs"]["approval_queue"]
        self._notification_queue = self._config["sqs"]["notification_queue"]
        self._auto_submit = self._config["agents"]["application"]["auto_submit_enabled"]
        self._auto_threshold = self._profile["job_preferences"]["auto_apply_threshold"]

    def process_job(self, job: dict, match: dict) -> dict:
        """
        Main entry point. Called for every HIGH_MATCH or MEDIUM_MATCH job.
        Returns action taken.
        """
        session = get_session()
        try:
            application_id = str(uuid.uuid4())

            # Build application record
            app = Application(
                application_id=application_id,
                job_id=job["job_id"],
                company=job["company"],
                role=job["title"],
                job_url=job["url"],
                country=job.get("country"),
                location=job.get("location"),
                job_description=job["description"],
                job_match_score=match["overall_score"],
                ai_relevance_score=match.get("ai_score", 0),
                java_relevance_score=match.get("java_score", 0),
                fullstack_relevance_score=match.get("frontend_score", 0),
                visa_status=job.get("visa_sponsorship", "UNKNOWN"),
                remote_status=job.get("remote_type", "UNKNOWN"),
                status=ApplicationStatus.EVALUATED,
            )
            save_application(session, app)

            # Generate tailored resume
            master_resume = self._resume_agent.get_master_resume()
            resume_meta = self._resume_agent.tailor_for_job(job, master_resume)
            app.resume_version = resume_meta["resume_id"]
            app.status = ApplicationStatus.RESUME_GENERATED
            save_application(session, app)

            # Determine if human approval is needed
            approval_reasons = self._check_approval_needed(job, match)

            if approval_reasons:
                return self._request_approval(session, app, job, match, approval_reasons)

            if self._auto_submit and match["overall_score"] >= self._auto_threshold:
                return self._auto_apply(session, app, job)

            # Default: queue for human review
            return self._request_approval(
                session, app, job, match,
                [{"question": "Please review and confirm this application.", "recommended": "Apply"}]
            )

        finally:
            session.close()

    def _check_approval_needed(self, job: dict, match: dict) -> list[dict]:
        """Returns list of questions requiring human input. Empty = safe to auto-apply."""
        reasons = []
        profile = self._profile
        country = (job.get("country") or "").upper()
        work_auth = profile.get("work_authorization", {})

        # Visa/work authorization check
        country_auth = work_auth.get(country.lower(), work_auth.get("remote", "authorized"))
        if country_auth == "requires_sponsorship":
            visa_status = job.get("visa_sponsorship", "UNKNOWN")
            if visa_status in ("UNKNOWN", "NOT_SUPPORTED"):
                reasons.append({
                    "question": f"This job is in {country}. Visa sponsorship status is {visa_status}. Do you want to apply?",
                    "recommended": "Apply only if sponsorship is available",
                })

        # Salary not configured
        salary_prefs = profile.get("salary_preferences", {})
        country_salary = salary_prefs.get(country.lower())
        if not country_salary:
            reasons.append({
                "question": "Salary expectation required but no default configured for this country.",
                "recommended": "Set salary preference in candidate_profile.yaml",
            })

        # Low confidence score
        if match["overall_score"] < profile["job_preferences"]["require_human_approval_below"]:
            reasons.append({
                "question": f"Match score is {match['overall_score']:.0f}% (below auto-apply threshold). Confirm?",
                "recommended": f"Score: {match['overall_score']:.0f}% — review before applying",
            })

        return reasons

    def _request_approval(self, session, app: Application, job: dict, match: dict, questions: list) -> dict:
        req = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            application_id=app.application_id,
            company=app.company,
            role=app.role,
            country=app.country,
            job_url=app.job_url,
            match_score=app.job_match_score,
            resume_used=app.resume_version,
            questions=questions,
            reason="Human approval required before submission",
        )
        save_approval_request(session, req)
        update_application_status(session, app.application_id, ApplicationStatus.PENDING_APPROVAL)

        # Notify via SQS → Notification Agent
        self._sqs.send_message(
            QueueUrl=self._notification_queue,
            MessageBody=json.dumps({
                "type": "APPROVAL_REQUIRED",
                "request_id": req.request_id,
                "company": app.company,
                "role": app.role,
                "country": app.country,
                "job_url": app.job_url,
                "match_score": app.job_match_score,
                "questions": questions,
            }),
        )

        logger.info("approval_requested", application_id=app.application_id, company=app.company)
        return {"action": "PENDING_APPROVAL", "application_id": app.application_id}

    def _auto_apply(self, session, app: Application, job: dict) -> dict:
        """
        Placeholder for automated application submission.
        Only called when auto_submit_enabled=true AND score >= threshold.
        Actual browser automation runs in ECS Fargate tasks.
        """
        update_application_status(session, app.application_id, ApplicationStatus.APPLICATION_STARTED)

        # Dispatch to ECS Fargate application task via SQS
        self._sqs.send_message(
            QueueUrl=self._config["sqs"]["application_queue"],
            MessageBody=json.dumps({
                "type": "SUBMIT_APPLICATION",
                "application_id": app.application_id,
                "job_id": job["job_id"],
                "job_url": job["url"],
                "resume_version": app.resume_version,
            }),
        )

        logger.info("application_queued", application_id=app.application_id, company=app.company)
        return {"action": "QUEUED_FOR_SUBMISSION", "application_id": app.application_id}
