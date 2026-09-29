#!/bin/bash
# run_local.sh — Start local dev environment and run an agent task
set -euo pipefail

TASK="${1:-discovery}"

echo "==> Starting local services"
docker-compose up -d postgres localstack

echo "==> Waiting for PostgreSQL to be ready"
until docker-compose exec -T postgres pg_isready -U jobagent -d job_agent; do
  sleep 2
done

echo "==> Running agent task: ${TASK}"
cd agents
PYTHONPATH=. \
  ENV=local \
  AWS_REGION=us-east-1 \
  AWS_ACCESS_KEY_ID=test \
  AWS_SECRET_ACCESS_KEY=test \
  AWS_ENDPOINT_URL=http://localhost:4566 \
  DATABASE_URL=postgresql://jobagent:jobagent@localhost:5432/job_agent \
  python -m orchestrator.main --task "$TASK" --env local
