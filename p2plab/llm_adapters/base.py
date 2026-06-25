"""The base interface every LLM adapter must implement.

The interface is intentionally small. An adapter is a thin HTTP wrapper
around the upstream's OpenAI-compatible chat-completions endpoint.

The class hierarchy:

```
BaseLLMAdapter (ABC)
├── OpenAIAdapter
├── DeepSeekAdapter
├── QwenAdapter
├── MoonshotAdapter
└── CustomAdapter
```

The `BaseLLMAdapter.call_chat_json` contract:

- Returns a parsed JSON `dict` (the upstream's response content, parsed
  out of the `choices[0].message.content` field).
- Raises `LLMError` on transport / parse / upstream errors.
- Raises `MissingAPIKeyError` when `self.api_key` is empty.

The `BaseLLMAdapter.health_check` contract:

- Returns `True` only when the upstream is reachable AND the API key is
  valid. A `False` return is informational, not an error: the agent
  falls back to the heuristic.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .exceptions import LLMError, MissingAPIKeyError


@dataclass
class LLMRequest:
    """A normalized request to the upstream.

    The `BaseLLMAdapter` does not use this; subclasses may use it to
    surface the request shape in their `health_check`.
    """

    messages: List[Dict[str, str]]
    model: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 2500
    timeout: int = 30


class BaseLLMAdapter(ABC):
    """Abstract base for LLM providers."""

    name: str = "base"
    base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4o-mini"
    supports_json_mode: bool = True

    def __init__(
        self,
        api_key: str = "",
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout_sec: float = 30.0,
    ):
        self.api_key = api_key or ""
        self.base_url = (base_url or self.base_url).rstrip("/")
        if default_model:
            self.default_model = default_model
        self.timeout_sec = float(timeout_sec)

    # ----- abstract -----

    @abstractmethod
    def call_chat_json(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2500,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Send a chat completion request; return a parsed JSON dict."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the upstream is reachable AND the API key is valid."""

    # ----- shared helpers -----

    def _require_api_key(self) -> None:
        if not self.api_key:
            raise MissingAPIKeyError(
                f"{self.name} adapter has no API key. Set ENERGY_LAB_LLM_API_KEY or "
                f"pass api_key in the request config."
            )

    def _http_post(
        self,
        path: str,
        payload: Dict[str, Any],
        *,
        timeout: int,
    ) -> Dict[str, Any]:
        url = self.base_url.rstrip("/") + path
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Authorization": "Bearer %s" % self.api_key,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise LLMError("LLM HTTP error %s: %s" % (exc.code, body[:500])) from exc
        except Exception as exc:
            raise LLMError("LLM request failed: %s" % exc) from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMError("LLM response was not JSON: %s" % raw[:500]) from exc

    def _extract_message_content(self, response: Dict[str, Any]) -> str:
        try:
            return response["choices"][0]["message"]["content"]
        except Exception as exc:
            raise LLMError("Unexpected LLM response shape: %s" % str(response)[:500]) from exc

    @staticmethod
    def parse_json_object(content: str) -> Dict[str, Any]:
        """Parse a string into a dict. Tolerant of ```json ... ``` fences."""
        content = (content or "").strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?", "", content).strip()
            content = re.sub(r"```$", "", content).strip()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise LLMError("LLM did not return JSON: %s" % content[:500])
            parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise LLMError("LLM JSON must be an object.")
        return parsed

    def _default_health_payload(self) -> Dict[str, Any]:
        """The chat-completions payload used by the health check."""
        return {
            "model": self.default_model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "temperature": 0.0,
        }

    def _status_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "base_url": self.base_url,
            "default_model": self.default_model,
            "has_api_key": bool(self.api_key),
            "supports_json_mode": self.supports_json_mode,
        }
