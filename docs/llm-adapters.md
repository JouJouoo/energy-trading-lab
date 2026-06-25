# LLM adapters — Provider interface and registry

> **Version**: 0.2.0
> **Status**: Stable. New providers must follow this spec.

The LLM is the only network dependency of Energy Trading Lab. It is reached through an **adapter pool** under `p2plab/llm_adapters/`, so that:

- A new provider is a single Python file plus one router entry.
- A provider that breaks the contract is replaceable in one diff.
- The Agent's structured-extraction step is reproducible: when no LLM is configured, the heuristic fallback (`p2plab/llm_analysis.py:fallback_*`) takes over and emits the same shape.

This is the analogue of open-design's [`apps/daemon/src/agents.ts`](https://github.com/nexu-io/open-design/blob/main/apps/daemon/src/agents.ts) — an adapter pool behind a single dispatch table.

## 1. Adapter interface

Every adapter inherits from `p2plab/llm_adapters/base.py:BaseLLMAdapter`:

```python
class BaseLLMAdapter(ABC):
    name: str                                  # "openai", "deepseek", ...
    base_url: str                              # "https://api.openai.com/v1"
    default_model: str                         # "gpt-4o-mini"

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
```

The contract is small on purpose: an adapter is a thin HTTP wrapper around the upstream's OpenAI-compatible chat completions endpoint. Vendors with non-compatible APIs (e.g. raw Anthropic) need a slightly larger adapter that translates to the OpenAI shape internally — but the surface stays the same.

## 2. Built-in adapters

| File | Provider | base_url | default_model |
|---|---|---|---|
| `openai_adapter.py` | OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| `deepseek_adapter.py` | DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| `qwen_adapter.py` | Qwen / DashScope | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| `moonshot_adapter.py` | Moonshot / Kimi | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| `custom_adapter.py` | Custom OpenAI-compatible | user-supplied | user-supplied |

All five implement the same `BaseLLMAdapter` contract. The differences are:

- The `base_url` default.
- The `default_model` default.
- A few providers (DeepSeek) don't support `response_format={"type": "json_object"}`; the adapter falls back to a non-forced completion and parses the first JSON object out of the response.
- The `health_check` ping uses the cheapest available model call.

## 3. Router

`p2plab/llm_adapters/router.py` exposes one function:

```python
def resolve_adapter(provider: str, request_config: Dict[str, Any]) -> BaseLLMAdapter:
    """Resolve a provider name + request config into a ready-to-use adapter.

    The `request_config` dict accepts:
      - api_key: explicit BYOK from the request body.
      - base_url: override the adapter's default.
      - model: override the adapter's default.
      - timeout_sec: per-request timeout.
      - temperature: default sampling temperature.
      - max_tokens: default max tokens.
    """
```

### 3.1 BYOK priority

The API key is resolved in this strict order:

1. `request_config["api_key"]` if non-empty.
2. `os.environ["ENERGY_LAB_LLM_API_KEY"]` if set and non-empty.
3. The persisted setting `data/db.sqlite` key `llm.api_key` (set via the web UI's LLM panel).
4. Empty string → adapter is constructed but `call_chat_json` raises `MissingAPIKeyError` on the first call.

The web UI form takes priority 1; the env var takes priority 2; the persisted setting is the long-term fallback. This way, a developer can override at the shell without losing the user's saved config.

### 3.2 Provider name resolution

`provider` is matched case-insensitively. `openai`, `OpenAI`, `OPENAI` all resolve to `OpenAIAdapter`. Unknown provider names raise `UnknownProviderError` with a message listing the registered adapters.

## 4. Compatibility shim

`p2plab/llm.py` (the legacy module) remains importable. Its public surface — `call_chat_json`, `llm_status`, `sanitize_llm_config` — is preserved by delegating to the router. Existing callers (`p2plab/agent.py`, `p2plab/llm_analysis.py`, `p2plab/api/fastapi_server.py`) need no changes.

The shim is a **back-compat layer**, not a parallel implementation. New code should call `p2plab/llm_adapters/router.resolve_adapter(...)` directly.

## 5. Health & observability

- `GET /api/llm-status` (and the CLI subcommand `python -m p2plab.cli llm-status`) returns the resolved adapter name, base URL, model, and a boolean `enabled` flag. The flag is `True` only when an API key resolves AND the upstream `health_check()` returns `True`.
- `agent_trace.json` includes the `llm_status` snapshot at the start of the run.

## 6. Adding a new provider

1. Create `p2plab/llm_adapters/<provider>_adapter.py` with a class that inherits `BaseLLMAdapter`.
2. Add an entry to `_REGISTRY` in `p2plab/llm_adapters/router.py`:
   ```python
   _REGISTRY = {
       "openai": OpenAIAdapter,
       "deepseek": DeepSeekAdapter,
       "qwen": QwenAdapter,
       "moonshot": MoonshotAdapter,
       "custom": CustomAdapter,
       "<your_provider>": <YourAdapter>,
   }
   ```
3. Add the provider to the web UI's LLM provider `<select>` in `web/src/views/ExperimentView.vue` (under `llmProvider`).
4. Add a test in `tests/test_llm_adapters.py` using a mocked `requests` / `httpx` call.
5. Add a row to the table in §2 of this doc.

The merge request is labeled `plugin:llm`.

## 7. Why OpenAI-compatible

Three reasons:

1. The structured-output / function-call / JSON-mode surface is increasingly standard.
2. Most Chinese model hosts (DeepSeek, Qwen via DashScope compatible mode, Moonshot, GLM) ship an OpenAI-compatible endpoint.
3. The HTTP client is a single dependency.

If we ever add a non-compatible provider (e.g. raw Anthropic or Google Vertex), the adapter just translates the request/response shape internally.
