# Spec — Design rationale for Energy Trading Lab

This document captures the **why** behind the project's structural choices. The "how" lives in `docs/architecture.md`; the "how to extend" lives in `docs/skills-protocol.md`, `docs/scenarios-protocol.md`, and `docs/llm-adapters.md`. Read this first if you're going to make a non-trivial change.

## 1. The product is an Agent, not a script

ETL started as a deterministic Python pipeline (`p2plab/cli.py` + `p2plab/agent.py`) for two reasons: it makes the demo runnable without an API key, and it makes the artifact trail auditable. The two-pipeline structure (paper → reproduction, theory → experiment) is the agent's "graph" — the same shape that a LangGraph runtime would execute, but with every step spelled out as a Python function.

The non-negotiable is that **the agent's behavior is reproducible from the artifacts on disk**: given a run directory, you can re-derive the model spec, the strategy classification, the innovation spec, the experiment recipe, the metrics, and the report. That is the "agent" half of "AI Agent application engineer".

The negotiable is the *runtime* — we can swap the deterministic Python for LangGraph or a state machine later, and the artifact trail still tells the same story.

## 2. Local-first, with an LLM BYOK hinge

The LLM is a hinge, not a backbone. The whole pipeline runs without an API key (heuristic fallback), and the LLM only changes the structured extraction step. This is intentional: it lets the project ship a working demo in any environment, and it keeps the user in control of their prompts and tokens.

The adapter pool (`p2plab/llm_adapters/`) is the seam where the hinge attaches. Adding a provider is a single file plus a router entry. We will never vendor a model runtime; we will never proxy through a central server.

## 3. Plugin-first, by way of files

The product's value is in the **domain knowledge**: which algorithm fits which paper, which grid case fits which scenario, which LLM provider fits which user. Encapsulating that knowledge in files (one folder = one algorithm, one folder = one scenario) is more honest than hiding it in a registry.

This is the same lesson the open-design project learned with `skills/` and `design-systems/`. A `TEMPLATE.md` next to `<name>.py` is greppable, diffable, and PR-friendly. A `SCENARIO.md` next to `feeder.json` is the contract the Agent consults before running an experiment.

The plugin system is not an afterthought — it is the primary surface for contribution. See `CONTRIBUTING.md` for the "three things you can ship in an afternoon" table.

## 4. Dual-track capability exposure

Every user-facing capability must be reachable through both the web UI **and** the `p2plab` CLI. This is the discipline that keeps the project embeddable. The CLI is the contract for external scripts, CI jobs, and operator workflows. The web UI is the contract for human users. Both call the same backend logic.

When we add an endpoint, we add the matching CLI subcommand. When we add a CLI subcommand, we add a UI button (or expose it via the workspace view). The FastAPI HTTP layer is the single source of truth for both.

## 5. Artifacts, not databases

We use SQLite for **metadata** (project list, jobs, settings) and the filesystem for **artifacts** (code, logs, metrics, reports). This is the same trade-off that `git`, `docker`, and the `npm` registry made: the artifacts are plain files, so you can `grep`, `diff`, and `tar` them. The database is a cache, not a source of truth.

`data/db.sqlite` is reproducible from the filesystem on a cold rebuild. The runs directory is reproducible from the agent trace + LLM responses (modulo non-deterministic environments).

## 6. Determinism where it matters

The simulation kernel (`p2plab/simulation.py`) is seeded. The LLM step is not, but the heuristic fallback is. The generated experiment scripts are pure functions of the recipe. This is the layer cake that makes the Agent's behavior explainable.

## 7. What we are not trying to be

- We are not a generic P2P energy trading simulator. We are an agent that produces reproducible experiments for energy trading research.
- We are not a UI for tweaking algorithm parameters. We are an agent that picks and configures algorithms based on a paper or theory.
- We are not a multi-tenant SaaS. We are a local-first tool that happens to expose a web UI for convenience.
- We are not a closed system. The plugin surfaces (`algorithm_templates/`, `scenarios/`, `llm_adapters/`) are the public contribution API.

## 8. What we are trying to be

A vertical AI Agent for energy trading research that:

- Reads a paper or a theory draft.
- Identifies the algorithm family, the baselines, the innovation.
- Generates an experiment package (config, code, run script, smoke test).
- Executes the experiment, validates the result, repairs the code if needed.
- Writes a Markdown report and a CSV metrics trail.
- Ships a `code_project/` the user can run independently.

That is the product. Everything else — the docs matrix, the plugin system, the LLM adapter pool, the CLI parity — exists to make that product easier to extend and easier to ship.
