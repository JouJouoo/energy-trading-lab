from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .grid import SimplePowerFlowValidator, candidate_prosumer_buses, load_grid_case
from .schemas import ExperimentRecipe, GridValidationResult, SimulationMetrics
from .utils import jain_fairness


GRID_BUY_PRICE = [0.62, 0.60, 0.58, 0.56, 0.55, 0.58, 0.70, 0.82, 0.91, 0.88, 0.80, 0.76,
                  0.72, 0.70, 0.74, 0.86, 0.98, 1.08, 1.02, 0.92, 0.84, 0.76, 0.68, 0.63]
GRID_SELL_PRICE = [0.30, 0.30, 0.29, 0.28, 0.28, 0.29, 0.34, 0.38, 0.42, 0.41, 0.38, 0.36,
                   0.35, 0.35, 0.36, 0.40, 0.45, 0.50, 0.48, 0.43, 0.39, 0.36, 0.33, 0.31]
CARBON_INTENSITY = [0.58, 0.57, 0.56, 0.56, 0.55, 0.54, 0.52, 0.50, 0.49, 0.47, 0.45, 0.43,
                    0.42, 0.42, 0.44, 0.48, 0.53, 0.59, 0.62, 0.61, 0.60, 0.59, 0.58, 0.58]


@dataclass
class Prosumer:
    prosumer_id: str
    bus: int
    pv_kw: float
    battery_kwh: float
    load_profile_kw: List[float]
    pv_profile_kw: List[float]
    soc_kwh: float = 0.0
    savings: float = 0.0

    def net_demand(self, hour: int) -> float:
        return self.load_profile_kw[hour % len(self.load_profile_kw)] - self.pv_profile_kw[hour % len(self.pv_profile_kw)]


@dataclass
class Bid:
    prosumer_id: str
    bus: int
    quantity_kwh: float
    price: float


@dataclass
class TradeSummary:
    p2p_volume_kwh: float = 0.0
    p2p_value: float = 0.0
    grid_import_kwh: float = 0.0
    grid_export_kwh: float = 0.0
    grid_cost: float = 0.0
    feed_in_revenue: float = 0.0
    bus_grid_power: Dict[int, float] = field(default_factory=dict)
    individual_savings: Dict[str, float] = field(default_factory=dict)


def default_recipe(grid_case: str = "ieee33", strategies: List[str] = None) -> ExperimentRecipe:
    return ExperimentRecipe(
        name="energy-trading-lab-default-experiment",
        grid_case=grid_case,
        horizon_hours=24,
        prosumer_count=8 if grid_case.lower().endswith("33") else 12,
        strategies=strategies or ["no_trading", "rule_double_auction", "optimization_clearing", "rl_bidding"],
        random_seed=42,
        training_episodes=60,
        voltage_limits=[0.95, 1.05],
        notes="MVP synthetic load/PV curves for paper reproduction scaffolding.",
        experiment_depth="quick",
        training_log_interval=50,
    )


def generate_prosumers(recipe: ExperimentRecipe) -> List[Prosumer]:
    grid = load_grid_case(recipe.grid_case)
    rng = random.Random(recipe.random_seed)
    buses = candidate_prosumer_buses(grid, recipe.prosumer_count)
    prosumers: List[Prosumer] = []
    for index, bus in enumerate(buses):
        load_base = 2.8 + 0.25 * (index % 4) + rng.random() * 0.25
        pv_kw = 2.0 + 0.35 * (index % 5) + rng.random() * 0.3
        load_profile = []
        pv_profile = []
        for hour in range(recipe.horizon_hours):
            morning = 0.7 * math.exp(-((hour - 8) ** 2) / 20.0)
            evening = 1.1 * math.exp(-((hour - 19) ** 2) / 14.0)
            noise = 0.08 * rng.random()
            load_profile.append(round(load_base * (0.55 + morning + evening + noise), 4))
            solar = max(0.0, math.sin((hour - 6) / 12.0 * math.pi))
            pv_profile.append(round(pv_kw * solar * (0.85 + 0.12 * rng.random()), 4))
        prosumers.append(
            Prosumer(
                prosumer_id="P%d" % (index + 1),
                bus=bus,
                pv_kw=pv_kw,
                battery_kwh=4.0 + index % 3,
                load_profile_kw=load_profile,
                pv_profile_kw=pv_profile,
                soc_kwh=2.0,
            )
        )
    return prosumers


