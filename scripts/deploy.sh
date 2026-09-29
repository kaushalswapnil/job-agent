#!/bin/bash
# deploy.sh — Build, push Docker image to ECR, and apply Terraform
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="job-agent"
IMAGE_TAG="${1:-latest}"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"

echo "==> Logging into ECR"
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "==> Creating ECR repository (if not exists)"
aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$AWS_REGION" 2>/dev/null || \
  aws ecr create-repository --repository-name "$ECR_REPO" --region "$AWS_REGION"

echo "==> Building Docker image"
docker build -f docker/Dockerfile.agent -t "${ECR_REPO}:${IMAGE_TAG}" .

echo "==> Tagging and pushing"
docker tag "${ECR_REPO}:${IMAGE_TAG}" "$ECR_URI"
docker push "$ECR_URI"

echo "==> Applying Terraform"
cd infrastructure
terraform init
terraform apply \
  -var="ecr_image_uri=${ECR_URI}" \
  -var-file="environments/prod.tfvars" \
  -auto-approve

echo "==> Deployment complete. ECR image: ${ECR_URI}"
