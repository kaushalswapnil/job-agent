from fastapi import APIRouter, Depends, BackgroundTasks
from app.agents.discovery.runner import run_discovery
from app.agents.matching.runner import run_matching
from app.agents.application.runner import process_high_match_jobs
from app.agents.notification.runner import send_daily_summary
from app.db.queries import get_profile, get_candidate_config
from app.api.deps import get_current_user

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/discover")
async def trigger_discovery(background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    """Manually trigger job discovery (also runs on schedule)."""
    background_tasks.add_task(run_discovery)
    return {"status": "discovery_started"}


@router.post("/match")
async def trigger_matching(background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    """Score all unmatched jobs for the current user."""
    background_tasks.add_task(run_matching, user["id"])
    return {"status": "matching_started"}


@router.post("/process-applications")
async def trigger_applications(background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    """Generate resumes and create approval requests for high-match jobs."""
    background_tasks.add_task(process_high_match_jobs, user["id"])
    return {"status": "application_processing_started"}


@router.post("/run-all")
async def run_all(background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    """Run full pipeline: discover → match → process applications."""
    async def pipeline():
        run_discovery()
        run_matching(user["id"])
        process_high_match_jobs(user["id"])

    background_tasks.add_task(pipeline)
    return {"status": "full_pipeline_started"}


@router.post("/daily-summary")
async def trigger_daily_summary(background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    profile = get_profile(user["id"])
    email = profile.get("email") if profile else None
    if email:
        background_tasks.add_task(send_daily_summary, email, user["id"])
    return {"status": "summary_queued", "email": email}
