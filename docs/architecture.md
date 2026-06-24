# Energy Trading Lab Architecture

Energy Trading Lab is a vertical Agent product for energy-trading research simulation and reproduction. The MVP uses P2P energy trading as the first concrete research scenario.

## Agent graph

```text
ingest_input
  -> retrieve_domain_context
  -> extract_model_spec
  -> classify_strategy_family
  -> detect_reproduction_gaps
  -> design_experiment
  -> generate_config
  -> select_strategy_template
  -> generate_or_patch_code
  -> run_simulation
  -> run_power_flow_validation
  -> inspect_logs
  -> repair_once
  -> analyze_results
  -> write_report
```

The MVP implements this graph as deterministic Python tools so the portfolio demo runs without an API key.
The production upgrade path is to swap the orchestration layer with LangGraph nodes while keeping the same tool
interfaces and artifacts.

## Tool families

- RAG tools: paper chunking, keyword retrieval, strategy/context extraction.
- Experiment design tools: `P2PModelSpec`, `StrategySpec`, `ExperimentRecipe`, `ReproductionGap`.
- Simulation tools: no trading, rule double auction, optimization clearing, RL bidding, proposed method.
- Grid validation tools: IEEE 33/69 feeder loading, voltage risk, loss, violation count.
- Report tools: Markdown reports, CSV hourly metrics, JSON trace.
