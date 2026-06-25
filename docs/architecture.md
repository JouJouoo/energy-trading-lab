# Energy Trading Lab Architecture

> This document is the canonical runtime topology and data-flow reference. It complements `docs/spec.md` (the *why*) and `docs/skills-protocol.md` / `docs/scenarios-protocol.md` / `docs/llm-adapters.md` (the *how to extend*).

## 1. Three deployment topologies

ETL ships in three shapes. The same web bundle, the same artifact trail, the same `p2plab` CLI; the difference is which transports are enabled.

### Topology A — Fully local (the default)

```
┌─────────────────── user's machine ──────────────────┐
│                                                     │
│   browser ──► FastAPI + Uvicorn (127.0.0.1:8765)   │
│                  │                                  │
│                  │  /api/* + static frontend         │
│                  ▼                                  │
│            P2PLabAgent (in-process)                 │
│                  │                                  │
│                  ▼                                  │
│            spawns: generated_experiment_attempt_*.py│
│                                                     │
│            artifacts ──► data/runs/<run_id>/        │
│            metadata  ──► data/db.sqlite             │
└─────────────────────────────────────────────────────┘
```

One `python -m p2plab.cli serve` starts the whole stack. Zero external services. The LLM, if used, is the only outbound call.

### Topology B — Tauri desktop

```
┌───────────── user's machine ──────────────┐
│                                           │
│   Tauri webview ──► 127.0.0.1:8765/api/*  │
│   (window)              │                 │
│                         ▼                 │
│                  same P2PLabAgent         │
│                         │                 │
│                         ▼                 │
│                  same data/runs/,         │
│                  same data/db.sqlite      │
└───────────────────────────────────────────┘
```

Tauri ships the same Vue 3 frontend in a desktop window, talks to the same FastAPI server, writes to the same `data/` directory. Use this when you want a single-click desktop app.

### Topology C — Docker Compose

```
┌───────────── user's machine ──────────────┐
│                                           │
│   browser ──► docker container :8765      │
│                                           │
│   container:                              │
│     FastAPI + Uvicorn                     │
│     P2PLabAgent                           │
│                                           │
│   volume mounts:                          │
│     ./data ──► /app/data                  │
│     ./runs ──► /app/runs (legacy)         │
└───────────────────────────────────────────┘
```

See `deploy/README.md` for the docker-compose commands. Use this when you want a self-contained environment that survives `pip` upgrades on the host.

## 2. Component diagram (logical)

```
┌────────────────────────── Web App (Vue 3 + Vite) ──────────────────────────┐
│                                                                            │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌─────────────────┐       │
│  │ workspace│  │ experiment   │  │ plugin    │  │ markdown viewer │       │
│  │ view     │  │ view         │  │ view      │  │ + chart         │       │
│  └────┬─────┘  └──────┬───────┘  └─────┬─────┘  └────────┬────────┘       │
│       │               │                │                  │               │
│       └───────────── HTTP client (api/client.js) ─────────┘               │
│                                │                                          │
└────────────────────────────────┼──────────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────── FastAPI + Uvicorn (p2plab/api) ────────────────────┐
│                                                                            │
│  /api/health    /api/llm-status   /api/runs   /api/upload                  │
│  /api/jobs/*    /api/workspace/*  /api/reproduce /api/theory                │
│  /api/paper2code /api/plugins/algorithms /api/plugins/scenarios            │
│                                                                            │
│  ┌────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────────┐        │
│  │ Workspace  │  │ Job queue    │  │ LLM router │  │ Plugin       │        │
│  │ manager    │  │ (in-memory)  │  │ (adapters) │  │ loader       │        │
│  └──────┬─────┘  └──────┬───────┘  └──────┬─────┘  └──────┬───────┘        │
│         │               │                 │                 │              │
│         └────── P2PLabAgent (p2plab/agent.py) ─────┬───────┘              │
│                                                       │                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │                     │
│  │ RAG          │  │ Code         │  │ Simulation   │ │                     │
│  │ (rag.py)     │  │ generator    │  │ kernel       │ │                     │
│  │              │  │ (executor)   │  │ (simulation) │ │                     │
│  └──────────────┘  └──────┬───────┘  └──────────────┘ │                     │
│                            │                          │                     │
│                            ▼                          │                     │
│              spawns: generated_experiment_*.py        │                     │
│                            │                          │                     │
└────────────────────────────┼──────────────────────────┼─────────────────────┘
                             │                          │
                             ▼                          ▼
              ┌─────────────────────┐    ┌────────────────────────┐
              │ filesystem          │    │ data/db.sqlite         │
              │ data/runs/<run_id>/ │    │ projects, jobs,        │
              │  + code_project/    │    │ settings, metrics      │
              │  + metrics.json     │    │                        │
              │  + hourly_*.csv     │    │                        │
              │  + training_*.json  │    │                        │
              │  + run_report.md    │    │                        │
              └─────────────────────┘    └────────────────────────┘
```

