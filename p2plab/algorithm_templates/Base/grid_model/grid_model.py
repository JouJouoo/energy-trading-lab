from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs"


class GridModel:
    def __init__(self, grid_case: str = "ieee33"):
        self.grid_case = grid_case
        self.config = self._load_config()
        self.net = None
        self._try_pandapower()

    def _load_config(self) -> Dict[str, Any]:
        config_path = CONFIG_DIR / f"{self.grid_case}_config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        if self.grid_case == "ieee33":
            return {
                "bus_count": 33,
                "line_count": 32,
                "base_kv": 12.66,
                "substation_bus": 0,
                "voltage_limits": [0.95, 1.05],
            }
        else:
            return {
                "bus_count": 69,
                "line_count": 68,
                "base_kv": 12.66,
                "substation_bus": 0,
                "voltage_limits": [0.95, 1.05],
            }

    def _try_pandapower(self) -> None:
        try:
            import pandapower as pp
            import pandapower.networks as pn

            self.net = pp.create_empty_network()
            if self.grid_case == "ieee33":
                self._build_ieee33(pp)
            else:
                self._build_ieee69(pp)
            self.has_pandapower = True
        except ImportError:
            self.has_pandapower = False

    def _build_ieee33(self, pp) -> None:
        n_bus = 33
        for i in range(n_bus):
            pp.create_bus(self.net, vn_kv=12.66, name=f"bus_{i}")
        pp.create_ext_grid(self.net, bus=0, vm_pu=1.0)
        line_data = [
            (0, 1, 0.0922, 0.0470),
            (1, 2, 0.4930, 0.2511),
            (2, 3, 0.3660, 0.1864),
            (3, 4, 0.3811, 0.1941),
            (4, 5, 0.8190, 0.7070),
            (5, 6, 0.1872, 0.6188),
            (6, 7, 1.7114, 1.2351),
            (7, 8, 1.0300, 0.7400),
            (8, 9, 1.0440, 0.7400),
            (9, 10, 0.1966, 0.0650),
            (10, 11, 0.3744, 0.1238),
            (11, 12, 1.4680, 1.1550),
            (12, 13, 0.5416, 0.7129),
            (13, 14, 0.5910, 0.5260),
            (14, 15, 0.7463, 0.5450),
            (15, 16, 1.2890, 1.7210),
            (16, 17, 0.7320, 0.5740),
            (17, 18, 0.1640, 0.1565),
            (18, 19, 1.5042, 1.3554),
            (19, 20, 0.4095, 0.4784),
            (20, 21, 0.7089, 0.9373),
            (21, 22, 0.4512, 0.3083),
            (22, 23, 0.8980, 0.7091),
            (23, 24, 0.8960, 0.7011),
            (24, 25, 0.2030, 0.1034),
            (25, 26, 0.2842, 0.1447),
            (26, 27, 1.0590, 0.9337),
            (27, 28, 0.4873, 0.3967),
            (28, 29, 0.7806, 0.6616),
            (29, 30, 0.1941, 0.1654),
            (30, 31, 0.2199, 0.1845),
            (31, 32, 0.3202, 0.2685),
        ]
        for from_bus, to_bus, r_ohm, x_ohm in line_data:
            pp.create_line_from_parameters(
                self.net,
                from_bus=from_bus,
                to_bus=to_bus,
                length_km=1.0,
                r_ohm_per_km=r_ohm,
                x_ohm_per_km=x_ohm,
                c_nf_per_km=0.0,
                max_i_ka=1.0,
            )

    def _build_ieee69(self, pp) -> None:
        n_bus = 69
        for i in range(n_bus):
            pp.create_bus(self.net, vn_kv=12.66, name=f"bus_{i}")
        pp.create_ext_grid(self.net, bus=0, vm_pu=1.0)
        line_data = [
            (0, 1, 0.0005, 0.0012),
            (1, 2, 0.0034, 0.0084),
            (2, 3, 0.0038, 0.0093),
            (3, 4, 0.0038, 0.0093),
            (4, 5, 0.0038, 0.0093),
            (5, 6, 0.0038, 0.0093),
            (6, 7, 0.0038, 0.0093),
            (7, 8, 0.0038, 0.0093),
            (8, 9, 0.0038, 0.0093),
            (9, 10, 0.0038, 0.0093),
        ]
        for from_bus, to_bus, r_ohm, x_ohm in line_data:
            pp.create_line_from_parameters(
                self.net,
                from_bus=from_bus,
                to_bus=to_bus,
                length_km=1.0,
                r_ohm_per_km=r_ohm,
                x_ohm_per_km=x_ohm,
                c_nf_per_km=0.0,
                max_i_ka=1.0,
            )

    def run_power_flow(self, load_profile: Dict[int, float], pv_profile: Dict[int, float]) -> Dict[str, Any]:
        if not self.has_pandapower or self.net is None:
            return self._approximate_power_flow(load_profile, pv_profile)

        import pandapower as pp

        for bus in range(self.config["bus_count"]):
            p_kw = load_profile.get(bus, 0.0) - pv_profile.get(bus, 0.0)
            if bus < len(self.net.load):
                self.net.load.p_kw[bus] = max(p_kw, 0)
                self.net.load.q_kvar[bus] = max(p_kw, 0) * 0.2
            else:
                pp.create_load(self.net, bus=bus, p_kw=max(p_kw, 0), q_kvar=max(p_kw, 0) * 0.2)

        try:
            pp.runpp(self.net, algorithm="nr")
            voltages = self.net.res_bus.vm_pu.tolist()
            converged = True
            loss_kw = float(self.net.res_ext_grid.p_kw.sum()) - sum(load_profile.values()) + sum(pv_profile.values())
        except Exception:
            converged = False
            voltages = [1.0] * self.config["bus_count"]
            loss_kw = 0.0

        return {
            "converged": converged,
            "voltages_pu": voltages,
            "min_voltage_pu": min(voltages),
            "max_voltage_pu": max(voltages),
            "voltage_violation_count": sum(
                1 for v in voltages
                if v < self.config["voltage_limits"][0] or v > self.config["voltage_limits"][1]
            ),
            "network_loss_kwh": max(loss_kw, 0.0),
            "line_loading_max_pct": 0.0,
        }

    def _approximate_power_flow(self, load_profile: Dict[int, float], pv_profile: Dict[int, float]) -> Dict[str, Any]:
        total_load = sum(load_profile.values())
        total_pv = sum(pv_profile.values())
        net_load = total_load - total_pv
        n_bus = self.config["bus_count"]

        voltages = []
        v_min, v_max = self.config["voltage_limits"]
        for bus in range(n_bus):
            distance = bus / max(n_bus - 1, 1)
            drop = 0.03 * distance * (net_load / max(total_load, 1.0))
            v = 1.0 - drop
            voltages.append(v)

        loss_est = 0.02 * abs(net_load)

        return {
            "converged": True,
            "voltages_pu": voltages,
            "min_voltage_pu": min(voltages),
            "max_voltage_pu": max(voltages),
            "voltage_violation_count": sum(
                1 for v in voltages if v < v_min or v > v_max
            ),
            "network_loss_kwh": loss_est,
            "line_loading_max_pct": min(100.0, abs(net_load) * 80 / max(total_load, 100.0)),
        }

    def get_voltage_profile(self) -> List[float]:
        if self.has_pandapower and self.net is not None:
            import pandapower as pp
            return self.net.res_bus.vm_pu.tolist()
        return [1.0] * self.config["bus_count"]

    def get_network_loss(self) -> float:
        if self.has_pandapower and self.net is not None:
            return float(self.net.res_ext_grid.p_kw.sum())
        return 0.0
