from fastapi import APIRouter, Depends, Query
from app.db.queries import get_matches, get_applications, get_dashboard_stats, get_pending_approvals
from app.api.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def stats(user=Depends(get_current_user)):
    return get_dashboard_stats(user["id"])


@router.get("/matches")
async def matches(
    level: str = Query(None, description="Filter by match level"),
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
):
    rows = get_matches(user["id"], level=level, limit=limit)
    return [
        {
            "job_id": r["job_id"],
            "company": r["jobs"]["company"] if r.get("jobs") else "",
            "title": r["jobs"]["title"] if r.get("jobs") else "",
            "url": r["jobs"]["url"] if r.get("jobs") else "",
            "country": r["jobs"].get("country") if r.get("jobs") else None,
            "remote_type": r["jobs"].get("remote_type") if r.get("jobs") else "UNKNOWN",
            "visa_sponsorship": r["jobs"].get("visa_sponsorship") if r.get("jobs") else "UNKNOWN",
            "match_level": r["match_level"],
            "overall_score": r["overall_score"],
            "ai_score": r.get("ai_score"),
            "java_score": r.get("java_score"),
            "frontend_score": r.get("frontend_score"),
            "cloud_score": r.get("cloud_score"),
            "location_score": r.get("location_score"),
            "visa_score": r.get("visa_score"),
            "explanation": r.get("explanation", {}),
        }
        for r in rows
    ]


@router.get("/applications")
async def applications(
    status: str = Query(None),
    limit: int = Query(100, le=500),
    user=Depends(get_current_user),
):
    return get_applications(user["id"], status=status, limit=limit)


@router.get("/approvals")
async def approvals(user=Depends(get_current_user)):
    return get_pending_approvals(user["id"])
