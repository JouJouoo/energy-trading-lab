"""Plugin manifest dataclasses for the Energy Trading Lab plugin system.

These are pure value objects — no I/O, no parsing, no imports outside the
standard library. Parsing lives in `p2plab/plugin_loader.py`.

The plugin system has two surfaces:

- **Algorithm templates** under `p2plab/algorithm_templates/<family>/<name>/`.
  One template = one algorithm the Agent can choose when generating a
  reproduction. See `docs/skills-protocol.md`.

- **Scenarios** under `scenarios/<grid>/`.
  One scenario = one distribution network the Agent can simulate on.
  See `docs/scenarios-protocol.md`.

The manifest shape is intentionally simple: a few top-level scalar fields plus
a free-form `parameters` / `inputs` / `validation` / `tags` dict. Anything more
expressive belongs in the implementation file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AlgorithmTemplate:
    """One algorithm the Agent can choose from when planning a reproduction.

    Attributes:
        name: snake_case identifier; must match the folder name.
        family: one of {"Base", "RL", "RL/MARL", "Optimization", "Auction",
            "GameTheory", "RuleBased"}. The family is what the agent's
            strategy classifier keys off.
        display_name: shown in the UI and the CLI listings.
        file_name: the Python file inside the template folder, e.g.
            "q_learning.py". The loader checks that this file exists.
        description: short human-readable summary, used as tooltip / list entry.
        affected_modules: hint for the Agent's code generator; which existing
            modules this template plugs into. e.g. ["reward.py", "agent.py"].
        inputs: typed input schema. Keys are field names; values are type
            strings ("float", "int", "str", "list[float]"). The Agent uses
            these to validate a recipe before running.
        parameters: default hyperparameters. The Agent merges these into the
            generated experiment config, with the recipe taking precedence.
        validation: validation hints. Reserved keys: `smoke_test`
            (path string), `min_episodes` (int), `tolerance` (float).
        tags: free-form labels for the Plugin UI. e.g. ["rl", "tabular",
            "baseline"].
        source: where this template was loaded from. Internal; not in the
            manifest file. Set by the loader.
    """

    name: str
    family: str
    display_name: str
    file_name: str
    description: str = ""
    affected_modules: List[str] = field(default_factory=list)
    inputs: Dict[str, str] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "family": self.family,
            "display_name": self.display_name,
            "file_name": self.file_name,
            "description": self.description,
            "affected_modules": list(self.affected_modules),
            "inputs": dict(self.inputs),
            "parameters": dict(self.parameters),
            "validation": dict(self.validation),
            "tags": list(self.tags),
            "source": self.source,
        }


@dataclass
class ScenarioSpec:
    """One distribution network the Agent can simulate on.

    Attributes:
        name: snake_case identifier; must match the folder name.
        display_name: shown in the UI and the CLI listings.
        bus_count: number of buses in the feeder.
        base_voltage_kv: line-to-line kV at the substation.
        voltage_limits: [min_pu, max_pu] per-bus operating range. e.g.
            [0.95, 1.05].
        topology_source: short citation. e.g. "Baran-Wu 1989".
        feeder_file: path (relative to the scenario folder) of the
            `feeder.json` data file. The loader resolves it.
        prosumer_layout_file: optional path of the prosumer placement file.
        load_profile_file: optional path of a 24-hour load profile JSON.
        pv_profile_file: optional path of a 24-hour PV profile JSON.
        metrics_schema: which metrics the Agent should report for this
            scenario. e.g. ["total_cost", "p2p_volume_kwh", "min_voltage_pu"].
        tags: free-form labels for the Plugin UI.
        source: where this scenario was loaded from. Internal.
    """

    name: str
    display_name: str
    bus_count: int
    base_voltage_kv: float
    voltage_limits: List[float]
    topology_source: str
    feeder_file: str = "feeder.json"
    prosumer_layout_file: Optional[str] = None
    load_profile_file: Optional[str] = None
    pv_profile_file: Optional[str] = None
    metrics_schema: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "bus_count": self.bus_count,
            "base_voltage_kv": self.base_voltage_kv,
            "voltage_limits": list(self.voltage_limits),
            "topology_source": self.topology_source,
            "feeder_file": self.feeder_file,
            "prosumer_layout_file": self.prosumer_layout_file,
            "load_profile_file": self.load_profile_file,
            "pv_profile_file": self.pv_profile_file,
            "metrics_schema": list(self.metrics_schema),
            "tags": list(self.tags),
            "source": self.source,
        }


# Allowed families for `AlgorithmTemplate.family`. Kept as a module-level
# constant so the loader can validate, and so the Agent's strategy
# classifier can cross-check.
ALLOWED_FAMILIES = {
    "Base",
    "RL",
    "RL/MARL",
    "Optimization",
    "Auction",
    "GameTheory",
    "RuleBased",
}


def family_directory(family: str) -> str:
    """Map a family to the legacy algorithm_templates/ sub-folder.

    The plugin system uses this to keep the existing on-disk layout
    (Base/, RL/, Optimization/, Auction/, GameTheory/, RuleBased/). New
    families can be added here, and the loader will pick them up.
    """
    aliases = {
        "Game Theory": "GameTheory",
        "Rule-based": "RuleBased",
    }
    return aliases.get(family, family)
