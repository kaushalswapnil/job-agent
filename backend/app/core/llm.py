"""
LLM Client — AWS Bedrock (primary) via Bearer token REST API + OpenAI (fallback).

BEDROCK_API_KEY is passed directly as a Bearer token — no decoding needed.
"""
import json
import requests
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import get_settings

logger = structlog.get_logger()

NOVA_MICRO = "amazon.nova-micro-v1:0"
NOVA_LITE  = "amazon.nova-lite-v1:0"


class LLMClient:
    """
    use_fast=True  → Nova Micro  (job matching — high volume)
    use_fast=False → Nova Lite   (resume tailoring — quality)
    Falls back to OpenAI if Bedrock fails.
    """

    def __init__(self, use_fast: bool = True):
        s = get_settings()
        self._use_fast      = use_fast
        self._nova_model    = NOVA_MICRO if use_fast else NOVA_LITE
        self._aws_region    = s.aws_region
        self._bedrock_key   = s.bedrock_api_key
        self._openai_key    = s.openai_api_key
        self._openai_model  = s.openai_fast_model if use_fast else s.openai_model

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(min=10, max=60))
    def invoke(self, prompt: str, system: str = "") -> str:
        if self._bedrock_key:
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
        url = (
            f"https://bedrock-runtime.{self._aws_region}.amazonaws.com"
            f"/model/{self._nova_model}/invoke"
        )
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        body: dict = {
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": 4096,
                "temperature": 0.1 if self._use_fast else 0.3,
            },
        }
        if system:
            body["system"] = [{"text": system}]

        resp = requests.post(
            url,
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._bedrock_key}",
            },
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Bedrock error ({resp.status_code}): {resp.text[:300]}")

        return resp.json()["output"]["message"]["content"][0]["text"]

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
            max_tokens=4096,
        )
        return resp.choices[0].message.content