## 3. Key components

### 3.1 Web app (Vue 3, Vite, Tauri)

- **Why Vue 3 + Vite?** SPA-grade reactivity, fast dev cycle, and the Tauri desktop shell is a thin wrapper. The web bundle is also served as static files by the FastAPI app, so the user never needs `npm run dev` for the bundled frontend.
- **State**: `ref` + `reactive` for UI config; the workspace view, experiment view, and plugin view hydrate from the FastAPI endpoints.
- **Charts**: Chart.js + vue-chartjs for the strategy comparison and training-curve plots. See `web/src/components/MetricsChart.vue`.
- **Markdown**: `marked` for the report preview, sanitized at the markdown-viewer level.

### 3.2 FastAPI + Uvicorn (`p2plab/api/fastapi_server.py`)

- Single process; long-running; one P2PLabAgent per process.
- CORS is wide open in dev (`allow_origins=["*"]`); tighten in production via a reverse proxy.
- The `JOBS` dict is in-memory; the `WorkspaceManager` is SQLite-backed. A future Redis-backed job queue is on the 0.4.x roadmap.

### 3.3 P2PLabAgent (`p2plab/agent.py`)

- Three pipelines: `run_paper_reproduction`, `run_theory_experiment`, `run_paper_to_code`. They share a `_run_pipeline` core.
- The agent emits a `TraceEvent` at every step. The events are streamed to the web UI via the in-memory job queue; the CLI gets them synchronously.
- The orchestrator is deterministic Python. A LangGraph port is on the 0.5.x roadmap (see `docs/roadmap.md`).

### 3.4 Plugin loader (`p2plab/plugin_loader.py`)

- `discover_algorithm_templates(roots)` and `discover_scenarios(roots)` scan the configured roots at startup.
- Merge order: user-global (`~/.energy_trading_lab/...`) > user-data (`$ENERGY_LAB_DATA_DIR/...`) > built-in (`p2plab/algorithm_templates/`, `scenarios/`).
- The discovery result is cached per process; restart the daemon to pick up new plugins.

### 3.5 LLM router (`p2plab/llm_adapters/router.py`)

- One entry point: `resolve_adapter(provider, request_config)`.
- BYOK priority: `request_config["api_key"]` > `os.environ["ENERGY_LAB_LLM_API_KEY"]` > `data/db.sqlite` persisted setting.
- 5 built-in adapters (OpenAI, DeepSeek, Qwen, Moonshot, Custom). See `docs/llm-adapters.md`.

### 3.6 Simulation kernel (`p2plab/simulation.py`)

- Pure functions of the `ExperimentRecipe`. Deterministic given the seed.
- The 4 baseline strategies (`no_trading`, `rule_double_auction`, `optimization_clearing`, `rl_bidding`) plus the per-paper `proposed_method` are all built on the same `step(market_state, action) -> (next_state, reward)` interface.
- Training progress is emitted via the `ETL_PROGRESS` stdout protocol; the executor parses it and forwards it to the job queue.

### 3.7 Storage

- **Artifacts**: `data/runs/<run_id>/` (per-run files: `model_spec.json`, `experiment_config.yaml`, `metrics.json`, `hourly_metrics.csv`, `training_curve.csv`, `agent_trace.json`, `run_report.md`, `code_project/`, `generated_experiment_attempt_*.py`, `execution_log_attempt_*.txt`).
- **Metadata**: `data/db.sqlite` (`projects`, `project_artifacts`, `project_metrics`, `settings`).
- **Caches**: `data/cache/` (reserved for future LLM response caching and embedding caches).
- The exact contract is in `AGENTS.md` §"Data directory contract".

