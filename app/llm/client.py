"""
LLM client abstraction.

All LLM calls route through this module. Swapping providers means
only changing this file (and prompts.py if prompt format differs).
"""
import json
from typing import Any

import httpx

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class LLMClient:
    def __init__(self) -> None:
        self._provider = settings.llm_provider.lower()
        self._api_key = settings.resolved_llm_api_key
        self._base_url = settings.llm_base_url.rstrip("/")

    def complete(self, system: str, user: str) -> str:
        """Synchronous completion. Returns raw text response."""
        if not self._api_key:
            raise LLMError("No LLM API key configured.")

        try:
            if self._provider == "anthropic":
                return self._complete_anthropic(system, user)
            if self._provider == "perplexity":
                return self._complete_openai_compatible(system, user)
            raise LLMError(f"Unsupported LLM provider: {self._provider}")
        except httpx.TimeoutException:
            logger.error("llm_timeout", model=settings.llm_model)
            raise LLMError("LLM request timed out. Try again shortly.")
        except httpx.HTTPStatusError as e:
            logger.error(
                "llm_api_error",
                provider=self._provider,
                status=e.response.status_code,
                message=e.response.text[:500],
            )
            raise LLMError(f"LLM API error: {e.response.status_code}")
        except httpx.HTTPError as e:
            logger.error("llm_connection_error", provider=self._provider, error=str(e))
            raise LLMError("Could not connect to LLM service.")

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        """Complete and parse JSON response. Returns dict."""
        raw = self.complete(system, user)
        try:
            # Strip markdown code fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            return json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            logger.error("llm_json_parse_error", raw_preview=raw[:200], error=str(e))
            raise LLMError(f"LLM returned invalid JSON: {str(e)[:100]}")

    def _complete_anthropic(self, system: str, user: str) -> str:
        response = self._post_json(
            f"{self._base_url}/v1/messages",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            },
            payload={
                "model": settings.llm_model,
                "max_tokens": settings.llm_max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        content = response.get("content", [])
        if not content or "text" not in content[0]:
            raise LLMError("Anthropic response was missing text content.")
        return str(content[0]["text"])

    def _complete_openai_compatible(self, system: str, user: str) -> str:
        response = self._post_json(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            payload={
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
                "max_tokens": settings.llm_max_tokens,
            },
        )
        choices = response.get("choices", [])
        if not choices:
            raise LLMError("LLM response did not include choices.")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not content:
            raise LLMError("LLM response did not include message content.")
        return str(content)

    def _post_json(self, url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    **headers,
                },
                json=payload,
            )
            response.raise_for_status()
            return response.json()


class LLMError(Exception):
    """Raised when the LLM call fails or returns unusable output."""
    pass


_client_instance: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = LLMClient()
    return _client_instance
