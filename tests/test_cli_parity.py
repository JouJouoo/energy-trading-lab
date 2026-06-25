"""Assert CLI dual-track output ≡ HTTP API output.

For every web-facing capability exposed by `p2plab.api.fastapi_server` and
mirrored by a CLI subcommand in `p2plab.cli`, this test:

1. Calls the underlying Python helper (the same one the endpoint / subcommand
   uses internally), and
2. Calls the CLI subcommand via `subprocess` and parses the JSON.

The two results must agree on the keys the dual-track contract promises.

The goal is to lock in the "both surfaces must call the same data" invariant
of the M6 dual-track refactor. If a CLI subcommand silently drifts from its
matching endpoint, this test catches it.

## What this test does NOT do

- It does not start a real FastAPI server. We use the in-process helpers.
- It does not require FastAPI to be installed — all exercised helpers live
  in `p2plab.plugin_loader`, `p2plab.llm_adapters`, and `p2plab.api.workspace`,
  none of which import `fastapi`.

## Running

```bash
pytest tests/test_cli_parity.py -v
```
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(*args: str) -> Dict[str, Any]:
    """Run `python -m p2plab.cli <args> --json` and parse the last JSON block.

    Some CLI handlers print a leading banner before the JSON payload. We
    locate the first `{` or `[` and parse from there to the end.
    """
    cmd = [sys.executable, "-m", "p2plab.cli", *args, "--json"]
    env = os.environ.copy()
    env.setdefault("ENERGY_LAB_DATA_DIR", str(REPO_ROOT / "data"))
    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(
            "CLI failed (rc=%d): %s\nstdout=%s\nstderr=%s"
            % (result.returncode, " ".join(cmd), result.stdout, result.stderr)
        )
    stdout = result.stdout
    # Find the first JSON start char
    for i, ch in enumerate(stdout):
        if ch in "[{":
            payload = stdout[i:]
            try:
                return json.loads(payload)
            except json.JSONDecodeError as exc:
                raise AssertionError(
                    "Could not parse CLI JSON for %s: %s\npayload=%s"
                    % (" ".join(args), exc, payload[:400])
                )
    raise AssertionError(
        "No JSON found in CLI output for %s\nstdout=%s" % (" ".join(args), stdout[:400])
    )


def _strip_volatile_keys(d: Dict[str, Any], keys: tuple = ("source",)) -> Dict[str, Any]:
    """Remove keys that are guaranteed to differ between surfaces (e.g. absolute paths)."""
    if not isinstance(d, dict):
        return d
    out: Dict[str, Any] = {}
    for k, v in d.items():
        if k in keys:
            continue
        out[k] = _strip_volatile_keys(v, keys) if isinstance(v, (dict, list)) else v
    return out


class TestPluginsAlgorithmsParity(unittest.TestCase):
    """`cli plugins-algorithms --json` ≡ `plugin_loader.list_algorithm_templates_with_runtime()`."""

    def test_plugins_algorithms_parity(self):
        from p2plab.plugin_loader import list_algorithm_templates_with_runtime

        truth = {
            t.name: {
                "name": t.name,
                "family": t.family,
                "display_name": t.display_name,
                "file_name": t.file_name,
                "description": t.description,
                "affected_modules": list(t.affected_modules),
                "inputs": dict(t.inputs),
                "parameters": dict(t.parameters),
                "validation": dict(t.validation),
                "tags": list(t.tags),
            }
            for t in list_algorithm_templates_with_runtime()
        }

        cli_payload = _run_cli("plugins-algorithms")
        # CLI output shape: {"count": N, "templates": [...]}
        self.assertIn("templates", cli_payload)
        cli_templates = {
            t["name"]: {
                "name": t["name"],
                "family": t["family"],
                "display_name": t["display_name"],
                "file_name": t["file_name"],
                "description": t["description"],
                "affected_modules": list(t.get("affected_modules") or []),
                "inputs": dict(t.get("inputs") or {}),
                "parameters": dict(t.get("parameters") or {}),
                "validation": dict(t.get("validation") or {}),
                "tags": list(t.get("tags") or []),
            }
            for t in cli_payload["templates"]
        }

        self.assertEqual(set(truth.keys()), set(cli_templates.keys()),
                         "Discovered template set differs from CLI output")
        for name, expected in truth.items():
            self.assertEqual(expected, cli_templates[name],
                             f"Template {name!r} mismatch: in-process ≡ CLI output")

    def test_plugins_scenarios_parity(self):
        from p2plab.plugin_loader import list_scenarios_with_runtime

        truth = {
            s.name: {
                "name": s.name,
                "display_name": s.display_name,
                "bus_count": s.bus_count,
                "base_voltage_kv": s.base_voltage_kv,
                "voltage_limits": list(s.voltage_limits),
                "topology_source": s.topology_source,
                "feeder_file": s.feeder_file,
                "prosumer_layout_file": s.prosumer_layout_file,
                "load_profile_file": s.load_profile_file,
                "pv_profile_file": s.pv_profile_file,
                "metrics_schema": list(s.metrics_schema),
                "tags": list(s.tags),
            }
            for s in list_scenarios_with_runtime()
        }

        cli_payload = _run_cli("plugins-scenarios")
        self.assertIn("scenarios", cli_payload)
        cli_scenarios = {
            s["name"]: {
                "name": s["name"],
                "display_name": s["display_name"],
                "bus_count": s["bus_count"],
                "base_voltage_kv": s["base_voltage_kv"],
                "voltage_limits": list(s["voltage_limits"]),
                "topology_source": s["topology_source"],
                "feeder_file": s["feeder_file"],
                "prosumer_layout_file": s.get("prosumer_layout_file"),
                "load_profile_file": s.get("load_profile_file"),
                "pv_profile_file": s.get("pv_profile_file"),
                "metrics_schema": list(s.get("metrics_schema") or []),
                "tags": list(s.get("tags") or []),
            }
            for s in cli_payload["scenarios"]
        }

        self.assertEqual(set(truth.keys()), set(cli_scenarios.keys()),
                         "Discovered scenario set differs from CLI output")
        for name, expected in truth.items():
            self.assertEqual(expected, cli_scenarios[name],
                             f"Scenario {name!r} mismatch: in-process ≡ CLI output")


class TestLLMProvidersParity(unittest.TestCase):
    """`cli llm-providers --json` ≡ `llm_adapters.list_providers()`."""

    def test_llm_providers_parity(self):
        from p2plab.llm_adapters import list_providers

        truth = list_providers()
        cli_payload = _run_cli("llm-providers")
        # CLI list-providers returns a bare list (not a dict)
        self.assertIsInstance(cli_payload, list)
        # Compare on the stable keys
        truth_keys = sorted(p["name"] for p in truth)
        cli_keys = sorted(p["name"] for p in cli_payload)
        self.assertEqual(truth_keys, cli_keys, "LLM provider names differ")

        truth_by_name = {p["name"]: p for p in truth}
        cli_by_name = {p["name"]: p for p in cli_payload}
        for name in truth_keys:
            t = truth_by_name[name]
            c = cli_by_name[name]
            for key in ("default_base_url", "default_model", "supports_json_mode"):
                self.assertEqual(
                    t.get(key), c.get(key),
                    f"LLM provider {name!r}.{key}: truth={t.get(key)!r} cli={c.get(key)!r}",
                )


class TestLLMStatusParity(unittest.TestCase):
    """`cli llm-status --json` ≡ `llm_adapters.snapshot_status()`."""

    # Env vars that `p2plab.llm._load_dotenv` would inject from `.env`.
    # Both surfaces must see the same effective env. The in-process test
    # does NOT go through `p2plab.llm` (it imports `p2plab.llm_adapters`
    # directly), so we set them explicitly here for the duration of the
    # test. The CLI subprocess inherits them from our test process.
    _LLM_ENV = {
        "ENERGY_LAB_LLM_BASE_URL": "https://api.deepseek.com",
        "ENERGY_LAB_LLM_MODEL": "deepseek-v4-flash",
        "ENERGY_LAB_LLM_API_KEY": "test-key",
    }

    def setUp(self) -> None:
        self._saved = {k: os.environ.get(k) for k in self._LLM_ENV}
        for k, v in self._LLM_ENV.items():
            os.environ[k] = v

    def tearDown(self) -> None:
        for k, prev in self._saved.items():
            if prev is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prev

    def test_llm_status_parity(self):
        from p2plab.llm_adapters import snapshot_status

        # Pass the provider explicitly to BOTH surfaces so we don't read
        # whatever the developer's shell env happens to be set to.
        status = snapshot_status(provider="openai", request_config={}, run_health_check=False)
        cli_payload = _run_cli("llm-status", "--provider", "openai")
        # Both should expose the same top-level keys (with possibly extra `providers` field).
        for key in ("provider", "base_url", "model", "enabled", "has_api_key"):
            self.assertIn(key, status)
            self.assertIn(key, cli_payload, f"llm-status missing key {key!r}")
            self.assertEqual(
                status[key], cli_payload[key],
                f"llm-status[{key!r}]: truth={status[key]!r} cli={cli_payload[key]!r}",
            )

    def test_llm_status_provider_override(self):
        from p2plab.llm_adapters import snapshot_status

        status = snapshot_status(provider="deepseek", request_config={}, run_health_check=False)
        cli_payload = _run_cli("llm-status", "--provider", "deepseek")
        self.assertEqual(status["provider"], cli_payload["provider"])
        self.assertEqual(status["base_url"], cli_payload["base_url"])
        self.assertEqual(status["model"], cli_payload["model"])


class TestWorkspaceListParity(unittest.TestCase):
    """`cli workspace-list --json` ≡ `WorkspaceManager.list_projects()` shape."""

    def test_workspace_list_parity(self):
        from p2plab.api.workspace import WorkspaceManager

        wm = WorkspaceManager()
        truth = wm.list_projects()
        cli_payload = _run_cli("workspace-list")
        # CLI may wrap as {"count": N, "projects": [...]} or be a bare list.
        if isinstance(cli_payload, dict) and "projects" in cli_payload:
            cli_projects = cli_payload["projects"]
        elif isinstance(cli_payload, list):
            cli_projects = cli_payload
        else:
            self.fail("Unexpected workspace-list payload shape: %r" % (cli_payload,))

        # Compare lengths; both surfaces scan the same dir + db.
        self.assertEqual(len(truth), len(cli_projects),
                         "WorkspaceManager.list_projects() length ≠ CLI workspace-list")

        # Each project dict should share the same keys.
        truth_keys = sorted(truth[0].keys()) if truth else []
        if cli_projects:
            cli_keys = sorted(cli_projects[0].keys())
            # Strip the volatile `source` key (added by plugin views) if present.
            truth_keys_stripped = [k for k in truth_keys if k != "source"]
            cli_keys_stripped = [k for k in cli_keys if k != "source"]
            self.assertEqual(
                truth_keys_stripped, cli_keys_stripped,
                "Project dict keys differ between WorkspaceManager and CLI",
            )


if __name__ == "__main__":
    unittest.main()
