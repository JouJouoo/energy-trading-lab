"""LLM adapter pool for Energy Trading Lab.

This package is the only allowed seam through which `p2plab/` reaches an
external language model. New providers are added by:

1. Writing a `<provider>_adapter.py` that subclasses `BaseLLMAdapter`.
2. Registering the class in `router._REGISTRY`.

See `docs/llm-adapters.md` for the full interface, the BYOK priority, and
the "adding a new provider" recipe.
"""

from __future__ import annotations

from .base import BaseLLMAdapter
from .exceptions import (
    LLMError,
    MissingAPIKeyError,
    ProviderNotConfiguredError,
    UnknownProviderError,
)
from .router import list_providers, resolve_adapter, snapshot_status

__all__ = [
    "BaseLLMAdapter",
    "LLMError",
    "MissingAPIKeyError",
    "ProviderNotConfiguredError",
    "UnknownProviderError",
    "list_providers",
    "resolve_adapter",
    "snapshot_status",
]
