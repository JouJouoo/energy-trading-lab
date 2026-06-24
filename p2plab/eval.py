from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any, Dict, List

from .agent import P2PLabAgent
from .cli import SAMPLE_PAPER, SAMPLE_THEORY
from .utils import ensure_dir, write_json, write_text


def run_eval(run_root: str = "runs", output_dir: str = "runs/eval") -> Dict[str, Any]:
    ensure_dir(output_dir)
    agent = P2PLabAgent(run_root=run_root)
    cases = [
        {"name": "paper_ieee33", "mode": "paper", "grid_case": "ieee33", "text": SAMPLE_PAPER},
        {"name": "paper_ieee69", "mode": "paper", "grid_case": "ieee69", "text": SAMPLE_PAPER},
        {"name": "theory_ieee33", "mode": "theory", "grid_case": "ieee33", "text": SAMPLE_THEORY},
        {"name": "theory_ieee69", "mode": "theory", "grid_case": "ieee69", "text": SAMPLE_THEORY},
    ]

    rows: List[Dict[str, Any]] = []
    for case in cases:
        started = time.perf_counter()
        error = ""
        result: Dict[str, Any] = {}
        try:
            if case["mode"] == "paper":
                result = agent.run_paper_reproduction(case["text"], grid_case=case["grid_case"])
            else:
                result = agent.run_theory_experiment(case["text"], grid_case=case["grid_case"])
        except Exception as exc:  # pragma: no cover - surfaced in report
            error = str(exc)
        elapsed = time.perf_counter() - started
        artifacts = result.get("artifacts", {})
        families = {item["family"] for item in result.get("strategy_spec", [])}
        strategies = result.get("experiment_config", {}).get("strategies", [])
        rows.append(
            {
                "case": case["name"],
                "mode": case["mode"],
                "grid_case": case["grid_case"],
                "success": not error,
                "latency_sec": round(elapsed, 4),
                "artifact_count": sum(1 for path in artifacts.values() if os.path.exists(path)),
                "strategy_count": len(strategies),
                "covers_rl": bool({"RL", "RL/MARL"} & families),
                "covers_traditional": bool({"Auction", "Optimization", "Rule-based"} & families),
                "metrics_count": len(result.get("metrics", [])),
                "error": error,
            }
        )

    success_count = sum(1 for row in rows if row["success"])
    avg_latency = sum(row["latency_sec"] for row in rows) / len(rows)
    summary = {
        "case_count": len(rows),
        "success_count": success_count,
        "success_rate": round(success_count / len(rows), 4),
        "avg_latency_sec": round(avg_latency, 4),
        "all_cases_have_artifacts": all(row["artifact_count"] >= 8 for row in rows if row["success"]),
        "all_cases_have_metrics": all(row["metrics_count"] >= 4 for row in rows if row["success"]),
        "rows": rows,
    }
    write_json(os.path.join(output_dir, "eval_report.json"), summary)
    write_text(os.path.join(output_dir, "eval_report.md"), render_eval_markdown(summary))
    return summary


def render_eval_markdown(summary: Dict[str, Any]) -> str:
    lines = [
        "# Energy Trading Lab Evaluation Report",
        "",
        "- Cases: %d" % summary["case_count"],
        "- Success rate: %.2f%%" % (summary["success_rate"] * 100.0),
        "- Average latency: %.4fs" % summary["avg_latency_sec"],
        "- Artifacts complete: %s" % ("yes" if summary["all_cases_have_artifacts"] else "no"),
        "- Metrics complete: %s" % ("yes" if summary["all_cases_have_metrics"] else "no"),
        "",
        "| Case | Grid | Success | Latency | Artifacts | Strategies | RL | Traditional |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary["rows"]:
        lines.append(
            "| {case} | {grid_case} | {success} | {latency_sec}s | {artifact_count} | {strategy_count} | {covers_rl} | {covers_traditional} |".format(
                **row
            )
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Energy Trading Lab portfolio evaluation.")
    parser.add_argument("--run-root", default="runs")
    parser.add_argument("--output-dir", default="runs/eval")
    args = parser.parse_args()
    print(json.dumps(run_eval(run_root=args.run_root, output_dir=args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
