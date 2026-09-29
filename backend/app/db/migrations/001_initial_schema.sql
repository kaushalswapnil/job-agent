-- ============================================================
-- Job Agent tables — added to existing Supabase project
-- (ngrudtbshliklqaznloi.supabase.co)
--
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- This does NOT touch the existing Roulette 'users' table.
-- All job agent tables are prefixed with 'ja_' to avoid conflicts.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- ja_profiles — job agent user profiles (separate from Roulette users)
-- Links to Supabase auth.users
-- ============================================================
CREATE TABLE IF NOT EXISTS public.ja_profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name       TEXT,
    email           TEXT,
    phone           TEXT,
    linkedin_url    TEXT,
    naukri_url      TEXT,
    github_url      TEXT,
    portfolio_url   TEXT,
    current_city    TEXT DEFAULT 'Bangalore',
    current_country TEXT DEFAULT 'India',
    timezone        TEXT DEFAULT 'Asia/Kolkata',
    onboarding_done BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ja_candidate_configs — job search preferences per user
-- ============================================================
CREATE TABLE IF NOT EXISTS public.ja_candidate_configs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES public.ja_profiles(id) ON DELETE CASCADE,
    target_roles        JSONB DEFAULT '[]',
    skills              JSONB DEFAULT '[]',
    experience_years    INT DEFAULT 0,
    ai_years            INT DEFAULT 0,
    java_years          INT DEFAULT 0,
    frontend_years      INT DEFAULT 0,
    cloud_years         INT DEFAULT 0,
    location_prefs      JSONB DEFAULT '{}',
    work_authorization  JSONB DEFAULT '{}',
    salary_prefs        JSONB DEFAULT '{}',
    job_prefs           JSONB DEFAULT '{}',
    notification_prefs  JSONB DEFAULT '{}',
    professional_summary TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- ============================================================
-- ja_resumes — master + tailored resume versions
-- ============================================================
CREATE TABLE IF NOT EXISTS public.ja_resumes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.ja_profiles(id) ON DELETE CASCADE,
    resume_type     TEXT NOT NULL CHECK (resume_type IN ('MASTER', 'TAILORED')),
    job_id          UUID,
    storage_path    TEXT NOT NULL,
    version         TEXT NOT NULL,
    raw_text        TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ja_resumes_user ON public.ja_resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_ja_resumes_type ON public.ja_resumes(resume_type);

-- ============================================================
-- ja_jobs — discovered job postings (shared across all users)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.ja_jobs (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source           TEXT NOT NULL,
    source_job_id    TEXT NOT NULL,
    company          TEXT NOT NULL,
    title            TEXT NOT NULL,
    description      TEXT NOT NULL,
    url              TEXT NOT NULL,
    location         TEXT,
    country          TEXT,
    remote_type      TEXT DEFAULT 'UNKNOWN',
    employment_type  TEXT,
    salary_min       NUMERIC,
    salary_max       NUMERIC,
    salary_currency  TEXT,
    visa_sponsorship TEXT DEFAULT 'UNKNOWN',
    relocation_support BOOLEAN,
    required_skills  JSONB DEFAULT '[]',
    seniority_level  TEXT,
    discovered_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source, source_job_id)
);

