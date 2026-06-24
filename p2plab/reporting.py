from __future__ import annotations

from typing import Any, Iterable, List, Optional

from .schemas import (
    ExperimentRecipe,
    P2PModelSpec,
    ReproductionGap,
    ResearchHypothesis,
    SimulationMetrics,
    StrategySpec,
    TraceEvent,
    InnovationSpec,
)


def markdown_table(headers: List[str], rows: Iterable[List[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(lines)


def render_gap_report(gaps: List[ReproductionGap]) -> str:
    if not gaps:
        return "# Reproduction Gaps\n\nNo major gaps detected. Manual review is still recommended.\n"
    rows = [[gap.category, gap.severity, gap.evidence, gap.suggested_assumption] for gap in gaps]
    return "# Reproduction Gaps\n\n" + markdown_table(
        ["Category", "Severity", "Evidence", "Agent assumption"], rows
    ) + "\n"


def render_run_report(
    model: P2PModelSpec,
    strategies: List[StrategySpec],
    hypotheses: List[ResearchHypothesis],
    gaps: List[ReproductionGap],
    recipe: ExperimentRecipe,
    metrics: List[SimulationMetrics],
    trace: List[TraceEvent],
    innovation: Optional[InnovationSpec] = None,
    executions: Optional[List[Any]] = None,
    analysis_meta: Optional[dict] = None,
) -> str:
    metric_rows = []
    for item in metrics:
        metric_rows.append(
            [
                item.strategy,
                "%.3f" % item.total_cost,
                "%.2f%%" % item.cost_saving_pct,
                "%.3f" % item.p2p_volume_kwh,
                "%.3f" % item.grid_import_kwh,
                "%.3f" % item.carbon_kg,
                "%.3f" % item.social_welfare,
                "%.3f" % item.voltage_risk_score,
                item.grid_validation.voltage_violation_count,
                "%.4f" % item.grid_validation.min_voltage_pu,
                "%.3f" % item.grid_validation.network_loss_kwh,
                "%d / %.3fs" % (item.training_episodes, item.training_elapsed_sec) if item.training_episodes else "-",
            ]
        )
    strategy_rows = [
        [spec.family, spec.algorithm_name, "yes" if spec.is_baseline else "no", ", ".join(spec.decision_variables)]
        for spec in strategies
    ]
    hypothesis_rows = [
        [idx + 1, hyp.statement, hyp.independent_variable, ", ".join(hyp.validation_metrics)]
        for idx, hyp in enumerate(hypotheses)
    ]
    gap_rows = [[gap.category, gap.severity, gap.suggested_assumption] for gap in gaps]
    trace_rows = [[event.step, event.status, event.summary] for event in trace]
    execution_rows = []
    for item in executions or []:
        execution_rows.append(
            [
                item.attempt,
                item.status,
                "%.4fs" % item.elapsed_sec,
                item.repair_note or "initial generated experiment",
                item.script_path,
            ]
        )

    if metrics:
        best = min(metrics, key=lambda item: item.total_cost)
        conclusion = (
            "In this MVP scaffold, `%s` produced the lowest community cost. "
            "Results are generated from transparent synthetic profiles and should be treated as a reproducible starting point, "
            "not a numeric reproduction claim." % best.strategy
        )
    else:
        conclusion = "No simulation metrics were generated."

    return "\n\n".join(
        [
            "# Energy Trading Lab Research Report",
            "## Model Summary\n\n"
            + "\n".join(
                [
                    "- Title: %s" % model.title,
                    "- Research problem: %s" % model.research_problem,
                    "- Market mechanism: %s" % model.market_mechanism,
                    "- Grid constraints: %s" % ", ".join(model.grid_constraints),
                    "- Metrics: %s" % ", ".join(model.metrics),
                ]
            ),
            "## Experiment Recipe\n\n"
            + "\n".join(
                [
                    "- Grid case: %s" % recipe.grid_case,
                    "- Experiment depth: %s" % recipe.experiment_depth,
                    "- Horizon: %d hours" % recipe.horizon_hours,
                    "- Prosumers: %d" % recipe.prosumer_count,
                    "- Strategies: %s" % ", ".join(recipe.strategies),
                    "- Training episodes: %d" % recipe.training_episodes,
                    "- Training log interval: %d episodes" % recipe.training_log_interval,
                    "- Notes: %s" % recipe.notes,
                ]
            ),
            "## Analysis Source\n\n"
            + "\n".join(
                [
                    "- Source: %s" % ((analysis_meta or {}).get("analysis_source", "unknown")),
                    "- LLM enabled: %s" % ((analysis_meta or {}).get("llm_status", {}).get("enabled", False)),
                    "- LLM model: %s" % ((analysis_meta or {}).get("llm_status", {}).get("model", "")),
                    "- LLM error: %s" % ((analysis_meta or {}).get("llm_error", "") or "none"),
                ]
            ),
            "## Paper-Specific Algorithm Generation\n\n"
            + (
                "\n".join(
                    [
                        "- Innovation type: %s" % innovation.innovation_type,
                        "- Base algorithm: %s" % innovation.base_algorithm,
                        "- Reward/objective terms: %s" % ", ".join(innovation.custom_reward_terms),
                        "- Code modifications: %s" % "; ".join(innovation.code_modifications),
                        "- Strategy parameters: %s" % innovation.strategy_parameters,
                    ]
                )
                if innovation
                else "No innovation spec generated."
            ),
            "## Strategy Classification\n\n"
            + markdown_table(["Family", "Algorithm", "Baseline", "Decision variables"], strategy_rows),
            "## Research Hypotheses\n\n"
            + markdown_table(["#", "Hypothesis", "Variable", "Metrics"], hypothesis_rows),
            "## Reproduction Gaps\n\n"
            + (markdown_table(["Category", "Severity", "Agent assumption"], gap_rows) if gap_rows else "No major gaps detected."),
            "## Simulation Results\n\n"
            + markdown_table(
                [
                    "Strategy",
                    "Cost",
                    "Saving",
                    "P2P kWh",
                    "Grid import",
                    "Carbon kg",
                    "Welfare",
                    "Voltage risk",
                    "Voltage violations",
                    "Min V",
                    "Loss kWh",
                    "RL train",
                ],
                metric_rows,
            ),
            "## Strategy Notes\n\n"
            + "\n".join(["- `%s`: %s" % (item.strategy, item.strategy_explanation) for item in metrics]),
            "## Generated Code Execution\n\n"
            + (
                markdown_table(["Attempt", "Status", "Elapsed", "Repair/optimization note", "Script"], execution_rows)
                if execution_rows
                else "No generated-code execution record."
            ),
            "## Agent Trace\n\n" + markdown_table(["Step", "Status", "Summary"], trace_rows),
            "## Conclusion\n\n" + conclusion,
            "## Limitations\n\n"
            + "\n".join(
                [
                    "- IEEE 69 data is a transparent built-in approximation until replaced with the researcher's preferred standard table.",
                    "- Power-flow validation uses a fast DistFlow-style approximation unless pandapower integration is enabled.",
                    "- RL bidding is intentionally lightweight for local demo speed; it is a scaffold for deeper MARL methods.",
                    "- Generated experiments are reproduction packages, not claims of exact paper-number replication.",
                ]
            ),
        ]
    )
