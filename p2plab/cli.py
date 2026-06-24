from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict

from .agent import P2PLabAgent
from .api.fastapi_server import run_server
from .utils import read_text


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

    args = parser.parse_args()
    if args.command == "serve":
        run_server(host=args.host, port=args.port, run_root=args.run_root)
        return

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


if __name__ == "__main__":
    main()
