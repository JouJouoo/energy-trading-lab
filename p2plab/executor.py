from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .schemas import ExperimentRecipe, GridValidationResult, SimulationMetrics, to_dict
from .utils import ensure_dir, write_json, write_text


@dataclass
class CodeExecutionResult:
    attempt: int
    status: str
    elapsed_sec: float
    script_path: str
    config_path: str
    metrics_path: str
    hourly_path: str
    training_path: str
    log_path: str
    stdout: str
    stderr: str
    repair_note: str
    metrics: List[SimulationMetrics]
    hourly_rows: Dict[str, List[Dict[str, float]]]
    training_rows: List[Dict[str, float]]


def run_generated_experiment(
    run_dir: str,
    recipe: ExperimentRecipe,
    attempt: int,
    repair_note: str = "",
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> CodeExecutionResult:
    ensure_dir(run_dir)
    safe_run_dir = os.path.abspath(run_dir)
    script_path = os.path.join(safe_run_dir, "generated_experiment_attempt_%d.py" % attempt)
    config_path = os.path.join(safe_run_dir, "experiment_config_attempt_%d.json" % attempt)
    metrics_path = os.path.join(safe_run_dir, "metrics_attempt_%d.json" % attempt)
    hourly_path = os.path.join(safe_run_dir, "hourly_metrics_attempt_%d.json" % attempt)
    training_path = os.path.join(safe_run_dir, "training_curve_attempt_%d.json" % attempt)
    log_path = os.path.join(safe_run_dir, "execution_log_attempt_%d.txt" % attempt)

    write_json(config_path, to_dict(recipe))
    write_text(script_path, render_generated_script(recipe=recipe, attempt=attempt, repair_note=repair_note))

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = dict(os.environ)
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
    command = [
        sys.executable,
        script_path,
        "--config",
        config_path,
        "--metrics",
        metrics_path,
        "--hourly",
        hourly_path,
        "--training",
        training_path,
    ]

    started = time.perf_counter()
    stdout_lines: List[str] = []
    stderr_lines: List[str] = []
    timed_out = False
    return_code = -1
    process = subprocess.Popen(
        command,
        cwd=project_root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    line_queue: "queue.Queue[Tuple[str, str]]" = queue.Queue()

    def reader(stream: Any, stream_name: str) -> None:
        try:
            for line in iter(stream.readline, ""):
                line_queue.put((stream_name, line))
        finally:
            stream.close()

    threads = [
        threading.Thread(target=reader, args=(process.stdout, "stdout"), daemon=True),
        threading.Thread(target=reader, args=(process.stderr, "stderr"), daemon=True),
    ]
    for thread in threads:
        thread.start()

    timeout_sec = execution_timeout(recipe)
    while True:
        try:
            stream_name, line = line_queue.get(timeout=0.1)
            if stream_name == "stdout":
                stdout_lines.append(line)
                _handle_progress_line(line, attempt, progress_callback)
            else:
                stderr_lines.append(line)
        except queue.Empty:
            pass

        if process.poll() is not None and line_queue.empty():
            return_code = process.returncode
            break
        if time.perf_counter() - started > timeout_sec:
            timed_out = True
            process.kill()
            return_code = process.wait()
            break

    for thread in threads:
        thread.join(timeout=1.0)
    elapsed = time.perf_counter() - started
    stdout_text = "".join(stdout_lines)
    stderr_text = "".join(stderr_lines)

    log = "\n".join(
        [
            "Command: %s" % " ".join(command),
            "Elapsed: %.4fs" % elapsed,
            "Return code: %s" % return_code,
            "Repair note: %s" % (repair_note or "initial generated experiment"),
            "Timed out: %s" % timed_out,
            "",
            "STDOUT:",
            stdout_text,
            "",
            "STDERR:",
            stderr_text,
        ]
    )
    write_text(log_path, log)

    if return_code != 0 or timed_out:
        return CodeExecutionResult(
            attempt=attempt,
            status="timeout" if timed_out else "failed",
            elapsed_sec=round(elapsed, 4),
            script_path=script_path,
            config_path=config_path,
            metrics_path=metrics_path,
            hourly_path=hourly_path,
            training_path=training_path,
            log_path=log_path,
            stdout=stdout_text,
            stderr=stderr_text,
            repair_note=repair_note,
            metrics=[],
            hourly_rows={},
            training_rows=[],
        )

    with open(metrics_path, "r", encoding="utf-8") as handle:
        metrics = [metric_from_dict(item) for item in json.load(handle)]
    with open(hourly_path, "r", encoding="utf-8") as handle:
        hourly_rows = json.load(handle)
    with open(training_path, "r", encoding="utf-8") as handle:
        training_rows = json.load(handle)

    return CodeExecutionResult(
        attempt=attempt,
        status="passed",
        elapsed_sec=round(elapsed, 4),
        script_path=script_path,
        config_path=config_path,
        metrics_path=metrics_path,
        hourly_path=hourly_path,
        training_path=training_path,
        log_path=log_path,
        stdout=stdout_text,
        stderr=stderr_text,
        repair_note=repair_note,
        metrics=metrics,
        hourly_rows=hourly_rows,
        training_rows=training_rows,
    )


def render_generated_script(recipe: ExperimentRecipe, attempt: int, repair_note: str) -> str:
    paper_specific_algorithm = {
        "innovation_tags": recipe.innovation_tags,
        "strategy_parameters": recipe.strategy_parameters,
        "use_proposed_method": "proposed_method" in recipe.strategies,
        "notes": recipe.notes,
        "repair_note": repair_note or "initial generated experiment",
    }
    paper_specific_json = json.dumps(paper_specific_algorithm, ensure_ascii=False, indent=2)
    paper_specific_literal = json.dumps(paper_specific_json, ensure_ascii=False)
    template = '''"""Generated by Energy Trading Lab.

This file is intentionally saved as an artifact so the reproduction package is
auditable. It is generated from the extracted paper/theory model and executes
only the controlled simulation API inside this repository.

Attempt: __ATTEMPT__
Repair/optimization note: __REPAIR_NOTE__
"""

from __future__ import annotations

import argparse
import json

from p2plab.schemas import ExperimentRecipe, to_dict
from p2plab.simulation import run_experiment_detailed


PAPER_SPECIFIC_ALGORITHM = json.loads(__PAPER_SPECIFIC_ALGORITHM__)


def recipe_from_dict(data):
    return ExperimentRecipe(
        name=data["name"],
        grid_case=data["grid_case"],
        horizon_hours=int(data["horizon_hours"]),
        prosumer_count=int(data["prosumer_count"]),
        strategies=list(data["strategies"]),
        random_seed=int(data["random_seed"]),
        training_episodes=int(data["training_episodes"]),
        voltage_limits=list(data["voltage_limits"]),
        notes=data.get("notes", ""),
        innovation_tags=list(data.get("innovation_tags", [])),
        strategy_parameters=dict(data.get("strategy_parameters", {})),
        experiment_depth=data.get("experiment_depth", "quick"),
        training_log_interval=int(data.get("training_log_interval", 50)),
    )


def apply_paper_specific_algorithm(recipe):
    """Apply the code-level adapter generated from this paper/theory.

    The controlled simulation engine provides the reusable market/grid runtime.
    This adapter is the per-paper layer: it changes the proposed-method switch,
    reward/objective weights, trading aggressiveness, and risk terms extracted
    from the source document.
    """

    adapter = PAPER_SPECIFIC_ALGORITHM
    recipe.strategy_parameters.update(dict(adapter.get("strategy_parameters", {})))
    for tag in adapter.get("innovation_tags", []):
        if tag not in recipe.innovation_tags:
            recipe.innovation_tags.append(tag)
    if adapter.get("use_proposed_method") and "proposed_method" not in recipe.strategies:
        recipe.strategies.append("proposed_method")
    recipe.notes = (recipe.notes + " Generated adapter: " + adapter.get("repair_note", "")).strip()
    return recipe


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--hourly", required=True)
    parser.add_argument("--training", required=True)
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as handle:
        recipe = recipe_from_dict(json.load(handle))
    recipe = apply_paper_specific_algorithm(recipe)

    def emit_progress(payload):
        print("ETL_PROGRESS " + json.dumps(payload, ensure_ascii=False), flush=True)

    metrics, hourly_rows, training_rows = run_experiment_detailed(recipe, progress_callback=emit_progress)

    with open(args.metrics, "w", encoding="utf-8") as handle:
        json.dump(to_dict(metrics), handle, ensure_ascii=False, indent=2)
    with open(args.hourly, "w", encoding="utf-8") as handle:
        json.dump(hourly_rows, handle, ensure_ascii=False, indent=2)
    with open(args.training, "w", encoding="utf-8") as handle:
        json.dump(training_rows, handle, ensure_ascii=False, indent=2)

    best = min(metrics, key=lambda item: item.total_cost)
    print("completed", recipe.name, recipe.grid_case, "best_strategy=", best.strategy, "cost=", best.total_cost)


if __name__ == "__main__":
    main()
'''
    return template.replace("__ATTEMPT__", str(attempt)).replace(
        "__REPAIR_NOTE__", (repair_note or "initial generated experiment").replace('"""', "")
    ).replace("__PAPER_SPECIFIC_ALGORITHM__", paper_specific_literal)


def metric_from_dict(data: Dict[str, Any]) -> SimulationMetrics:
    grid = GridValidationResult(**data["grid_validation"])
    payload = dict(data)
    payload["grid_validation"] = grid
    return SimulationMetrics(**payload)


def _handle_progress_line(
    line: str,
    attempt: int,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]],
) -> None:
    if progress_callback is None or not line.startswith("ETL_PROGRESS "):
        return
    try:
        payload = json.loads(line[len("ETL_PROGRESS ") :])
        payload["attempt"] = attempt
        progress_callback(payload)
    except json.JSONDecodeError:
        return


