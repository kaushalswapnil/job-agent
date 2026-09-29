import os
import json
import boto3
import structlog
from functools import lru_cache
from botocore.exceptions import ClientError

logger = structlog.get_logger()


@lru_cache(maxsize=128)
def get_secret(secret_name: str) -> dict:
    """Fetch secret from AWS Secrets Manager. Cached per process."""
    client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except ClientError as e:
        logger.error("secrets_manager_error", secret=secret_name, error=str(e))
        raise


def get_db_url() -> str:
    env = os.environ.get("ENV", "local")
    if env == "local":
        return os.environ.get(
            "DATABASE_URL",
            "postgresql://jobagent:jobagent@localhost:5432/job_agent"
        )
    secret = get_secret("job-agent/database")
    return (
        f"postgresql://{secret['username']}:{secret['password']}"
        f"@{secret['host']}:{secret['port']}/{secret['dbname']}"
    )


def get_bedrock_client():
    return boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def get_s3_client():
    return boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def get_sqs_client():
    return boto3.client("sqs", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def get_ses_client():
    return boto3.client("ses", region_name=os.environ.get("AWS_REGION", "us-east-1"))
