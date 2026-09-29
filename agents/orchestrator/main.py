import json
import argparse
import structlog
from datetime import datetime, date
from common.database import get_session
from common.config_loader import load_system_config
from discovery.agent import JobDiscoveryAgent
from matching.agent import JobMatchingAgent
from application.agent import ApplicationAgent
from notification.agent import NotificationAgent
from sqlalchemy import text

logger = structlog.get_logger()


class Orchestrator:
    """
    Central coordinator for all agents.
    Each method corresponds to one EventBridge-triggered Lambda/ECS task.
    """

    def __init__(self):
        self._config = load_system_config()

    # ------------------------------------------------------------------
    # Triggered by EventBridge every 4 hours
    # ------------------------------------------------------------------
    def run_discovery(self) -> dict:
        logger.info("orchestrator_discovery_start")
        result = JobDiscoveryAgent().run()
        logger.info("orchestrator_discovery_done", **result)
        return result

    # ------------------------------------------------------------------
    # Triggered by SQS (job_evaluation_queue) or EventBridge every 30 min
    # ------------------------------------------------------------------
    def run_matching(self) -> dict:
        logger.info("orchestrator_matching_start")
        agent = JobMatchingAgent()
        result = agent.run(batch_size=self._config["agents"]["job_batch_size"])

        # After matching, queue HIGH_MATCH jobs for application processing
        session = get_session()
        try:
            high_match_jobs = session.execute(
                text("""
                    SELECT j.*, m.overall_score, m.ai_score, m.java_score,
                           m.frontend_score, m.visa_score, m.match_level, m.explanation
                    FROM jobs j
                    JOIN job_matches m ON j.job_id = m.job_id
                    LEFT JOIN applications a ON j.job_id = a.job_id
                    WHERE m.match_level IN ('HIGH_MATCH', 'MEDIUM_MATCH')
                      AND a.application_id IS NULL
                    ORDER BY m.overall_score DESC
                    LIMIT 20
                """)
            ).fetchall()

            queued = 0
            app_agent = ApplicationAgent()
            notif_agent = NotificationAgent()

            for row in high_match_jobs:
                job = dict(row._mapping)
                match = {
                    "overall_score": float(job["overall_score"]),
                    "ai_score": float(job.get("ai_score") or 0),
                    "java_score": float(job.get("java_score") or 0),
                    "frontend_score": float(job.get("frontend_score") or 0),
                }
                try:
                    app_agent.process_job(job, match)
                    if float(job["overall_score"]) >= 85:
                        notif_agent.send_high_match_alert(job, float(job["overall_score"]))
                    queued += 1
                except Exception as e:
                    logger.error("application_processing_failed", job_id=job["job_id"], error=str(e))

            result["queued_for_application"] = queued
        finally:
            session.close()

        logger.info("orchestrator_matching_done", **result)
        return result

    # ------------------------------------------------------------------
    # Triggered daily by EventBridge (cron)
    # ------------------------------------------------------------------
    def run_daily_summary(self) -> dict:
        session = get_session()
        try:
            today = date.today()
            row = session.execute(
                text("""
                    SELECT
                        (SELECT COUNT(*) FROM jobs WHERE DATE(discovered_at) = :today) AS jobs_discovered,
                        (SELECT COUNT(*) FROM job_matches WHERE DATE(evaluated_at) = :today) AS jobs_evaluated,
                        (SELECT COUNT(*) FROM job_matches WHERE match_level = 'HIGH_MATCH' AND DATE(evaluated_at) = :today) AS high_match_jobs,
                        (SELECT COUNT(*) FROM applications WHERE status = 'APPLICATION_SUBMITTED' AND DATE(application_date) = :today) AS apps_submitted,
                        (SELECT COUNT(*) FROM applications WHERE status = 'PENDING_APPROVAL') AS apps_pending,
                        (SELECT COUNT(*) FROM applications WHERE status = 'RECRUITER_CONTACTED') AS recruiter_responses,
                        (SELECT COUNT(*) FROM applications WHERE status IN ('INTERVIEW_REQUESTED','INTERVIEW_SCHEDULED')) AS interviews,
                        (SELECT COUNT(*) FROM applications WHERE status = 'REJECTED' AND DATE(last_checked) = :today) AS rejections
                """),
                {"today": today},
            ).fetchone()

            top_jobs = session.execute(
                text("""
                    SELECT j.title, j.company, j.country, m.overall_score
                    FROM jobs j JOIN job_matches m ON j.job_id = m.job_id
                    WHERE m.match_level = 'HIGH_MATCH' AND DATE(j.discovered_at) = :today
                    ORDER BY m.overall_score DESC LIMIT 5
                """),
                {"today": today},
            ).fetchall()

            summary = {
                "date": str(today),
                "jobs_discovered": row.jobs_discovered,
                "jobs_evaluated": row.jobs_evaluated,
                "high_match_jobs": row.high_match_jobs,
                "apps_submitted": row.apps_submitted,
                "apps_pending": row.apps_pending,
                "recruiter_responses": row.recruiter_responses,
                "interviews": row.interviews,
                "rejections": row.rejections,
                "action_required": row.apps_pending,
                "top_new_jobs": [
                    {"title": r.title, "company": r.company, "country": r.country, "score": float(r.overall_score)}
                    for r in top_jobs
                ],
            }

            NotificationAgent().send_daily_summary(summary)
            logger.info("daily_summary_sent", date=str(today))
            return summary
        finally:
            session.close()


# ------------------------------------------------------------------
# Lambda / ECS entrypoints
# ------------------------------------------------------------------

def lambda_handler(event: dict, context) -> dict:
    """AWS Lambda handler — routes to correct agent based on event source."""
    orchestrator = Orchestrator()
    task = event.get("task", "discovery")

    handlers = {
        "discovery": orchestrator.run_discovery,
        "matching": orchestrator.run_matching,
        "daily_summary": orchestrator.run_daily_summary,
    }

    handler = handlers.get(task)
    if not handler:
        raise ValueError(f"Unknown task: {task}")

    return handler()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["discovery", "matching", "daily_summary"], default="discovery")
    parser.add_argument("--env", default="local")
    args = parser.parse_args()

    import os
    os.environ.setdefault("ENV", args.env)

    orchestrator = Orchestrator()
    result = {
        "discovery": orchestrator.run_discovery,
        "matching": orchestrator.run_matching,
        "daily_summary": orchestrator.run_daily_summary,
    }[args.task]()

    print(json.dumps(result, indent=2, default=str))
