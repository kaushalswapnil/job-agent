import structlog
from common.database import get_session, upsert_job
from common.config_loader import load_system_config
from discovery.sources.remotive import RemotiveSource
from discovery.sources.arbeitnow import ArbeitnowSource
from discovery.sources.greenhouse import GreenhouseSource
from discovery.sources.lever import LeverSource

logger = structlog.get_logger()

# Curated list of tech companies with Greenhouse boards
GREENHOUSE_COMPANIES = [
    "airbnb", "stripe", "notion", "figma", "databricks", "snowflake",
    "hashicorp", "confluent", "mongodb", "elastic", "twilio", "sendgrid",
    "cloudflare", "datadog", "pagerduty", "okta", "auth0", "segment",
    "mixpanel", "amplitude", "brex", "rippling", "lattice", "gusto",
    "benchling", "scale-ai", "cohere", "huggingface", "weights-biases",
    "anthropic", "openai", "mistral", "together-ai",
]

# Curated list of tech companies with Lever boards
LEVER_COMPANIES = [
    "netflix", "reddit", "lyft", "coinbase", "robinhood", "plaid",
    "chime", "affirm", "carta", "checkr", "faire", "flexport",
    "nerdwallet", "opendoor", "postmates", "thumbtack", "zendesk",
    "asana", "box", "dropbox", "evernote", "invision", "miro",
]


class JobDiscoveryAgent:
    """
    Orchestrates all job sources, deduplicates, and persists to database.
    Triggered by EventBridge every 4 hours.
    """

    def run(self) -> dict:
        config = load_system_config()
        sources_cfg = config.get("job_sources", {})
        session = get_session()
        total_new = 0
        total_seen = 0
        results = {}

        sources = self._build_sources(sources_cfg)

        for source in sources:
            source_name = source.source_name
            try:
                jobs = source.fetch()
                new_count = 0
                for job in jobs:
                    is_new = upsert_job(session, job)
                    if is_new:
                        new_count += 1
                    else:
                        total_seen += 1
                total_new += new_count
                results[source_name] = {"fetched": len(jobs), "new": new_count}
                logger.info("source_complete", source=source_name, fetched=len(jobs), new=new_count)
            except Exception as e:
                logger.error("source_failed", source=source_name, error=str(e))
                results[source_name] = {"error": str(e)}
            finally:
                session.close()
                session = get_session()

        session.close()
        summary = {"total_new": total_new, "total_seen": total_seen, "by_source": results}
        logger.info("discovery_complete", **summary)
        return summary

    def _build_sources(self, cfg: dict) -> list:
        sources = []
        if cfg.get("remotive", {}).get("enabled", True):
            sources.append(RemotiveSource())
        if cfg.get("arbeitnow", {}).get("enabled", True):
            sources.append(ArbeitnowSource())
        if cfg.get("greenhouse", {}).get("enabled", True):
            sources.append(GreenhouseSource(GREENHOUSE_COMPANIES))
        if cfg.get("lever", {}).get("enabled", True):
            sources.append(LeverSource(LEVER_COMPANIES))
        return sources
