from __future__ import annotations

import csv
import os
from typing import Any, Callable, Dict, List, Optional

from .code_generator import CodeGenerator
from .executor import CodeExecutionResult, optimized_recipe, run_generated_experiment, should_optimize
from .llm import llm_status, sanitize_llm_config
from .llm_analysis import (
    fallback_detailed_innovation,
    fallback_payload,
    refine_analysis_with_llm,
    refine_detailed_innovation_with_llm,
)
from .memory import JsonlMemoryStore
from .project_assembler import ProjectAssembler
from .project_builder import build_code_project
from .rag import (
    classify_strategy_family,
    detect_reproduction_gaps,
    extract_detailed_innovation,
    extract_model_spec,
    extract_innovation_spec,
    generate_hypotheses,
    retrieve_domain_context,
)
from .reporting import render_gap_report, render_run_report
from .schemas import DetailedInnovationSpec, ExperimentRecipe, TraceEvent, to_dict
from .simulation import default_recipe
from .utils import ensure_dir, simple_yaml, task_id, write_json, write_text


class P2PLabAgent:
    def __init__(self, run_root: str = "runs"):
        self.run_root = ensure_dir(run_root)
        self.memory = JsonlMemoryStore(run_root)

    def run_paper_reproduction(
        self,
        paper_text: str,
        grid_case: str = "ieee33",
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        experiment_depth: str = "quick",
    ) -> Dict[str, Any]:
        return self._run_pipeline(source_text=paper_text, source_type="paper", grid_case=grid_case, on_event=on_event, llm_config=llm_config, experiment_depth=experiment_depth)

    def run_theory_experiment(
        self,
        theory_text: str,
        grid_case: str = "ieee33",
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        experiment_depth: str = "quick",
    ) -> Dict[str, Any]:
        return self._run_pipeline(source_text=theory_text, source_type="theory", grid_case=grid_case, on_event=on_event, llm_config=llm_config, experiment_depth=experiment_depth)

    def run_paper_to_code(
        self,
        paper_text: str,
        grid_case: str = "ieee33",
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the new paper-to-code pipeline:
        1. Parse paper and identify algorithm + innovations
        2. Generate code modules (base + algorithm) with validation
        3. Assemble a standalone project with pandapower integration
        4. Run integration smoke test
        """
        run_id = task_id("paper2code")
        if output_dir is None:
            run_dir = ensure_dir(os.path.join(self.run_root, run_id))
        else:
            run_dir = ensure_dir(output_dir)
        trace: List[TraceEvent] = []

        def step(name: str, summary: str, details: Dict[str, Any] = None) -> None:
            event = TraceEvent(step=name, status="ok", summary=summary, details=details or {})
            trace.append(event)
            if on_event is not None:
                on_event(to_dict(event))

        def module_progress(payload: Dict[str, Any]) -> None:
            evt = str(payload.get("event", "module_progress"))
            module_name = str(payload.get("module", "unknown"))
            if evt == "module_generation_start":
                summary = "Generating module: %s" % module_name
            elif evt == "module_generation_done":
                status = payload.get("status", "unknown")
                attempts = payload.get("repair_attempts", 0)
                summary = "Module %s generated: status=%s, repair_attempts=%d" % (module_name, status, attempts)
            else:
                summary = "Module %s: %s" % (module_name, evt)
            step(evt, summary, payload)

        step("ingest_input", "Loaded paper with %d characters." % len(paper_text))

        context = retrieve_domain_context(paper_text)
        step("retrieve_domain_context", "Retrieved domain snippets.", {"keys": list(context.keys())})

        model_spec = extract_model_spec(paper_text, source_type="paper")
        step("extract_model_spec", "Extracted model spec.", {"title": model_spec.title})

        strategies = classify_strategy_family(paper_text)
        step(
            "classify_strategy_family",
            "Classified %d strategy families." % len(strategies),
            {"families": [spec.family for spec in strategies]},
        )

        detailed_innovation: DetailedInnovationSpec = fallback_detailed_innovation(paper_text, strategies)
        analysis_meta = {
            "analysis_source": "heuristic_fallback",
            "llm_status": llm_status(llm_config),
            "llm_config": sanitize_llm_config(llm_config),
            "llm_error": "",
        }
        try:
            detailed_innovation, llm_meta = refine_detailed_innovation_with_llm(
                paper_text, strategies, detailed_innovation, llm_config=llm_config
            )
            analysis_meta.update(llm_meta)
            step(
                "llm_detailed_innovation",
                "LLM refined detailed innovation spec: %s algorithm, %d innovations."
                % (detailed_innovation.innovation_mode, len(detailed_innovation.layered_innovations)),
                {"base_algorithm": detailed_innovation.base_algorithm, "family": detailed_innovation.base_algorithm_family},
            )
        except Exception as exc:
            analysis_meta["llm_error"] = str(exc)
            step(
                "llm_detailed_innovation",
                "LLM refinement unavailable; using heuristic fallback.",
                {"error": str(exc), "source": analysis_meta["analysis_source"]},
            )

        step(
            "innovation_summary",
            "Algorithm: %s (%s), mode=%s, %d innovation layers."
            % (
                detailed_innovation.base_algorithm,
                detailed_innovation.base_algorithm_family,
                detailed_innovation.innovation_mode,
                len(detailed_innovation.layered_innovations),
            ),
            to_dict(detailed_innovation),
        )

        generator = CodeGenerator(llm_config=llm_config, progress_callback=module_progress)

        step(
            "generate_code",
            "Generating %d code modules for %s algorithm..."
            % (
                len(detailed_innovation.layered_innovations) + 2,
                detailed_innovation.base_algorithm,
            ),
        )
        modules = generator.generate_all_modules(
            algorithm_family=detailed_innovation.base_algorithm_family,
            innovation_spec=detailed_innovation,
            model_spec=model_spec,
            strategies=strategies,
            paper_text=paper_text,
        )

        passed_modules = [m for m in modules if m.status == "passed"]
        failed_modules = [m for m in modules if m.status != "passed"]
        step(
            "generate_code_done",
            "Generated %d modules: %d passed, %d failed."
            % (len(modules), len(passed_modules), len(failed_modules)),
            {
                "total": len(modules),
                "passed": [m.module_name for m in passed_modules],
                "failed": [m.module_name for m in failed_modules],
            },
        )

        step("assemble_project", "Assembling standalone project with pandapower integration...")
        assembler = ProjectAssembler(os.path.join(run_dir, "generated_project"))
        project = assembler.assemble_project(
            modules=modules,
            model_spec=model_spec,
            innovation_spec=detailed_innovation,
            grid_case=grid_case,
        )
        step(
            "assemble_project_done",
            "Project assembled at %s. Integration test: %s."
            % (project.project_dir, "PASSED" if project.integration_test_passed else "FAILED"),
            {
                "project_dir": project.project_dir,
                "integration_test_passed": project.integration_test_passed,
            },
        )

        artifacts = self._write_paper2code_artifacts(
            run_dir=run_dir,
            run_id=run_id,
            model_spec=model_spec,
            strategies=strategies,
            detailed_innovation=detailed_innovation,
            modules=modules,
            project=project,
            trace=trace,
            analysis_meta=analysis_meta,
        )

        self.memory.append(
            "paper2code_completed",
            {
                "run_id": run_id,
                "grid_case": grid_case,
                "project_dir": project.project_dir,
                "base_algorithm": detailed_innovation.base_algorithm,
                "algorithm_family": detailed_innovation.base_algorithm_family,
                "innovation_mode": detailed_innovation.innovation_mode,
                "integration_test_passed": project.integration_test_passed,
                "n_modules": len(modules),
            },
        )

        return {
            "run_id": run_id,
            "run_dir": run_dir,
            "artifacts": artifacts,
            "model_spec": to_dict(model_spec),
            "strategy_spec": to_dict(strategies),
            "detailed_innovation": to_dict(detailed_innovation),
            "analysis_meta": analysis_meta,
            "modules": [to_dict(m) for m in modules],
            "project": to_dict(project),
            "integration_test_passed": project.integration_test_passed,
            "trace": to_dict(trace),
        }

    def _run_pipeline(
        self,
        source_text: str,
        source_type: str,
        grid_case: str,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        experiment_depth: str = "quick",
    ) -> Dict[str, Any]:
        run_id = task_id("paper" if source_type == "paper" else "theory")
        run_dir = ensure_dir(os.path.join(self.run_root, run_id))
        trace: List[TraceEvent] = []

        def step(name: str, summary: str, details: Dict[str, Any] = None) -> None:
            event = TraceEvent(step=name, status="ok", summary=summary, details=details or {})
            trace.append(event)
            if on_event is not None:
                on_event(to_dict(event))

        def execution_progress(payload: Dict[str, Any]) -> None:
            event_name = str(payload.get("event", "execution_progress"))
            attempt = int(payload.get("attempt", 0) or 0)
            strategy = str(payload.get("strategy", "strategy"))
            if event_name == "training_progress":
                summary = (
                    "Attempt %d training %s: episode %d/%d, avg_reward %.4f, %.2fs elapsed."
                    % (
                        attempt,
                        strategy,
                        int(payload.get("episode", 0) or 0),
                        int(payload.get("episodes", 0) or 0),
                        float(payload.get("avg_reward", 0.0) or 0.0),
                        float(payload.get("elapsed_sec", 0.0) or 0.0),
                    )
                )
                step_name = "training_progress"
            elif event_name == "strategy_start":
                episodes = int(payload.get("training_episodes", 0) or 0)
                summary = (
                    "Attempt %d started %s over %d hours%s."
                    % (
                        attempt,
                        strategy,
                        int(payload.get("horizon_hours", 0) or 0),
                        ", RL training %d episodes" % episodes if episodes else "",
                    )
                )
                step_name = "strategy_start"
            elif event_name == "strategy_done":
                summary = (
                    "Attempt %d finished %s: cost %.4f, P2P %.2f kWh, train %.2fs."
                    % (
                        attempt,
                        strategy,
                        float(payload.get("total_cost", 0.0) or 0.0),
                        float(payload.get("p2p_volume_kwh", 0.0) or 0.0),
                        float(payload.get("training_elapsed_sec", 0.0) or 0.0),
                    )
                )
                step_name = "strategy_done"
            else:
                summary = "Attempt %d execution progress: %s." % (attempt, event_name)
                step_name = "execution_progress"
            step(step_name, summary, payload)

        step("ingest_input", "Loaded %s input with %d characters." % (source_type, len(source_text)))

        context = retrieve_domain_context(source_text)
        step("retrieve_domain_context", "Retrieved domain snippets for strategy, grid, and metrics.", {"keys": list(context.keys())})

        model_spec = extract_model_spec(source_text, source_type=source_type)
        step("extract_model_spec", "Extracted initial model spec and grid constraints.", {"title": model_spec.title})

        strategies = classify_strategy_family(source_text)
        step(
            "classify_strategy_family",
            "Classified %d strategy families including traditional and RL baselines." % len(strategies),
            {"families": [spec.family for spec in strategies]},
        )

        innovation = extract_innovation_spec(source_text, strategies)
        step(
            "extract_innovation_spec",
            "Synthesized initial paper-specific algorithm modifications: %s." % innovation.innovation_type,
            to_dict(innovation),
        )

        gaps = detect_reproduction_gaps(source_text)
        step("detect_reproduction_gaps", "Detected initial %d reproducibility gaps." % len(gaps))

        hypotheses = generate_hypotheses(source_text)
        step("design_experiment", "Generated initial %d experiment hypotheses." % len(hypotheses))

        analysis_meta = {
            "analysis_source": "heuristic_fallback",
            "llm_status": llm_status(llm_config),
            "llm_config": sanitize_llm_config(llm_config),
            "llm_error": "",
        }
        fallback = fallback_payload(model_spec, strategies, innovation, gaps, hypotheses)
        try:
            refined, llm_meta = refine_analysis_with_llm(source_text, source_type, fallback, llm_config=llm_config)
            model_spec = refined["model_spec"]
            strategies = refined["strategy_spec"]
            innovation = refined["innovation_spec"]
            gaps = refined["reproduction_gaps"]
            hypotheses = refined["hypotheses"]
            analysis_meta.update(llm_meta)
            step(
                "llm_structured_analysis",
                "LLM refined model, strategy, innovation, gaps, and hypotheses.",
                {"model": analysis_meta["llm_status"].get("model"), "source": analysis_meta["analysis_source"]},
            )
        except Exception as exc:
            analysis_meta["llm_error"] = str(exc)
            step(
                "llm_structured_analysis",
                "LLM refinement unavailable; using deterministic fallback extraction.",
                {"error": str(exc), "source": analysis_meta["analysis_source"]},
            )

        recipe = self._build_recipe(grid_case, strategies, source_type, innovation, experiment_depth)
        step("generate_config", "Generated executable experiment recipe for %s." % recipe.grid_case, to_dict(recipe))

        executions: List[CodeExecutionResult] = []
        step(
            "execute_attempt_1",
            "Running generated baseline/RL experiment code in sandbox (%s depth, %d episodes)."
            % (recipe.experiment_depth, recipe.training_episodes),
        )
        first_execution = run_generated_experiment(run_dir, recipe, attempt=1, progress_callback=execution_progress)
        executions.append(first_execution)
        step(
            "generate_or_patch_code",
            "Generated paper-specific experiment code and executed attempt 1 in sandbox.",
            {
                "script": first_execution.script_path,
                "config": first_execution.config_path,
                "status": first_execution.status,
                "elapsed_sec": first_execution.elapsed_sec,
            },
        )

        optimize, reason = should_optimize(first_execution.metrics)
        force_innovation_iteration = bool(innovation.code_modifications)
        if force_innovation_iteration:
            optimize = True
            reason = "Apply paper-specific innovation to create/modify the proposed method: %s" % "; ".join(
                innovation.code_modifications
            )
        final_recipe = recipe
        final_execution = first_execution
        if first_execution.status != "passed" or optimize:
            final_recipe = optimized_recipe(recipe, reason=reason, include_proposed=True)
            step("inspect_logs", "Attempt 1 inspection requested a code/config revision: %s" % reason)
            step(
                "execute_attempt_2",
                "Running revised paper-specific proposed-method experiment code in sandbox (%s depth, %d episodes)."
                % (final_recipe.experiment_depth, final_recipe.training_episodes),
            )
            second_execution = run_generated_experiment(
                run_dir,
                final_recipe,
                attempt=2,
                repair_note=reason,
                progress_callback=execution_progress,
            )
            executions.append(second_execution)
            final_execution = second_execution if second_execution.status == "passed" else first_execution
            step(
                "repair_once",
                "Generated revised experiment code/config and executed attempt 2.",
                {
                    "script": second_execution.script_path,
                    "config": second_execution.config_path,
                    "status": second_execution.status,
                    "elapsed_sec": second_execution.elapsed_sec,
                },
            )
        else:
            step("inspect_logs", "Attempt 1 passed quality gates: %s" % reason)
            step("repair_once", "No repair iteration needed.")

        metrics = final_execution.metrics
        hourly_rows = final_execution.hourly_rows
        training_rows = final_execution.training_rows
        recipe = final_recipe
        step("run_simulation", "Ran generated experiment code for %d P2P trading strategies." % len(metrics), {"strategies": recipe.strategies})

        step("run_power_flow_validation", "Validated IEEE feeder risk for every strategy and hour.")

        step("analyze_results", "Generated metrics tables and conclusion.")
        step(
            "generate_code_project",
            "Prepared a dedicated code project for this %s with configs, adapter, runner, and smoke test."
            % source_type,
        )
        report = render_run_report(
            model_spec,
            strategies,
            hypotheses,
            gaps,
            recipe,
            metrics,
            trace,
            innovation=innovation,
            executions=executions,
            analysis_meta=analysis_meta,
        )
        step("write_report", "Wrote research report and reproduction package artifacts.")

        artifacts = self._write_artifacts(
            run_dir=run_dir,
            run_id=run_id,
            source_type=source_type,
            model_spec=model_spec,
            strategies=strategies,
            innovation=innovation,
            analysis_meta=analysis_meta,
            gaps=gaps,
            hypotheses=hypotheses,
            recipe=recipe,
            metrics=metrics,
            hourly_rows=hourly_rows,
            training_rows=training_rows,
            trace=trace,
            report=report,
            executions=executions,
        )
        self.memory.append(
            "run_completed",
            {
                "run_id": run_id,
                "source_type": source_type,
                "grid_case": grid_case,
                "artifact_dir": run_dir,
                "strategies": recipe.strategies,
                "attempts": len(executions),
            },
        )
        return {
            "run_id": run_id,
            "run_dir": run_dir,
            "artifacts": artifacts,
            "report_preview": report,
            "model_spec": to_dict(model_spec),
            "strategy_spec": to_dict(strategies),
            "innovation_spec": to_dict(innovation),
            "analysis_meta": analysis_meta,
            "reproduction_gaps": to_dict(gaps),
            "hypotheses": to_dict(hypotheses),
            "experiment_config": to_dict(recipe),
            "metrics": to_dict(metrics),
            "trace": to_dict(trace),
            "executions": [self._execution_summary(item) for item in executions],
        }

    def _write_paper2code_artifacts(
        self,
        run_dir: str,
        run_id: str,
        model_spec: Any,
        strategies: Any,
        detailed_innovation: DetailedInnovationSpec,
        modules: List[Any],
        project: Any,
        trace: List[TraceEvent],
        analysis_meta: Dict[str, Any],
    ) -> Dict[str, str]:
        artifacts = {
            "model_spec": os.path.join(run_dir, "model_spec.json"),
            "strategy_spec": os.path.join(run_dir, "strategy_spec.json"),
            "detailed_innovation": os.path.join(run_dir, "detailed_innovation.json"),
            "analysis_meta": os.path.join(run_dir, "analysis_meta.json"),
            "modules_summary": os.path.join(run_dir, "modules_summary.json"),
            "trace": os.path.join(run_dir, "agent_trace.json"),
            "project_dir": project.project_dir,
        }
        write_json(artifacts["model_spec"], to_dict(model_spec))
        write_json(artifacts["strategy_spec"], to_dict(strategies))
        write_json(artifacts["detailed_innovation"], to_dict(detailed_innovation))
        write_json(artifacts["analysis_meta"], analysis_meta)
        write_json(artifacts["modules_summary"], [to_dict(m) for m in modules])
        write_json(artifacts["trace"], to_dict(trace))

        readme = self._render_paper2code_readme(model_spec, detailed_innovation, project)
        artifacts["readme"] = os.path.join(run_dir, "paper2code_readme.md")
        write_text(artifacts["readme"], readme)

        return artifacts

    def _render_paper2code_readme(self, model_spec: Any, innovation: DetailedInnovationSpec, project: Any) -> str:
        lines = []
        lines.append("# Paper-to-Code Generation Summary")
        lines.append("")
        lines.append("## Paper")
        lines.append("- **Title**: %s" % getattr(model_spec, "title", "Unknown"))
        lines.append("- **Problem**: %s" % getattr(model_spec, "research_problem", "Unknown"))
        lines.append("")
        lines.append("## Algorithm")
        lines.append("- **Type**: %s" % innovation.base_algorithm_family)
        lines.append("- **Base algorithm**: %s" % innovation.base_algorithm)
        lines.append("- **Innovation mode**: %s" % innovation.innovation_mode)
        lines.append("- **Number of innovation layers**: %d" % len(innovation.layered_innovations))
        lines.append("")
        lines.append("### Innovation Layers")
        for i, inv in enumerate(innovation.layered_innovations, 1):
            lines.append("%d. **%s**: %s" % (i, inv.layer, inv.description))
            lines.append("   - Code change: %s" % inv.code_change_hint)
            if inv.affected_modules:
                lines.append("   - Affected modules: %s" % ", ".join(inv.affected_modules))
            lines.append("")
        lines.append("## Generated Project")
        lines.append("- **Directory**: `%s`" % project.project_dir)
        lines.append("- **Integration test**: %s" % ("PASSED" if project.integration_test_passed else "FAILED"))
        lines.append("- **Modules**: %d" % len(project.modules))
        lines.append("")
        lines.append("### Usage")
        lines.append("```bash")
        lines.append("cd %s" % project.project_dir)
        lines.append("pip install -r requirements.txt")
        lines.append("python src/run_experiment.py --config configs/smoke_config.json --output-dir outputs/smoke")
        lines.append("```")
        lines.append("")
        return "\n".join(lines) + "\n"

    def _build_recipe(self, grid_case: str, strategies: List[Any], source_type: str, innovation: Any, experiment_depth: str) -> ExperimentRecipe:
        recipe = default_recipe(grid_case=grid_case)
        strategy_names = ["no_trading", "rule_double_auction", "optimization_clearing"]
        if any(spec.family in ("RL", "RL/MARL") for spec in strategies):
            strategy_names.append("rl_bidding")
        else:
            strategy_names.append("rl_bidding")
        recipe.strategies = self._supported_strategies(strategy_names)
        self._apply_experiment_depth(recipe, experiment_depth)
        recipe.innovation_tags = [innovation.innovation_type]
        recipe.strategy_parameters = dict(innovation.strategy_parameters)
        recipe.notes = (
            "Generated by Energy Trading Lab Agent. Paper-specific algorithm: %s on top of %s."
            % (innovation.innovation_type, innovation.base_algorithm)
        )
        return recipe

    def _apply_experiment_depth(self, recipe: ExperimentRecipe, depth: str) -> None:
        normalized = (depth or "quick").lower()
        if normalized == "deep":
            recipe.experiment_depth = "deep"
            recipe.horizon_hours = 336
            recipe.prosumer_count = 16 if recipe.grid_case == "ieee33" else 24
            recipe.training_episodes = 12000
            recipe.training_log_interval = 500
        elif normalized == "research":
            recipe.experiment_depth = "research"
            recipe.horizon_hours = 168
            recipe.prosumer_count = 12 if recipe.grid_case == "ieee33" else 18
            recipe.training_episodes = 3000
            recipe.training_log_interval = 150
        else:
            recipe.experiment_depth = "quick"
            recipe.horizon_hours = 48
            recipe.prosumer_count = 8 if recipe.grid_case == "ieee33" else 12
            recipe.training_episodes = 100
            recipe.training_log_interval = 25

    def _supported_strategies(self, strategies: List[str]) -> List[str]:
        allowed = {"no_trading", "rule_double_auction", "optimization_clearing", "rl_bidding", "proposed_method"}
        normalized = []
        for strategy in strategies:
            value = strategy
            if value in allowed and value not in normalized:
                normalized.append(value)
        return normalized

    def _write_artifacts(
        self,
        run_dir: str,
        run_id: str,
        source_type: str,
        model_spec: Any,
        strategies: Any,
        innovation: Any,
        analysis_meta: Dict[str, Any],
        gaps: Any,
        hypotheses: Any,
        recipe: ExperimentRecipe,
        metrics: Any,
        hourly_rows: Dict[str, List[Dict[str, float]]],
        training_rows: List[Dict[str, float]],
        trace: List[TraceEvent],
        report: str,
        executions: List[CodeExecutionResult],
    ) -> Dict[str, str]:
        artifacts = {
            "model_spec": os.path.join(run_dir, "model_spec.json"),
            "strategy_spec": os.path.join(run_dir, "strategy_spec.json"),
            "innovation_spec": os.path.join(run_dir, "innovation_spec.json"),
            "analysis_meta": os.path.join(run_dir, "analysis_meta.json"),
            "reproduction_gaps": os.path.join(run_dir, "reproduction_gaps.md"),
            "experiment_config": os.path.join(run_dir, "experiment_config.yaml"),
            "metrics": os.path.join(run_dir, "metrics.json"),
            "trace": os.path.join(run_dir, "agent_trace.json"),
            "report": os.path.join(run_dir, "run_report.md"),
            "hourly_metrics": os.path.join(run_dir, "hourly_metrics.csv"),
            "training_curve": os.path.join(run_dir, "training_curve.csv"),
            "execution_summary": os.path.join(run_dir, "execution_summary.json"),
        }
        write_json(artifacts["model_spec"], to_dict(model_spec))
        write_json(artifacts["strategy_spec"], to_dict(strategies))
        write_json(artifacts["innovation_spec"], to_dict(innovation))
        write_json(artifacts["analysis_meta"], analysis_meta)
        write_text(artifacts["reproduction_gaps"], render_gap_report(gaps))
        write_text(artifacts["experiment_config"], simple_yaml(to_dict(recipe)) + "\n")
        write_json(artifacts["metrics"], to_dict(metrics))
        write_json(artifacts["trace"], to_dict(trace))
        write_text(artifacts["report"], report + "\n")
        write_json(artifacts["execution_summary"], [self._execution_summary(item) for item in executions])
        self._write_hourly_csv(artifacts["hourly_metrics"], hourly_rows)
        self._write_training_csv(artifacts["training_curve"], training_rows)
        artifacts.update(
            build_code_project(
                run_dir=run_dir,
                run_id=run_id,
                source_type=source_type,
                model_spec=model_spec,
                strategies=strategies,
                innovation=innovation,
                gaps=gaps,
                hypotheses=hypotheses,
                recipe=recipe,
                metrics=metrics,
                executions=executions,
                analysis_meta=analysis_meta,
            )
        )
        return artifacts

    def _write_hourly_csv(self, path: str, hourly_rows: Dict[str, List[Dict[str, float]]]) -> None:
        fieldnames = [
            "strategy",
            "hour",
            "p2p_volume_kwh",
            "grid_import_kwh",
            "grid_export_kwh",
            "min_voltage_pu",
            "max_voltage_pu",
            "voltage_violation_count",
            "network_loss_kwh",
            "line_loading_max_pct",
        ]
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for strategy, rows in hourly_rows.items():
                for row in rows:
                    payload = dict(row)
                    payload["strategy"] = strategy
                    writer.writerow(payload)

    def _write_training_csv(self, path: str, training_rows: List[Dict[str, float]]) -> None:
        fieldnames = ["strategy", "episode", "avg_reward", "epsilon", "elapsed_sec"]
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in training_rows:
                writer.writerow({name: row.get(name, "") for name in fieldnames})

    def _execution_summary(self, execution: CodeExecutionResult) -> Dict[str, Any]:
        return {
            "attempt": execution.attempt,
            "status": execution.status,
            "elapsed_sec": execution.elapsed_sec,
            "script_path": os.path.abspath(execution.script_path),
            "config_path": os.path.abspath(execution.config_path),
            "metrics_path": os.path.abspath(execution.metrics_path),
            "hourly_path": os.path.abspath(execution.hourly_path),
            "training_path": os.path.abspath(execution.training_path),
            "log_path": os.path.abspath(execution.log_path),
            "repair_note": execution.repair_note,
            "stdout": execution.stdout[-1200:],
            "stderr": execution.stderr[-1200:],
        }
