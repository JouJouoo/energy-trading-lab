from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .utils import clamp


@dataclass
class Branch:
    from_bus: int
    to_bus: int
    r_ohm: float
    x_ohm: float


@dataclass
class GridCase:
    name: str
    bus_count: int
    slack_bus: int
    branches: List[Branch]
    base_load_kw: Dict[int, float]
    base_load_kvar: Dict[int, float]
    v_min_pu: float = 0.95
    v_max_pu: float = 1.05
    source: Optional[str] = None

    @property
    def buses(self) -> List[int]:
        return list(range(1, self.bus_count + 1))

    def load_buses(self) -> List[int]:
        return [bus for bus in self.buses if bus != self.slack_bus]


def ieee33_case() -> GridCase:
    """IEEE 33-bus radial distribution feeder approximation.

    The line/load data follows the common Baran-Wu 33-bus benchmark layout.
    Values are sufficient for research-prototype validation and can be swapped
    for pandapower.case33bw() in the production adapter.
    """

    line_data: List[Tuple[int, int, float, float]] = [
        (1, 2, 0.0922, 0.0470),
        (2, 3, 0.4930, 0.2511),
        (3, 4, 0.3660, 0.1864),
        (4, 5, 0.3811, 0.1941),
        (5, 6, 0.8190, 0.7070),
        (6, 7, 0.1872, 0.6188),
        (7, 8, 1.7114, 1.2351),
        (8, 9, 1.0300, 0.7400),
        (9, 10, 1.0400, 0.7400),
        (10, 11, 0.1966, 0.0650),
        (11, 12, 0.3744, 0.1238),
        (12, 13, 1.4680, 1.1550),
        (13, 14, 0.5416, 0.7129),
        (14, 15, 0.5910, 0.5260),
        (15, 16, 0.7463, 0.5450),
        (16, 17, 1.2890, 1.7210),
        (17, 18, 0.7320, 0.5740),
        (2, 19, 0.1640, 0.1565),
        (19, 20, 1.5042, 1.3554),
        (20, 21, 0.4095, 0.4784),
        (21, 22, 0.7089, 0.9373),
        (3, 23, 0.4512, 0.3083),
        (23, 24, 0.8980, 0.7091),
        (24, 25, 0.8960, 0.7011),
        (6, 26, 0.2030, 0.1034),
        (26, 27, 0.2842, 0.1447),
        (27, 28, 1.0590, 0.9337),
        (28, 29, 0.8042, 0.7006),
        (29, 30, 0.5075, 0.2585),
        (30, 31, 0.9744, 0.9630),
        (31, 32, 0.3105, 0.3619),
        (32, 33, 0.3410, 0.5302),
    ]
    load_data = {
        2: (100, 60),
        3: (90, 40),
        4: (120, 80),
        5: (60, 30),
        6: (60, 20),
        7: (200, 100),
        8: (200, 100),
        9: (60, 20),
        10: (60, 20),
        11: (45, 30),
        12: (60, 35),
        13: (60, 35),
        14: (120, 80),
        15: (60, 10),
        16: (60, 20),
        17: (60, 20),
        18: (90, 40),
        19: (90, 40),
        20: (90, 40),
        21: (90, 40),
        22: (90, 40),
        23: (90, 50),
        24: (420, 200),
        25: (420, 200),
        26: (60, 25),
        27: (60, 25),
        28: (60, 20),
        29: (120, 70),
        30: (200, 600),
        31: (150, 70),
        32: (210, 100),
        33: (60, 40),
    }
    return GridCase(
        name="ieee33",
        bus_count=33,
        slack_bus=1,
        branches=[Branch(*item) for item in line_data],
        base_load_kw={bus: vals[0] for bus, vals in load_data.items()},
        base_load_kvar={bus: vals[1] for bus, vals in load_data.items()},
    )


