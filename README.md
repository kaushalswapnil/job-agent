# Autonomous AI Job Search & Application Agent

A production-ready, cloud-native AI agent that continuously discovers, evaluates, tailors resumes for, and tracks job applications — operating 24/7 on AWS without requiring your laptop to be on.

## Architecture Overview

```
EventBridge (Scheduler)
        │
        ▼
   SQS Queues
        │
   ┌────┴────────────────────────────────┐
   │         Agent Orchestrator          │
   │         (ECS Fargate / Lambda)      │
   └────┬──────────┬──────────┬──────────┘
        │          │          │
   Discovery   Matching   Application
    Agent       Agent       Agent
        │          │          │
        └──────────┴──────────┘
                   │
            PostgreSQL (RDS)
            S3 (Resumes/Docs)
            Bedrock (LLM/RAG)
            SES (Email/Notify)
            Secrets Manager
```

## MVP Scope

1. Candidate profile management
2. Master resume upload & storage
3. Job discovery (Greenhouse, Lever, Remotive, public APIs)
4. Job description extraction & normalization
5. Job matching with semantic scoring (Bedrock)
6. Resume tailoring (Bedrock)
7. Application tracking database
8. Email response detection
9. Interview notification
10. Human approval workflow
11. Cloud scheduling (EventBridge)

## Project Structure

```
job-agent/
├── agents/                  # Python AI agent workflows
│   ├── discovery/           # Job Discovery Agent
│   ├── matching/            # Job Matching Agent
│   ├── resume/              # Resume Tailoring Agent
│   ├── cover_letter/        # Cover Letter Agent
│   ├── application/         # Application Agent
│   ├── monitoring/          # Response Monitoring Agent
│   ├── notification/        # Notification Agent
│   ├── orchestrator/        # Agent Orchestrator
│   └── common/              # Shared utilities, models, LLM client
├── api/                     # Java Spring Boot REST API + Dashboard backend
├── frontend/                # React Dashboard
├── infrastructure/          # Terraform IaC
│   ├── modules/
│   └── environments/
├── config/                  # Candidate profile & system config
│   └── resume/              # Master resume storage
├── prompts/                 # LLM prompt templates
├── tests/                   # Unit, integration, e2e tests
├── scripts/                 # Deployment & utility scripts
└── docker/                  # Dockerfiles
```

## Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- Python 3.11+
- Java 21+
- Node.js 20+
- Docker
- Terraform 1.6+

### Local Development
```bash
# 1. Copy and fill candidate profile
cp config/candidate_profile.example.yaml config/candidate_profile.yaml

# 2. Set up Python environment
cd agents && pip install -r requirements.txt

# 3. Start local services (PostgreSQL, LocalStack)
docker-compose up -d

# 4. Run database migrations
cd api && ./mvnw flyway:migrate

# 5. Start API
cd api && ./mvnw spring-boot:run

# 6. Start frontend
cd frontend && npm install && npm start

# 7. Run discovery agent locally
cd agents && python -m orchestrator.main --env local
```

### Cloud Deployment
```bash
cd infrastructure && terraform init && terraform apply -var-file=environments/prod.tfvars
```

## Security

- All secrets stored in AWS Secrets Manager
- IAM least-privilege roles per agent
- All sensitive candidate data encrypted at rest (AES-256)
- Audit log for every application action
- No credentials ever committed to source control

## Configuration

Edit `config/candidate_profile.yaml` to update your profile, skills, preferences, and job search strategy. No code changes required.
