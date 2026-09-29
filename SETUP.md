# Setup Guide — Using Your Existing Keys

## What We're Reusing (Zero New Signups Needed)

| What | From | Value |
|---|---|---|
| Supabase project | Roulette app | `ngrudtbshliklqaznloi.supabase.co` |
| Supabase anon key | Roulette/src/lib/supabase.ts | already in code |
| OpenAI API key | agenticAI_swap/.env | `sk-proj-XHSHRGb6...` (fallback only) |
| AWS region | agenticAI_swap/application.yml | `us-east-1` |
| **Amazon Nova** | AWS Bedrock | **FREE — primary LLM** |

## LLM Strategy (Updated)
- **Job matching** → `amazon.nova-micro-v1:0` (FREE, fastest)
- **Resume tailoring** → `amazon.nova-lite-v1:0` (FREE, better quality)
- **Fallback** → OpenAI `gpt-4o-mini` (from agenticAI key, if Nova fails)

---

## Step 1: Add Job Agent Tables to Supabase (3 minutes)

1. Go to https://supabase.com/dashboard/project/ngrudtbshliklqaznloi
2. Click **SQL Editor** → **New Query**
3. Paste the entire contents of `backend/app/db/migrations/001_initial_schema.sql`
4. Click **Run**
5. You should see: "Success. No rows returned"

This adds `ja_` prefixed tables — does NOT touch your existing Roulette tables.

## Step 2: Create Resumes Storage Bucket (1 minute)

1. In Supabase Dashboard → **Storage** → **New Bucket**
2. Name: `resumes`
3. Toggle **Private** ON
4. Click **Create bucket**

## Step 3: Get Your Supabase Service Role Key (1 minute)

1. Supabase Dashboard → **Settings** → **API**
2. Copy the **service_role** key (under "Project API keys")
3. Keep this secret — never commit it

## Step 4: Enable Amazon Nova on Bedrock (FREE — 2 minutes)

1. Go to https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess
2. Click **Manage model access**
3. Check these boxes:
   - ✅ **Amazon Nova Micro** (free)
   - ✅ **Amazon Nova Lite** (free)
   - ✅ **Amazon Nova Pro** (free)
4. Click **Save changes** — access granted instantly, no wait

**Then check if AWS CLI is already configured on your machine:**
```bash
aws configure list
```
If it shows `access_key` and `region = us-east-1` → you're done, no need to set AWS keys in `.env`.

If NOT configured, get your keys here:
https://us-east-1.console.aws.amazon.com/iam/home#/security_credentials
→ **Access keys** → **Create access key** → copy both values

## Step 5: Create Backend .env File

```bash
cd Job_Agent/backend
copy .env.example .env
```

Edit `.env`:

```env
SUPABASE_URL=https://ngrudtbshliklqaznloi.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5ncnVkdGJzaGxpa2xxYXpubG9pIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM0MDUxMzAsImV4cCI6MjA5ODk4MTEzMH0.n5B5AV_8hvLQRayF3g1MhAbGqsSh4TAu6EiY_xrd4K4
SUPABASE_SERVICE_KEY=<paste service_role key from Step 3>

# AWS Nova — FREE primary LLM
# Leave blank if `aws configure` is already set up on your machine
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# OpenAI — fallback only (from agenticAI_swap/.env)
OPENAI_API_KEY=<your-openai-api-key>
OPENAI_MODEL=gpt-4o
OPENAI_FAST_MODEL=gpt-4o-mini

# Resend — free email (resend.com — 3000 emails/month free)
RESEND_API_KEY=<get from resend.com>
RESEND_FROM_EMAIL=onboarding@resend.dev

SECRET_KEY=job-agent-secret-key-change-this-32chars
FRONTEND_URL=http://localhost:8081
APP_ENV=development
```

## Step 6: Run Backend Locally

```bash
cd Job_Agent/backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/docs — full API docs.

## Step 7: Run Mobile App

Install **Expo Go** on your phone first:
- iPhone: https://apps.apple.com/app/expo-go/id982107779
- Android: https://play.google.com/store/apps/details?id=host.exp.exponent

```bash
cd Job_Agent/mobile
npm install

# Create .env (values already filled in)
copy .env.example .env
# Edit EXPO_PUBLIC_API_URL=http://localhost:8000

npx expo start
```

- Press `w` → opens in browser
- Scan QR code with Expo Go → opens on your phone

## Step 8: Onboard Yourself

1. Open app → **Sign Up** with your email
2. Go to **Setup** tab → fill profile → upload resume PDF
3. Go to **Dashboard** → tap **Run Full Pipeline Now**
4. Jobs appear in **Matches** tab within ~2 minutes
5. **Approvals** tab shows jobs waiting for your go-ahead

---

## Deploy to Railway (Free Cloud Hosting)

```bash
npm install -g @railway/cli
railway login

cd Job_Agent/backend
railway init
railway up
```

Then in Railway dashboard → **Variables** → add all the same env vars from Step 5.
Copy your Railway URL → update `EXPO_PUBLIC_API_URL` in `mobile/.env`.

---

## Architecture (Final)

```
Mobile App (Expo — iOS/Android/Web)
         │
         ▼
  FastAPI Backend (Railway — free)
         │
    ┌────┴──────────────────────────────┐
    │                                   │
Supabase                         Amazon Nova (FREE)
(existing Roulette project)      nova-micro → matching
ja_* tables + Storage + Auth     nova-lite  → resume tailoring
                                       │
                                 OpenAI gpt-4o-mini
                                 (fallback if Nova fails)
    │
Job Sources (free public APIs)
  Remotive · Arbeitnow · Greenhouse · Lever
```

## Cost Estimate

| Service | Cost |
|---|---|
| Supabase | $0 (existing project) |
| Railway | $0 ($5 free credit/month) |
| Amazon Nova Micro (job matching) | **$0 FREE** |
| Amazon Nova Lite (resume tailoring) | **$0 FREE** |
| OpenAI (fallback only, rarely used) | ~$0 |
| Resend email | $0 (3000/month free) |
| **Total** | **$0/month** |

## Checklist

- [ ] Step 1 — SQL ran in Supabase, tables created
- [ ] Step 2 — `resumes` storage bucket created
- [ ] Step 3 — service_role key copied
- [ ] Step 4 — Nova Micro + Lite + Pro enabled on Bedrock
- [ ] Step 5 — `.env` file created and filled
- [ ] Step 6 — backend running at localhost:8000
- [ ] Step 7 — mobile app running, QR scanned on phone
- [ ] Step 8 — profile filled, resume uploaded, pipeline triggered
