"""Tests for the LLM adapter pool.

All tests mock the upstream HTTP layer; we never call a real provider
from a test. The fixture pattern uses `unittest.mock.patch` to swap the
adapter's `_http_post` for a stub that returns a pre-canned response.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from p2plab.llm_adapters import (
    BaseLLMAdapter,
    LLMError,
    MissingAPIKeyError,
    UnknownProviderError,
    list_providers,
    resolve_adapter,
    snapshot_status,
)
from p2plab.llm_adapters.custom_adapter import CustomAdapter
from p2plab.llm_adapters.deepseek_adapter import DeepSeekAdapter
from p2plab.llm_adapters.moonshot_adapter import MoonshotAdapter
from p2plab.llm_adapters.openai_adapter import OpenAIAdapter
from p2plab.llm_adapters.qwen_adapter import QwenAdapter


def _ok_response(content: str = '{"answer": 42}') -> dict:
    return {"choices": [{"message": {"content": content}}]}


class LLMAdapterRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        # Wipe LLM env so each test starts clean.
        for k in list(os.environ.keys()):
            if k.startswith("ENERGY_LAB_LLM"):
                del os.environ[k]

    def test_list_providers_has_all_five(self) -> None:
        providers = list_providers()
        names = {p["name"] for p in providers}
        self.assertEqual(
            names,
            {"openai", "deepseek", "qwen", "moonshot", "custom"},
        )

    def test_resolve_adapter_dispatches_to_correct_class(self) -> None:
        for provider, expected_cls in [
            ("openai", OpenAIAdapter),
            ("deepseek", DeepSeekAdapter),
            ("qwen", QwenAdapter),
            ("moonshot", MoonshotAdapter),
            ("custom", CustomAdapter),
        ]:
            with self.subTest(provider=provider):
                adapter = resolve_adapter(provider, {"api_key": "test-key"})
                self.assertIsInstance(adapter, expected_cls)

    def test_resolve_adapter_case_insensitive(self) -> None:
        for variant in ("OpenAI", "OPENAI", "openai", "openAI"):
            with self.subTest(variant=variant):
                adapter = resolve_adapter(variant, {"api_key": "x"})
                self.assertIsInstance(adapter, OpenAIAdapter)

    def test_resolve_adapter_unknown_raises(self) -> None:
        with self.assertRaises(UnknownProviderError):
            resolve_adapter("nonexistent", {"api_key": "x"})

    def test_byok_priority_request_over_env(self) -> None:
        os.environ["ENERGY_LAB_LLM_API_KEY"] = "env-key"
        adapter = resolve_adapter(
            "openai",
            {"api_key": "request-key"},
        )
        self.assertEqual(adapter.api_key, "request-key")

    def test_byok_priority_env_over_scoped(self) -> None:
        os.environ["ENERGY_LAB_LLM_API_KEY"] = "global-env-key"
        os.environ["ENERGY_LAB_LLM_OPENAI_API_KEY"] = "scoped-env-key"
        adapter = resolve_adapter("openai", {})
        self.assertEqual(adapter.api_key, "global-env-key")

    def test_byok_priority_scoped_when_no_global(self) -> None:
        os.environ["ENERGY_LAB_LLM_DEEPSEEK_API_KEY"] = "scoped"
        adapter = resolve_adapter("deepseek", {})
        self.assertEqual(adapter.api_key, "scoped")

    def test_byok_priority_empty_when_no_key(self) -> None:
        adapter = resolve_adapter("openai", {})
        self.assertEqual(adapter.api_key, "")

    def test_request_key_overrides_base_url_and_model(self) -> None:
        adapter = resolve_adapter(
            "openai",
            {
                "api_key": "k",
                "base_url": "https://example.com/v1",
                "model": "gpt-4o",
            },
        )
        self.assertEqual(adapter.base_url, "https://example.com/v1")
        self.assertEqual(adapter.default_model, "gpt-4o")

    def test_snapshot_status_disabled_by_default(self) -> None:
        status = snapshot_status("openai", {})
        self.assertFalse(status["enabled"])
        self.assertFalse(status["has_api_key"])

    def test_snapshot_status_enabled_with_api_key(self) -> None:
        status = snapshot_status("openai", {"api_key": "k"})
        self.assertTrue(status["enabled"])
        self.assertTrue(status["has_api_key"])
        self.assertEqual(status["provider"], "openai")
        self.assertEqual(status["model"], "gpt-4o-mini")
        self.assertIn("providers", status)
        self.assertEqual(len(status["providers"]), 5)


class OpenAIAdapterTests(unittest.TestCase):
    def test_missing_api_key_raises(self) -> None:
        adapter = OpenAIAdapter(api_key="")
        with self.assertRaises(MissingAPIKeyError):
            adapter.call_chat_json([{"role": "user", "content": "hi"}])

    def test_call_chat_json_parses_response(self) -> None:
        adapter = OpenAIAdapter(api_key="k", default_model="gpt-4o-mini")
        with patch.object(
            BaseLLMAdapter, "_http_post", return_value=_ok_response()
        ) as mocked:
            result = adapter.call_chat_json(
                [{"role": "user", "content": "ping"}]
            )
        self.assertEqual(result, {"answer": 42})
        # First call uses json mode; verify the payload included it.
        self.assertIn("response_format", mocked.call_args.args[1])
        self.assertEqual(
            mocked.call_args.args[1]["response_format"],
            {"type": "json_object"},
        )

    def test_call_chat_json_falls_back_when_json_mode_rejected(self) -> None:
        adapter = OpenAIAdapter(api_key="k")
        # First call raises LLMError (json mode rejected); second succeeds.
        with patch.object(
            BaseLLMAdapter,
            "_http_post",
            side_effect=[LLMError("response_format not supported"), _ok_response()],
        ) as mocked:
            result = adapter.call_chat_json(
                [{"role": "user", "content": "ping"}]
            )
        self.assertEqual(result, {"answer": 42})
        # The retry should have stripped response_format.
        second_payload = mocked.call_args_list[1].args[1]
        self.assertNotIn("response_format", second_payload)

    def test_health_check_returns_false_without_api_key(self) -> None:
        adapter = OpenAIAdapter(api_key="")
        self.assertFalse(adapter.health_check())

    def test_health_check_returns_true_on_success(self) -> None:
        adapter = OpenAIAdapter(api_key="k")
        with patch.object(BaseLLMAdapter, "_http_post", return_value=_ok_response()):
            self.assertTrue(adapter.health_check())

    def test_health_check_returns_false_on_error(self) -> None:
        adapter = OpenAIAdapter(api_key="k")
        with patch.object(
            BaseLLMAdapter,
            "_http_post",
            side_effect=LLMError("downstream error"),
        ):
            self.assertFalse(adapter.health_check())


class DeepSeekAdapterTests(unittest.TestCase):
    def test_missing_api_key_raises(self) -> None:
        adapter = DeepSeekAdapter(api_key="")
        with self.assertRaises(MissingAPIKeyError):
            adapter.call_chat_json([{"role": "user", "content": "hi"}])

    def test_no_json_mode_in_payload(self) -> None:
        adapter = DeepSeekAdapter(api_key="k")
        with patch.object(
            BaseLLMAdapter, "_http_post", return_value=_ok_response()
        ) as mocked:
            adapter.call_chat_json([{"role": "user", "content": "ping"}])
        payload = mocked.call_args.args[1]
        self.assertNotIn("response_format", payload)

    def test_supports_json_mode_false(self) -> None:
        adapter = DeepSeekAdapter(api_key="k")
        self.assertFalse(adapter.supports_json_mode)


class QwenAdapterTests(unittest.TestCase):
    def test_call_chat_json_parses(self) -> None:
        adapter = QwenAdapter(api_key="k")
        with patch.object(
            BaseLLMAdapter, "_http_post", return_value=_ok_response()
        ):
            result = adapter.call_chat_json(
                [{"role": "user", "content": "ping"}]
            )
        self.assertEqual(result, {"answer": 42})


class MoonshotAdapterTests(unittest.TestCase):
    def test_call_chat_json_parses(self) -> None:
        adapter = MoonshotAdapter(api_key="k")
        with patch.object(
            BaseLLMAdapter, "_http_post", return_value=_ok_response()
        ):
            result = adapter.call_chat_json(
                [{"role": "user", "content": "ping"}]
            )
        self.assertEqual(result, {"answer": 42})


class CustomAdapterTests(unittest.TestCase):
    def test_refuses_default_base_url(self) -> None:
        # No explicit base_url → adapter refuses to call.
        adapter = CustomAdapter(api_key="k")
        with self.assertRaises(Exception) as ctx:
            adapter.call_chat_json([{"role": "user", "content": "ping"}])
        self.assertIn("base_url", str(ctx.exception).lower())

    def test_works_with_explicit_base_url(self) -> None:
        adapter = CustomAdapter(api_key="k", base_url="https://my-llm.example/v1")
        adapter._explicit_custom = True
        with patch.object(
            BaseLLMAdapter, "_http_post", return_value=_ok_response()
        ):
            result = adapter.call_chat_json(
                [{"role": "user", "content": "ping"}]
            )
        self.assertEqual(result, {"answer": 42})

    def test_health_check_requires_explicit_base_url(self) -> None:
        adapter = CustomAdapter(api_key="k")
        self.assertFalse(adapter.health_check())


class LegacyShimTests(unittest.TestCase):
    """The legacy `p2plab.llm` surface must still work."""

    def setUp(self) -> None:
        for k in list(os.environ.keys()):
            if k.startswith("ENERGY_LAB_LLM"):
                del os.environ[k]

    def test_llm_status_disabled_by_default(self) -> None:
        from p2plab.llm import llm_status
        status = llm_status()
        self.assertFalse(status["enabled"])
        self.assertIn("providers", status)

    def test_llm_status_with_key(self) -> None:
        from p2plab.llm import llm_status
        os.environ["ENERGY_LAB_LLM_API_KEY"] = "k"
        status = llm_status()
        self.assertTrue(status["enabled"])

    def test_call_chat_json_dispatches_via_router(self) -> None:
        from p2plab.llm import call_chat_json
        os.environ["ENERGY_LAB_LLM_PROVIDER"] = "deepseek"
        os.environ["ENERGY_LAB_LLM_API_KEY"] = "k"
        with patch.object(
            BaseLLMAdapter, "_http_post", return_value=_ok_response()
        ):
            result = call_chat_json([{"role": "user", "content": "ping"}])
        self.assertEqual(result, {"answer": 42})

    def test_sanitize_llm_config_redacts_api_key(self) -> None:
        from p2plab.llm import sanitize_llm_config
        sanitized = sanitize_llm_config({"api_key": "secret", "model": "x"})
        self.assertEqual(sanitized["api_key"], "***")
        self.assertEqual(sanitized["model"], "x")


if __name__ == "__main__":
    unittest.main()
