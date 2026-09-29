"""
LLM Client — AWS Bedrock Amazon Nova (primary) + OpenAI (fallback).

BEDROCK_API_KEY is a base64-encoded "accessKeyId:secretKey" token.
We decode it at runtime to get the actual AWS credentials.
"""
import json
import base64
import boto3
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import get_settings

logger = structlog.get_logger()

NOVA_MICRO = "amazon.nova-micro-v1:0"
NOVA_LITE  = "amazon.nova-lite-v1:0"


def _decode_bedrock_key(api_key: str) -> tuple[str, str]:
    """
    Decode BEDROCK_API_KEY (base64) → (access_key_id, secret_access_key).
    Format after decode: BedrockAPIKey-<id>:<secret>
    """
    try:
        decoded = base64.b64decode(api_key).decode("utf-8")
        # Strip prefix if present e.g. "BedrockAPIKey-nja3-at-..."
        if ":" in decoded:
            parts = decoded.split(":", 1)
            # access key id is the part before colon, strip any prefix
            access_key = parts[0].split("-")[-1] if "-" in parts[0] else parts[0]
            secret_key = parts[1]
            return access_key, secret_key
    except Exception as e:
        logger.warning("bedrock_key_decode_failed", error=str(e))
    return "", ""


class LLMClient:
    """
    use_fast=True  → Nova Micro  (job matching — high volume)
    use_fast=False → Nova Lite   (resume tailoring — quality)
    Falls back to OpenAI if Bedrock fails.
    """

    def __init__(self, use_fast: bool = True):
        s = get_settings()
        self._use_fast    = use_fast
        self._nova_model  = NOVA_MICRO if use_fast else NOVA_LITE
        self._aws_region  = s.aws_region
        self._openai_key  = s.openai_api_key
        self._openai_model = s.openai_fast_model if use_fast else s.openai_model

        # Decode Bedrock API key
        self._aws_key_id, self._aws_secret = "", ""
        if s.bedrock_api_key:
            self._aws_key_id, self._aws_secret = _decode_bedrock_key(s.bedrock_api_key)
        # Also accept explicit keys if set
        if s.aws_access_key_id:
            self._aws_key_id = s.aws_access_key_id
        if s.aws_secret_access_key:
            self._aws_secret = s.aws_secret_access_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def invoke(self, prompt: str, system: str = "") -> str:
        if self._aws_key_id and self._aws_secret:
            try:
                return self._call_nova(prompt, system)
            except Exception as e:
                logger.warning("nova_failed_falling_back", error=str(e))

        if self._openai_key:
            return self._call_openai(prompt, system)

        raise RuntimeError("No LLM provider available. Check BEDROCK_API_KEY or OPENAI_API_KEY in .env")

    def invoke_json(self, prompt: str, system: str = "") -> dict:
        raw = self.invoke(
            prompt + "\n\nRespond with ONLY valid JSON. No markdown fences.",
            system,
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(raw)

    def _call_nova(self, prompt: str, system: str) -> str:
        client = boto3.client(
            "bedrock-runtime",
            region_name=self._aws_region,
            aws_access_key_id=self._aws_key_id,
            aws_secret_access_key=self._aws_secret,
        )
        request = {
            "modelId": self._nova_model,
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {
                "maxTokens": 1024 if self._use_fast else 4096,
                "temperature": 0.1 if self._use_fast else 0.3,
            },
        }
        if system:
            request["system"] = [{"text": system}]

        resp = client.converse(**request)
        return resp["output"]["message"]["content"][0]["text"]

    def _call_openai(self, prompt: str, system: str) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=self._openai_key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=self._openai_model,
            messages=messages,
            temperature=0.1 if self._use_fast else 0.3,
            max_tokens=1024 if self._use_fast else 4096,
        )
        return resp.choices[0].message.content
