"""Moonshot / Kimi adapter.

base_url:    https://api.moonshot.cn/v1
model:       moonshot-v1-8k (override via ENERGY_LAB_LLM_MODEL)
json mode:   not advertised; we parse the response ourselves.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import BaseLLMAdapter
from .exceptions import LLMError


class MoonshotAdapter(BaseLLMAdapter):
    name = "moonshot"
    base_url = "https://api.moonshot.cn/v1"
    default_model = "moonshot-v1-8k"
    supports_json_mode = False

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
        }
        if max_tokens and max_tokens > 0:
            payload["max_tokens"] = max_tokens
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
        except (LLMError, Exception):
            return False
