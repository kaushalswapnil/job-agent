import pytest
import json
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3
import os

os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["ENV"] = "local"


@mock_aws
class TestApplicationAgentIntegration:
    """
    Integration test: ApplicationAgent correctly routes HIGH_MATCH jobs
    to approval queue when visa sponsorship is unknown for international roles.
    """

    def setup_method(self):
        # Create SQS queues
        sqs = boto3.client("sqs", region_name="us-east-1")
        sqs.create_queue(QueueName="job-agent-notifications")
        sqs.create_queue(QueueName="job-agent-applications")
        sqs.create_queue(QueueName="job-agent-approvals")

        # Create S3 bucket
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="job-agent-resumes-local")
        s3.put_object(
            Bucket="job-agent-resumes-local",
            Key="master/master_resume.txt",
            Body=b"Master Resume Content",
        )

    @patch("application.agent.load_system_config")
    @patch("application.agent.load_candidate_profile")
    @patch("application.agent.get_session")
    @patch("application.agent.save_application")
    @patch("application.agent.save_approval_request")
    @patch("application.agent.update_application_status")
    def test_international_job_requires_approval(
        self, mock_update, mock_save_approval, mock_save_app, mock_session,
        mock_profile, mock_config
    ):
        mock_config.return_value = {
            "sqs": {
                "approval_queue": "https://sqs.us-east-1.amazonaws.com/123/job-agent-approvals",
                "notification_queue": "https://sqs.us-east-1.amazonaws.com/123/job-agent-notifications",
                "application_queue": "https://sqs.us-east-1.amazonaws.com/123/job-agent-applications",
            },
            "agents": {"application": {"auto_submit_enabled": False}},
            "s3": {"resumes_bucket": "job-agent-resumes-local"},
            "llm": {
                "primary_model": "anthropic.claude-3-haiku-20240307-v1:0",
                "fallback_model": "anthropic.claude-3-haiku-20240307-v1:0",
                "resume_tailoring": {"model": "anthropic.claude-3-haiku-20240307-v1:0", "temperature": 0.3, "max_tokens": 4096},
                "cover_letter": {"model": "anthropic.claude-3-haiku-20240307-v1:0", "temperature": 0.4, "max_tokens": 1024},
            },
        }
        mock_profile.return_value = {
            "personal_information": {"full_name": "Test User"},
            "experience": {"total_years": 7, "ai_years": 3, "java_years": 6, "frontend_years": 4, "cloud_years": 4},
            "work_authorization": {"usa": "requires_sponsorship", "remote": "authorized"},
            "salary_preferences": {},
            "job_preferences": {"auto_apply_threshold": 80, "require_human_approval_below": 80},
            "professional_summary": "Test summary",
        }
        mock_session.return_value = MagicMock()

        from application.agent import ApplicationAgent

        with patch.object(ApplicationAgent, "_resume_agent") as mock_resume:
            mock_resume.get_master_resume.return_value = "Master resume text"
            mock_resume.tailor_for_job.return_value = {
                "resume_id": "test-resume-id",
                "s3_key": "tailored/test/resume.txt",
                "version": "20240101_120000",
                "tailoring_notes": "Tailored for AI role",
                "key_requirements_matched": ["Python", "LangChain"],
            }

            agent = ApplicationAgent()
            result = agent.process_job(
                job={
                    "job_id": "test_001",
                    "company": "US Tech Corp",
                    "title": "AI Engineer",
                    "url": "https://example.com/job",
                    "country": "USA",
                    "location": "San Francisco, CA",
                    "description": "AI Engineer role requiring Python and LangChain.",
                    "visa_sponsorship": "UNKNOWN",
                    "remote_type": "ONSITE",
                },
                match={"overall_score": 88, "ai_score": 92, "java_score": 70, "frontend_score": 60},
            )

        assert result["action"] == "PENDING_APPROVAL"
        mock_save_approval.assert_called_once()
