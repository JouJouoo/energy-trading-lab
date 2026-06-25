"""Back-compat shim for the legacy `p2plab/llm.py` surface.

This module is intentionally thin. It exists so that:

- `from p2plab.llm import call_chat_json, llm_status, sanitize_llm_config`
  keeps working for every existing caller (`p2plab/agent.py`,
  `p2plab/llm_analysis.py`, `p2plab/code_generator.py`).
- The new `p2plab.llm_adapters.router.resolve_adapter(...)` is the
  primary entry point for new code.

The default provider is OpenAI. The default base URL is
`https://api.openai.com/v1`. The default model is `gpt-4o-mini`.

See `docs/llm-adapters.md` for the full provider list, the BYOK
priority, and the "adding a new provider" recipe.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .llm_adapters.exceptions import LLMError, MissingAPIKeyError
from .llm_adapters.router import (
    list_providers,
    resolve_adapter,
    snapshot_status,
)


__all__ = [
    "LLMSettings",
    "LLMError",
    "load_llm_settings",
    "llm_status",
    "call_chat_json",
    "parse_json_object",
    "sanitize_llm_config",
    "safe_float",
]


def _load_dotenv() -> None:
    """Load the .env file at the repository root, if present."""
    import os
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


# Back-compat dataclass. New code should use `BaseLLMAdapter` or the
# `llm_status` dict directly.
class LLMSettings:
    """Resolved LLM settings. Field names are kept for back-compat."""

    def __init__(
        self,
        enabled: bool,
        base_url: str,
        api_key: str,
        model: str,
        timeout_sec: float,
        temperature: float,
        max_tokens: int,
    ):
        self.enabled = enabled
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.timeout_sec = timeout_sec
        self.temperature = temperature
        self.max_tokens = max_tokens


def safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_llm_settings(overrides: Optional[Dict[str, Any]] = None) -> LLMSettings:
    """Resolve the legacy `LLMSettings` shape from overrides + env vars."""
    import os
    overrides = overrides or {}
    provider = str(overrides.get("provider") or os.getenv("ENERGY_LAB_LLM_PROVIDER", "openai"))
    api_key = str(overrides.get("api_key") or os.getenv("ENERGY_LAB_LLM_API_KEY", "")).strip()
    base_url = str(
        overrides.get("base_url")
        or os.getenv("ENERGY_LAB_LLM_BASE_URL")
        or "https://api.openai.com/v1"
    ).strip().rstrip("/")
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
    """Return the legacy status dict. Delegates to the router."""
    import os
    overrides = overrides or {}
    provider = str(overrides.get("provider") or os.getenv("ENERGY_LAB_LLM_PROVIDER", "openai"))
    return snapshot_status(provider=provider, request_config=overrides, run_health_check=False)


def call_chat_json(
    messages: List[Dict[str, str]],
    temperature: Optional[float] = None,
    llm_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Send a chat completion request; return a parsed JSON dict.

    Delegates to the router, which dispatches to the configured
    provider. See `docs/llm-adapters.md`.
    """
    import os
    config = dict(llm_config or {})
    provider = str(config.get("provider") or os.getenv("ENERGY_LAB_LLM_PROVIDER", "openai"))
    adapter = resolve_adapter(provider, config)
    if temperature is not None:
        config["temperature"] = temperature
    return adapter.call_chat_json(
        messages,
        model=config.get("model"),
        temperature=float(config.get("temperature", 0.1)),
        max_tokens=int(config.get("max_tokens", 2500)),
        timeout=int(config.get("timeout_sec", 30)),
    )


def parse_json_object(content: str) -> Dict[str, Any]:
    """Parse a JSON object out of an LLM response. Tolerant of ```json ... ``` fences."""
    from .llm_adapters.base import BaseLLMAdapter
    return BaseLLMAdapter.parse_json_object(content)


def sanitize_llm_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    config = dict(config or {})
    if "api_key" in config and config["api_key"]:
        config["api_key"] = "***"
    return config
