from enum import Enum
from datetime import datetime
from typing import Optional
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
    APPLICATION_STARTED = "APPLICATION_STARTED"
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


class VisaSponsorshipStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    LIKELY = "LIKELY"
    UNKNOWN = "UNKNOWN"
    NOT_SUPPORTED = "NOT_SUPPORTED"


class RemoteType(str, Enum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ONSITE = "ONSITE"
    UNKNOWN = "UNKNOWN"


class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    CONTRACT = "CONTRACT"
    PART_TIME = "PART_TIME"
    FREELANCE = "FREELANCE"


class MessageClassification(str, Enum):
    APPLICATION_RECEIVED = "APPLICATION_RECEIVED"
    APPLICATION_REVIEW = "APPLICATION_REVIEW"
    RECRUITER_CONTACT = "RECRUITER_CONTACT"
    INTERVIEW_REQUEST = "INTERVIEW_REQUEST"
    INTERVIEW_CONFIRMATION = "INTERVIEW_CONFIRMATION"
    ASSESSMENT_REQUEST = "ASSESSMENT_REQUEST"
    REJECTION = "REJECTION"
    OFFER = "OFFER"
    OTHER = "OTHER"


class Job(BaseModel):
    job_id: str
    source: str
    source_job_id: str
    company: str
    title: str
    description: str
    url: str
    location: Optional[str] = None
    country: Optional[str] = None
    remote_type: RemoteType = RemoteType.UNKNOWN
    employment_type: Optional[EmploymentType] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    visa_sponsorship: VisaSponsorshipStatus = VisaSponsorshipStatus.UNKNOWN
    relocation_support: Optional[bool] = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    years_experience_required: Optional[int] = None
    seniority_level: Optional[str] = None
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    raw_data: Optional[dict] = None


class JobMatch(BaseModel):
    job_id: str
    match_level: MatchLevel
    overall_score: float                  # 0-100
    technical_score: float
    ai_score: float
    java_score: float
    frontend_score: float
    cloud_score: float
    location_score: float
    visa_score: float
    seniority_score: float
    explanation: dict                     # Human-readable breakdown
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class Application(BaseModel):
    application_id: str
    job_id: str
    company: str
    role: str
    job_url: str
    country: Optional[str] = None
    location: Optional[str] = None
    job_description: str
    job_match_score: float
    ai_relevance_score: float
    java_relevance_score: float
    fullstack_relevance_score: float
    visa_status: VisaSponsorshipStatus
    remote_status: RemoteType
    salary: Optional[str] = None
    resume_version: Optional[str] = None
    cover_letter_version: Optional[str] = None
    application_date: Optional[datetime] = None
    status: ApplicationStatus = ApplicationStatus.DISCOVERED
    last_checked: datetime = Field(default_factory=datetime.utcnow)
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    recruiter_message: Optional[str] = None
    interview_status: Optional[str] = None
    interview_date: Optional[datetime] = None
    notes: Optional[str] = None
    next_action: Optional[str] = None
    audit_log: list[dict] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    request_id: str
    application_id: str
    company: str
    role: str
    country: Optional[str]
    job_url: str
    match_score: float
    resume_used: Optional[str]
    questions: list[dict]                 # [{"question": "...", "recommended": "..."}]
    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