## 4. Data flow — a typical "reproduce a paper" turn

```
1. User pastes paper text + clicks "Run Agent" in the web UI.
2. The web client POSTs to /api/jobs with { mode: "reproduce", text, grid_case, experiment_depth, llm_config }.
3. FastAPI enqueues the job in JOBS[job_id] and starts a background task.
4. P2PLabAgent.run_paper_reproduction:
     a. retrieve_domain_context ──► rag.py:KeywordRetriever
     b. extract_model_spec ──► rag.py:extract_model_spec
     c. classify_strategy_family ──► rag.py:classify_strategy_family
     d. extract_innovation_spec ──► rag.py:extract_innovation_spec
     e. detect_reproduction_gaps ──► rag.py:detect_reproduction_gaps
     f. generate_hypotheses ──► rag.py:generate_hypotheses
     g. (optional) LLM refinement via llm_adapters/router.py
     h. build_recipe ──► agent.py:_build_recipe
     i. run_generated_experiment(attempt=1) ──► executor.py
        - writes generated_experiment_attempt_1.py + experiment_config_attempt_1.json
        - spawns subprocess; stdout ETL_PROGRESS lines are forwarded to on_event
        - reads metrics_attempt_1.json, hourly_metrics_attempt_1.json, training_curve_attempt_1.json
     j. (if needed) run_generated_experiment(attempt=2) with the optimized recipe
     k. run_simulation / run_power_flow_validation ──► simulation.py + grid.py
     l. analyze_results, write_report ──► reporting.py
5. Every step emits a TraceEvent; the events are appended to JOBS[job_id]["events"] and polled by the web client.
6. On completion, the run's metadata (title, source_type, best_strategy, llm_model) is upserted into data/db.sqlite by WorkspaceManager.finish_job.
7. The web UI shows the metrics table, the agent trace timeline, the strategy comparison chart, and the rendered Markdown report.
```

## 5. CLI parity (dual-track)

Every user-facing capability is also a CLI subcommand. See `AGENTS.md` §"Capability exposure". The CLI subcommands call the same internal helpers as the FastAPI endpoints; the FastAPI HTTP layer is a thin wrapper.

```
$ python -m p2plab.cli workspace-list --json | jq '.[0].run_id'
"paper_20250624_xxx"

$ curl -s http://127.0.0.1:8765/api/workspace/projects | jq '.projects[0].run_id'
"paper_20250624_xxx"
```

The two outputs match. `tests/test_cli_parity.py` enforces this.

## 6. Config files

| File | Purpose |
|---|---|
| `p2plab/algorithm_templates/<family>/<name>/TEMPLATE.md` | Algorithm manifest (see `docs/skills-protocol.md`) |
| `scenarios/<grid>/SCENARIO.md` + `feeder.json` | Scenario manifest (see `docs/scenarios-protocol.md`) |
| `p2plab/llm_adapters/<provider>_adapter.py` | LLM adapter (see `docs/llm-adapters.md`) |
| `.env.example` | Sample environment variables |
| `data/db.sqlite` | Workspace metadata, jobs, settings |

Data directory paths are governed only by `AGENTS.md` §"Data directory contract". Do not add config-path examples here.

## 7. Protocol between web and FastAPI

Representative API surface:

```
GET    /api/health
GET    /api/llm-status
GET    /api/runs
GET    /api/workspace/projects
GET    /api/workspace/projects/{run_id}
GET    /api/workspace/projects/{run_id}/metrics
GET    /api/workspace/projects/{run_id}/trace
GET    /api/workspace/projects/{run_id}/report
GET    /api/workspace/projects/{run_id}/artifact/{artifact_name}
DELETE /api/workspace/projects/{run_id}
POST   /api/upload
POST   /api/extract-document
POST   /api/jobs                → returns { job_id, status: "queued" }
GET    /api/jobs/{job_id}       → returns status + events
POST   /api/reproduce           → synchronous, returns summarize_result
POST   /api/theory              → synchronous, returns summarize_result
POST   /api/paper2code          → synchronous, returns the assembled project
GET    /api/plugins/algorithms  → list discovered algorithm templates
GET    /api/plugins/scenarios   → list discovered scenarios
```

`GET /docs` (Swagger) is the live API contract. `summarize_result` is the canonical shape returned by the synchronous endpoints.
