import httpx
import structlog
from datetime import datetime
from common.models import Job, RemoteType, VisaSponsorshipStatus, EmploymentType
from common.config_loader import get_all_target_roles, get_all_skills

logger = structlog.get_logger()

ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowSource:
    """
    Arbeitnow public API — free, no auth, Europe-focused jobs with visa sponsorship data.
    https://www.arbeitnow.com/api/job-board-api
    """

    source_name = "arbeitnow"

    def fetch(self) -> list[Job]:
        roles = get_all_target_roles()
        skills = get_all_skills()
        jobs = []

        try:
            page = 1
            while page <= 5:  # Max 5 pages per run
                resp = httpx.get(ARBEITNOW_URL, params={"page": page}, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                items = data.get("data", [])
                if not items:
                    break
                for item in items:
                    job = self._parse(item)
                    if job and self._is_relevant(job, roles, skills):
                        jobs.append(job)
                page += 1
        except Exception as e:
            logger.error("arbeitnow_fetch_error", error=str(e))

        logger.info("arbeitnow_fetched", count=len(jobs))
        return jobs

    def _parse(self, item: dict) -> Job | None:
        try:
            visa = (
                VisaSponsorshipStatus.CONFIRMED
                if item.get("visa_sponsorship")
                else VisaSponsorshipStatus.UNKNOWN
            )
            remote = RemoteType.REMOTE if item.get("remote") else RemoteType.ONSITE

            return Job(
                job_id=f"arbeitnow_{item['slug']}",
                source=self.source_name,
                source_job_id=item["slug"],
                company=item.get("company_name", ""),
                title=item.get("title", ""),
                description=item.get("description", ""),
                url=item.get("url", ""),
                location=item.get("location", ""),
                country=self._extract_country(item.get("location", "")),
                remote_type=remote,
                employment_type=EmploymentType.FULL_TIME,
                visa_sponsorship=visa,
                required_skills=item.get("tags", []),
                discovered_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.warning("arbeitnow_parse_error", error=str(e))
            return None

    def _extract_country(self, location: str) -> str | None:
        loc = location.lower()
        mapping = {
            "germany": "Germany", "berlin": "Germany", "munich": "Germany",
            "hamburg": "Germany", "frankfurt": "Germany",
            "netherlands": "Netherlands", "amsterdam": "Netherlands",
            "ireland": "Ireland", "dublin": "Ireland",
            "uk": "UK", "london": "UK",
            "france": "France", "paris": "France",
            "sweden": "Sweden", "stockholm": "Sweden",
            "austria": "Austria", "vienna": "Austria",
            "switzerland": "Switzerland", "zurich": "Switzerland",
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
