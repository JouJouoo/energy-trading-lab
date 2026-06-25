# Energy Trading Lab

> **Research Simulation and Experiment Generation Agent for Energy Trading.**

Energy Trading Lab is a vertical AI Agent that turns an energy-trading paper or a researcher's theory draft into a runnable, validated, documented experiment — and ships the experiment as a standalone `code_project/` the user can keep working on.

## Quick start

```bash
source .venv/bin/activate
python -m p2plab.cli serve --port 8765
# open http://127.0.0.1:8765
```

Full setup: [`QUICKSTART.md`](QUICKSTART.md).

## Languages

- [English](docs/i18n/README.en.md)
- [简体中文](docs/i18n/README.zh-CN.md)

## Documentation

- [`AGENTS.md`](AGENTS.md) — directory guide, data directory contract, dual-track rule.
- [`QUICKSTART.md`](QUICKSTART.md) — one-page local setup.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — "three things you can ship in an afternoon".
- [`CHANGELOG.md`](CHANGELOG.md) — what changed when.
- [`docs/spec.md`](docs/spec.md) — design rationale.
- [`docs/architecture.md`](docs/architecture.md) — runtime topology, data flow.
- [`docs/skills-protocol.md`](docs/skills-protocol.md) — algorithm template manifest spec.
- [`docs/scenarios-protocol.md`](docs/scenarios-protocol.md) — scenario manifest spec.
- [`docs/llm-adapters.md`](docs/llm-adapters.md) — LLM adapter interface.
- [`docs/roadmap.md`](docs/roadmap.md) — 0.2.x → 1.0.0 plan.
- [`docs/references.md`](docs/references.md) — reading list.
- [`docs/code-review-guidelines.md`](docs/code-review-guidelines.md) — PR bar.
- [`MAINTAINERS.md`](MAINTAINERS.md) — maintainer path.
- [`PRIVACY.md`](PRIVACY.md) — local-first, no telemetry.
- [`TRANSLATIONS.md`](TRANSLATIONS.md) — i18n rules.

## Project layout

```
p2plab/                    # Python backend
  api/                     # FastAPI server
  llm_adapters/            # LLM provider pool (OpenAI / DeepSeek / Qwen / Moonshot / Custom)
  algorithm_templates/     # drop-in algorithm plugins
  ...                      # agent, rag, executor, simulation, grid, ...
scenarios/                 # drop-in grid scenarios
  ieee33/
  ieee69/
  ieee123/                 # optional, demonstrates plugin extensibility
web/                       # Vue 3 + Vite + Tauri desktop shell
tests/                     # pytest suites
docs/                      # design docs, protocols, i18n
deploy/                    # Docker Compose
examples/                  # sample paper + theory draft
runs/                      # legacy run artifacts (deprecated; new runs live in data/runs/)
data/                      # SQLite + per-run artifacts (see AGENTS.md §Data directory contract)
```

## License

Apache 2.0. See [`LICENSE`](LICENSE).
