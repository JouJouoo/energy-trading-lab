# Roadmap

This is the public release plan for Energy Trading Lab. Versions follow [Semantic Versioning](https://semver.org/). The dates are best-effort; the project ships when the milestone's verification gates pass, not on a calendar.

## 0.2.x — Plugin-ization (in progress, current milestone)

> Theme: make every domain knowledge unit a file, not a code change.

- 0.2.0: documentation matrix (AGENTS, QUICKSTART, CONTRIBUTING, CHANGELOG, MAINTAINERS, PRIVACY, TRANSLATIONS) and `docs/spec.md`, `docs/skills-protocol.md`, `docs/scenarios-protocol.md`, `docs/llm-adapters.md`.
- 0.2.0: algorithm template plugin system (`p2plab/plugin_manifest.py`, `p2plab/plugin_loader.py`).
- 0.2.0: scenario plugin system (`scenarios/ieee33/`, `scenarios/ieee69/`, optional `scenarios/ieee123/`).
- 0.2.0: LLM adapter pool (5 built-in providers behind `BaseLLMAdapter` + `router.py`).
- 0.2.0: CLI dual-track (11 new subcommands mirroring the FastAPI endpoints).
- 0.2.0: Docker Compose deployment (`deploy/`).
- 0.2.0: GitHub automation (CI, issue + PR templates, AGENTS guide).
- 0.2.1: `tests/test_cli_parity.py` enforces CLI ≡ HTTP shape.
- 0.2.2: web UI Plugin view shows the discovered templates and scenarios.

## 0.3.x — Hardening

- Migrate the in-source `IEEE33_FEEDER` / `IEEE69_FEEDER` constants to `scenarios/ieee33/feeder.json` and `scenarios/ieee69/feeder.json`. Drop the back-compat shim in `p2plab/grid.py`.
- Wire `data/runs/` as the canonical experiment root; add a one-time migration helper for legacy `runs/` directories.
- Add `tests/test_simulation_regression.py` that pins the cost, P2P volume, and voltage ranges for the IEEE 33 quick demo; fails on accidental regression.
- Add `tests/test_plugin_manifest.py` for the user-level plugin roots (`~/.energy_trading_lab/`).
- Add `p2plab eval --suite plugin` to evaluate a curated set of paper reproductions across all installed algorithm templates and scenarios.

## 0.4.x — Productionization

- Replace `python -m p2plab.cli serve` with a proper Uvicorn factory + process supervisor in the Docker image.
- Add rate limiting and per-IP concurrency caps to the FastAPI app.
- Add a `make release` target that bumps version, tags, and publishes the Tauri bundle.
- Add `CONTRIBUTING.md` "release checklist" section.
- Add an offline mode (no LLM, no network) that the CI uses by default; the LLM path is opt-in.

## 0.5.x — Optional, eval-only

These are scoped but not committed; they land when there's a clear product reason.

- **LangGraph runtime**: swap the deterministic Python pipeline in `p2plab/agent.py` for a `langgraph` StateGraph. The 14 tool nodes stay the same; the wiring moves to a graph definition. The artifact trail (`runs/<run_id>/agent_trace.json`) is preserved.
- **Vector store (Chroma / LanceDB)**: replace the keyword retriever in `p2plab/rag.py` with a small embedded Chroma index. The heuristic fallback remains; vector retrieval is opt-in.
- **Live IEEE feed data**: ship a sample 30-day load + PV profile sourced from an open dataset (e.g. Ausgrid), under `examples/profiles/`.
- **Power flow upgrade**: optional `pandapower` adapter behind the same `SimplePowerFlowValidator` interface; falls back gracefully if `pandapower` is not installed.

## 1.0.0 — Stable

- All 0.2.x / 0.3.x / 0.4.x features land.
- 14-day soak test of the FastAPI + Tauri bundle on macOS / Windows / Linux.
- Public `Tauri` signed release on GitHub Releases.
- Public Docker image on GHCR.
- Move the project license to a stable SPDX identifier in `LICENSE`.
- `MAINTAINERS.md` officially opens (see "Path to becoming a Maintainer").

## Non-goals

These are explicitly out of scope. Listing them here prevents scope creep.

- A central server, an account system, or any kind of telemetry.
- A general-purpose P2P energy trading simulator decoupled from the agent.
- A standalone LLM that we ship ourselves. We are a client of upstream providers; we never vendor a model runtime.
- A web framework swap. The Vue 3 + Vite + Tauri stack is the line; we will not migrate to React, Svelte, or Solid.
- A real-time dashboard. The Agent is research software, not an operations console.
- A multi-tenant workspace. Each install has one workspace, one user, one set of runs.

## Tracking

This document is updated as milestones land. The authoritative list of what *is* in a release lives in `CHANGELOG.md`.
