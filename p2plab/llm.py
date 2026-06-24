from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class LLMSettings:
    enabled: bool
    base_url: str
    api_key: str
    model: str
    timeout_sec: float
    temperature: float
    max_tokens: int


class LLMError(RuntimeError):
    pass


def load_llm_settings(overrides: Optional[Dict[str, Any]] = None) -> LLMSettings:
    overrides = overrides or {}
    api_key = str(overrides.get("api_key") or os.getenv("ENERGY_LAB_LLM_API_KEY", "")).strip()
    base_url = str(overrides.get("base_url") or os.getenv("ENERGY_LAB_LLM_BASE_URL", "https://api.openai.com/v1")).strip().rstrip("/")
    model = str(overrides.get("model") or os.getenv("ENERGY_LAB_LLM_MODEL", "gpt-4o-mini")).strip()
    timeout = safe_float(overrides.get("timeout_sec"), safe_float(os.getenv("ENERGY_LAB_LLM_TIMEOUT", "30"), 30.0))
    temperature = safe_float(overrides.get("temperature"), safe_float(os.getenv("ENERGY_LAB_LLM_TEMPERATURE", "0.1"), 0.1))
    max_tokens = int(safe_float(overrides.get("max_tokens"), safe_float(os.getenv("ENERGY_LAB_LLM_MAX_TOKENS", "2500"), 2500)))
    disabled_value = overrides.get("disabled", os.getenv("ENERGY_LAB_LLM_DISABLED", ""))
    disabled = str(disabled_value).strip().lower() in ("1", "true", "yes")
    return LLMSettings(
        enabled=bool(api_key and not disabled),
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_sec=timeout,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def llm_status(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    settings = load_llm_settings(overrides)
    return {
        "enabled": settings.enabled,
        "base_url": settings.base_url,
        "model": settings.model,
        "has_api_key": bool(settings.api_key),
        "temperature": settings.temperature,
        "timeout_sec": settings.timeout_sec,
        "max_tokens": settings.max_tokens,
    }


def call_chat_json(
    messages: List[Dict[str, str]],
    temperature: Optional[float] = None,
    llm_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    settings = load_llm_settings(llm_config)
    if not settings.enabled:
        raise LLMError("LLM is not configured. Set ENERGY_LAB_LLM_API_KEY to enable model calls.")

    url = settings.base_url + "/chat/completions"
    payload = {
        "model": settings.model,
        "messages": messages,
        "temperature": settings.temperature if temperature is None else temperature,
        "response_format": {"type": "json_object"},
    }
    if settings.max_tokens > 0:
        payload["max_tokens"] = settings.max_tokens
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": "Bearer %s" % settings.api_key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.timeout_sec) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise LLMError("LLM HTTP error %s: %s" % (exc.code, body[:500])) from exc
    except Exception as exc:
        raise LLMError("LLM request failed: %s" % exc) from exc

    try:
        content = json.loads(raw)["choices"][0]["message"]["content"]
    except Exception as exc:
        raise LLMError("Unexpected LLM response shape: %s" % raw[:500]) from exc
    return parse_json_object(content)


def parse_json_object(content: str) -> Dict[str, Any]:
    content = content.strip()
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


def sanitize_llm_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    config = dict(config or {})
    if "api_key" in config and config["api_key"]:
        config["api_key"] = "***"
    return config


def safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
