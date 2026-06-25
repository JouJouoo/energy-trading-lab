"""OpenAI adapter. The default adapter for the Energy Trading Lab.

base_url:    https://api.openai.com/v1
model:       gpt-4o-mini (override via ENERGY_LAB_LLM_MODEL)
json mode:   supported (response_format=json_object)
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .base import BaseLLMAdapter
from .exceptions import LLMError


class OpenAIAdapter(BaseLLMAdapter):
    name = "openai"
    base_url = "https://api.openai.com/v1"
    default_model = "gpt-4o-mini"
    supports_json_mode = True

    def call_chat_json(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2500,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        self._require_api_key()
        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        if max_tokens and max_tokens > 0:
            payload["max_tokens"] = max_tokens
        try:
            response = self._http_post("/chat/completions", payload, timeout=timeout)
        except LLMError:
            # Some accounts / regions reject json_object; fall back.
            payload.pop("response_format", None)
            response = self._http_post("/chat/completions", payload, timeout=timeout)
        content = self._extract_message_content(response)
        return self.parse_json_object(content)

    def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            self._http_post(
                "/chat/completions",
                self._default_health_payload(),
                timeout=10,
            )
            return True
        except (LLMError, urllib.error.URLError, TimeoutError, OSError):
            return False
        except Exception:
            return False
