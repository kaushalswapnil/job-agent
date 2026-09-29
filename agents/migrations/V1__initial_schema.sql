-- =============================================================================
-- V1__initial_schema.sql
-- Full application tracking database schema
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- JOBS — Every discovered job posting
-- ---------------------------------------------------------------------------
CREATE TABLE jobs (
    job_id                   VARCHAR(64)  PRIMARY KEY,
    source                   VARCHAR(64)  NOT NULL,
    source_job_id            VARCHAR(256) NOT NULL,
    company                  VARCHAR(256) NOT NULL,
    title                    VARCHAR(256) NOT NULL,
    description              TEXT         NOT NULL,
    url                      TEXT         NOT NULL,
    location                 VARCHAR(256),
    country                  VARCHAR(128),
    remote_type              VARCHAR(32)  NOT NULL DEFAULT 'UNKNOWN',
    employment_type          VARCHAR(32),
    salary_min               NUMERIC,
    salary_max               NUMERIC,
    salary_currency          VARCHAR(8),
    visa_sponsorship         VARCHAR(32)  NOT NULL DEFAULT 'UNKNOWN',
    relocation_support       BOOLEAN,
    required_skills          TEXT,
    preferred_skills         TEXT,
    years_experience_required INT,
    seniority_level          VARCHAR(64),
    status                   VARCHAR(64)  NOT NULL DEFAULT 'DISCOVERED',
    discovered_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    raw_data                 TEXT,
    UNIQUE (source, source_job_id)
);

CREATE INDEX idx_jobs_status       ON jobs(status);
CREATE INDEX idx_jobs_country      ON jobs(country);
CREATE INDEX idx_jobs_discovered   ON jobs(discovered_at DESC);
CREATE INDEX idx_jobs_company      ON jobs(company);

