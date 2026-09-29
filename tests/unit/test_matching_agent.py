import pytest
from unittest.mock import patch, MagicMock
from common.models import JobMatch, MatchLevel
from matching.agent import JobMatchingAgent


SAMPLE_JOB = {
    "job_id": "test_job_001",
    "title": "Senior AI Engineer",
    "company": "AI Startup",
    "location": "Remote",
    "description": (
        "We are looking for a Senior AI Engineer with expertise in Python, "
        "LangChain, RAG systems, LLMs, Amazon Bedrock, and vector databases. "
        "Java Spring Boot experience is a plus. AWS required."
    ),
}

LLM_RESPONSE = {
    "overall_score": 92,
    "match_level": "HIGH_MATCH",
    "technical_score": 90,
    "ai_score": 95,
    "java_score": 70,
    "frontend_score": 60,
    "cloud_score": 88,
    "location_score": 95,
    "visa_score": 80,
    "seniority_score": 85,
    "explanation": {
        "technical_match": "Strong Python, LangChain, RAG alignment",
        "ai_match": "Excellent — RAG, LLM, Bedrock all match",
        "java_match": "Java mentioned as plus, candidate has 6 years",
        "frontend_match": "Not primary requirement",
        "location_match": "Remote — no restrictions",
        "visa_match": "UNKNOWN",
        "recommendation": "apply",
        "key_gaps": [],
    },
}


class TestJobMatchingAgent:
    @patch("matching.agent.LLMClient")
    @patch("matching.agent.load_candidate_profile")
    def test_evaluate_returns_high_match(self, mock_profile, mock_llm_cls):
        mock_profile.return_value = {
            "personal_information": {"full_name": "Test User", "current_city": "Bangalore", "current_location": "India"},
            "experience": {"total_years": 7, "ai_years": 3, "java_years": 6, "frontend_years": 4, "cloud_years": 4},
            "target_roles": {"ai_genai": ["AI Engineer"]},
            "skills": {"languages": [{"name": "Python", "proficiency": "advanced", "years": 3}]},
            "work_authorization": {"india": "authorized", "remote": "authorized"},
            "location_preferences": {},
        }
        mock_llm = MagicMock()
        mock_llm.invoke_json.return_value = LLM_RESPONSE
        mock_llm_cls.return_value = mock_llm

        agent = JobMatchingAgent()
        match = agent._evaluate(SAMPLE_JOB)

        assert match.match_level == MatchLevel.HIGH_MATCH
        assert match.overall_score == 92.0
        assert match.ai_score == 95.0

    @patch("matching.agent.LLMClient")
    @patch("matching.agent.load_candidate_profile")
    def test_evaluate_do_not_apply_for_low_score(self, mock_profile, mock_llm_cls):
        mock_profile.return_value = {
            "personal_information": {"full_name": "Test", "current_city": "Bangalore", "current_location": "India"},
            "experience": {"total_years": 7, "ai_years": 3, "java_years": 6, "frontend_years": 4, "cloud_years": 4},
            "target_roles": {},
            "skills": {},
            "work_authorization": {},
            "location_preferences": {},
        }
        low_score_response = {**LLM_RESPONSE, "overall_score": 25, "match_level": "DO_NOT_APPLY"}
        mock_llm = MagicMock()
        mock_llm.invoke_json.return_value = low_score_response
        mock_llm_cls.return_value = mock_llm

        agent = JobMatchingAgent()
        match = agent._evaluate(SAMPLE_JOB)

        assert match.match_level == MatchLevel.DO_NOT_APPLY
        assert match.overall_score == 25.0
