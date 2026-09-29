import structlog
from common.llm_client import LLMClient
from common.database import get_session, update_application_status
from common.models import ApplicationStatus, MessageClassification

logger = structlog.get_logger()

CLASSIFY_PROMPT = """
Classify this email message from a recruiter or job application system.

Subject: {subject}
From: {from_address}
Body:
{body}

Return ONLY this JSON:
{{
  "classification": "<APPLICATION_RECEIVED|APPLICATION_REVIEW|RECRUITER_CONTACT|INTERVIEW_REQUEST|INTERVIEW_CONFIRMATION|ASSESSMENT_REQUEST|REJECTION|OFFER|OTHER>",
  "company": "<company name if detectable>",
  "role": "<role if detectable>",
  "interview_details": {{
    "proposed_dates": ["<date1>"],
    "proposed_times": ["<time1>"],
    "timezone": "<timezone>",
    "interview_type": "<video|phone|onsite>"
  }},
  "requires_response": <true|false>,
  "summary": "<one sentence summary>"
}}
"""


class EmailMonitoringAgent:
    """
    Classifies incoming emails related to job applications.
    Triggered every 10 minutes via EventBridge.

    Email fetching is done via IMAP (configured separately) or
    via SES inbound rules that write to S3.
    """

    def __init__(self):
        self._llm = LLMClient(task="job_normalization")

    def classify_message(self, message: dict) -> dict:
        """Classify a single email message."""
        prompt = CLASSIFY_PROMPT.format(
            subject=message.get("subject", ""),
            from_address=message.get("from_address", ""),
            body=message.get("body", "")[:2000],
        )
        try:
            result = self._llm.invoke_json(prompt)
            logger.info(
                "email_classified",
                classification=result.get("classification"),
                company=result.get("company"),
            )
            return result
        except Exception as e:
            logger.error("email_classification_failed", error=str(e))
            return {"classification": "OTHER", "requires_response": False}

    def process_classified_message(self, message: dict, classification: dict, application_id: str = None):
        """Update application status based on email classification."""
        cls = classification.get("classification", "OTHER")
        session = get_session()
        try:
            status_map = {
                "INTERVIEW_REQUEST": ApplicationStatus.INTERVIEW_REQUESTED,
                "INTERVIEW_CONFIRMATION": ApplicationStatus.INTERVIEW_SCHEDULED,
                "REJECTION": ApplicationStatus.REJECTED,
                "OFFER": ApplicationStatus.OFFER,
                "RECRUITER_CONTACT": ApplicationStatus.RECRUITER_CONTACTED,
                "ASSESSMENT_REQUEST": ApplicationStatus.MANUAL_ACTION_REQUIRED,
            }
            if application_id and cls in status_map:
                update_application_status(
                    session,
                    application_id,
                    status_map[cls],
                    notes=classification.get("summary"),
                )
        finally:
            session.close()
