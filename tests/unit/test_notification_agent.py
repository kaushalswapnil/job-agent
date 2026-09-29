import pytest
from unittest.mock import patch, MagicMock
from notification.agent import NotificationAgent


class TestNotificationAgent:
    @patch("notification.agent.get_ses_client")
    @patch("notification.agent.load_candidate_profile")
    def test_high_match_alert_sent_above_threshold(self, mock_profile, mock_ses_cls):
        mock_profile.return_value = {
            "notifications": {
                "email": {"enabled": True, "address": "test@example.com"},
                "high_match_alert": {"enabled": True, "threshold": 85},
                "application_submitted_alert": True,
                "human_approval_required_alert": True,
                "interview_request_alert": True,
                "daily_summary": {"enabled": True},
            }
        }
        mock_ses = MagicMock()
        mock_ses_cls.return_value = mock_ses

        agent = NotificationAgent()
        agent.send_high_match_alert(
            {"title": "AI Engineer", "company": "TechCorp", "location": "Remote",
             "visa_sponsorship": "UNKNOWN", "url": "https://example.com"},
            score=92.0,
        )

        mock_ses.send_email.assert_called_once()
        call_args = mock_ses.send_email.call_args[1]
        assert "92%" in call_args["Message"]["Subject"]["Data"]

    @patch("notification.agent.get_ses_client")
    @patch("notification.agent.load_candidate_profile")
    def test_high_match_alert_not_sent_below_threshold(self, mock_profile, mock_ses_cls):
        mock_profile.return_value = {
            "notifications": {
                "email": {"enabled": True, "address": "test@example.com"},
                "high_match_alert": {"enabled": True, "threshold": 85},
            }
        }
        mock_ses = MagicMock()
        mock_ses_cls.return_value = mock_ses

        agent = NotificationAgent()
        agent.send_high_match_alert(
            {"title": "AI Engineer", "company": "TechCorp", "location": "Remote",
             "visa_sponsorship": "UNKNOWN", "url": "https://example.com"},
            score=70.0,
        )

        mock_ses.send_email.assert_not_called()
