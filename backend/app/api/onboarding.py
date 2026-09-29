from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.db.models import OnboardingRequest
from app.db.queries import upsert_profile, upsert_candidate_config, get_profile, get_candidate_config
from app.agents.resume.runner import upload_master_resume
from app.api.deps import get_current_user

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/profile")
async def save_profile(data: OnboardingRequest, user=Depends(get_current_user)):
    """Step 1: Save candidate profile and preferences."""
    upsert_profile(user["id"], {
        "full_name": data.full_name,
        "phone": data.phone,
        "linkedin_url": data.linkedin_url,
        "naukri_url": data.naukri_url,
        "github_url": data.github_url,
        "portfolio_url": data.portfolio_url,
        "current_city": data.current_city,
        "current_country": data.current_country,
        "timezone": data.timezone,
    })

    upsert_candidate_config(user["id"], {
        "experience_years": data.experience_years,
        "ai_years": data.ai_years,
        "java_years": data.java_years,
        "frontend_years": data.frontend_years,
        "cloud_years": data.cloud_years,
        "target_roles": data.target_roles,
        "skills": data.skills,
        "professional_summary": data.professional_summary,
        "location_prefs": data.location_prefs,
        "work_authorization": data.work_authorization,
        "salary_prefs": data.salary_prefs,
        "job_prefs": data.job_prefs,
        "notification_prefs": {"email": data.notification_email} if data.notification_email else {},
    })

    return {"status": "ok", "message": "Profile saved. Now upload your resume."}


@router.post("/resume")
async def upload_resume(file: UploadFile = File(...), user=Depends(get_current_user)):
    """Step 2: Upload master resume (PDF or DOCX)."""
    if not file.filename.lower().endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(400, "Only PDF, DOCX, or TXT files are supported")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(400, "File too large. Maximum 5MB.")

    record = upload_master_resume(user["id"], content, file.filename)
    return {"status": "ok", "resume_id": record["id"], "message": "Resume uploaded. Job search will start automatically."}


@router.get("/status")
async def onboarding_status(user=Depends(get_current_user)):
    """Check what onboarding steps are complete."""
    profile = get_profile(user["id"])
    config = get_candidate_config(user["id"])
    from app.db.queries import get_master_resume
    resume = get_master_resume(user["id"])

    return {
        "profile_complete": bool(profile and profile.get("full_name")),
        "config_complete": bool(config),
        "resume_uploaded": bool(resume),
        "ready_to_search": bool(profile and config and resume),
    }
