"""LLM adapter router.

The router is the single entry point that turns a provider name + request
config into a ready-to-use `BaseLLMAdapter`. The Agent's `llm.py` shim
calls `resolve_adapter(...)`; the FastAPI server's `/api/llm-status`
endpoint calls `list_providers()` to populate the dropdown.

## BYOK priority

The API key is resolved in this strict order:

1. `request_config["api_key"]` if non-empty.
2. `os.environ["ENERGY_LAB_LLM_API_KEY"]` if set and non-empty.
3. `os.environ["ENERGY_LAB_LLM_<PROVIDER>_API_KEY"]` if set and non-empty.
4. Empty string → `MissingAPIKeyError` on first call.

The web UI form takes priority 1; the env var takes priority 2/3; the
persisted setting in `data/db.sqlite` is the long-term fallback (the
web UI reads it back through the `/api/llm-status` response, not the
router directly).
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Type

from .base import BaseLLMAdapter
from .custom_adapter import CustomAdapter
from .deepseek_adapter import DeepSeekAdapter
from .exceptions import ProviderNotConfiguredError, UnknownProviderError
from .moonshot_adapter import MoonshotAdapter
from .openai_adapter import OpenAIAdapter
from .qwen_adapter import QwenAdapter


# Provider registry. Add new providers here.
_REGISTRY: Dict[str, Type[BaseLLMAdapter]] = {
    "openai": OpenAIAdapter,
    "deepseek": DeepSeekAdapter,
    "qwen": QwenAdapter,
    "moonshot": MoonshotAdapter,
    "custom": CustomAdapter,
}


def list_providers() -> List[Dict[str, Any]]:
    """List all registered providers, in stable order."""
    out: List[Dict[str, Any]] = []
    for key, cls in _REGISTRY.items():
        out.append({
            "name": key,
            "default_base_url": cls.base_url,
            "default_model": cls.default_model,
            "supports_json_mode": cls.supports_json_mode,
        })
    return out


def resolve_adapter(
    provider: str,
    request_config: Optional[Dict[str, Any]] = None,
) -> BaseLLMAdapter:
    """Resolve a provider name + request config into a ready-to-use adapter.

    Args:
        provider: One of the keys in `_REGISTRY` (case-insensitive).
        request_config: A dict that may carry:
            - api_key: explicit BYOK from the request body.
            - base_url: override the adapter's default.
            - model: override the adapter's default.
            - timeout_sec: per-request timeout.
            - temperature: default sampling temperature.
            - max_tokens: default max tokens.

    Returns:
        A configured `BaseLLMAdapter` instance.

    Raises:
        UnknownProviderError: when `provider` is not in the registry.
    """
    if not provider:
        provider = "openai"
    key = provider.lower().strip()
    if key not in _REGISTRY:
        raise UnknownProviderError(
            f"Unknown LLM provider {provider!r}. "
            f"Registered: {sorted(_REGISTRY.keys())}."
        )
    cls = _REGISTRY[key]
    config = request_config or {}

    api_key = _resolve_api_key(provider=key, request_config=config)
    base_url = (
        config.get("base_url")
        or os.environ.get("ENERGY_LAB_LLM_BASE_URL")
        or None
    )
    default_model = config.get("model") or os.environ.get("ENERGY_LAB_LLM_MODEL") or None
    timeout_sec = float(
        config.get("timeout_sec")
        or os.environ.get("ENERGY_LAB_LLM_TIMEOUT")
        or 30
    )

    adapter = cls(
        api_key=api_key,
        base_url=base_url,
        default_model=default_model,
        timeout_sec=timeout_sec,
    )

    # The Custom adapter requires an explicit base_url; mark it so the
    # adapter doesn't refuse the call as "using the default base_url".
    if key == "custom" and base_url is not None:
        adapter._explicit_custom = True  # type: ignore[attr-defined]

    return adapter


def _resolve_api_key(*, provider: str, request_config: Dict[str, Any]) -> str:
    """Apply the BYOK priority chain."""
    explicit = str(request_config.get("api_key") or "").strip()
    if explicit:
        return explicit
    env_key = str(os.environ.get("ENERGY_LAB_LLM_API_KEY") or "").strip()
    if env_key:
        return env_key
    scoped = str(os.environ.get(f"ENERGY_LAB_LLM_{provider.upper()}_API_KEY") or "").strip()
    if scoped:
        return scoped
    return ""


def snapshot_status(
    provider: str,
    request_config: Optional[Dict[str, Any]] = None,
    *,
    run_health_check: bool = False,
) -> Dict[str, Any]:
    """Return a status dict for the `/api/llm-status` endpoint.

    The shape matches what `p2plab/llm.py:llm_status` used to return,
    plus a `provider` key and a `providers` list. Existing callers
    (the web UI, the CLI) see no breaking change.
    """
    config = request_config or {}
    api_key = _resolve_api_key(provider=provider, request_config=config)
    enabled = bool(api_key) and not _is_disabled(config)
    status: Dict[str, Any] = {
        "enabled": enabled,
        "provider": provider,
        "base_url": config.get("base_url")
            or os.environ.get("ENERGY_LAB_LLM_BASE_URL")
            or _REGISTRY[provider.lower()].base_url,
        "model": config.get("model")
            or os.environ.get("ENERGY_LAB_LLM_MODEL")
            or _REGISTRY[provider.lower()].default_model,
        "has_api_key": bool(api_key),
        "providers": list_providers(),
    }
    if run_health_check and enabled:
        try:
            adapter = resolve_adapter(provider, config)
            status["upstream_reachable"] = adapter.health_check()
        except Exception as exc:  # noqa: BLE001 - we want a status dict
            status["upstream_reachable"] = False
            status["upstream_error"] = str(exc)[:200]
    return status


def _is_disabled(request_config: Dict[str, Any]) -> bool:
    flag = str(
        request_config.get("disabled")
        or os.environ.get("ENERGY_LAB_LLM_DISABLED")
        or ""
    ).strip().lower()
    return flag in ("1", "true", "yes")
