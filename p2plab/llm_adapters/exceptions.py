"""Exceptions raised by the LLM adapter pool.

These are public: callers (`p2plab/llm.py`, `p2plab/agent.py`,
`p2plab/api/fastapi_server.py`) are expected to import them and surface
the messages in the agent trace, the `analysis_meta.json` artifact, and
the `/api/llm-status` response.
"""

from __future__ import annotations


class LLMError(RuntimeError):
    """Base class for all LLM-related errors."""


class MissingAPIKeyError(LLMError):
    """Raised when an adapter is asked to call the upstream without an API key.

    The `LLM_ENABLED` flag in the agent trace should be `False` whenever
    this is raised; the heuristic fallback in `p2plab/llm_analysis.py`
    takes over.
    """


class ProviderNotConfiguredError(LLMError):
    """Raised when a provider's base_url / default_model is not configured."""


class UnknownProviderError(LLMError):
    """Raised when the router is asked for a provider that is not in the registry."""
