# Changelog

All notable changes to Energy Trading Lab are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased] — 0.2.0 — Plugin-ization & Open-Design alignment

### Added

- **Algorithm template plugin system**: new `p2plab/plugin_manifest.py` and `p2plab/plugin_loader.py`. Adding a new algorithm is now "drop a folder in `p2plab/algorithm_templates/<family>/<name>/`", no source code change.
- **Scenario plugin system**: new `scenarios/<grid>/SCENARIO.md` + `feeder.json` format. Adding IEEE 123 (or any custom feeder) is one folder, no `grid.py` change.
- **LLM adapter pool**: 5 adapters under `p2plab/llm_adapters/` (OpenAI, DeepSeek, Qwen, Moonshot, Custom) behind a `BaseLLMAdapter` interface and a `router.py` BYOK-resolving dispatcher. The legacy `p2plab/llm.py` API is preserved as a thin compatibility shim.
- **CLI dual-track**: 11 new subcommands under `python -m p2plab.cli` mirror the FastAPI endpoints: `workspace-list`, `workspace-get`, `workspace-delete`, `metrics-get`, `trace-get`, `report-get`, `plugins-algorithms`, `plugins-scenarios`, `llm-status`, `paper2code`, `eval`. All support `--json`.
- **Plugin UI view**: new `web/src/views/PluginView.vue` lists discovered algorithms and scenarios; reachable from the workspace header.
- **Two new FastAPI endpoints**: `GET /api/plugins/algorithms` and `GET /api/plugins/scenarios`.
- **Documentation matrix**: `AGENTS.md`, `QUICKSTART.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `MAINTAINERS.md`, `PRIVACY.md`, `TRANSLATIONS.md`, plus `docs/spec.md`, `docs/skills-protocol.md`, `docs/scenarios-protocol.md`, `docs/llm-adapters.md`, `docs/roadmap.md`, `docs/references.md`, `docs/code-review-guidelines.md`, and `docs/i18n/README.{en,zh-CN}.md`.
- **Data directory contract**: `$ENERGY_LAB_DATA_DIR` is now the single source of truth for daemon-owned paths; documented in `AGENTS.md`.
- **Docker Compose deployment**: `deploy/docker-compose.yml` + `deploy/Dockerfile` + `deploy/.env.example` + `deploy/README.md`.
- **GitHub automation**: `.github/AGENTS.md` + `.github/ISSUE_TEMPLATE/*.md` + `.github/PULL_REQUEST_TEMPLATE.md` + `.github/workflows/ci.yml`.
- **Plugin manifest tests**: `tests/test_plugin_manifest.py` and `tests/test_llm_adapters.py`.
- **CLI parity test**: `tests/test_cli_parity.py` — asserts that the CLI subcommand output is byte-equivalent (modulo volatile keys) to the in-process helper used by the matching FastAPI endpoint. Covers `plugins-algorithms`, `plugins-scenarios`, `llm-providers`, `llm-status`, `workspace-list`.
- **Data root helper move**: `get_data_root()` is now defined in `p2plab/api/workspace.py` and re-exported by `p2plab/api/fastapi_server.py`. This lets the CLI dual-track subcommands resolve `$ENERGY_LAB_DATA_DIR` without importing FastAPI.
- **WorkspaceManager db_path**: `WorkspaceManager` now accepts a `db_path` argument so the CLI can write to `data/db.sqlite` (the daemon contract) instead of the in-source default.

### Fixed

- **CLI subcommand registration shadowing** (`p2plab/cli.py`): the dual-track subcommand parser variables were originally assigned as `sub = sub.add_parser(...)`, which overwrote the `sub` reference and broke every subsequent `add_parser` call. Each new subcommand now uses a distinct parser variable (`ws_list`, `ws_get`, `metrics`, `trace`, `report`, `plg_alg`, `plg_scn`, `llm_st`, `llm_pv`, `p2c`, `evl`) — mirroring the existing `demo` / `reproduce` / `theory` / `serve` style.

### Changed

- `p2plab/code_generator.py:ALGORITHM_MODULE_MAP` is no longer the source of truth; it is kept as a fallback for back-compat. The new `CodeGenerator` consults `plugin_loader.discover_algorithm_templates()` first.
- `p2plab/grid.py` reads feeder data from `scenarios/<name>/feeder.json` when available; the historical in-source `IEEE33_FEEDER` / `IEEE69_FEEDER` constants remain as the fallback.
- `p2plab/api/fastapi_server.py` resolves `RUN_ROOT` from `ENERGY_LAB_DATA_DIR` (or `./data`).
- `README.md` slimmed; the long-form English copy moved to `docs/i18n/README.en.md`, Chinese copy to `docs/i18n/README.zh-CN.md`.

### Deprecated

- Bare `runs/` at the repository root as a daemon data root. New runs write under `data/runs/`.

## [0.1.0] — 2026-06-24 — Initial public MVP

### Added

- P2P energy trading research Agent with paper-to-reproduction, theory-to-experiment, and paper-to-code pipelines.
- IEEE 33 / IEEE 69 grid cases.
- Five algorithm template families: Base, RL, Optimization, Auction, Game Theory.
- 8 algorithm template implementations: `grid_model`, `market_env`, `optimizer`, `double_auction`, `stackelberg_game`, `q_learning`, `reward`, `training_loop`.
- Deterministic fallback paper understanding with optional OpenAI-compatible LLM refinement.
- Generated experiment runner that writes `generated_experiment_attempt_*.py`, `execution_log_attempt_*.txt`, `training_curve_attempt_*.json`, `metrics_attempt_*.json`, `hourly_metrics_attempt_*.json`.
- Dedicated `code_project/` per run, with adapter, runner, and smoke test.
- FastAPI + Uvicorn workspace with `/docs` Swagger, job queue, workspace management, and SQLite persistence.
- Vue 3 + Vite + Chart.js + marked web UI, packaged with Tauri for desktop.
- `p2plab eval` portfolio evaluation runner.
- PDF / TXT / Markdown document upload and parsing.
- Markdown report rendering and side-by-side strategy comparison charts.

[Unreleased]: https://github.com/JouJouoo/energy-trading-lab/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/JouJouoo/energy-trading-lab/releases/tag/v0.1.0
