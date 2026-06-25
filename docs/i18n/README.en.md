# Energy Trading Lab (English)

> Research Simulation and Experiment Generation Agent for Energy Trading. P2P energy trading is the first concrete research scenario.

Energy Trading Lab is a vertical AI Agent built for the **AI Agent Application Engineer** resume line. The MVP uses P2P energy trading as the demo entry point, focused on two recurring pain points in energy-trading research:

- Journal papers rarely publish the code. Reproducing them is a long, manual effort.
- Once a researcher has a new theory, scaffolding an IEEE 33/69 test case from scratch is tedious.

The Agent implements a full research loop: paper / theory input → RAG-based domain extraction → strategy family classification → reproduction gap analysis → IEEE 33/69 experiment config generation → traditional algorithm and lightweight RL strategy comparison → distribution power-flow risk validation → research report. With an LLM API key configured, the structured paper-understanding step uses an OpenAI-compatible LLM; without one, it falls back to a deterministic heuristic so the demo runs offline.

Every paper or theory draft produces a dedicated `runs/{run_id}/code_project/` with its own `configs/`, `src/energy_project/`, `tests/`, and `outputs/`. It is not a saved script — it is a real, runnable, smoke-testable project directory.

## Quick Start

```bash
source .venv/bin/activate
python -m p2plab.cli demo --grid-case ieee33 --experiment-depth quick
python -m p2plab.cli reproduce --input examples/sample_paper.md --grid-case ieee33 --experiment-depth research
python -m p2plab.cli theory --input examples/theory_draft.md --grid-case ieee69 --experiment-depth research
```

Start the local product workspace:

```bash
source .venv/bin/activate
python -m p2plab.cli serve --port 8765
```

Open <http://127.0.0.1:8765>.

## Experiment Depth

The web UI defaults to `Research`, not a 5-second demo:

| Depth | Horizon | RL episodes | Use case |
| --- | --- | --- | --- |
| `quick` | 48 hours | 100 | Interview-room demo; confirms the end-to-end loop |
| `research` | 168 hours | 3000 | Default product experience; real script generation, subprocess execution, RL training |
| `deep` | 336 hours | 12000 | Long-horizon validation, demo recording, offline experiments |

Every run writes `generated_experiment_attempt_*.py`, `execution_log_attempt_*.txt`, `training_curve_attempt_*.json`, and the final `training_curve.csv`. The Agent Trace in the web UI shows `strategy_start`, `training_progress`, and `strategy_done` events with the live episode count.

## LLM API Configuration

Real paper understanding needs an LLM. ETL supports OpenAI-compatible Chat Completions:

```bash
source .venv/bin/activate
export ENERGY_LAB_LLM_API_KEY="your-key"
export ENERGY_LAB_LLM_BASE_URL="https://api.openai.com/v1"
export ENERGY_LAB_LLM_MODEL="gpt-4o-mini"
export ENERGY_LAB_LLM_TEMPERATURE="0.1"
export ENERGY_LAB_LLM_MAX_TOKENS="2500"
python -m p2plab.cli serve --port 8765
```

The endpoint is OpenAI-compatible, so DeepSeek / Qwen / Moonshot / Kimi also work — just swap `BASE_URL` and `MODEL`. See `docs/llm-adapters.md` for the full provider list and the BYOK priority.

The top of the web UI shows:

- `LLM gpt-4o-mini` — LLM is active.
- `LLM fallback` — no API key, the heuristic fallback is in use.

The CLI and the report's `analysis_meta.json` carry the same provenance.

## What the Agent Generates

Each run writes to `runs/{task_id}/`:

- `model_spec.json`
- `strategy_spec.json`
- `reproduction_gaps.md`
- `experiment_config.yaml`
- `metrics.json`
- `hourly_metrics.csv`
- `training_curve.csv`
- `agent_trace.json`
- `innovation_spec.json`
- `analysis_meta.json`
- `execution_summary.json`
- `generated_experiment_attempt_*.py`
- `training_curve_attempt_*.json`
- `execution_log_attempt_*.txt`
- `run_report.md`
- `code_project/README.md`
- `code_project/configs/experiment_config.json`
- `code_project/configs/smoke_config.json`
- `code_project/src/energy_project/adapter.py`
- `code_project/src/energy_project/run_experiment.py`
- `code_project/src/energy_project/generated_attempt.py`
- `code_project/tests/test_smoke.py`

The dedicated code project is runnable on its own:

```bash
cd runs/{run_id}/code_project
python src/energy_project/run_experiment.py --config configs/experiment_config.json --output-dir outputs/research
python -m unittest discover -s tests
```

## Implemented Agent Capabilities

- **Paper-to-Reproduction**: upload or paste a P2P energy trading paper, get a structured reproduction experiment package.
- **Theory-to-Experiment**: paste a Chinese theory draft, get 3 experiment hypotheses and runnable experiments.
- **Strategy classification**: RL / MARL, Optimization, Auction, Game Theory, Rule-based.
- **Traditional baselines**: `no_trading`, `rule_double_auction`, `optimization_clearing`.
- **RL baseline**: lightweight Q-learning-style bidding for local demo.
- **Proposed method**: voltage / carbon-aware bidding variants in the theory flow.
- **Paper-specific algorithm generation**: the classic algorithm is morphed with paper-specific parameters and reward / objective combos.
- **LLM structured analysis**: with an API key, an OpenAI-compatible LLM extracts model, algorithm, innovations, gaps, hypotheses.
- **Generated-code execution**: every run saves the generated script, the config, the log, the metrics — not an opaque in-memory call.
- **Dedicated code project**: per-paper / per-idea `code_project/` with adapter, configs, runner, smoke test, output dir.
- **Streaming training progress**: Research / Deep mode streams episode progress and saves the training curve.
- **IEEE 33 / 69 support**: IEEE 33 uses Baran-Wu style data; IEEE 69 uses a built-in swappable radial feeder.
- **Agent trace**: every step, every tool call, every input / output summary, every status flag.
- **Portfolio eval**: batch stats for success rate, latency, artifact completeness, strategy coverage.

## Portfolio Mapping

Resume project name:

**Energy Trading Lab: A research simulation experiment agent for energy trading**

Resume description:

Built a vertical research simulation experiment agent on Python, OpenAI-compatible LLM APIs, and Agent tool-use primitives. Supports energy-trading paper parsing, strategy-type identification, reproduction gap analysis, IEEE 33/69 bus experiment config generation, RL vs traditional trading algorithm comparison, distribution power-flow validation, and research report generation. Designed a multi-step Agent graph with task planning, tool calling, structured output, experiment log memory, failure diagnosis, and auto-repair. Used an evaluation suite to track extraction accuracy, experiment success rate, average response latency, and call cost.

## Project Structure

See `AGENTS.md` for the full directory guide. The plugin surfaces are:

- `p2plab/algorithm_templates/<family>/<name>/` — drop in a new algorithm (one folder, see `docs/skills-protocol.md`).
- `scenarios/<grid>/` — drop in a new grid case (one folder, see `docs/scenarios-protocol.md`).
- `p2plab/llm_adapters/` — add a new LLM provider (one Python file, see `docs/llm-adapters.md`).

## License

Apache 2.0. See `LICENSE`.
