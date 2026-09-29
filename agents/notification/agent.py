import json
import structlog
from common.aws_clients import get_ses_client
from common.config_loader import load_candidate_profile

logger = structlog.get_logger()

SENDER_EMAIL = "noreply@jobagent.yourdomain.com"  # Must be verified in SES


class NotificationAgent:
    """Sends email notifications via Amazon SES for key job search events."""

    def __init__(self):
        self._ses = get_ses_client()
        self._profile = load_candidate_profile()
        self._prefs = self._profile.get("notifications", {})
        self._recipient = self._prefs.get("email", {}).get("address", "")

    def send_high_match_alert(self, job: dict, score: float):
        if not self._prefs.get("high_match_alert", {}).get("enabled"):
            return
        threshold = self._prefs.get("high_match_alert", {}).get("threshold", 85)
        if score < threshold:
            return
        self._send(
            subject=f"New {score:.0f}% match: {job['title']} at {job['company']}",
            body=(
                f"New high-match job found!\n\n"
                f"Role: {job['title']}\n"
                f"Company: {job['company']}\n"
                f"Location: {job.get('location', 'Unknown')}\n"
                f"Match Score: {score:.0f}%\n"
                f"Visa Sponsorship: {job.get('visa_sponsorship', 'UNKNOWN')}\n"
                f"URL: {job['url']}\n"
            ),
        )

    def send_application_submitted(self, application: dict):
        if not self._prefs.get("application_submitted_alert"):
            return
        self._send(
            subject=f"Application submitted: {application['role']} at {application['company']}",
            body=(
                f"Application submitted successfully.\n\n"
                f"Role: {application['role']}\n"
                f"Company: {application['company']}\n"
                f"Country: {application.get('country', 'Unknown')}\n"
                f"Match Score: {application.get('job_match_score', 0):.0f}%\n"
                f"Application ID: {application['application_id']}\n"
            ),
        )

    def send_approval_required(self, request: dict):
        if not self._prefs.get("human_approval_required_alert"):
            return
        questions_text = "\n".join(
            f"  Q: {q['question']}\n  Recommended: {q.get('recommended', 'N/A')}"
            for q in request.get("questions", [])
        )
        self._send(
            subject=f"Action required: {request['role']} at {request['company']}",
            body=(
                f"Your input is required before this application can be submitted.\n\n"
                f"Company: {request['company']}\n"
                f"Role: {request['role']}\n"
                f"Country: {request.get('country', 'Unknown')}\n"
                f"Match Score: {request.get('match_score', 0):.0f}%\n"
                f"Job URL: {request['job_url']}\n\n"
                f"Questions requiring your response:\n{questions_text}\n\n"
                f"Request ID: {request['request_id']}\n"
                f"Approve via dashboard or API: POST /api/approvals/{request['request_id']}/approve\n"
            ),
        )

    def send_interview_request(self, details: dict):
        if not self._prefs.get("interview_request_alert"):
            return
        self._send(
            subject=f"Interview request: {details.get('role')} at {details.get('company')}",
            body=(
                f"Interview request received!\n\n"
                f"Company: {details.get('company')}\n"
                f"Role: {details.get('role')}\n"
                f"Recruiter: {details.get('recruiter_name', 'Unknown')}\n"
                f"Interview Type: {details.get('interview_type', 'Unknown')}\n"
                f"Proposed Times:\n{details.get('proposed_times', 'See original message')}\n\n"
                f"Would you like to confirm one of these times?\n"
                f"Respond via dashboard: /api/interviews/{details.get('application_id')}/schedule\n"
            ),
        )

    def send_daily_summary(self, summary: dict):
        if not self._prefs.get("daily_summary", {}).get("enabled"):
            return
        new_opps = "\n".join(
            f"  {i+1}. {j['title']} — {j.get('country', 'Remote')} — {j['score']:.0f}% match"
            for i, j in enumerate(summary.get("top_new_jobs", [])[:5])
        )
        self._send(
            subject=f"Job Search Summary — {summary.get('date')}",
            body=(
                f"JOB SEARCH DAILY SUMMARY — {summary.get('date')}\n"
                f"{'='*50}\n\n"
                f"Jobs discovered:          {summary.get('jobs_discovered', 0)}\n"
                f"Relevant jobs:            {summary.get('jobs_evaluated', 0)}\n"
                f"High-match jobs:          {summary.get('high_match_jobs', 0)}\n"
                f"Applications submitted:   {summary.get('apps_submitted', 0)}\n"
                f"Pending approval:         {summary.get('apps_pending', 0)}\n"
                f"Recruiter responses:      {summary.get('recruiter_responses', 0)}\n"
                f"Interviews:               {summary.get('interviews', 0)}\n"
                f"Rejected:                 {summary.get('rejections', 0)}\n\n"
                f"Top new opportunities:\n{new_opps or '  None today'}\n\n"
                f"Action required: {summary.get('action_required', 0)} item(s) need your attention.\n"
                f"View dashboard: https://your-dashboard-url.com\n"
            ),
        )

    def _send(self, subject: str, body: str):
        if not self._recipient:
            logger.warning("notification_no_recipient")
            return
        try:
            self._ses.send_email(
                Source=SENDER_EMAIL,
                Destination={"ToAddresses": [self._recipient]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
                },
            )
            logger.info("notification_sent", subject=subject)
        except Exception as e:
            logger.error("notification_failed", subject=subject, error=str(e))
