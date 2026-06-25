"""Custom OpenAI-compatible adapter.

The base_url and default_model are user-supplied. The user passes them
in the request config (`base_url`, `model`). If the request config
omits them, the adapter falls back to the OpenAI defaults and emits a
warning in the agent trace.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import BaseLLMAdapter
from .exceptions import LLMError, ProviderNotConfiguredError


class CustomAdapter(BaseLLMAdapter):
    name = "custom"
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
        # The custom adapter refuses to fall back silently: the operator
        # must have set a non-OpenAI base_url explicitly.
        if self.base_url == "https://api.openai.com/v1" and not getattr(self, "_explicit_custom", False):
            raise ProviderNotConfiguredError(
                "Custom adapter is using the default OpenAI base_url. "
                "Pass base_url='https://your-host/v1' in the request config."
            )
        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
        }
        if self.supports_json_mode:
            payload["response_format"] = {"type": "json_object"}
        if max_tokens and max_tokens > 0:
            payload["max_tokens"] = max_tokens
        try:
            response = self._http_post("/chat/completions", payload, timeout=timeout)
        except LLMError:
            if "response_format" in payload:
                payload.pop("response_format")
                response = self._http_post("/chat/completions", payload, timeout=timeout)
            else:
                raise
        content = self._extract_message_content(response)
        return self.parse_json_object(content)

    def health_check(self) -> bool:
        if not self.api_key:
            return False
        if self.base_url == "https://api.openai.com/v1" and not getattr(self, "_explicit_custom", False):
            return False
        try:
            self._http_post(
                "/chat/completions",
                self._default_health_payload(),
                timeout=10,
            )
            return True
        except (LLMError, Exception):
            return False
