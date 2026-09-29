import httpx
import structlog
from datetime import datetime
from common.models import Job, RemoteType, VisaSponsorshipStatus
from common.config_loader import get_all_target_roles, get_all_skills

logger = structlog.get_logger()

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
CATEGORIES = ["software-dev", "devops", "data"]


class RemotiveSource:
    """
    Remotive public API — free, no auth required, remote jobs only.
    https://remotive.com/api/remote-jobs
    """

    source_name = "remotive"

    def fetch(self) -> list[Job]:
        roles = get_all_target_roles()
        skills = get_all_skills()
        jobs = []

        for category in CATEGORIES:
            try:
                resp = httpx.get(
                    REMOTIVE_URL,
                    params={"category": category, "limit": 100},
                    timeout=30,
                )
                resp.raise_for_status()
                for item in resp.json().get("jobs", []):
                    job = self._parse(item)
                    if job and self._is_relevant(job, roles, skills):
                        jobs.append(job)
            except Exception as e:
                logger.error("remotive_fetch_error", category=category, error=str(e))

        logger.info("remotive_fetched", count=len(jobs))
        return jobs

    def _parse(self, item: dict) -> Job | None:
        try:
            return Job(
                job_id=f"remotive_{item['id']}",
                source=self.source_name,
                source_job_id=str(item["id"]),
                company=item.get("company_name", ""),
                title=item.get("title", ""),
                description=item.get("description", ""),
                url=item.get("url", ""),
                location=item.get("candidate_required_location", "Worldwide"),
                country=self._extract_country(item.get("candidate_required_location", "")),
                remote_type=RemoteType.REMOTE,
                visa_sponsorship=VisaSponsorshipStatus.UNKNOWN,
                required_skills=self._extract_tags(item.get("tags", [])),
                discovered_at=datetime.utcnow(),
                raw_data={"salary": item.get("salary"), "job_type": item.get("job_type")},
            )
        except Exception as e:
            logger.warning("remotive_parse_error", error=str(e))
            return None

    def _extract_country(self, location: str) -> str | None:
        loc = location.lower()
        mapping = {
            "usa": "USA", "united states": "USA", "us only": "USA",
            "uk": "UK", "united kingdom": "UK",
            "canada": "Canada", "germany": "Germany",
            "india": "India", "australia": "Australia",
            "singapore": "Singapore",
        }
        for key, val in mapping.items():
            if key in loc:
                return val
        return None

    def _extract_tags(self, tags: list) -> list[str]:
        return [t.get("name", t) if isinstance(t, dict) else str(t) for t in tags]

    def _is_relevant(self, job: Job, roles: list[str], skills: list[str]) -> bool:
        title_lower = job.title.lower()
        desc_lower = job.description.lower()
        role_hit = any(r.lower() in title_lower for r in roles)
        skill_hit = any(s.lower() in desc_lower for s in skills[:20])
        return role_hit or skill_hit