-- ---------------------------------------------------------------------------
-- JOB_MATCHES — Scoring results per job
-- ---------------------------------------------------------------------------
CREATE TABLE job_matches (
    job_id               VARCHAR(64)  PRIMARY KEY REFERENCES jobs(job_id),
    match_level          VARCHAR(32)  NOT NULL,
    overall_score        NUMERIC(5,2) NOT NULL,
    technical_score      NUMERIC(5,2),
    ai_score             NUMERIC(5,2),
    java_score           NUMERIC(5,2),
    frontend_score       NUMERIC(5,2),
    cloud_score          NUMERIC(5,2),
    location_score       NUMERIC(5,2),
    visa_score           NUMERIC(5,2),
    seniority_score      NUMERIC(5,2),
    explanation          TEXT,
    evaluated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_matches_level ON job_matches(match_level);
CREATE INDEX idx_matches_score ON job_matches(overall_score DESC);

-- ---------------------------------------------------------------------------
-- RESUMES — Master and tailored resume versions
-- ---------------------------------------------------------------------------
CREATE TABLE resumes (
    resume_id        VARCHAR(64)  PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    resume_type      VARCHAR(32)  NOT NULL,   -- MASTER | TAILORED
    job_id           VARCHAR(64)  REFERENCES jobs(job_id),
    s3_key           TEXT         NOT NULL,
    version          VARCHAR(32)  NOT NULL,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    llm_model_used   VARCHAR(128),
    prompt_version   VARCHAR(32)
);

-- ---------------------------------------------------------------------------
-- APPLICATIONS — Central application tracking
-- ---------------------------------------------------------------------------
CREATE TABLE applications (
    application_id           VARCHAR(64)  PRIMARY KEY,
    job_id                   VARCHAR(64)  REFERENCES jobs(job_id),
    company                  VARCHAR(256) NOT NULL,
    role                     VARCHAR(256) NOT NULL,
    job_url                  TEXT         NOT NULL,
    country                  VARCHAR(128),
    location                 VARCHAR(256),
    job_description          TEXT,
    job_match_score          NUMERIC(5,2),
    ai_relevance_score       NUMERIC(5,2),
    java_relevance_score     NUMERIC(5,2),
    fullstack_relevance_score NUMERIC(5,2),
    visa_status              VARCHAR(32)  NOT NULL DEFAULT 'UNKNOWN',
    remote_status            VARCHAR(32)  NOT NULL DEFAULT 'UNKNOWN',
    salary                   VARCHAR(128),
    resume_version           VARCHAR(64)  REFERENCES resumes(resume_id),
    cover_letter_version     VARCHAR(64),
    application_date         TIMESTAMPTZ,
    status                   VARCHAR(64)  NOT NULL DEFAULT 'DISCOVERED',
    last_checked             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    recruiter_name           VARCHAR(256),
    recruiter_email          VARCHAR(256),
    recruiter_message        TEXT,
    interview_status         VARCHAR(64),
    interview_date           TIMESTAMPTZ,
    notes                    TEXT,
    next_action              TEXT
);

CREATE INDEX idx_apps_status      ON applications(status);
CREATE INDEX idx_apps_company     ON applications(company);
CREATE INDEX idx_apps_country     ON applications(country);
CREATE INDEX idx_apps_date        ON applications(application_date DESC);
CREATE INDEX idx_apps_score       ON applications(job_match_score DESC);

-- ---------------------------------------------------------------------------
-- AUDIT_LOG — Immutable record of every agent action
-- ---------------------------------------------------------------------------
CREATE TABLE audit_log (
    log_id           VARCHAR(64)  PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    application_id   VARCHAR(64)  REFERENCES applications(application_id),
    action           VARCHAR(128) NOT NULL,
    detail           TEXT,
    agent_name       VARCHAR(128),
    llm_model_used   VARCHAR(128),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_app  ON audit_log(application_id);
CREATE INDEX idx_audit_time ON audit_log(created_at DESC);

-- ---------------------------------------------------------------------------
-- APPROVAL_REQUESTS — Human-in-the-loop queue
-- ---------------------------------------------------------------------------
CREATE TABLE approval_requests (
    request_id       VARCHAR(64)  PRIMARY KEY,
    application_id   VARCHAR(64)  REFERENCES applications(application_id),
    company          VARCHAR(256),
    role             VARCHAR(256),
    country          VARCHAR(128),
    job_url          TEXT,
    match_score      NUMERIC(5,2),
    resume_used      VARCHAR(64),
    questions        JSONB,
    reason           TEXT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    resolved         BOOLEAN      NOT NULL DEFAULT FALSE,
    resolved_at      TIMESTAMPTZ,
    resolution       TEXT
);

-- ---------------------------------------------------------------------------
-- EMAIL_MESSAGES — Tracked recruiter/application emails
-- ---------------------------------------------------------------------------
CREATE TABLE email_messages (
    message_id       VARCHAR(256) PRIMARY KEY,
    application_id   VARCHAR(64)  REFERENCES applications(application_id),
    from_address     VARCHAR(256),
    subject          TEXT,
    body_preview     TEXT,
    classification   VARCHAR(64),
    received_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    processed        BOOLEAN      NOT NULL DEFAULT FALSE
);

-- ---------------------------------------------------------------------------
-- DAILY_SUMMARIES — Stored daily report snapshots
-- ---------------------------------------------------------------------------
CREATE TABLE daily_summaries (
    summary_id       VARCHAR(64)  PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    summary_date     DATE         NOT NULL UNIQUE,
    jobs_discovered  INT          DEFAULT 0,
    jobs_evaluated   INT          DEFAULT 0,
    high_match_jobs  INT          DEFAULT 0,
    apps_submitted   INT          DEFAULT 0,
    apps_pending     INT          DEFAULT 0,
    recruiter_responses INT       DEFAULT 0,
    interviews       INT          DEFAULT 0,
    rejections       INT          DEFAULT 0,
    offers           INT          DEFAULT 0,
    summary_json     JSONB,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
