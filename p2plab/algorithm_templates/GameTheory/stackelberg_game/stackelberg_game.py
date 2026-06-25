from __future__ import annotations

from typing import Any, Dict, List, Optional


class StackelbergGameEngine:
    """Stackelberg game engine for leader-follower P2P energy pricing.

    Leader sets price, followers respond with demand/supply adjustments.
    """

    def __init__(
        self,
        n_followers: int = 5,
        leader_id: int = 0,
        max_iterations: int = 50,
        convergence_threshold: float = 0.001,
    ):
        self.n_followers = n_followers
        self.leader_id = leader_id
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.leader_price: float = 0.10
        self.follower_responses: Dict[int, Dict[str, float]] = {}
        self.equilibrium_reached: bool = False

    def set_leader_price(self, price: float) -> None:
        """Set the leader's price."""
        self.leader_price = price

    def get_follower_response(self, follower_id: int, market_state: Dict[str, Any]) -> Dict[str, float]:
        """Compute a follower's best response to the leader price.

        Args:
            follower_id: ID of the follower
            market_state: Current market state

        Returns:
            Dict with demand, supply, utility
        """
        prosumers = market_state.get("prosumers", [])
        follower = next((p for p in prosumers if p["id"] == follower_id), None)
        if not follower:
            return {"demand": 0.0, "supply": 0.0, "utility": 0.0}

        net_load = follower.get("net_load_kw", 0)
        grid_buy_price = market_state.get("grid_buy_price", 0.12)
        grid_sell_price = market_state.get("grid_sell_price", 0.06)

        if net_load > 0:
            if self.leader_price < grid_buy_price:
                demand = net_load
                supply = 0.0
            else:
                demand = 0.0
                supply = 0.0
            utility = (grid_buy_price - self.leader_price) * demand
        else:
            if self.leader_price > grid_sell_price:
                supply = -net_load
                demand = 0.0
            else:
                demand = 0.0
                supply = 0.0
            utility = (self.leader_price - grid_sell_price) * supply

        self.follower_responses[follower_id] = {
            "demand": demand,
            "supply": supply,
            "utility": utility,
        }
        return self.follower_responses[follower_id]

    def find_equilibrium(self, market_state: Dict[str, Any]) -> Dict[str, Any]:
        """Find Stackelberg equilibrium price.

        Uses binary search over leader price to maximize leader revenue.
        """
        follower_ids = [p["id"] for p in market_state.get("prosumers", []) if p["id"] != self.leader_id]
        grid_buy_price = market_state.get("grid_buy_price", 0.12)
        grid_sell_price = market_state.get("grid_sell_price", 0.06)

        low = grid_sell_price
        high = grid_buy_price
        best_price = (low + high) / 2
        best_leader_utility = 0.0

        for _ in range(self.max_iterations):
            mid = (low + high) / 2
            self.set_leader_price(mid)

            total_demand = 0.0
            total_supply = 0.0
            for fid in follower_ids:
                resp = self.get_follower_response(fid, market_state)
                total_demand += resp["demand"]
                total_supply += resp["supply"]

            trade_volume = min(total_demand, total_supply)
            leader_utility = trade_volume * (mid - grid_sell_price)

            if leader_utility > best_leader_utility:
                best_leader_utility = leader_utility
                best_price = mid

            if total_demand > total_supply:
                high = mid
            else:
                low = mid

            if high - low < self.convergence_threshold:
                self.equilibrium_reached = True
                break

        self.leader_price = best_price
        for fid in follower_ids:
            self.get_follower_response(fid, market_state)

        total_demand = sum(r["demand"] for r in self.follower_responses.values())
        total_supply = sum(r["supply"] for r in self.follower_responses.values())

        return {
            "equilibrium_price": best_price,
            "equilibrium_reached": self.equilibrium_reached,
            "leader_id": self.leader_id,
            "leader_utility": best_leader_utility,
            "total_demand": total_demand,
            "total_supply": total_supply,
            "trade_volume": min(total_demand, total_supply),
            "follower_responses": dict(self.follower_responses),
        }
