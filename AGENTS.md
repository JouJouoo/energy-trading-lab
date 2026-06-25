# AGENTS.md — Directory Guide for Energy Trading Lab

> This file is the single source of truth for agents (human or AI) entering this repository. Read it first; before entering `p2plab/`, `web/`, `tests/`, or `deploy/`, read that layer's own `AGENTS.md` for module-level details. Do not copy module details back into the root file; root stays focused on cross-repository boundaries, workflow, and commands.

## Core documentation index

- Product and onboarding: `README.md`, `docs/i18n/README.zh-CN.md`, `QUICKSTART.md`.
- Contribution and environment: `CONTRIBUTING.md`, `docs/code-review-guidelines.md`, `.env.example`.
- Architecture and protocols: `docs/spec.md`, `docs/architecture.md`, `docs/skills-protocol.md`, `docs/scenarios-protocol.md`, `docs/llm-adapters.md`.
- Roadmap and references: `docs/roadmap.md`, `docs/references.md`, `CHANGELOG.md`.
- Directory-level agent guidance: `p2plab/AGENTS.md`, `web/AGENTS.md`, `tests/AGENTS.md`, `deploy/AGENTS.md`, `.github/AGENTS.md`.

## Workspace directories

- `p2plab/` — Python backend: agent, RAG, simulation, code generation, LLM adapters, FastAPI server. See `p2plab/AGENTS.md`.
- `p2plab/algorithm_templates/<family>/<name>/` — drop-in algorithm template plugins. Add a new `TEMPLATE.md` (or `.yaml`) + `<name>.py` here to register a new algorithm; no code change in `code_generator.py` required. See `docs/skills-protocol.md`.
- `scenarios/<grid>/` — drop-in simulation scenario plugins. Add a new `SCENARIO.md` + `feeder.json` here to register a new grid case; no code change in `grid.py` required. See `docs/scenarios-protocol.md`.
- `p2plab/llm_adapters/` — LLM provider adapter pool. Drop in a `<provider>_adapter.py` and add one entry to `_REGISTRY` in `router.py` to wire a new model host.
- `web/` — Vue 3 + Vite + Tauri desktop shell. See `web/AGENTS.md`.
- `examples/` — sample paper Markdown and Chinese theory drafts used by `p2plab.cli demo`.
- `tests/` — pytest unit + integration tests. See `tests/AGENTS.md`.
- `docs/` — design docs, protocols, roadmap, references.
- `deploy/` — Docker Compose deployment assets. See `deploy/AGENTS.md`.
- `runs/` — runtime experiment artifacts. See "Data directory contract" below.
- `data/` — SQLite database (`data/db.sqlite`), settings, and small caches. See "Data directory contract" below.

## Inactive or placeholder directories

- `runs/` and `data/` are runtime data and must stay out of git. `runs/<run_id>/code_project/` may be committed selectively as a reproducibility artifact; everything else is per-run scratch.
- `web/src-tauri/target/` and `web/dist/` are build outputs and must stay out of git.

# Development workflow

## Environment baseline

- Python 3.9+ is required (matches `pyproject.toml`).
- For the web frontend, Node 18+ and npm.
- New Python modules should default to `from __future__ import annotations`, dataclass + type hints, and snake_case. New Vue components should default to `<script setup>` and Composition API.
- The only allowed heavy backend dependency is FastAPI + Uvicorn; the only allowed heavy frontend dependencies are Vue 3, Chart.js, marked. LLM and other vendors are accessed through the `llm_adapters/` abstraction, not by importing a vendor SDK directly.

## Local lifecycle

- Use `python -m p2plab.cli serve` as the only local development lifecycle entry point. It boots the FastAPI + Uvicorn server on `http://127.0.0.1:8765`.
- For Docker-based development lifecycle, use `cd deploy && docker compose up -d`. See `deploy/AGENTS.md`.
- Ports are governed by `python -m p2plab.cli serve --port <port>`. Default is `8765`.
- Do not add root lifecycle aliases like `pnpm dev`, `npm start`, etc. — the project is Python-first with a Vue + Vite web layer, not a Node monorepo.

# Data directory contract

This section is the only repository-wide source of truth for daemon-managed data paths. Every README, guide, deployment note, and operational handoff that mentions data paths must point here instead of restating the rules.

The daemon has one active data-root truth source:

- On backend startup, `p2plab/api/fastapi_server.py` resolves the data root in this order:
  1. `os.environ["ENERGY_LAB_DATA_DIR"]` if set.
  2. Else `./data` (the directory containing `db.sqlite`).
