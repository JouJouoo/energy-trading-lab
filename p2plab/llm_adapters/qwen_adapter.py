"""Qwen / DashScope adapter (OpenAI-compatible mode).

base_url:    https://dashscope.aliyuncs.com/compatible-mode/v1
model:       qwen-plus (override via ENERGY_LAB_LLM_MODEL)
json mode:   supported.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import BaseLLMAdapter
from .exceptions import LLMError


class QwenAdapter(BaseLLMAdapter):
    name = "qwen"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    default_model = "qwen-plus"
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
            "result_format": "message",
        }
        if max_tokens and max_tokens > 0:
            payload["max_tokens"] = max_tokens
        try:
            response = self._http_post("/chat/completions", payload, timeout=timeout)
        except LLMError:
            # If json mode is rejected, retry without the format hint.
            payload.pop("result_format", None)
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
