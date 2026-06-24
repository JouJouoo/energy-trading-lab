import os
import base64
import subprocess
import sys
import tempfile
import unittest

from p2plab.agent import P2PLabAgent
from p2plab.document_loader import extract_document_from_base64
from p2plab.grid import load_grid_case
from p2plab.rag import classify_strategy_family
from p2plab.simulation import default_recipe, run_experiment


SAMPLE_TEXT = """
Network-aware multi-agent reinforcement learning for P2P energy trading in an IEEE 33-bus distribution network.
The method uses double auction clearing, Q-learning bidding, PV generation, battery SOC, voltage constraints,
network loss, carbon emissions, and compares rule-based trading with optimization clearing.
"""


class P2PLabCoreTests(unittest.TestCase):
    def test_grid_cases_load(self):
        grid33 = load_grid_case("ieee33")
        grid69 = load_grid_case("ieee69")
        self.assertEqual(grid33.bus_count, 33)
        self.assertEqual(grid69.bus_count, 69)
        self.assertEqual(len(grid33.branches), 32)
        self.assertEqual(len(grid69.branches), 68)

    def test_strategy_classification_covers_rl_and_traditional(self):
        specs = classify_strategy_family(SAMPLE_TEXT)
        families = {spec.family for spec in specs}
        self.assertTrue({"RL", "RL/MARL"} & families)
        self.assertIn("Auction", families)
        self.assertIn("Optimization", families)
        self.assertIn("Rule-based", families)

    def test_simulation_runs_ieee33_and_ieee69(self):
        for case in ("ieee33", "ieee69"):
            recipe = default_recipe(grid_case=case, strategies=["no_trading", "rule_double_auction", "rl_bidding"])
            recipe.horizon_hours = 6
            recipe.training_episodes = 4
            metrics, rows = run_experiment(recipe)
            self.assertEqual(len(metrics), 3)
            self.assertIn("rl_bidding", rows)
            for item in metrics:
                self.assertTrue(item.grid_validation.converged)
                self.assertGreater(item.grid_validation.min_voltage_pu, 0.85)

    def test_strategy_metrics_are_distinguishable(self):
        recipe = default_recipe(
            grid_case="ieee33",
            strategies=["no_trading", "rule_double_auction", "optimization_clearing", "rl_bidding", "proposed_method"],
        )
        recipe.horizon_hours = 24
        recipe.training_episodes = 8
        metrics, _rows = run_experiment(recipe)
        p2p_values = {item.strategy: item.p2p_volume_kwh for item in metrics}
        self.assertEqual(p2p_values["no_trading"], 0.0)
        self.assertGreater(p2p_values["optimization_clearing"], p2p_values["rule_double_auction"])
        self.assertTrue(any(item.cost_saving_pct > 0 for item in metrics if item.strategy != "no_trading"))

    def test_agent_writes_reproduction_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = P2PLabAgent(run_root=tmp)
            result = agent.run_paper_reproduction(SAMPLE_TEXT, grid_case="ieee33")
            artifacts = result["artifacts"]
            for key in ("model_spec", "strategy_spec", "reproduction_gaps", "experiment_config", "report", "training_curve"):
                self.assertTrue(os.path.exists(artifacts[key]), key)
            self.assertTrue(os.path.exists(artifacts["innovation_spec"]))
            self.assertTrue(os.path.exists(artifacts["execution_summary"]))
            self.assertTrue(os.path.isdir(artifacts["code_project"]))
            self.assertTrue(os.path.exists(artifacts["code_project_runner"]))
            self.assertTrue(os.path.exists(artifacts["code_project_test"]))
            self.assertTrue(result["executions"])
            self.assertTrue(os.path.exists(result["executions"][0]["script_path"]))
            self.assertTrue(os.path.exists(result["executions"][0]["log_path"]))
            self.assertTrue(os.path.exists(result["executions"][0]["training_path"]))
            self.assertTrue(any(item["step"] == "training_progress" for item in result["trace"]))
            self.assertIn("innovation_type", result["innovation_spec"])
            self.assertTrue(result["trace"])
            self.assertTrue(result["metrics"])
            env = os.environ.copy()
            env["ENERGY_TRADING_LAB_REPO"] = os.getcwd()
            completed = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                cwd=artifacts["code_project"],
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_theory_pipeline_includes_proposed_method(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = P2PLabAgent(run_root=tmp)
            result = agent.run_theory_experiment("我提出电压感知低碳强化学习 P2P 能源交易机制。", grid_case="ieee33")
            self.assertIn("proposed_method", result["experiment_config"]["strategies"])
            self.assertEqual(len(result["hypotheses"]), 3)

    def test_document_upload_extracts_markdown_text(self):
        raw = (SAMPLE_TEXT * 3).encode("utf-8")
        payload = base64.b64encode(raw).decode("ascii")
        result = extract_document_from_base64("paper.md", payload)
        self.assertEqual(result["method"], "text")
        self.assertGreater(result["chars"], 200)
        self.assertIn("P2P energy trading", result["text"])


if __name__ == "__main__":
    unittest.main()
