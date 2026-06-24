from __future__ import annotations

from typing import Any, Dict, List, Optional


class RewardCalculator:
    """Base reward calculator for P2P energy trading.

    Computes reward/objective based on cost, P2P volume, and optional
    penalty terms. Override methods to add custom reward shaping.
    """

    def __init__(
        self,
        cost_weight: float = 1.0,
        p2p_weight: float = 0.0,
        carbon_weight: float = 0.0,
        voltage_weight: float = 0.0,
        fairness_weight: float = 0.0,
        network_loss_weight: float = 0.0,
    ):
        self.cost_weight = cost_weight
        self.p2p_weight = p2p_weight
        self.carbon_weight = carbon_weight
        self.voltage_weight = voltage_weight
        self.fairness_weight = fairness_weight
        self.network_loss_weight = network_loss_weight

    def compute_reward(
        self,
        prosumer_cost: float,
        info: Dict[str, Any],
        grid_result: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Compute per-step reward for a single prosumer.

        Args:
            prosumer_cost: Cost for this prosumer this step (positive = cost)
            info: Step info dict from environment
            grid_result: Power flow result, if available

        Returns:
            Reward value (higher is better)
        """
        reward = -self.cost_weight * prosumer_cost

        if self.p2p_weight > 0:
            p2p_volume = self._get_prosumer_p2p_volume(info, prosumer_cost)
            reward += self.p2p_weight * p2p_volume

        if self.carbon_weight > 0:
            carbon_penalty = self._compute_carbon_penalty(info)
            reward -= self.carbon_weight * carbon_penalty

        if self.voltage_weight > 0 and grid_result:
            voltage_penalty = self._compute_voltage_penalty(grid_result)
            reward -= self.voltage_weight * voltage_penalty

        if self.network_loss_weight > 0 and grid_result:
            loss_penalty = grid_result.get("network_loss_kwh", 0.0)
            reward -= self.network_loss_weight * loss_penalty

        return reward

    def compute_objective(
        self,
        total_cost: float,
        info: Dict[str, Any],
        grid_result: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Compute overall objective value (for optimization-based methods).

        Lower is better (minimization).
        """
        objective = self.cost_weight * total_cost

        if self.p2p_weight > 0:
            p2p_volume = info.get("total_p2p_volume_kwh", 0.0)
            objective -= self.p2p_weight * p2p_volume

        if self.carbon_weight > 0:
            carbon_penalty = self._compute_carbon_penalty(info)
            objective += self.carbon_weight * carbon_penalty

        if self.voltage_weight > 0 and grid_result:
            voltage_penalty = self._compute_voltage_penalty(grid_result)
            objective += self.voltage_weight * voltage_penalty

        if self.fairness_weight > 0:
            fairness_penalty = self._compute_fairness_penalty(info)
            objective += self.fairness_weight * fairness_penalty

        if self.network_loss_weight > 0 and grid_result:
            objective += self.network_loss_weight * grid_result.get("network_loss_kwh", 0.0)

        return objective

    def _get_prosumer_p2p_volume(self, info: Dict[str, Any], prosumer_id: int) -> float:
        """Get P2P trading volume for a specific prosumer."""
        trades = info.get("p2p_trades", [])
        volume = 0.0
        for trade in trades:
            if trade.get("buyer") == prosumer_id or trade.get("seller") == prosumer_id:
                volume += trade.get("quantity_kwh", 0.0)
        return volume

    def _compute_carbon_penalty(self, info: Dict[str, Any]) -> float:
        """Compute carbon emission penalty (kg CO2)."""
        grid_import = info.get("grid_import_kwh", 0.0)
        carbon_intensity = 0.5
        return grid_import * carbon_intensity

    def _compute_voltage_penalty(self, grid_result: Dict[str, Any]) -> float:
        """Compute voltage violation penalty."""
        violations = grid_result.get("voltage_violation_count", 0)
        return float(violations) * 10.0

    def _compute_fairness_penalty(self, info: Dict[str, Any]) -> float:
        """Compute fairness penalty based on cost distribution."""
        costs = list(info.get("prosumer_costs", {}).values())
        if len(costs) < 2:
            return 0.0
        mean_cost = sum(costs) / len(costs)
        variance = sum((c - mean_cost) ** 2 for c in costs) / len(costs)
        return variance / max(mean_cost ** 2, 1e-6)
