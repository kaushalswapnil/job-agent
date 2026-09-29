import pytest
from unittest.mock import patch, MagicMock
from discovery.sources.remotive import RemotiveSource
from discovery.sources.arbeitnow import ArbeitnowSource
from common.models import RemoteType, VisaSponsorshipStatus


REMOTIVE_SAMPLE = {
    "jobs": [
        {
            "id": 123,
            "title": "Senior AI Engineer",
            "company_name": "TechCorp",
            "description": "We need a Python and LangChain expert for RAG systems.",
            "url": "https://remotive.com/job/123",
            "candidate_required_location": "Worldwide",
            "tags": [{"name": "python"}, {"name": "langchain"}],
            "salary": "$120k-$160k",
            "job_type": "full_time",
        },
        {
            "id": 456,
            "title": "Marketing Manager",
            "company_name": "BrandCo",
            "description": "Manage social media campaigns.",
            "url": "https://remotive.com/job/456",
            "candidate_required_location": "USA",
            "tags": [],
        },
    ]
}

ARBEITNOW_SAMPLE = {
    "data": [
        {
            "slug": "senior-java-dev-berlin",
            "title": "Senior Java Developer",
            "company_name": "Berlin Tech GmbH",
            "description": "Spring Boot microservices, AWS, Kubernetes.",
            "url": "https://arbeitnow.com/job/senior-java-dev-berlin",
            "location": "Berlin, Germany",
            "remote": False,
            "visa_sponsorship": True,
            "tags": ["java", "spring-boot", "aws"],
        }
    ]
}


class TestRemotiveSource:
    def test_fetch_filters_irrelevant_jobs(self):
        source = RemotiveSource()
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = REMOTIVE_SAMPLE
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            jobs = source.fetch()

        # Marketing Manager should be filtered out
        titles = [j.title for j in jobs]
        assert "Senior AI Engineer" in titles
        assert "Marketing Manager" not in titles

    def test_parse_sets_remote_type(self):
        source = RemotiveSource()
        job = source._parse(REMOTIVE_SAMPLE["jobs"][0])
        assert job.remote_type == RemoteType.REMOTE

    def test_parse_extracts_tags_as_skills(self):
        source = RemotiveSource()
        job = source._parse(REMOTIVE_SAMPLE["jobs"][0])
        assert "python" in job.required_skills
        assert "langchain" in job.required_skills

    def test_extract_country_worldwide_returns_none(self):
        source = RemotiveSource()
        assert source._extract_country("Worldwide") is None

    def test_extract_country_usa(self):
        source = RemotiveSource()
        assert source._extract_country("USA only") == "USA"

    def test_parse_invalid_item_returns_none(self):
        source = RemotiveSource()
        result = source._parse({})
        assert result is None


class TestArbeitnowSource:
    def test_fetch_returns_jobs_with_visa_sponsorship(self):
        source = ArbeitnowSource()
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = ARBEITNOW_SAMPLE
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            jobs = source.fetch()

        assert len(jobs) == 1
        assert jobs[0].visa_sponsorship == VisaSponsorshipStatus.CONFIRMED
        assert jobs[0].country == "Germany"

    def test_parse_sets_onsite_when_not_remote(self):
        source = ArbeitnowSource()
        job = source._parse(ARBEITNOW_SAMPLE["data"][0])
        assert job.remote_type == RemoteType.ONSITE

    def test_extract_country_berlin(self):
        source = ArbeitnowSource()
        assert source._extract_country("Berlin, Germany") == "Germany"
