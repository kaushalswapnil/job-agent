#!/bin/bash
# LocalStack initialization — creates required AWS resources locally

awslocal s3 mb s3://job-agent-resumes-local
awslocal s3 mb s3://job-agent-config-local

awslocal sqs create-queue --queue-name job-agent-discovery
awslocal sqs create-queue --queue-name job-agent-evaluation
awslocal sqs create-queue --queue-name job-agent-applications
awslocal sqs create-queue --queue-name job-agent-notifications
awslocal sqs create-queue --queue-name job-agent-approvals

awslocal secretsmanager create-secret \
  --name job-agent/database \
  --secret-string '{"username":"jobagent","password":"jobagent","host":"postgres","port":5432,"dbname":"job_agent"}'

echo "LocalStack resources initialized."
