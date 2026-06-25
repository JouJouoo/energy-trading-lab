from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

from .agent import P2PLabAgent
from .utils import read_text


def _get_run_server():
    """Lazy import of the FastAPI server. The dual-track subcommands
    (workspace-list, plugins-algorithms, llm-status, ...) do not require
    FastAPI to be installed, but the legacy `serve` subcommand does.
    """
    from .api.fastapi_server import run_server
    return run_server


SAMPLE_PAPER = """# Network-aware multi-agent reinforcement learning for P2P energy trading

This study investigates peer-to-peer energy trading among prosumers in an IEEE 33-bus distribution network.
The market uses double auction clearing and compares no trading, rule-based bidding, optimization clearing,
and multi-agent reinforcement learning. Agent states include PV generation, load, battery SOC, time-of-use
price, and voltage. Actions include buy/sell/hold, bid quantity, bid price, and storage dispatch. The reward
minimizes energy cost and carbon emissions while penalizing voltage violations and network loss.
"""


SAMPLE_THEORY = """我提出一种面向 P2P 能源交易的低碳电压感知奖励机制。
在 IEEE 33/69 节点配电网中，prosumer 不仅根据本地光伏、负荷、储能 SOC 和电价报价，
还需要感知节点电压风险和实时碳强度。理论预期是：相比传统双边拍卖和普通强化学习，
加入电压越限惩罚与碳排惩罚后，可以在保持较高 P2P 交易量的同时降低网损、碳排和越限次数。
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Energy Trading Lab research simulation and experiment generation agent.")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="Run both paper and theory demo pipelines.")
    demo.add_argument("--grid-case", default="ieee33", choices=["ieee33", "ieee69"])
    demo.add_argument("--run-root", default="runs")
    demo.add_argument("--experiment-depth", default="quick", choices=["quick", "research", "deep"])

    reproduce = sub.add_parser("reproduce", help="Run Paper-to-Reproduction.")
    reproduce.add_argument("--input", required=True, help="Path to paper text/markdown file.")
    reproduce.add_argument("--grid-case", default="ieee33", choices=["ieee33", "ieee69"])
    reproduce.add_argument("--run-root", default="runs")
    reproduce.add_argument("--experiment-depth", default="quick", choices=["quick", "research", "deep"])

    theory = sub.add_parser("theory", help="Run Theory-to-Experiment.")
    theory.add_argument("--input", required=True, help="Path to Chinese theory draft.")
    theory.add_argument("--grid-case", default="ieee33", choices=["ieee33", "ieee69"])
    theory.add_argument("--run-root", default="runs")
    theory.add_argument("--experiment-depth", default="quick", choices=["quick", "research", "deep"])

    serve = sub.add_parser("serve", help="Start the local HTTP workspace.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=8765, type=int)
    serve.add_argument("--run-root", default="runs")

    # 双轨能力暴露(0.2.0 起):workspace / metrics / trace / 插件 等子命令
    # 注意:每个子命令 parser 用独立变量名,避免覆盖 `sub` 引用导致后续 add_parser 失败
    ws_list = sub.add_parser("workspace-list", help="列工作空间项目(对应 GET /api/workspace/projects)")
    ws_list.add_argument("--json", action="store_true", help="以 JSON 形式输出")
    ws_list.add_argument("--limit", type=int, default=50, help="最多列出多少条")

    ws_get = sub.add_parser("workspace-get", help="获取单个项目详情(对应 GET /api/workspace/projects/{run_id})")
    ws_get.add_argument("run_id", help="run id")
    ws_get.add_argument("--json", action="store_true", help="以 JSON 形式输出")

    ws_del = sub.add_parser("workspace-delete", help="删除项目(对应 DELETE /api/workspace/projects/{run_id})")
    ws_del.add_argument("run_id", help="run id")
    ws_del.add_argument("--yes", action="store_true", help="跳过二次确认")

    metrics = sub.add_parser("metrics-get", help="获取指标(对应 GET /api/workspace/projects/{run_id}/metrics)")
    metrics.add_argument("run_id", help="run id")
    metrics.add_argument("--json", action="store_true", help="以 JSON 形式输出")

    trace = sub.add_parser("trace-get", help="获取 Agent Trace(对应 GET /api/workspace/projects/{run_id}/trace)")
    trace.add_argument("run_id", help="run id")
    trace.add_argument("--json", action="store_true", help="以 JSON 形式输出")

    report = sub.add_parser("report-get", help="获取研究报告(对应 GET /api/workspace/projects/{run_id}/report)")
    report.add_argument("run_id", help="run id")
    report.add_argument("--output-file", help="保存到指定文件,默认输出到 stdout")

    plg_alg = sub.add_parser("plugins-algorithms", help="列出已发现的算法模板(对应 GET /api/plugins/algorithms)")
    plg_alg.add_argument("--json", action="store_true", help="以 JSON 形式输出")

    plg_scn = sub.add_parser("plugins-scenarios", help="列出已发现的仿真场景(对应 GET /api/plugins/scenarios)")
    plg_scn.add_argument("--json", action="store_true", help="以 JSON 形式输出")

    llm_st = sub.add_parser("llm-status", help="查询 LLM 状态(对应 GET /api/llm-status)")
    llm_st.add_argument("--json", action="store_true", help="以 JSON 形式输出")
    llm_st.add_argument("--provider", default=None, help="覆盖默认 provider")

    llm_pv = sub.add_parser("llm-providers", help="列出所有 LLM provider")
    llm_pv.add_argument("--json", action="store_true", help="以 JSON 形式输出")

    p2c = sub.add_parser("paper2code", help="Paper-to-Code 流程(对应 POST /api/paper2code)")
    p2c.add_argument("--input", help="输入文件路径")
    p2c.add_argument("--text", help="直接传入文本(优先级高于 --input)")
    p2c.add_argument("--grid-case", default="ieee33")
    p2c.add_argument("--experiment-depth", default="quick", choices=["quick", "research", "deep"])
    p2c.add_argument("--run-root", default="runs")
    p2c.add_argument("--json", action="store_true", help="以 JSON 形式输出")

    evl = sub.add_parser("eval", help="跑评测套件")
    evl.add_argument("--output-dir", default="runs/eval", help="评测产物输出目录")
    evl.add_argument("--json", action="store_true", help="以 JSON 形式输出")

    args = parser.parse_args()
    if args.command == "serve":
        run_server = _get_run_server()
        run_server(host=args.host, port=args.port, run_root=args.run_root)
        return

    if args.command in ("workspace-list", "workspace-get", "workspace-delete",
                        "metrics-get", "trace-get", "report-get",
                        "plugins-algorithms", "plugins-scenarios",
                        "llm-status", "llm-providers",
                        "paper2code", "eval"):
        return _dispatch_dual_track(args)

    agent = P2PLabAgent(run_root=args.run_root)
    if args.command == "demo":
        paper = agent.run_paper_reproduction(SAMPLE_PAPER, grid_case=args.grid_case, experiment_depth=args.experiment_depth)
        draft = agent.run_theory_experiment(SAMPLE_THEORY, grid_case=args.grid_case, experiment_depth=args.experiment_depth)
        print_json({"paper_demo": summarize_result(paper), "theory_demo": summarize_result(draft)})
    elif args.command == "reproduce":
        result = agent.run_paper_reproduction(read_text(args.input), grid_case=args.grid_case, experiment_depth=args.experiment_depth)
        print_json(summarize_result(result))
    elif args.command == "theory":
        result = agent.run_theory_experiment(read_text(args.input), grid_case=args.grid_case, experiment_depth=args.experiment_depth)
        print_json(summarize_result(result))


def summarize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": result["run_id"],
        "run_dir": os.path.abspath(result["run_dir"]),
        "artifacts": {key: os.path.abspath(path) for key, path in result["artifacts"].items()},
        "report_preview": result.get("report_preview", "")[:1200],
        "innovation": result.get("innovation_spec", {}),
        "analysis_meta": result.get("analysis_meta", {}),
        "executions": result.get("executions", []),
        "experiment_depth": result["experiment_config"].get("experiment_depth"),
        "training_episodes": result["experiment_config"].get("training_episodes"),
        "horizon_hours": result["experiment_config"].get("horizon_hours"),
        "strategies": result["experiment_config"]["strategies"],
        "metrics": [
            {
                "strategy": item["strategy"],
                "total_cost": item["total_cost"],
                "p2p_volume_kwh": item["p2p_volume_kwh"],
                "min_voltage_pu": item["grid_validation"]["min_voltage_pu"],
                "voltage_violations": item["grid_validation"]["voltage_violation_count"],
            }
            for item in result["metrics"]
        ],
    }


def print_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# 双轨能力暴露(0.2.0 起)
# ---------------------------------------------------------------------------


def _dispatch_dual_track(args: argparse.Namespace) -> int:
    """Dispatch the new dual-track subcommands.

    Each handler returns the same shape as the matching `/api/*` endpoint,
    so `tests/test_cli_parity.py` can assert the two surfaces agree.
    """
    handler = {
        "workspace-list": cmd_workspace_list,
        "workspace-get": cmd_workspace_get,
        "workspace-delete": cmd_workspace_delete,
        "metrics-get": cmd_metrics_get,
        "trace-get": cmd_trace_get,
        "report-get": cmd_report_get,
        "plugins-algorithms": cmd_plugins_algorithms,
        "plugins-scenarios": cmd_plugins_scenarios,
        "llm-status": cmd_llm_status,
        "llm-providers": cmd_llm_providers,
        "paper2code": cmd_paper2code,
        "eval": cmd_eval,
    }.get(args.command)
    if handler is None:
        print_json({"error": "unknown command: %s" % args.command})
        return 2
    return handler(args)


def _human(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _print_payload(args: argparse.Namespace, payload: Any) -> None:
    if getattr(args, "json", False):
        print_json(payload)
    else:
        if isinstance(payload, (list, tuple)):
            for item in payload:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("run_id") or ""
                    family = item.get("family", "")
                    buses = item.get("bus_count")
                    if buses is not None:
                        print(f"  - {name:18s} {buses} buses")
                    elif family:
                        print(f"  - {name:18s} family={family}")
                    else:
                        print(f"  - {name}")
                else:
                    print(f"  - {item}")
            return
        if isinstance(payload, dict):
            for key, value in payload.items():
                if isinstance(value, (dict, list)):
                    print(f"  {key}:")
                    print(_human(value))
                else:
                    print(f"  {key}: {value}")
        else:
            print(_human(payload))


def _get_workspace_manager(run_root: str = "runs"):
    """Construct a WorkspaceManager pointed at the same data root the
    FastAPI server would use, honoring `ENERGY_LAB_DATA_DIR` per the
    contract in `AGENTS.md`.
    """
    from .api.workspace import WorkspaceManager, get_data_root
    import os
    data_root = get_data_root()
    db_path = os.path.join(data_root, "db.sqlite")
    return WorkspaceManager(db_path=db_path, run_root=run_root)


def cmd_workspace_list(args: argparse.Namespace) -> int:
    wm = _get_workspace_manager()
    projects = wm.list_projects()
    limit = getattr(args, "limit", 50)
    if limit and len(projects) > limit:
        projects = projects[:limit]
    if getattr(args, "json", False):
        print_json({"count": len(projects), "projects": projects})
    else:
        _print_payload(args, projects)
    return 0


def cmd_workspace_get(args: argparse.Namespace) -> int:
    wm = _get_workspace_manager()
    project = wm.get_project(args.run_id)
    if project is None:
        print_json({"error": "not found", "run_id": args.run_id})
        return 1
    if getattr(args, "json", False):
        print_json(project)
    else:
        _print_payload(args, project)
    return 0


def cmd_workspace_delete(args: argparse.Namespace) -> int:
    if not getattr(args, "yes", False):
        print("Refusing to delete without --yes.", file=sys.stderr)
        return 1
    wm = _get_workspace_manager()
    ok = wm.delete_project(args.run_id)
    print_json({"deleted": ok, "run_id": args.run_id})
    return 0 if ok else 1


def cmd_metrics_get(args: argparse.Namespace) -> int:
    wm = _get_workspace_manager()
    metrics = wm.get_project_metrics(args.run_id)
    if getattr(args, "json", False):
        print_json({"run_id": args.run_id, "metrics": metrics})
    else:
        _print_payload(args, metrics)
    return 0


def cmd_trace_get(args: argparse.Namespace) -> int:
    wm = _get_workspace_manager()
    trace = wm.get_project_trace(args.run_id)
    if getattr(args, "json", False):
        print_json({"run_id": args.run_id, "trace": trace})
    else:
        _print_payload(args, trace)
    return 0


def cmd_report_get(args: argparse.Namespace) -> int:
    wm = _get_workspace_manager()
    report = wm.get_project_report(args.run_id)
    if report is None:
        print_json({"error": "not found", "run_id": args.run_id})
        return 1
    out = getattr(args, "output_file", None)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(report)
        print_json({"saved_to": out})
    else:
        sys.stdout.write(report)
    return 0


def cmd_plugins_algorithms(args: argparse.Namespace) -> int:
    from .plugin_loader import list_algorithm_templates_with_runtime
    templates = list_algorithm_templates_with_runtime()
    payload = {
        "count": len(templates),
        "templates": [t.to_dict() for t in templates],
    }
    _print_payload(args, payload if getattr(args, "json", False) else [t.to_dict() for t in templates])
    return 0


def cmd_plugins_scenarios(args: argparse.Namespace) -> int:
    from .plugin_loader import list_scenarios_with_runtime
    scenarios = list_scenarios_with_runtime()
    payload = {
        "count": len(scenarios),
        "scenarios": [s.to_dict() for s in scenarios],
    }
    _print_payload(args, payload if getattr(args, "json", False) else [s.to_dict() for s in scenarios])
    return 0


def cmd_llm_status(args: argparse.Namespace) -> int:
    from .llm_adapters import snapshot_status
    import os
    provider = getattr(args, "provider", None) or os.getenv("ENERGY_LAB_LLM_PROVIDER", "openai")
    status = snapshot_status(provider=provider, request_config={}, run_health_check=False)
    if getattr(args, "json", False):
        print_json(status)
    else:
        print(f"provider: {status['provider']}")
        print(f"model: {status['model']}")
        print(f"base_url: {status['base_url']}")
        print(f"enabled: {status['enabled']}")
        print(f"has_api_key: {status['has_api_key']}")
        print(f"registered_providers: {[p['name'] for p in status['providers']]}")
    return 0


def cmd_llm_providers(args: argparse.Namespace) -> int:
    from .llm_adapters import list_providers
    providers = list_providers()
    if getattr(args, "json", False):
        print_json(providers)
    else:
        for p in providers:
            print(f"  - {p['name']:10s} base_url={p['default_base_url']} model={p['default_model']} json_mode={p['supports_json_mode']}")
    return 0


def cmd_paper2code(args: argparse.Namespace) -> int:
    from .agent import P2PLabAgent
    text = args.text
    if text is None and args.input:
        text = read_text(args.input)
    if not text:
        print_json({"error": "no input text (use --input or --text)"})
        return 1
    agent = P2PLabAgent(run_root=args.run_root)
    result = agent.run_paper_to_code(
        text=text,
        grid_case=args.grid_case,
        experiment_depth=args.experiment_depth,
    )
    summary = summarize_result(result)
    if getattr(args, "json", False):
        print_json(summary)
    else:
        _print_payload(args, summary)
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    from .eval import run_eval
    summary = run_eval(output_dir=args.output_dir)
    if getattr(args, "json", False):
        print_json(summary)
    else:
        _print_payload(args, summary)
    return 0


if __name__ == "__main__":
    main()
