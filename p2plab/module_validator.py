from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
from typing import Any, Callable, Dict, List, Optional, Tuple


class ModuleValidator:
    """Validate generated code modules at multiple levels.

    Levels:
    1. Syntax check - ast.parse
    2. Interface check - required classes/functions exist
    3. Smoke test - run with minimal inputs
    """

    def __init__(self, max_repair_attempts: int = 3):
        self.max_repair_attempts = max_repair_attempts

    def validate_syntax(self, code: str) -> Tuple[bool, List[str]]:
        """Level 1: Check Python syntax."""
        errors = []
        try:
            ast.parse(code)
            return True, errors
        except SyntaxError as e:
            errors.append(f"Syntax error: {e.msg} at line {e.lineno}")
            return False, errors

    def validate_interface(
        self,
        code: str,
        module_type: str,
        required_items: Optional[Dict[str, List[str]]] = None,
    ) -> Tuple[bool, List[str]]:
        """Level 2: Check required classes and functions exist."""
        errors = []
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Cannot parse: {e.msg}")
            return False, errors

        if required_items is None:
            required_items = self._default_required_items(module_type)

        classes = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
        functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

        for cls in required_items.get("classes", []):
            if cls not in classes:
                errors.append(f"Missing required class: {cls}")

        for func in required_items.get("functions", []):
            if func not in functions:
                errors.append(f"Missing required function: {func}")

        return len(errors) == 0, errors

    def validate_smoke(
        self,
        code: str,
        module_name: str,
        module_type: str,
        project_dir: Optional[str] = None,
    ) -> Tuple[bool, List[str], str]:
        """Level 3: Run smoke test with minimal inputs."""
        errors = []
        output = ""

        with tempfile.TemporaryDirectory() as tmpdir:
            module_path = os.path.join(tmpdir, f"{module_name}.py")
            with open(module_path, "w", encoding="utf-8") as f:
                f.write(code)

            init_path = os.path.join(tmpdir, "__init__.py")
            with open(init_path, "w", encoding="utf-8") as f:
                f.write("")

            test_code = self._smoke_test_code(module_name, module_type)
            test_path = os.path.join(tmpdir, f"test_{module_name}.py")
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_code)

            try:
                result = subprocess.run(
                    [sys.executable, test_path],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env={**os.environ, "PYTHONPATH": tmpdir + os.pathsep + os.environ.get("PYTHONPATH", "")},
                )
                output = result.stdout + result.stderr
                if result.returncode != 0:
                    errors.append(f"Smoke test failed with exit code {result.returncode}")
                    if result.stderr:
                        errors.append(result.stderr[:500])
                    return False, errors, output
                return True, errors, output
            except subprocess.TimeoutExpired:
                errors.append("Smoke test timed out after 30 seconds")
                return False, errors, output
            except Exception as e:
                errors.append(f"Smoke test error: {str(e)}")
                return False, errors, output

    def validate_module(
        self,
        code: str,
        module_name: str,
        module_type: str,
        project_dir: Optional[str] = None,
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Run all validation levels."""
        all_errors = []
        details = {}

        syntax_ok, syntax_errors = self.validate_syntax(code)
        details["syntax_ok"] = syntax_ok
        details["syntax_errors"] = syntax_errors
        all_errors.extend(syntax_errors)

        if not syntax_ok:
            return False, all_errors, details

        interface_ok, interface_errors = self.validate_interface(code, module_type)
        details["interface_ok"] = interface_ok
        details["interface_errors"] = interface_errors
        all_errors.extend(interface_errors)

        if not interface_ok:
            return False, all_errors, details

        smoke_ok, smoke_errors, smoke_output = self.validate_smoke(
            code, module_name, module_type, project_dir
        )
        details["smoke_ok"] = smoke_ok
        details["smoke_errors"] = smoke_errors
        details["smoke_output"] = smoke_output
        all_errors.extend(smoke_errors)

        return len(all_errors) == 0, all_errors, details

    def _default_required_items(self, module_type: str) -> Dict[str, List[str]]:
        """Get required classes/functions for each module type."""
        requirements = {
            "grid_model": {
                "classes": ["GridModel"],
                "functions": [],
            },
            "market_env": {
                "classes": ["MarketEnvironment"],
                "functions": [],
            },
            "q_learning": {
                "classes": ["QLearningAgent"],
                "functions": [],
            },
            "training_loop": {
                "classes": ["TrainingLoop"],
                "functions": [],
            },
            "reward": {
                "classes": ["RewardCalculator"],
                "functions": [],
            },
            "optimizer": {
                "classes": ["OptimizationSolver"],
                "functions": [],
            },
            "double_auction": {
                "classes": ["DoubleAuctionEngine"],
                "functions": [],
            },
            "stackelberg_game": {
                "classes": ["StackelbergGameEngine"],
                "functions": [],
            },
        }
        return requirements.get(module_type, {"classes": [], "functions": []})

    def _smoke_test_code(self, module_name: str, module_type: str) -> str:
        """Generate minimal smoke test code."""
        smoke_tests = {
            "grid_model": f'''
from {module_name} import GridModel
model = GridModel(grid_case="ieee33")
result = model.run_power_flow({{0: 10.0, 1: 5.0}}, {{0: 2.0, 1: 3.0}})
assert "min_voltage_pu" in result
assert "max_voltage_pu" in result
print("GridModel smoke test passed")
''',
            "market_env": f'''
from {module_name} import MarketEnvironment
env = MarketEnvironment(prosumer_count=3, horizon_hours=4, grid_case="ieee33")
state = env.reset()
assert "prosumers" in state
actions = {{i: {{"bid_price": 0.1, "battery_kw": 0.0}} for i in range(3)}}
next_state, rewards, done, info = env.step(actions)
assert "total_p2p_volume_kwh" in info
print("MarketEnvironment smoke test passed")
''',
            "q_learning": f'''
from {module_name} import QLearningAgent
agent = QLearningAgent(agent_id=0, state_size=4, action_size=5)
state = {{"hour_of_day": 12, "net_load_kw": 2.0, "grid_buy_price": 0.12, "battery_soc_kwh": 5.0}}
action = agent.select_action(state)
assert "bid_price" in action
agent.update(state, action, -1.0, state, False)
print("QLearningAgent smoke test passed")
''',
            "reward": f'''
from {module_name} import RewardCalculator
calc = RewardCalculator(cost_weight=1.0, carbon_weight=0.5)
info = {{"grid_import_kwh": 10.0, "p2p_trades": [], "prosumer_costs": {{0: 5.0}}}}
reward = calc.compute_reward(5.0, info)
assert isinstance(reward, float)
obj = calc.compute_objective(10.0, info)
assert isinstance(obj, float)
print("RewardCalculator smoke test passed")
''',
            "optimizer": f'''
from {module_name} import OptimizationSolver
solver = OptimizationSolver()
market_state = {{
    "prosumers": [
        {{"id": 0, "net_load_kw": 2.0}},
        {{"id": 1, "net_load_kw": -1.5}},
    ],
    "grid_buy_price": 0.12,
    "grid_sell_price": 0.06,
}}
result = solver.solve(market_state)
assert "total_cost" in result
print("OptimizationSolver smoke test passed")
''',
            "double_auction": f'''
from {module_name} import DoubleAuctionEngine
engine = DoubleAuctionEngine()
engine.submit_bid({{"id": 0, "price": 0.15, "quantity": 2.0}})
engine.submit_ask({{"id": 1, "price": 0.08, "quantity": 1.5}})
result = engine.clear_market()
assert "trades" in result
print("DoubleAuctionEngine smoke test passed")
''',
            "stackelberg_game": f'''
from {module_name} import StackelbergGameEngine
game = StackelbergGameEngine(n_followers=2, leader_id=0)
market_state = {{
    "prosumers": [
        {{"id": 0, "net_load_kw": -3.0}},
        {{"id": 1, "net_load_kw": 2.0}},
        {{"id": 2, "net_load_kw": 1.0}},
    ],
    "grid_buy_price": 0.12,
    "grid_sell_price": 0.06,
}}
result = game.find_equilibrium(market_state)
assert "equilibrium_price" in result
print("StackelbergGameEngine smoke test passed")
''',
        }
        test_code = smoke_tests.get(module_type, "print('No smoke test defined for module type')\n")
        return test_code