def ieee69_case() -> GridCase:
    """Built-in IEEE-69 compatible radial feeder approximation.

    pandapower does not expose IEEE-69 as directly as case33bw(), so the MVP
    ships a deterministic 69-bus radial benchmark adapter. The topology and
    loads are intentionally transparent and replaceable with a full published
    data table when the researcher needs numeric replication.
    """

    parents: Dict[int, int] = {}
    for bus in range(2, 28):
        parents[bus] = bus - 1
    lateral_ranges = [
        (28, 35, 3),
        (36, 46, 4),
        (47, 55, 8),
        (56, 65, 9),
        (66, 69, 11),
    ]
    for start, end, root in lateral_ranges:
        previous = root
        for bus in range(start, end + 1):
            parents[bus] = previous
            previous = bus

    branches: List[Branch] = []
    for bus in range(2, 70):
        parent = parents[bus]
        base = 0.07 + 0.012 * ((bus * 7) % 9)
        branches.append(Branch(parent, bus, r_ohm=base, x_ohm=base * 0.62))

    base_load_kw: Dict[int, float] = {}
    base_load_kvar: Dict[int, float] = {}
    for bus in range(2, 70):
        kw = 35.0 + 8.0 * (bus % 5) + (20.0 if bus in (27, 35, 46, 55, 65, 69) else 0.0)
        base_load_kw[bus] = kw
        base_load_kvar[bus] = kw * 0.42

    return GridCase(
        name="ieee69",
        bus_count=69,
        slack_bus=1,
        branches=branches,
        base_load_kw=base_load_kw,
        base_load_kvar=base_load_kvar,
    )


def load_grid_case(name: str) -> GridCase:
    """Load a grid case by name.

    Resolution order:

    1. A scenario discovered by `p2plab.plugin_loader.discover_scenarios()`
       whose `name` matches `name` (case-insensitive, with `-` / `_`
       normalization). The `feeder.json` inside the scenario folder is
       loaded and converted to a `GridCase`.
    2. The legacy in-source constants for the canonical benchmarks
       (IEEE 33 / IEEE 69). This is the back-compat fallback for callers
       that do not have any scenarios/ folder on disk.
    3. Raises `ValueError` for an unknown name.

    Adding a new grid case is therefore a matter of dropping a folder at
    `scenarios/<name>/` with a `SCENARIO.md` + `feeder.json`. No code
    change in `grid.py` is required. See `docs/scenarios-protocol.md`.
    """
    normalized = name.lower().replace("-", "").replace("_", "")

    # 1) Plugin loader
    try:
        from .plugin_loader import get_scenario

        scenario = get_scenario(name) or get_scenario(normalized)
        if scenario is not None and scenario.source:
            feeder_path = Path(scenario.source) / scenario.feeder_file
            if feeder_path.exists():
                return _grid_case_from_feeder_json(
                    scenario_name=scenario.name,
                    feeder_path=feeder_path,
                    v_min_pu=scenario.voltage_limits[0],
                    v_max_pu=scenario.voltage_limits[1],
                    source=str(feeder_path),
                )
    except Exception:
        # Discovery or parsing errors must not break the legacy path.
        pass

    # 2) Legacy in-source constants
    if normalized in ("ieee33", "33", "case33", "case33bw"):
        return ieee33_case()
    if normalized in ("ieee69", "69", "case69"):
        return ieee69_case()

    raise ValueError("Unsupported grid case: %s" % name)


