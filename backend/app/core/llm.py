"""
LLM Client — OpenAI primary, AWS Bedrock secondary (when valid credentials available).
"""
import json
import time
import requests
import structlog
from app.core.config import get_settings

logger = structlog.get_logger()

NOVA_MICRO = "amazon.nova-micro-v1:0"
NOVA_LITE  = "amazon.nova-lite-v1:0"


class LLMClient:
    def __init__(self, use_fast: bool = True):
        s = get_settings()
        self._use_fast     = use_fast
        self._nova_model   = NOVA_MICRO if use_fast else NOVA_LITE
        self._aws_region   = s.aws_region
        self._bedrock_key  = s.bedrock_api_key
        self._openai_key   = s.openai_api_key
        self._openai_model = s.openai_fast_model if use_fast else s.openai_model

    def invoke(self, prompt: str, system: str = "") -> str:
        # Try OpenAI first if available
        if self._openai_key:
            return self._call_openai_with_retry(prompt, system)

        # Fall back to Bedrock
        if self._bedrock_key:
            return self._call_nova(prompt, system)

        raise RuntimeError("No LLM provider available. Set OPENAI_API_KEY or BEDROCK_API_KEY.")

    def invoke_json(self, prompt: str, system: str = "") -> dict:
        raw = self.invoke(
            prompt + "\n\nRespond with ONLY valid JSON. No markdown fences.",
            system,
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(raw)

    def _call_openai_with_retry(self, prompt: str, system: str, max_retries: int = 5) -> str:
        from openai import OpenAI, RateLimitError
        client = OpenAI(api_key=self._openai_key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        wait = 30  # start with 30s wait on rate limit
        for attempt in range(max_retries):
            try:
                resp = client.chat.completions.create(
                    model=self._openai_model,
                    messages=messages,
                    temperature=0.1 if self._use_fast else 0.3,
                    max_tokens=4096,
                )
                return resp.choices[0].message.content
            except RateLimitError:
                if attempt == max_retries - 1:
                    raise
                logger.warning("openai_rate_limit", attempt=attempt + 1, wait_seconds=wait)
                time.sleep(wait)
                wait = min(wait * 2, 120)  # exponential backoff, cap at 2 min
            except Exception:
                raise

    def _call_nova(self, prompt: str, system: str) -> str:
        url = (
            f"https://bedrock-runtime.{self._aws_region}.amazonaws.com"
            f"/model/{self._nova_model}/invoke"
        )
        body: dict = {
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": 4096, "temperature": 0.1 if self._use_fast else 0.3},
        }
        if system:
            body["system"] = [{"text": system}]

        resp = requests.post(
            url,
            json=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._bedrock_key}"},
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Bedrock error ({resp.status_code}): {resp.text[:300]}")
        return resp.json()["output"]["message"]["content"][0]["text"]
