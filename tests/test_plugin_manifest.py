"""Tests for the plugin manifest schema and discovery.

These tests iterate every discovered algorithm template and scenario
and assert the manifest shape is valid. They are the CI gate for the
plugin system; a failing assertion here is a release blocker.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from p2plab.plugin_loader import (
    BUILTIN_SCENARIOS_ROOT,
    BUILTIN_TEMPLATES_ROOT,
    discover_algorithm_templates,
    discover_scenarios,
    get_algorithm_template,
    get_scenario,
)
from p2plab.plugin_manifest import (
    ALLOWED_FAMILIES,
    AlgorithmTemplate,
    ScenarioSpec,
    family_directory,
)


class AlgorithmTemplateDiscoveryTests(unittest.TestCase):
    def test_at_least_five_templates_discovered(self) -> None:
        templates = discover_algorithm_templates()
        self.assertGreaterEqual(
            len(templates), 5,
            "Expected at least 5 built-in algorithm templates. "
            "If a template was removed, update CHANGELOG.md and this test.",
        )

    def test_every_template_has_required_fields(self) -> None:
        for template in discover_algorithm_templates():
            with self.subTest(template=template.name):
                self.assertTrue(template.name)
                self.assertTrue(template.family)
                self.assertTrue(template.display_name)
                self.assertTrue(template.file_name)
                self.assertIn(template.family, ALLOWED_FAMILIES)

    def test_every_template_implementation_file_exists(self) -> None:
        for template in discover_algorithm_templates():
            with self.subTest(template=template.name):
                self.assertIsNotNone(template.source)
                impl = Path(template.source) / template.file_name
                self.assertTrue(
                    impl.exists(),
                    f"Template {template.name} declares file_name={template.file_name} "
                    f"but the file does not exist at {impl}.",
                )

    def test_every_template_has_a_public_entry_point(self) -> None:
        """Every template must expose at least one public function or method.

        The plugin contract (see `docs/skills-protocol.md` §3) recommends
        specific prefixes per family: `build_` for Base, `train_` / `act_`
        for RL, `solve_` for Optimization, `match_` for Auction,
        `equilibrium_` for Game Theory, `decide_` for RuleBased. We do not
        require these exact prefixes for back-compat (the MVP templates
        use a class-method style: `MarketEnv.step`, `StackelbergGame.find_equilibrium`,
        `DoubleAuction.clear_market`, etc.). We require *some* public
        callable, and we *warn* in the assertion message when the canonical
        prefix is missing so plugin authors can align over time.
        """
        family_entry_points = {
            "Base": ["build_"],
            "RL": ["train_", "act_"],
            "RL/MARL": ["train_", "act_"],
            "Optimization": ["solve_"],
            "Auction": ["match_"],
            "GameTheory": ["equilibrium_"],
            "RuleBased": ["decide_"],
        }
        for template in discover_algorithm_templates():
            with self.subTest(template=template.name):
                # Shared templates (reward, training_loop) are exempt —
                # they are referenced by the other RL templates.
                if template.tags and "shared" in template.tags:
                    continue
                impl = Path(template.source) / template.file_name
                source = impl.read_text(encoding="utf-8")
                tree = ast.parse(source)
                public_callables = sorted({
                    node.name
                    for node in ast.walk(tree)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not node.name.startswith("_")
                })
                self.assertTrue(
                    public_callables,
                    f"Template {template.name} has no public functions/methods.",
                )
                canonical = family_entry_points.get(template.family, [])
                aligned = any(
                    any(c.startswith(p) for c in public_callables) for p in canonical
                )
                if not aligned:
                    # Informational only — the existing MVP uses
                    # class-method style; we just want the plugin author
                    # to know the canonical name.
                    print(
                        f"  note: template {template.name!r} (family={template.family}) "
                        f"exposes {public_callables[:3]}; canonical prefix "
                        f"{canonical} is not used. See docs/skills-protocol.md §3."
                    )

    def test_no_duplicate_template_names(self) -> None:
        names = [t.name for t in discover_algorithm_templates()]
        self.assertEqual(len(names), len(set(names)), f"Duplicate template names: {names}")

    def test_get_algorithm_template_lookup(self) -> None:
        template = get_algorithm_template("q_learning")
        self.assertIsNotNone(template)
        self.assertEqual(template.family, "RL")


class ScenarioDiscoveryTests(unittest.TestCase):
    def test_at_least_three_scenarios_discovered(self) -> None:
        scenarios = discover_scenarios()
        self.assertGreaterEqual(
            len(scenarios), 3,
            "Expected at least 3 built-in scenarios.",
        )

    def test_every_scenario_has_required_fields(self) -> None:
        for scenario in discover_scenarios():
            with self.subTest(scenario=scenario.name):
                self.assertTrue(scenario.name)
                self.assertTrue(scenario.display_name)
                self.assertGreater(scenario.bus_count, 0)
                self.assertGreater(scenario.base_voltage_kv, 0.0)
                self.assertEqual(len(scenario.voltage_limits), 2)
                self.assertLess(scenario.voltage_limits[0], scenario.voltage_limits[1])
                self.assertTrue(scenario.topology_source)

    def test_every_scenario_has_feeder_file(self) -> None:
        for scenario in discover_scenarios():
            with self.subTest(scenario=scenario.name):
                self.assertIsNotNone(scenario.source)
                feeder = Path(scenario.source) / scenario.feeder_file
                self.assertTrue(
                    feeder.exists(),
                    f"Scenario {scenario.name} declares feeder_file={scenario.feeder_file} "
                    f"but the file does not exist at {feeder}.",
                )

    def test_no_duplicate_scenario_names(self) -> None:
        names = [s.name for s in discover_scenarios()]
        self.assertEqual(len(names), len(set(names)), f"Duplicate scenario names: {names}")

    def test_get_scenario_lookup(self) -> None:
        scenario = get_scenario("ieee33")
        self.assertIsNotNone(scenario)
        self.assertEqual(scenario.bus_count, 33)


class PluginManifestTypeTests(unittest.TestCase):
    """Pure data tests for the dataclasses."""

    def test_algorithm_template_to_dict_round_trip(self) -> None:
        template = AlgorithmTemplate(
            name="x",
            family="RL",
            display_name="X",
            file_name="x.py",
            description="desc",
        )
        d = template.to_dict()
        self.assertEqual(d["name"], "x")
        self.assertEqual(d["family"], "RL")
        self.assertEqual(d["file_name"], "x.py")
        self.assertEqual(d["description"], "desc")
        self.assertEqual(d["affected_modules"], [])
        self.assertEqual(d["inputs"], {})

    def test_scenario_spec_to_dict_round_trip(self) -> None:
        spec = ScenarioSpec(
            name="x",
            display_name="X",
            bus_count=10,
            base_voltage_kv=10.0,
            voltage_limits=[0.9, 1.1],
            topology_source="X",
        )
        d = spec.to_dict()
        self.assertEqual(d["name"], "x")
        self.assertEqual(d["bus_count"], 10)
        self.assertEqual(d["voltage_limits"], [0.9, 1.1])

    def test_family_directory_aliases(self) -> None:
        self.assertEqual(family_directory("Game Theory"), "GameTheory")
        self.assertEqual(family_directory("Rule-based"), "RuleBased")
        self.assertEqual(family_directory("RL"), "RL")
        self.assertEqual(family_directory("Unknown"), "Unknown")


class BuiltinRootsTests(unittest.TestCase):
    def test_builtin_templates_root_is_a_real_directory(self) -> None:
        self.assertTrue(BUILTIN_TEMPLATES_ROOT.is_dir())
        self.assertEqual(BUILTIN_TEMPLATES_ROOT.name, "algorithm_templates")

    def test_builtin_scenarios_root_is_a_real_directory(self) -> None:
        self.assertTrue(BUILTIN_SCENARIOS_ROOT.is_dir())
        self.assertEqual(BUILTIN_SCENARIOS_ROOT.name, "scenarios")


if __name__ == "__main__":
    unittest.main()