CREATE INDEX IF NOT EXISTS idx_ja_jobs_country    ON public.ja_jobs(country);
CREATE INDEX IF NOT EXISTS idx_ja_jobs_discovered ON public.ja_jobs(discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_ja_jobs_remote     ON public.ja_jobs(remote_type);

-- ============================================================
-- ja_job_matches — per-user AI scoring of each job
-- ============================================================
CREATE TABLE IF NOT EXISTS public.ja_job_matches (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.ja_profiles(id) ON DELETE CASCADE,
    job_id          UUID NOT NULL REFERENCES public.ja_jobs(id) ON DELETE CASCADE,
    match_level     TEXT NOT NULL,
    overall_score   NUMERIC(5,2),
    technical_score NUMERIC(5,2),
    ai_score        NUMERIC(5,2),
    java_score      NUMERIC(5,2),
    frontend_score  NUMERIC(5,2),
    cloud_score     NUMERIC(5,2),
    location_score  NUMERIC(5,2),
    visa_score      NUMERIC(5,2),
    explanation     JSONB DEFAULT '{}',
    evaluated_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_ja_matches_user  ON public.ja_job_matches(user_id);
CREATE INDEX IF NOT EXISTS idx_ja_matches_level ON public.ja_job_matches(match_level);
CREATE INDEX IF NOT EXISTS idx_ja_matches_score ON public.ja_job_matches(overall_score DESC);

-- ============================================================
-- ja_applications — central application tracking per user
-- ============================================================
CREATE TABLE IF NOT EXISTS public.ja_applications (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES public.ja_profiles(id) ON DELETE CASCADE,
    job_id                  UUID REFERENCES public.ja_jobs(id),
    company                 TEXT NOT NULL,
    role                    TEXT NOT NULL,
    job_url                 TEXT NOT NULL,
    country                 TEXT,
    location                TEXT,
    job_match_score         NUMERIC(5,2),
    ai_score                NUMERIC(5,2),
    java_score              NUMERIC(5,2),
    fullstack_score         NUMERIC(5,2),
    visa_status             TEXT DEFAULT 'UNKNOWN',
    remote_status           TEXT DEFAULT 'UNKNOWN',
    salary                  TEXT,
    resume_id               UUID REFERENCES public.ja_resumes(id),
    cover_letter_text       TEXT,
    application_date        TIMESTAMPTZ,
    status                  TEXT DEFAULT 'DISCOVERED',
    last_checked            TIMESTAMPTZ DEFAULT NOW(),
    recruiter_name          TEXT,
    recruiter_email         TEXT,
    recruiter_message       TEXT,
    interview_status        TEXT,
    interview_date          TIMESTAMPTZ,
    notes                   TEXT,
    next_action             TEXT,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ja_apps_user    ON public.ja_applications(user_id);
CREATE INDEX IF NOT EXISTS idx_ja_apps_status  ON public.ja_applications(status);
CREATE INDEX IF NOT EXISTS idx_ja_apps_company ON public.ja_applications(company);
CREATE INDEX IF NOT EXISTS idx_ja_apps_date    ON public.ja_applications(application_date DESC);

-- ============================================================
-- ja_approval_requests — human-in-the-loop queue
-- ============================================================
CREATE TABLE IF NOT EXISTS public.ja_approval_requests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.ja_profiles(id) ON DELETE CASCADE,
    application_id  UUID REFERENCES public.ja_applications(id),
    company         TEXT,
    role            TEXT,
    country         TEXT,
    job_url         TEXT,
    match_score     NUMERIC(5,2),
    resume_id       UUID,
    questions       JSONB DEFAULT '[]',
    reason          TEXT,
    resolved        BOOLEAN DEFAULT FALSE,
    resolution      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ja_approvals_user     ON public.ja_approval_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_ja_approvals_resolved ON public.ja_approval_requests(resolved);

-- ============================================================
-- ja_audit_log — immutable record of every agent action
-- ============================================================
CREATE TABLE IF NOT EXISTS public.ja_audit_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES public.ja_profiles(id),
    application_id  UUID REFERENCES public.ja_applications(id),
    action          TEXT NOT NULL,
    detail          TEXT,
    agent_name      TEXT,
    llm_model       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ja_audit_user ON public.ja_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_ja_audit_time ON public.ja_audit_log(created_at DESC);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE public.ja_profiles          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ja_candidate_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ja_resumes           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ja_job_matches       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ja_applications      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ja_approval_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ja_audit_log         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ja_jobs              ENABLE ROW LEVEL SECURITY;

-- Jobs are shared/readable by all authenticated users
CREATE POLICY "ja_jobs_read"   ON public.ja_jobs FOR SELECT TO authenticated USING (true);
CREATE POLICY "ja_jobs_insert" ON public.ja_jobs FOR INSERT WITH CHECK (true);

-- Per-user isolation
CREATE POLICY "ja_own_profile"   ON public.ja_profiles          USING (auth.uid() = id);
CREATE POLICY "ja_own_config"    ON public.ja_candidate_configs USING (auth.uid() = user_id);
CREATE POLICY "ja_own_resumes"   ON public.ja_resumes           USING (auth.uid() = user_id);
CREATE POLICY "ja_own_matches"   ON public.ja_job_matches       USING (auth.uid() = user_id);
CREATE POLICY "ja_own_apps"      ON public.ja_applications      USING (auth.uid() = user_id);
CREATE POLICY "ja_own_approvals" ON public.ja_approval_requests USING (auth.uid() = user_id);
CREATE POLICY "ja_own_audit"     ON public.ja_audit_log         USING (auth.uid() = user_id);

-- ============================================================
-- TRIGGER — auto-create ja_profile when user signs up
-- ============================================================
CREATE OR REPLACE FUNCTION public.ja_handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.ja_profiles (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', '')
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Only create trigger if it doesn't already exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'ja_on_auth_user_created'
    ) THEN
        CREATE TRIGGER ja_on_auth_user_created
            AFTER INSERT ON auth.users
            FOR EACH ROW EXECUTE FUNCTION public.ja_handle_new_user();
    END IF;
END $$;

-- ============================================================
-- STORAGE BUCKET — for resumes
-- Run separately in Supabase Dashboard → Storage → New Bucket
-- Name: resumes, Private: true
-- Or run this if using service role:
-- ============================================================
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('resumes', 'resumes', false)
-- ON CONFLICT (id) DO NOTHING;
