from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = "https://ngrudtbshliklqaznloi.supabase.co"
    supabase_anon_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5ncnVkdGJzaGxpa2xxYXpubG9pIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM0MDUxMzAsImV4cCI6MjA5ODk4MTEzMH0.n5B5AV_8hvLQRayF3g1MhAbGqsSh4TAu6EiY_xrd4K4"
    supabase_service_key: str

    # AWS Bedrock — base64 encoded API key (primary LLM)
    aws_region: str = "eu-north-1"
    bedrock_api_key: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # OpenAI — fallback
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_fast_model: str = "gpt-4o-mini"

    # Gmail SMTP
    gmail_address: str = ""
    gmail_app_password: str = ""

    secret_key: str = "change-me"
    app_env: str = "development"
    frontend_url: str = "http://localhost:8081"
    port: int = 8000

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