- All daemon-owned data paths must derive from this resolved root:
  - `data/db.sqlite` — project metadata, settings, jobs.
  - `data/runs/<run_id>/` — per-run experiment artifacts (parallel to the historical `runs/` layout, but always under `data/`).
  - `data/cache/` — small caches (LLM responses, embeddings, paper text). Reserved for future use.
- The historical `runs/` directory at the repo root is **deprecated** as a daemon data root. New runs write under `data/runs/`. A one-time migration helper may copy `runs/<run_id>/` to `data/runs/<run_id>/` on first startup; treat it as implementation detail.
- `ENERGY_LAB_LLM_API_KEY` and friends are LLM credentials, not data roots. The daemon must not describe them as Energy Trading Lab runtime data.
- Manifest keys, CSS identifiers, and metric names are semantic namespaces, not filesystem path conventions.

## Sanctioned exceptions

- `ENERGY_LAB_LLM_*` env vars are configuration inputs from the operator, not daemon data.
- The Tauri desktop bundle uses `web/src-tauri/` for build inputs; that is a build concern, not a daemon data root.

## Known escape candidates that must not be reused

- Hard-coded `runs/` or `./runs` paths in any new code. Always go through `get_data_root()`.
- Module-level defaults that compute a path from `os.getcwd()` instead of receiving the resolved data root.
- `open(db_path)` calls that rely on a relative path; pass an absolute path derived from the data root.

# Root command boundary

- Keep the entrypoint simple: `python -m p2plab.cli <subcommand>`. Subcommands live in `p2plab/cli.py`.
- Do not add a competing CLI under `scripts/`, `bin/`, or `tools/`. New capabilities must extend `cli.py`.
- Build/test commands stay package-scoped: `pytest tests/`, `npm --prefix web run build`.

# GitHub automation boundary

Read `.github/AGENTS.md` before editing `.github/workflows/`, `.github/scripts/`, or any CI surfaces.

CI uses a single business workflow (`.github/workflows/ci.yml`) for `pytest` + `python -m p2plab.eval` on every PR. Do not add per-feature workflows without prior discussion.

# Release channel model

- The project does not ship multiple release channels yet. `main` is the only integration branch. Stable releases will be tagged from `main` once 1.0.0 is cut (see `docs/roadmap.md`).
- Public Tauri bundle identity is `Energy Trading Lab` (product name from `tauri.conf.json`); do not change it without a coordinated doc + UI update.

# Boundary constraints

- Tests under `tests/` live as siblings to the modules they exercise, named `test_<module>.py`. Do not add new `*_test.py` files inside `p2plab/` or `web/src/`.
- `p2plab/` must not import `web/`. `web/` talks to the backend through HTTP only. The shared shapes live in `p2plab/schemas.py` and are mirrored in `web/src/api/client.js` by hand (or generated by a future codegen step).
- Algorithm templates under `p2plab/algorithm_templates/` are loaded at runtime through `p2plab/plugin_loader.py`; do not `import` them statically from any other `p2plab/` module. Same rule for `scenarios/`.
- LLM providers are reached through `p2plab/llm_adapters/router.py`; do not call vendor SDKs directly from `agent.py` or `llm_analysis.py`.

# Capability exposure (UI/CLI dual-track)

Every user-facing capability must be reachable through both the web UI **and** the `p2plab` CLI. Shipping a feature with only one of the two surfaces is a regression.

- The CLI is the embeddability contract. External scripts, CI jobs, and operator workflows drive Energy Trading Lab through `python -m p2plab.cli <subcommand>`; they do not render the web UI.
- Both surfaces must call the same backend logic. The FastAPI HTTP layer is the single source of truth, with the CLI delegating to internal helper functions shared with the endpoint bodies.
- The CLI form must support `--json` for machine-readable output and accept long-form input via `--input-file <path|->` (where applicable), so jobs that pipe through `xargs`, `jq`, or shell loops are first-class.
- Web UI changes that ship a new endpoint must add the matching `cli.py` subcommand in the same PR, and the matching test in `tests/test_cli_parity.py`.

# Further reading

- `docs/spec.md` — design rationale.
- `docs/architecture.md` — runtime topology, data flow, file layout.
- `docs/skills-protocol.md` — algorithm template manifest spec.
- `docs/scenarios-protocol.md` — scenario manifest spec.
- `docs/llm-adapters.md` — LLM adapter interface and registry.
- `docs/roadmap.md` — release plan.
- `CHANGELOG.md` — what changed when.
