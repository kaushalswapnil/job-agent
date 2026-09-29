from fastapi import APIRouter, Depends, HTTPException
from app.db.models import ApprovalDecision
from app.db.queries import (
    get_pending_approvals, resolve_approval, update_application,
    get_profile, get_candidate_config, log_action
)
from app.agents.notification.runner import notify_approval_required
from app.api.deps import get_current_user

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/")
async def list_approvals(user=Depends(get_current_user)):
    return get_pending_approvals(user["id"])


@router.post("/{approval_id}/decide")
async def decide(approval_id: str, decision: ApprovalDecision, user=Depends(get_current_user)):
    """Approve or reject a pending application."""
    approvals = get_pending_approvals(user["id"])
    approval = next((a for a in approvals if a["id"] == approval_id), None)
    if not approval:
        raise HTTPException(404, "Approval request not found")

    resolution = "APPROVED" if decision.approved else "REJECTED_BY_USER"
    resolve_approval(approval_id, resolution)

    if approval.get("application_id"):
        new_status = "APPLICATION_SUBMITTED" if decision.approved else "WITHDRAWN"
        update_application(approval["application_id"], {
            "status": new_status,
            "notes": decision.notes,
        })
        log_action(
            user["id"], f"APPROVAL_{resolution}",
            detail=decision.notes,
            application_id=approval["application_id"],
            agent="human",
        )

    return {"status": "ok", "resolution": resolution}


@router.post("/notify-pending")
async def notify_pending(user=Depends(get_current_user)):
    """Send email notifications for all unresolved approvals."""
    profile = get_profile(user["id"])
    config = get_candidate_config(user["id"])
    email = (
        profile.get("email") or
        (config.get("notification_prefs") or {}).get("email")
    )
    if not email:
        raise HTTPException(400, "No notification email configured")

    approvals = get_pending_approvals(user["id"])
    for approval in approvals:
        notify_approval_required(email, approval)

    return {"notified": len(approvals)}