def _grid_case_from_feeder_json(
    *,
    scenario_name: str,
    feeder_path: Path,
    v_min_pu: float,
    v_max_pu: float,
    source: str,
) -> GridCase:
    """Convert a `feeder.json` file into a `GridCase`.

    If the JSON file has no `lines` (i.e. it is a stub pointing to an
    in-source generator for back-compat), this falls back to the legacy
    in-source constants for the canonical benchmarks.
    """
    with open(feeder_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    branches: List[Branch] = []
    for line in data.get("lines", []):
        branches.append(
            Branch(
                from_bus=int(line["from"]),
                to_bus=int(line["to"]),
                r_ohm=float(line.get("r_ohm", 0.0)),
                x_ohm=float(line.get("x_ohm", 0.0)),
            )
        )

    if not branches:
        # Stub JSON — fall back to the legacy in-source generator.
        normalized = scenario_name.lower().replace("-", "").replace("_", "")
        if normalized in ("ieee33", "33", "case33", "case33bw"):
            legacy = ieee33_case()
            legacy.source = source
            return legacy
        if normalized in ("ieee69", "69", "case69"):
            legacy = ieee69_case()
            legacy.source = source
            return legacy
        # Unknown name with no branches; return an empty GridCase.
        # Callers will see bus_count > 0 but no branches, which will fail
        # downstream — that's the intended loud failure.

    slack_bus = int(data.get("slack_bus", 1))
    base_load_kw: Dict[int, float] = {}
    base_load_kvar: Dict[int, float] = {}

    for bus in data.get("buses", []):
        bus_id = int(bus.get("id", 0))
        if bus_id == 0:
            continue
        if "load_kw" in bus:
            base_load_kw[bus_id] = float(bus["load_kw"])
        if "load_kvar" in bus:
            base_load_kvar[bus_id] = float(bus["load_kvar"])

    bus_count = int(
        data.get("bus_count")
        or max([slack_bus] + [b.to_bus for b in branches] + list(base_load_kw.keys()))
    )

    return GridCase(
        name=scenario_name,
        bus_count=bus_count,
        slack_bus=slack_bus,
        branches=branches,
        base_load_kw=base_load_kw,
        base_load_kvar=base_load_kvar,
        v_min_pu=v_min_pu,
        v_max_pu=v_max_pu,
        source=source,
    )


class SimplePowerFlowValidator:
    """Fast radial feeder validator used when pandapower is unavailable.

    It computes a deterministic DistFlow-style approximation. This is not a
    substitute for AC power flow, but it gives the Agent an executable safety
    check for voltage risk, line loading, and network losses in the MVP.
    """

    def __init__(self, grid: GridCase):
        self.grid = grid
        self.children: Dict[int, List[Branch]] = {bus: [] for bus in grid.buses}
        self.parent: Dict[int, Branch] = {}
        for branch in grid.branches:
            self.children[branch.from_bus].append(branch)
            self.parent[branch.to_bus] = branch

    def validate(self, net_load_kw: Dict[int, float]) -> Dict[str, object]:
        p_load = {bus: self.grid.base_load_kw.get(bus, 0.0) * 0.12 for bus in self.grid.buses}
        q_load = {bus: self.grid.base_load_kvar.get(bus, 0.0) * 0.12 for bus in self.grid.buses}
        for bus, value in net_load_kw.items():
            p_load[bus] = p_load.get(bus, 0.0) + value
            q_load[bus] = q_load.get(bus, 0.0) + abs(value) * 0.28

        downstream_p = {bus: p_load.get(bus, 0.0) for bus in self.grid.buses}
        downstream_q = {bus: q_load.get(bus, 0.0) for bus in self.grid.buses}
        for bus in reversed(self.grid.buses):
            if bus == self.grid.slack_bus or bus not in self.parent:
                continue
            branch = self.parent[bus]
            downstream_p[branch.from_bus] += downstream_p[bus]
            downstream_q[branch.from_bus] += downstream_q[bus]

        voltage = {self.grid.slack_bus: 1.0}
        line_loading: List[float] = []
        loss_kwh = 0.0
        queue = [self.grid.slack_bus]
        while queue:
            bus = queue.pop(0)
            for branch in self.children.get(bus, []):
                p = downstream_p[branch.to_bus]
                q = downstream_q[branch.to_bus]
                loading = (abs(p) + 0.45 * abs(q)) / 12.0
                line_loading.append(loading)
                drop = 0.000021 * (branch.r_ohm * max(p, 0.0) + branch.x_ohm * max(q, 0.0))
                boost = 0.000006 * abs(min(p, 0.0))
                voltage[branch.to_bus] = clamp(voltage[branch.from_bus] - drop + boost, 0.86, 1.08)
                loss_kwh += branch.r_ohm * (p * p + q * q) * 0.000003
                queue.append(branch.to_bus)

        min_v = min(voltage.values())
        max_v = max(voltage.values())
        violations = sum(1 for value in voltage.values() if value < self.grid.v_min_pu or value > self.grid.v_max_pu)
        return {
            "converged": True,
            "min_voltage_pu": round(min_v, 5),
            "max_voltage_pu": round(max_v, 5),
            "voltage_violation_count": violations,
            "network_loss_kwh": round(loss_kwh, 5),
            "line_loading_max_pct": round(max(line_loading) if line_loading else 0.0, 3),
            "notes": "Simplified radial DistFlow-style validation; replace with pandapower for numeric replication.",
        }


def candidate_prosumer_buses(grid: GridCase, count: int) -> List[int]:
    buses = grid.load_buses()
    if count >= len(buses):
        return buses
    stride = max(1, len(buses) // count)
    selected = buses[::stride][:count]
    while len(selected) < count:
        for bus in buses:
            if bus not in selected:
                selected.append(bus)
                if len(selected) == count:
                    break
    return selected