def train_lightweight_q_policy(
    prosumers: List[Prosumer],
    recipe: ExperimentRecipe,
    strategy: str = "rl_bidding",
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[Dict[str, Dict[str, int]], Dict[str, object]]:
    """Train a tiny tabular policy for demo-grade RL bidding.

    States are coarse surplus/deficit and price-period buckets. Actions are
    conservative, neutral, and aggressive bid/ask margins.
    """

    started = time.perf_counter()
    rng = random.Random(recipe.random_seed + 11)
    actions = [-1, 0, 1]
    q_table: Dict[str, Dict[str, List[float]]] = {}
    for prosumer in prosumers:
        q_table[prosumer.prosumer_id] = {}
        for state in ("surplus_low", "surplus_high", "deficit_low", "deficit_high"):
            q_table[prosumer.prosumer_id][state] = [0.0, 0.0, 0.0]

    curve: List[Dict[str, float]] = []
    log_interval = max(1, int(recipe.training_log_interval or 50))
    final_avg_reward = 0.0
    for episode in range(recipe.training_episodes):
        episode_reward = 0.0
        updates = 0
        for hour in range(recipe.horizon_hours):
            high_price = GRID_BUY_PRICE[hour % 24] > 0.82
            for prosumer in prosumers:
                net = prosumer.net_demand(hour)
                state = ("deficit" if net > 0 else "surplus") + ("_high" if high_price else "_low")
                action_idx = rng.randrange(len(actions)) if rng.random() < 0.18 else max(
                    range(len(actions)), key=lambda idx: q_table[prosumer.prosumer_id][state][idx]
                )
                action = actions[action_idx]
                if net > 0:
                    reward = (0.06 + 0.025 * action) if high_price else (0.03 + 0.01 * action)
                else:
                    reward = (0.05 - 0.015 * action) if high_price else (0.02 - 0.005 * action)
                episode_reward += reward
                updates += 1
                q_table[prosumer.prosumer_id][state][action_idx] = (
                    0.82 * q_table[prosumer.prosumer_id][state][action_idx] + 0.18 * reward
                )
        final_avg_reward = episode_reward / max(1, updates)
        if episode == 0 or (episode + 1) % log_interval == 0 or episode + 1 == recipe.training_episodes:
            elapsed_now = time.perf_counter() - started
            curve.append(
                {
                    "episode": float(episode + 1),
                    "avg_reward": round(final_avg_reward, 6),
                    "epsilon": 0.18,
                }
            )
            if progress_callback is not None:
                progress_callback(
                    {
                        "event": "training_progress",
                        "strategy": strategy,
                        "episode": episode + 1,
                        "episodes": recipe.training_episodes,
                        "avg_reward": round(final_avg_reward, 6),
                        "epsilon": 0.18,
                        "elapsed_sec": round(elapsed_now, 4),
                        "depth": recipe.experiment_depth,
                    }
                )

    learned: Dict[str, Dict[str, int]] = {}
    for prosumer in prosumers:
        learned[prosumer.prosumer_id] = {}
        for state, values in q_table[prosumer.prosumer_id].items():
            learned[prosumer.prosumer_id][state] = actions[max(range(len(values)), key=lambda idx: values[idx])]
    elapsed = time.perf_counter() - started
    diagnostics = {
        "episodes": recipe.training_episodes,
        "elapsed_sec": round(elapsed, 4),
        "final_avg_reward": round(final_avg_reward, 6),
        "curve": curve,
    }
    return learned, diagnostics


def price_for_strategy(
    strategy: str,
    prosumer: Prosumer,
    net_demand: float,
    hour: int,
    q_policy: Dict[str, Dict[str, int]],
    params: Dict[str, float],
) -> float:
    buy = GRID_BUY_PRICE[hour % 24]
    sell = GRID_SELL_PRICE[hour % 24]
    if strategy == "optimization_clearing":
        return (buy + sell) / 2.0
    if strategy in ("rl_bidding", "proposed_method"):
        high_price = buy > 0.82
        state = ("deficit" if net_demand > 0 else "surplus") + ("_high" if high_price else "_low")
        action = q_policy.get(prosumer.prosumer_id, {}).get(state, 0)
        rl_aggressiveness = float(params.get("rl_aggressiveness", 1.0))
        voltage_margin = 0.045 * float(params.get("voltage_weight", 0.0)) if strategy == "proposed_method" and hour in (17, 18, 19, 20) else 0.0
        carbon_margin = 0.025 * float(params.get("carbon_weight", 0.0)) if strategy == "proposed_method" and CARBON_INTENSITY[hour % 24] > 0.56 else 0.0
        leader_bias = 0.025 * float(params.get("price_leadership", 0.0)) if strategy == "proposed_method" else 0.0
        if net_demand > 0:
            return buy - 0.025 + 0.04 * action * rl_aggressiveness - voltage_margin - carbon_margin + leader_bias
        return sell + 0.035 - 0.025 * action * rl_aggressiveness + voltage_margin + carbon_margin + leader_bias
    if net_demand > 0:
        return buy - 0.11
    return sell + 0.11


def quantity_factor(
    strategy: str,
    prosumer: Prosumer,
    net_demand: float,
    hour: int,
    grid_bus_count: int,
    params: Dict[str, float],
) -> float:
    if strategy == "rule_double_auction":
        return 0.55
    if strategy == "optimization_clearing":
        return 1.0
    if strategy == "rl_bidding":
        factor = 0.72 * float(params.get("rl_aggressiveness", 1.0))
        if GRID_BUY_PRICE[hour % 24] > 0.82 or (net_demand < 0 and 9 <= hour <= 15):
            factor += 0.22
        return min(1.0, factor)
    if strategy == "proposed_method":
        factor = float(params.get("trading_aggressiveness", 0.82))
        feeder_tail = prosumer.bus > int(grid_bus_count * 0.72)
        evening_peak = hour in (17, 18, 19, 20)
        if feeder_tail and evening_peak:
            factor -= 0.45 * float(params.get("risk_sensitivity", 0.0))
        if CARBON_INTENSITY[hour % 24] < 0.48 and net_demand < 0:
            factor += 0.22 * float(params.get("carbon_weight", 0.0))
        if float(params.get("fairness_weight", 0.0)) > 0 and prosumer.bus % 3 == 0:
            factor -= 0.05
        return max(0.35, min(0.96, factor))
    return 1.0


def strategy_explanation(strategy: str) -> str:
    explanations = {
        "no_trading": "Tariff-only baseline; all surplus/deficit is settled with the external grid.",
        "rule_double_auction": "Conservative rule baseline with fixed bid/ask margins and partial willingness to trade.",
        "optimization_clearing": "Deterministic clearing baseline that exposes most flexible energy to the P2P market.",
        "rl_bidding": "Lightweight tabular RL-style policy adjusts bid aggressiveness by surplus/deficit and tariff state.",
        "proposed_method": "Voltage/carbon-aware variant reduces risky peak-hour feeder-tail trades and favors lower-carbon periods.",
    }
    return explanations.get(strategy, "Custom strategy scaffold.")


def clear_double_auction(buyers: List[Bid], sellers: List[Bid]) -> Tuple[float, float, Dict[str, float], Dict[str, float]]:
    buyers = sorted(buyers, key=lambda bid: bid.price, reverse=True)
    sellers = sorted(sellers, key=lambda bid: bid.price)
    bought = {bid.prosumer_id: 0.0 for bid in buyers}
    sold = {bid.prosumer_id: 0.0 for bid in sellers}
    volume = 0.0
    value = 0.0
    b_idx = 0
    s_idx = 0
    while b_idx < len(buyers) and s_idx < len(sellers):
        buyer = buyers[b_idx]
        seller = sellers[s_idx]
        if buyer.price < seller.price:
            break
        qty = min(buyer.quantity_kwh, seller.quantity_kwh)
        if qty <= 1e-9:
            if buyer.quantity_kwh <= 1e-9:
                b_idx += 1
            if seller.quantity_kwh <= 1e-9:
                s_idx += 1
            continue
        clearing_price = (buyer.price + seller.price) / 2.0
        volume += qty
        value += qty * clearing_price
        bought[buyer.prosumer_id] += qty
        sold[seller.prosumer_id] += qty
        buyer.quantity_kwh -= qty
        seller.quantity_kwh -= qty
        if buyer.quantity_kwh <= 1e-9:
            b_idx += 1
        if seller.quantity_kwh <= 1e-9:
            s_idx += 1
    return volume, value, bought, sold


def simulate_strategy(
    strategy: str,
    recipe: ExperimentRecipe,
    prosumers: List[Prosumer],
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[SimulationMetrics, List[Dict[str, float]], List[Dict[str, float]]]:
    grid = load_grid_case(recipe.grid_case)
    validator = SimplePowerFlowValidator(grid)
    training_diag: Dict[str, object] = {"episodes": 0, "elapsed_sec": 0.0, "final_avg_reward": 0.0, "curve": []}
    if progress_callback is not None:
        progress_callback(
            {
                "event": "strategy_start",
                "strategy": strategy,
                "depth": recipe.experiment_depth,
                "horizon_hours": recipe.horizon_hours,
                "training_episodes": recipe.training_episodes if strategy in ("rl_bidding", "proposed_method") else 0,
            }
        )
    if strategy in ("rl_bidding", "proposed_method"):
        q_policy, training_diag = train_lightweight_q_policy(
            prosumers,
            recipe,
            strategy=strategy,
            progress_callback=progress_callback,
        )
    else:
        q_policy = {}
    params = recipe.strategy_parameters or {}

    totals = TradeSummary()
    hourly_grid_results: List[Dict[str, object]] = []
    hourly_rows: List[Dict[str, float]] = []

    for hour in range(recipe.horizon_hours):
        buy_price = GRID_BUY_PRICE[hour % 24]
        sell_price = GRID_SELL_PRICE[hour % 24]
        buyers: List[Bid] = []
        sellers: List[Bid] = []
        net_by_prosumer: Dict[str, float] = {}
        bus_grid_power: Dict[int, float] = {}

        for prosumer in prosumers:
            net = prosumer.net_demand(hour)
            net_by_prosumer[prosumer.prosumer_id] = net
            if strategy == "no_trading":
                continue
            price = price_for_strategy(strategy, prosumer, net, hour, q_policy, params)
            factor = quantity_factor(strategy, prosumer, net, hour, grid.bus_count, params)
            if net > 0:
                buyers.append(Bid(prosumer.prosumer_id, prosumer.bus, net * factor, price))
            elif net < 0:
                sellers.append(Bid(prosumer.prosumer_id, prosumer.bus, abs(net) * factor, price))

        p2p_volume, p2p_value, bought, sold = (0.0, 0.0, {}, {})
        if strategy != "no_trading":
            p2p_volume, p2p_value, bought, sold = clear_double_auction(buyers, sellers)

        for prosumer in prosumers:
            net = net_by_prosumer[prosumer.prosumer_id]
            p2p_bought = bought.get(prosumer.prosumer_id, 0.0)
            p2p_sold = sold.get(prosumer.prosumer_id, 0.0)
            if net > 0:
                grid_need = max(0.0, net - p2p_bought)
                totals.grid_import_kwh += grid_need
                totals.grid_cost += grid_need * buy_price
                bus_grid_power[prosumer.bus] = bus_grid_power.get(prosumer.bus, 0.0) + grid_need
                no_trade_cost = net * buy_price
                strategy_cost = grid_need * buy_price + p2p_bought * ((p2p_value / p2p_volume) if p2p_volume else buy_price)
                totals.individual_savings[prosumer.prosumer_id] = totals.individual_savings.get(prosumer.prosumer_id, 0.0) + max(0.0, no_trade_cost - strategy_cost)
            elif net < 0:
                surplus = abs(net)
                grid_export = max(0.0, surplus - p2p_sold)
                totals.grid_export_kwh += grid_export
                totals.feed_in_revenue += grid_export * sell_price
                bus_grid_power[prosumer.bus] = bus_grid_power.get(prosumer.bus, 0.0) - grid_export
                no_trade_revenue = surplus * sell_price
                strategy_revenue = grid_export * sell_price + p2p_sold * ((p2p_value / p2p_volume) if p2p_volume else sell_price)
                totals.individual_savings[prosumer.prosumer_id] = totals.individual_savings.get(prosumer.prosumer_id, 0.0) + max(0.0, strategy_revenue - no_trade_revenue)

        totals.p2p_volume_kwh += p2p_volume
        totals.p2p_value += p2p_value
        totals.bus_grid_power = bus_grid_power
        grid_result = validator.validate(bus_grid_power)
        hourly_grid_results.append(grid_result)
        hourly_rows.append(
            {
                "hour": hour,
                "p2p_volume_kwh": p2p_volume,
                "grid_import_kwh": sum(v for v in bus_grid_power.values() if v > 0),
                "grid_export_kwh": abs(sum(v for v in bus_grid_power.values() if v < 0)),
                "min_voltage_pu": float(grid_result["min_voltage_pu"]),
                "max_voltage_pu": float(grid_result["max_voltage_pu"]),
                "voltage_violation_count": float(grid_result["voltage_violation_count"]),
                "network_loss_kwh": float(grid_result["network_loss_kwh"]),
                "line_loading_max_pct": float(grid_result["line_loading_max_pct"]),
            }
        )

    carbon = sum(row["grid_import_kwh"] * CARBON_INTENSITY[int(row["hour"]) % 24] for row in hourly_rows)
    pv_total = sum(sum(p.pv_profile_kw[: recipe.horizon_hours]) for p in prosumers)
    renewable_self_consumption = (totals.p2p_volume_kwh / pv_total * 100.0) if pv_total else 0.0
    total_cost = totals.grid_cost - totals.feed_in_revenue
    validation = GridValidationResult(
        converged=all(bool(row["converged"]) for row in hourly_grid_results),
        min_voltage_pu=min(float(row["min_voltage_pu"]) for row in hourly_grid_results),
        max_voltage_pu=max(float(row["max_voltage_pu"]) for row in hourly_grid_results),
        voltage_violation_count=sum(int(row["voltage_violation_count"]) for row in hourly_grid_results),
        network_loss_kwh=sum(float(row["network_loss_kwh"]) for row in hourly_grid_results),
        line_loading_max_pct=max(float(row["line_loading_max_pct"]) for row in hourly_grid_results),
        notes="Aggregated over %d hourly validations." % recipe.horizon_hours,
    )
    voltage_risk = sum(
        max(0.0, 0.95 - float(row["min_voltage_pu"])) * 100.0
        + max(0.0, float(row["max_voltage_pu"]) - 1.05) * 100.0
        for row in hourly_rows
    )
    metrics = SimulationMetrics(
        strategy=strategy,
        total_cost=round(total_cost, 4),
        p2p_volume_kwh=round(totals.p2p_volume_kwh, 4),
        grid_import_kwh=round(totals.grid_import_kwh, 4),
        grid_export_kwh=round(totals.grid_export_kwh, 4),
        carbon_kg=round(carbon, 4),
        renewable_self_consumption_pct=round(min(100.0, renewable_self_consumption), 3),
        social_welfare=0.0,
        fairness_index=round(jain_fairness(totals.individual_savings.values()), 4),
        grid_validation=validation,
        voltage_risk_score=round(voltage_risk, 4),
        strategy_explanation=strategy_explanation(strategy),
        training_episodes=int(training_diag.get("episodes", 0) or 0),
        training_elapsed_sec=float(training_diag.get("elapsed_sec", 0.0) or 0.0),
        training_final_reward=float(training_diag.get("final_avg_reward", 0.0) or 0.0),
    )
    training_rows: List[Dict[str, float]] = []
    for row in training_diag.get("curve", []) or []:
        payload = dict(row)
        payload["strategy"] = strategy
        payload["elapsed_sec"] = round(
            metrics.training_elapsed_sec * (float(payload["episode"]) / max(1.0, float(metrics.training_episodes))),
            4,
        )
        training_rows.append(payload)
    if progress_callback is not None:
        progress_callback(
            {
                "event": "strategy_done",
                "strategy": strategy,
                "depth": recipe.experiment_depth,
                "total_cost": metrics.total_cost,
                "p2p_volume_kwh": metrics.p2p_volume_kwh,
                "training_episodes": metrics.training_episodes,
                "training_elapsed_sec": metrics.training_elapsed_sec,
            }
        )
    return metrics, hourly_rows, training_rows


def run_experiment_detailed(
    recipe: ExperimentRecipe,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[List[SimulationMetrics], Dict[str, List[Dict[str, float]]], List[Dict[str, float]]]:
    prosumers = generate_prosumers(recipe)
    strategy_rows: Dict[str, List[Dict[str, float]]] = {}
    training_rows: List[Dict[str, float]] = []
    metrics: List[SimulationMetrics] = []
    baseline_cost = None
    for strategy in recipe.strategies:
        strategy_metrics, rows, strategy_training_rows = simulate_strategy(
            strategy,
            recipe,
            prosumers,
            progress_callback=progress_callback,
        )
        if strategy == "no_trading":
            baseline_cost = strategy_metrics.total_cost
        if baseline_cost is not None:
            strategy_metrics.social_welfare = round(baseline_cost - strategy_metrics.total_cost, 4)
            if baseline_cost:
                strategy_metrics.cost_saving_pct = round((baseline_cost - strategy_metrics.total_cost) / baseline_cost * 100.0, 3)
        metrics.append(strategy_metrics)
        strategy_rows[strategy] = rows
        training_rows.extend(strategy_training_rows)
    return metrics, strategy_rows, training_rows


def run_experiment(recipe: ExperimentRecipe) -> Tuple[List[SimulationMetrics], Dict[str, List[Dict[str, float]]]]:
    metrics, strategy_rows, _training_rows = run_experiment_detailed(recipe)
    return metrics, strategy_rows
