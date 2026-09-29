from enum import Enum
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class MatchLevel(str, Enum):
    HIGH_MATCH = "HIGH_MATCH"
    MEDIUM_MATCH = "MEDIUM_MATCH"
    LOW_MATCH = "LOW_MATCH"
    DO_NOT_APPLY = "DO_NOT_APPLY"


class ApplicationStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    EVALUATED = "EVALUATED"
    RESUME_GENERATED = "RESUME_GENERATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED"
    APPLICATION_FAILED = "APPLICATION_FAILED"
    WAITING = "WAITING"
    RECRUITER_CONTACTED = "RECRUITER_CONTACTED"
    INTERVIEW_REQUESTED = "INTERVIEW_REQUESTED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    OFFER = "OFFER"
    MANUAL_ACTION_REQUIRED = "MANUAL_ACTION_REQUIRED"


class VisaStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    LIKELY = "LIKELY"
    UNKNOWN = "UNKNOWN"
    NOT_SUPPORTED = "NOT_SUPPORTED"


class RemoteType(str, Enum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ONSITE = "ONSITE"
    UNKNOWN = "UNKNOWN"


# ── API request/response models ──────────────────────────────

class OnboardingRequest(BaseModel):
    full_name: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    naukri_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    current_city: str = "Bangalore"
    current_country: str = "India"
    timezone: str = "Asia/Kolkata"
    experience_years: int = 0
    ai_years: int = 0
    java_years: int = 0
    frontend_years: int = 0
    cloud_years: int = 0
    target_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    professional_summary: str = ""
    location_prefs: dict = Field(default_factory=dict)
    work_authorization: dict = Field(default_factory=dict)
    salary_prefs: dict = Field(default_factory=dict)
    job_prefs: dict = Field(default_factory=dict)
    notification_email: Optional[str] = None


class JobOut(BaseModel):
    id: str
    company: str
    title: str
    url: str
    location: Optional[str]
    country: Optional[str]
    remote_type: str
    visa_sponsorship: str
    source: str
    discovered_at: str


class MatchOut(BaseModel):
    job_id: str
    company: str
    title: str
    url: str
    match_level: str
    overall_score: float
    ai_score: float
    java_score: float
    frontend_score: float
    cloud_score: float
    location_score: float
    visa_score: float
    explanation: dict
    country: Optional[str]
    remote_type: str
    visa_sponsorship: str


class ApplicationOut(BaseModel):
    id: str
    company: str
    role: str
    job_url: str
    country: Optional[str]
    status: str
    job_match_score: Optional[float]
    visa_status: str
    remote_status: str
    application_date: Optional[str]
    resume_id: Optional[str]
    recruiter_name: Optional[str]
    interview_date: Optional[str]
    notes: Optional[str]
    next_action: Optional[str]


class ApprovalOut(BaseModel):
    id: str
    company: str
    role: str
    country: Optional[str]
    job_url: str
    match_score: Optional[float]
    questions: list[dict]
    reason: str
    created_at: str


class ApprovalDecision(BaseModel):
    approved: bool
    notes: Optional[str] = None


class DashboardStats(BaseModel):
    total_jobs_discovered: int
    jobs_evaluated: int
    high_match_jobs: int
    applications_submitted: int
    pending_approval: int
    recruiter_responses: int
    interviews: int
    rejections: int
    offers: int
    top_matches: list[MatchOut]
