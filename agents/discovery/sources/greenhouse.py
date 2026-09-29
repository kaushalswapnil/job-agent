import httpx
import structlog
from datetime import datetime
from common.models import Job, RemoteType, VisaSponsorshipStatus, EmploymentType
from common.config_loader import get_all_target_roles, get_all_skills

logger = structlog.get_logger()

GREENHOUSE_BASE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


class GreenhouseSource:
    """
    Greenhouse public job board API — no auth required for reading public boards.
    Each company has a unique board token.
    """

    source_name = "greenhouse"

    def __init__(self, company_tokens: list[str]):
        self.company_tokens = company_tokens

    def fetch(self) -> list[Job]:
        roles = get_all_target_roles()
        skills = get_all_skills()
        jobs = []

        for token in self.company_tokens:
            try:
                resp = httpx.get(
                    GREENHOUSE_BASE.format(token=token),
                    params={"content": "true"},
                    timeout=30,
                )
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                for item in resp.json().get("jobs", []):
                    job = self._parse(item, token)
                    if job and self._is_relevant(job, roles, skills):
                        jobs.append(job)
            except Exception as e:
                logger.warning("greenhouse_fetch_error", token=token, error=str(e))

        logger.info("greenhouse_fetched", count=len(jobs))
        return jobs

    def _parse(self, item: dict, token: str) -> Job | None:
        try:
            location = item.get("location", {}).get("name", "")
            return Job(
                job_id=f"greenhouse_{item['id']}",
                source=self.source_name,
                source_job_id=str(item["id"]),
                company=token,
                title=item.get("title", ""),
                description=item.get("content", ""),
                url=item.get("absolute_url", ""),
                location=location,
                country=self._extract_country(location),
                remote_type=self._detect_remote(location, item.get("title", "")),
                visa_sponsorship=VisaSponsorshipStatus.UNKNOWN,
                discovered_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.warning("greenhouse_parse_error", error=str(e))
            return None

    def _detect_remote(self, location: str, title: str) -> RemoteType:
        combined = (location + " " + title).lower()
        if "remote" in combined:
            return RemoteType.REMOTE
        if "hybrid" in combined:
            return RemoteType.HYBRID
        return RemoteType.ONSITE

    def _extract_country(self, location: str) -> str | None:
        loc = location.lower()
        mapping = {
            "united states": "USA", "usa": "USA", "new york": "USA",
            "san francisco": "USA", "seattle": "USA", "austin": "USA",
            "united kingdom": "UK", "london": "UK",
            "germany": "Germany", "berlin": "Germany",
            "india": "India", "bangalore": "India", "hyderabad": "India",
            "canada": "Canada", "toronto": "Canada",
            "australia": "Australia", "sydney": "Australia",
            "singapore": "Singapore",
            "netherlands": "Netherlands", "amsterdam": "Netherlands",
        }
        for key, val in mapping.items():
            if key in loc:
                return val
        return None

    def _is_relevant(self, job: Job, roles: list[str], skills: list[str]) -> bool:
        title_lower = job.title.lower()
        desc_lower = job.description.lower()
        role_hit = any(r.lower() in title_lower for r in roles)
        skill_hit = any(s.lower() in desc_lower for s in skills[:20])
        return role_hit or skill_hit
