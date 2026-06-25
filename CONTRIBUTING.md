# Contributing to Energy Trading Lab

Thanks for thinking about contributing. ETL is small on purpose — most of the value lives in **files** (algorithm templates, scenarios, LLM adapters) rather than framework code. That means the highest-leverage contributions are usually one folder, one Markdown file, or one Python file.

This guide tells you exactly where to look for each type of contribution and what bar a PR has to clear before we merge it.

## Three things you can ship in an afternoon

| If you want to… | You're really adding | Where it lives | Ship size |
|---|---|---|---|
| Make ETL ship a new algorithm (DQN, PPO, MARL, …) | an **Algorithm template** | `p2plab/algorithm_templates/<family>/<name>/` | one folder, ~2 files |
| Make ETL support a new grid (IEEE 123, custom feeder) | a **Scenario** | `scenarios/<grid>/` | one folder, ~2 files |
| Hook up a new LLM host (Anthropic, GLM, etc.) | an **LLM adapter** | `p2plab/llm_adapters/<provider>_adapter.py` | one Python file + one router entry |
| Add a new CLI subcommand | a CLI surface | `p2plab/cli.py` | a few lines |
| Improve docs, port a section to English, fix typos | docs | `README.md`, `docs/`, `docs/i18n/` | one PR |

If you're not sure which bucket your idea is in, open an issue first and we'll point you at the right surface.

## Local setup

The full one-page setup lives in [`QUICKSTART.md`](QUICKSTART.md). The TL;DR for contributors:

```bash
git clone https://github.com/JouJouoo/energy-trading-lab.git
cd energy-trading-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m p2plab.cli serve --port 8765   # daemon
pytest tests/                              # unit tests
```

Python 3.9+ is required. The web frontend is bundled into the FastAPI app; you only need `npm` if you want to run the Tauri desktop shell.

## Adding a new Algorithm template

An algorithm template is a folder under `p2plab/algorithm_templates/<family>/<name>/` with a `TEMPLATE.md` (or `.yaml`) at the root. **No registration step.** Drop the folder in, restart the daemon, it shows up.

### Folder layout

```
p2plab/algorithm_templates/RL/dqn/
├── TEMPLATE.md        # required, manifest
├── dqn.py             # required, implementation
└── tests/
    └── dqn_smoke.py   # optional, smoke test
```

### `TEMPLATE.md` shape

The full spec is in [`docs/skills-protocol.md`](docs/skills-protocol.md). The minimum:

```markdown
---
name: dqn
family: RL
display_name: Deep Q-Network Bidding
file_name: dqn.py
description: |
  Lightweight DQN bidding baseline using PyTorch-free dense layers.
  Replaces the Q-table with a 2-layer MLP and an epsilon-greedy policy.
affected_modules: [reward.py, agent.py]
parameters:
  epsilon: 0.18
  hidden_dim: 32
  batch_size: 16
tags: [rl, neural]
---

# Deep Q-Network Bidding

> Family: RL
> Use when: a single-agent DQN bidding baseline is required and the Q-table is too small.

## 1. Inputs
…

## 2. Outputs
…
```

### Bar for merging

1. `TEMPLATE.md` parses cleanly (use `tests/test_plugin_manifest.py` to assert).
2. `<name>.py` exposes the contract documented in `docs/skills-protocol.md` §3 (entry point signature).
3. The Agent's `reproduce` flow can select this template without code changes in `code_generator.py`.
4. A short smoke test exists (or one is added) and `pytest tests/ -k <name>` passes.

## Adding a new Scenario

A scenario is a folder under `scenarios/<grid>/` with a `SCENARIO.md` + `feeder.json`. **One folder, no code change in `grid.py`.**

### Folder layout

```
scenarios/ieee123/
├── SCENARIO.md        # required, 9-section manifest
├── feeder.json        # required, bus/line/load data
└── prosumer_layout.json  # optional, default prosumer placement
```

### `SCENARIO.md` shape

The full spec is in [`docs/scenarios-protocol.md`](docs/scenarios-protocol.md). The minimum 9 sections:

1. Network topology
2. Bus types
3. Voltage base & limits
4. Line parameters
5. Load / PV profile source
6. Prosumer injection mapping
7. Constraints & violations
8. Output metrics
9. Anti-patterns

### Bar for merging

1. All 9 sections present. Empty section bodies are fine for hard-to-find data, but headings must be there.
2. `feeder.json` parses and the Agent's `reproduce` flow can select this scenario without code changes in `grid.py`.
3. `python -c "from p2plab.plugin_loader import discover_scenarios; print(discover_scenarios())"` lists the new scenario.

## Adding a new LLM provider

A provider is a Python file under `p2plab/llm_adapters/<provider>_adapter.py` plus one entry in the `_REGISTRY` inside `p2plab/llm_adapters/router.py`. See [`docs/llm-adapters.md`](docs/llm-adapters.md) for the interface.

### Bar for merging

1. Adapter passes `pytest tests/test_llm_adapters.py -k <provider>`.
2. Adapter gracefully handles a missing API key (returns the same fallback shape as the heuristic).
3. The `docs/llm-adapters.md` provider table gets one row.

## Code style

We're not pedantic about formatting, but two rules are non-negotiable:

1. **English in code comments.** Even if the PR is translating UI to 中文, code comments stay in English so we can keep one set of greppable references.
2. **Type hints everywhere.** Python 3.9+ syntax (use `from __future__ import annotations` and `list[str]`/`dict[str, str]` style is fine).

Beyond that:

- **Don't narrate.** No `# import the module`, no `# loop through items`. If the code reads obviously, the comment is noise. Save comments for non-obvious intent or constraints the code can't express.
- **No new top-level dependencies** without a paragraph in the PR description on what we get vs. what bytes we ship.
- **Run `pytest tests/`** before pushing. CI runs it; failing it earns a "please fix" comment.
- **Don't add backwards-compat shims** for removed code; we delete cleanly.

## Commits & pull requests

- **One concern per PR.** Adding an algorithm + refactoring the parser + bumping a dep is three PRs.
- **Title is imperative + scope.** `add dqn algorithm template`, `fix agent SSE backpressure when CLI hangs`, `docs: clarify storage contract`.
- **Use the PR template** at [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md). Fill every section — Why, What users will see, Surface area, Tests, Bug fix verification (if bug fix). Empty sections earn a "please fill in" reply.
- **Body explains the why.** "What does this do" is usually obvious from the diff; "why does this need to exist" rarely is.
- **Reference an issue** if there is one. If there isn't and the PR is non-trivial, open one first.
- **No squash-during-review.** Push fixups; we'll squash on merge.

## Reporting bugs

Open an issue with:

- What you ran (the exact `python -m p2plab.cli ...` invocation).
- Which mode was selected (`reproduce`, `theory`, `paper2code`, `serve`).
- The relevant **backend stderr tail** — most "the artifact never showed up" reports get diagnosed in 30 seconds when we can see the actual error.
- The output of `python -c "from p2plab.plugin_loader import discover_algorithm_templates, discover_scenarios; print(discover_algorithm_templates()); print(discover_scenarios())"` if the bug is plugin-related.
- A screenshot if it's UI.

## Becoming a Maintainer

This project is currently maintained by a single contributor. Once 1.0.0 is cut, the maintainer program will move to [`MAINTAINERS.md`](MAINTAINERS.md). Until then, the bar is "ship three merged PRs, with at least one of them being a non-trivial feature." Track your progress in your own fork's issues; we'll notice.

The tl;dr: ship good PRs, review thoughtfully, and we'll talk.
