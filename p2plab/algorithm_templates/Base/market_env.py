from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple


class MarketEnvironment:
    def __init__(
        self,
        prosumer_count: int = 8,
        horizon_hours: int = 24,
        grid_case: str = "ieee33",
        random_seed: int = 42,
    ):
        self.prosumer_count = prosumer_count
        self.horizon_hours = horizon_hours
        self.grid_case = grid_case
        self.random_seed = random_seed
        self.rng = random.Random(random_seed)
        self.current_hour = 0
        self.grid_buy_price = 0.12
        self.grid_sell_price = 0.06
        self._init_prosumers()
        self._init_price_curve()

    def _init_prosumers(self) -> None:
        self.prosumers = []
        for i in range(self.prosumer_count):
            base_load = 1.5 + self.rng.random() * 2.5
            pv_capacity = 1.0 + self.rng.random() * 3.0
            battery_capacity = 0.0
            if self.rng.random() > 0.5:
                battery_capacity = 5.0 + self.rng.random() * 10.0
            self.prosumers.append({
                "id": i,
                "base_load": base_load,
                "pv_capacity": pv_capacity,
                "battery_capacity": battery_capacity,
                "battery_soc": battery_capacity * 0.5 if battery_capacity > 0 else 0.0,
            })

    def _init_price_curve(self) -> None:
        self.buy_prices = []
        self.sell_prices = []
        for h in range(24):
            hour_factor = 1.0 + 0.3 * math.sin(2 * math.pi * (h - 6) / 24)
            self.buy_prices.append(self.grid_buy_price * hour_factor)
            self.sell_prices.append(self.grid_sell_price * hour_factor * 0.8)

    def reset(self) -> Dict[str, Any]:
        self.current_hour = 0
        self.rng = random.Random(self.random_seed)
        for prosumer in self.prosumers:
            prosumer["battery_soc"] = prosumer["battery_capacity"] * 0.5 if prosumer["battery_capacity"] > 0 else 0.0
        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        hour = self.current_hour % 24
        load_profile = {}
        pv_profile = {}
        prosumer_states = []

        for i, prosumer in enumerate(self.prosumers):
            load = self._compute_load(i, hour)
            pv = self._compute_pv(i, hour)
            net_load = load - pv
            load_profile[i] = load
            pv_profile[i] = pv
            prosumer_states.append({
                "id": i,
                "load_kw": load,
                "pv_kw": pv,
                "net_load_kw": net_load,
                "battery_soc_kwh": prosumer["battery_soc"],
                "battery_capacity_kwh": prosumer["battery_capacity"],
            })

        return {
            "hour": self.current_hour,
            "hour_of_day": hour,
            "grid_buy_price": self.buy_prices[hour],
            "grid_sell_price": self.sell_prices[hour],
            "prosumers": prosumer_states,
            "load_profile": load_profile,
            "pv_profile": pv_profile,
            "total_load_kw": sum(load_profile.values()),
            "total_pv_kw": sum(pv_profile.values()),
        }

    def _compute_load(self, prosumer_idx: int, hour: int) -> float:
        prosumer = self.prosumers[prosumer_idx]
        daily_pattern = 0.6 + 0.4 * math.sin(2 * math.pi * (hour - 18) / 24)
        noise = 0.9 + 0.2 * self.rng.random()
        return prosumer["base_load"] * max(daily_pattern, 0.3) * noise

    def _compute_pv(self, prosumer_idx: int, hour: int) -> float:
        prosumer = self.prosumers[prosumer_idx]
        if 6 <= hour <= 18:
            solar_pattern = math.sin(math.pi * (hour - 6) / 12)
            noise = 0.85 + 0.3 * self.rng.random()
            return prosumer["pv_capacity"] * solar_pattern * noise
        return 0.0

    def step(self, actions: Dict[int, Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, float], bool, Dict[str, Any]]:
        hour = self.current_hour % 24
        buy_price = self.buy_prices[hour]
        sell_price = self.sell_prices[hour]

        p2p_trades = []
        total_p2p_volume = 0.0
        costs = {}
        grid_import = 0.0
        grid_export = 0.0

        buy_bids = []
        sell_bids = []
        for pid, action in actions.items():
            prosumer = self.prosumers[pid]
            load = self._compute_load(pid, hour)
            pv = self._compute_pv(pid, hour)
            net = load - pv

            battery_action = action.get("battery_kw", 0.0)
            if prosumer["battery_capacity"] > 0:
                max_charge = prosumer["battery_capacity"] - prosumer["battery_soc"]
                max_discharge = prosumer["battery_soc"]
                battery_action = max(-max_discharge, min(max_charge, battery_action))
                prosumer["battery_soc"] += battery_action
                net += battery_action

            bid_price = action.get("bid_price", buy_price if net > 0 else sell_price)
            bid_quantity = abs(net)

            if net > 0:
                buy_bids.append({"prosumer": pid, "price": bid_price, "quantity": bid_quantity, "net": net})
            else:
                sell_bids.append({"prosumer": pid, "price": bid_price, "quantity": bid_quantity, "net": net})

        buy_bids.sort(key=lambda x: x["price"], reverse=True)
        sell_bids.sort(key=lambda x: x["price"])

        matched = {}
        for buy in buy_bids:
            for sell in sell_bids:
                if buy["price"] >= sell["price"] and buy["quantity"] > 0 and sell["quantity"] > 0:
                    trade_qty = min(buy["quantity"], sell["quantity"])
                    trade_price = (buy["price"] + sell["price"]) / 2
                    p2p_trades.append({
                        "buyer": buy["prosumer"],
                        "seller": sell["prosumer"],
                        "quantity_kwh": trade_qty,
                        "price": trade_price,
                    })
                    total_p2p_volume += trade_qty
                    buy["quantity"] -= trade_qty
                    sell["quantity"] -= trade_qty

        for buy in buy_bids:
            remaining = buy["net"] - (buy["net"] - buy["quantity"])
            grid_cost = buy["quantity"] * buy_price
            costs[buy["prosumer"]] = costs.get(buy["prosumer"], 0.0) + grid_cost
            grid_import += buy["quantity"]

        for sell in sell_bids:
            revenue = sell["quantity"] * sell_price
            costs[sell["prosumer"]] = costs.get(sell["prosumer"], 0.0) - revenue
            grid_export += sell["quantity"]

        for trade in p2p_trades:
            costs[trade["buyer"]] = costs.get(trade["buyer"], 0.0) + trade["quantity_kwh"] * trade["price"]
            costs[trade["seller"]] = costs.get(trade["seller"], 0.0) - trade["quantity_kwh"] * trade["price"]

        total_cost = sum(costs.values())

        self.current_hour += 1
        done = self.current_hour >= self.horizon_hours

        next_state = self.get_state() if not done else {}
        info = {
            "p2p_trades": p2p_trades,
            "total_p2p_volume_kwh": total_p2p_volume,
            "grid_import_kwh": grid_import,
            "grid_export_kwh": grid_export,
            "prosumer_costs": costs,
            "hour": self.current_hour - 1,
        }

        return next_state, {"total_cost": total_cost, **costs}, done, info

    def get_grid_state(self) -> Dict[str, Any]:
        state = self.get_state()
        return {
            "load_profile": state["load_profile"],
            "pv_profile": state["pv_profile"],
            "hour": state["hour_of_day"],
        }
