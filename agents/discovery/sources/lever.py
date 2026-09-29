import httpx
import structlog
from datetime import datetime
from common.models import Job, RemoteType, VisaSponsorshipStatus
from common.config_loader import get_all_target_roles, get_all_skills

logger = structlog.get_logger()

LEVER_BASE = "https://api.lever.co/v0/postings/{company}?mode=json"


class LeverSource:
    """
    Lever public postings API — no auth required for reading public job boards.
    """

    source_name = "lever"

    def __init__(self, company_slugs: list[str]):
        self.company_slugs = company_slugs

    def fetch(self) -> list[Job]:
        roles = get_all_target_roles()
        skills = get_all_skills()
        jobs = []

        for slug in self.company_slugs:
            try:
                resp = httpx.get(LEVER_BASE.format(company=slug), timeout=30)
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                for item in resp.json():
                    job = self._parse(item, slug)
                    if job and self._is_relevant(job, roles, skills):
                        jobs.append(job)
            except Exception as e:
                logger.warning("lever_fetch_error", slug=slug, error=str(e))

        logger.info("lever_fetched", count=len(jobs))
        return jobs

    def _parse(self, item: dict, slug: str) -> Job | None:
        try:
            location = item.get("categories", {}).get("location", "")
            description = " ".join(
                block.get("content", "") if isinstance(block.get("content"), str)
                else " ".join(block.get("content", []))
                for block in item.get("descriptionBody", {}).get("descriptionBodyParts", [])
            )
            return Job(
                job_id=f"lever_{item['id']}",
                source=self.source_name,
                source_job_id=item["id"],
                company=item.get("company", slug),
                title=item.get("text", ""),
                description=description or item.get("descriptionPlain", ""),
                url=item.get("hostedUrl", ""),
                location=location,
                country=self._extract_country(location),
                remote_type=self._detect_remote(location, item.get("text", "")),
                visa_sponsorship=VisaSponsorshipStatus.UNKNOWN,
                discovered_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.warning("lever_parse_error", error=str(e))
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
            "san francisco": "USA", "remote": None,
            "united kingdom": "UK", "london": "UK",
            "germany": "Germany", "india": "India",
            "canada": "Canada", "australia": "Australia",
            "singapore": "Singapore",
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
