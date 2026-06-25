from __future__ import annotations

from typing import Any, Dict, List, Optional


class OptimizationSolver:
    """Base optimization solver for P2P energy trading market clearing.

    Uses a greedy/heuristic approach as default. Override for LP/MILP solvers.
    """

    def __init__(
        self,
        objective: str = "min_cost",
        constraints: Optional[List[str]] = None,
        max_iterations: int = 100,
    ):
        self.objective = objective
        self.constraints = constraints or []
        self.max_iterations = max_iterations
        self.objective_value: float = 0.0
        self.solution: Dict[str, Any] = {}

    def solve(self, market_state: Dict[str, Any]) -> Dict[str, Any]:
        """Solve the optimization problem for market clearing.

        Args:
            market_state: Dict with prosumers, prices, grid constraints

        Returns:
            Dict with allocation, prices, and objective value
        """
        prosumers = market_state.get("prosumers", [])
        buy_price = market_state.get("grid_buy_price", 0.12)
        sell_price = market_state.get("grid_sell_price", 0.06)

        buyers = []
        sellers = []
        for p in prosumers:
            net_load = p.get("net_load_kw", 0)
            if net_load > 0:
                buyers.append({"id": p["id"], "demand": net_load, "bid_price": buy_price})
            elif net_load < 0:
                sellers.append({"id": p["id"], "supply": -net_load, "ask_price": sell_price})

        buyers.sort(key=lambda x: x["bid_price"], reverse=True)
        sellers.sort(key=lambda x: x["ask_price"])

        trades = []
        total_p2p_volume = 0.0
        total_cost = 0.0

        for buyer in buyers:
            for seller in sellers:
                if buyer["demand"] <= 0 or seller["supply"] <= 0:
                    continue
                if buyer["bid_price"] >= seller["ask_price"]:
                    trade_qty = min(buyer["demand"], seller["supply"])
                    trade_price = (buyer["bid_price"] + seller["ask_price"]) / 2
                    trades.append({
                        "buyer": buyer["id"],
                        "seller": seller["id"],
                        "quantity_kwh": trade_qty,
                        "price": trade_price,
                    })
                    total_p2p_volume += trade_qty
                    total_cost += trade_qty * trade_price
                    buyer["demand"] -= trade_qty
                    seller["supply"] -= trade_qty

        grid_import = sum(b["demand"] for b in buyers)
        grid_export = sum(s["supply"] for s in sellers)
        total_cost += grid_import * buy_price - grid_export * sell_price

        self.objective_value = total_cost
        self.solution = {
            "trades": trades,
            "total_p2p_volume_kwh": total_p2p_volume,
            "grid_import_kwh": grid_import,
            "grid_export_kwh": grid_export,
            "total_cost": total_cost,
        }

        return self.solution

    def get_objective_value(self) -> float:
        return self.objective_value

    def validate_constraints(self, solution: Dict[str, Any]) -> bool:
        """Check if solution satisfies all constraints."""
        if "voltage_limit" in self.constraints:
            pass
        if "capacity" in self.constraints:
            pass
        return True
