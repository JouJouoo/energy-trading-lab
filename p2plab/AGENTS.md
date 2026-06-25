# p2plab/ — Python backend

> This is the Python backend. Read this file before editing any module under `p2plab/`.

## Module map

```
p2plab/
├── __init__.py
├── __main__.py             # python -m p2plab entry
├── cli.py                  # argparse, all subcommands
├── agent.py                # P2PLabAgent, 3 pipelines
├── api.py                  # legacy http.server (kept for compat)
├── server.py               # legacy http.server entry
├── code_generator.py       # CodeGenerator, uses plugin_loader
├── executor.py             # subprocess runner, ETL_PROGRESS protocol
├── eval.py                 # portfolio evaluation runner
├── grid.py                 # IEEE 33/69 in-source fallback (deprecated; see scenarios/)
├── llm.py                  # back-compat shim → llm_adapters/router
├── llm_analysis.py         # fallback_*_innovation, fallback_payload
├── memory.py               # JsonlMemoryStore
├── module_validator.py     # generated-module AST validator
├── project_assembler.py    # assembles the standalone code_project/
├── project_builder.py      # writes the per-run code_project/
├── rag.py                  # KeywordRetriever, extract_* helpers
├── reporting.py            # run_report + gap_report renderers
├── schemas.py              # dataclasses shared by the agent + CLI + HTTP
├── simulation.py           # default_recipe, run_experiment_detailed
├── database.py             # SQLite, projects + settings tables
├── document_loader.py      # PDF / TXT / Markdown parser
├── utils.py                # ensure_dir, write_json, write_text, simple_yaml
├── api/
│   ├── __init__.py
│   ├── fastapi_server.py   # the live HTTP server
│   ├── workspace.py        # WorkspaceManager
│   └── logging.py          # setup_logging
├── llm_adapters/           # provider adapter pool
│   ├── __init__.py
│   ├── base.py             # BaseLLMAdapter
│   ├── openai_adapter.py
│   ├── deepseek_adapter.py
│   ├── qwen_adapter.py
│   ├── moonshot_adapter.py
│   ├── custom_adapter.py
│   ├── router.py           # resolve_adapter(...)
│   └── exceptions.py
├── plugin_manifest.py      # AlgorithmTemplate, ScenarioSpec dataclasses
├── plugin_loader.py        # discover_algorithm_templates, discover_scenarios
└── algorithm_templates/    # drop-in algorithm plugins
    ├── Base/
    ├── RL/
    ├── Optimization/
    ├── Auction/
    └── GameTheory/
```

## Conventions

- All new modules start with `from __future__ import annotations`.
- All public dataclasses are in `schemas.py`; do not re-declare them in sub-modules.
- All filesystem paths come from `p2plab/api/fastapi_server.py:get_data_root()` (or a helper derived from it). Do not hard-code `runs/`, `./runs`, `data/`, or any path.
- All LLM calls go through `p2plab.llm_adapters.router.resolve_adapter(...)`. Do not import vendor SDKs directly.
- Algorithm templates and scenarios are loaded through `p2plab.plugin_loader`; do not `import` them statically from another `p2plab/` module.

## Testing

- Unit + integration tests live under `tests/` (see `tests/AGENTS.md`).
- The plugin manifest test (`tests/test_plugin_manifest.py`) iterates every discovered template / scenario and asserts the manifest is valid. CI runs it on every PR.
- The LLM adapter test (`tests/test_llm_adapters.py`) mocks the upstream and asserts the router dispatches correctly.
- The CLI parity test (`tests/test_cli_parity.py`) spins up a FastAPI app + a CLI subprocess and asserts the outputs match.