def execution_timeout(recipe: ExperimentRecipe) -> int:
    if recipe.experiment_depth == "deep":
        return 900
    if recipe.experiment_depth == "research":
        return 240
    return 60


def should_optimize(metrics: List[SimulationMetrics]) -> Tuple[bool, str]:
    if not metrics:
        return True, "Initial generated experiment failed to produce metrics."
    baseline = next((item for item in metrics if item.strategy == "no_trading"), None)
    best = min(metrics, key=lambda item: item.total_cost)
    if baseline and best.strategy == "no_trading":
        return True, "No strategy improved over the no-trading baseline; add/strengthen adaptive strategies."
    if baseline and best.cost_saving_pct < 0.12:
        return True, "Best cost saving is below 0.12%; increase horizon/training and include proposed method."
    if best.grid_validation.voltage_violation_count > 0 or best.voltage_risk_score > 0:
        return True, "Voltage risk detected; add voltage-aware proposed method and rerun."
    return False, "Generated experiment passed quality gates."


def optimized_recipe(recipe: ExperimentRecipe, reason: str, include_proposed: bool) -> ExperimentRecipe:
    strategies = list(recipe.strategies)
    if include_proposed and "proposed_method" not in strategies:
        strategies.append("proposed_method")
    if "rl_bidding" not in strategies:
        strategies.append("rl_bidding")
    params = dict(recipe.strategy_parameters)
    params["trading_aggressiveness"] = min(0.96, float(params.get("trading_aggressiveness", 0.82)) + 0.08)
    params["rl_aggressiveness"] = min(1.25, float(params.get("rl_aggressiveness", 1.0)) + 0.10)
    if "Voltage" in reason or "voltage" in reason:
        params["risk_sensitivity"] = min(0.65, float(params.get("risk_sensitivity", 0.0)) + 0.16)
        params["voltage_weight"] = min(0.75, float(params.get("voltage_weight", 0.0)) + 0.12)
    return ExperimentRecipe(
        name=recipe.name + "-optimized",
        grid_case=recipe.grid_case,
        horizon_hours=max(recipe.horizon_hours, 48),
        prosumer_count=recipe.prosumer_count,
        strategies=strategies,
        random_seed=recipe.random_seed + 7,
        training_episodes=max(recipe.training_episodes, 100),
        voltage_limits=recipe.voltage_limits,
        notes=recipe.notes + " Iteration 2 optimization: " + reason,
        innovation_tags=list(recipe.innovation_tags),
        strategy_parameters=params,
        experiment_depth=recipe.experiment_depth,
        training_log_interval=recipe.training_log_interval,
    )
