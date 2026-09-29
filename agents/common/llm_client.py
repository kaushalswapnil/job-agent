import json
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from common.aws_clients import get_bedrock_client
from common.config_loader import get_llm_config

logger = structlog.get_logger()


class LLMClient:
    """
    Abstraction over Amazon Bedrock.
    Supports configurable models per task with automatic fallback.
    """

    def __init__(self, task: str = "default"):
        self._client = get_bedrock_client()
        cfg = get_llm_config(task)
        self.model = cfg["model"]
        self.fallback_model = cfg["fallback_model"]
        self.temperature = cfg["temperature"]
        self.max_tokens = cfg["max_tokens"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def invoke(self, prompt: str, system_prompt: str = "") -> str:
        """Invoke Bedrock model. Falls back to fallback_model on throttling."""
        try:
            return self._call_model(self.model, prompt, system_prompt)
        except Exception as e:
            if "ThrottlingException" in str(e) and self.fallback_model:
                logger.warning("llm_throttled_falling_back", model=self.model, fallback=self.fallback_model)
                return self._call_model(self.fallback_model, prompt, system_prompt)
            raise

    def _call_model(self, model_id: str, prompt: str, system_prompt: str) -> str:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt

        response = self._client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]

    def invoke_json(self, prompt: str, system_prompt: str = "") -> dict:
        """Invoke and parse JSON response."""
        raw = self.invoke(prompt, system_prompt)
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(raw)
