from __future__ import annotations

from typing import Any, Dict, List, Optional


class DoubleAuctionEngine:
    """Double auction engine for P2P energy trading.

    Implements continuous double auction with price matching.
    """

    def __init__(
        self,
        price_rule: str = "midpoint",
        matching_rule: str = "price_time",
    ):
        self.price_rule = price_rule
        self.matching_rule = matching_rule
        self.buy_orders: List[Dict[str, Any]] = []
        self.sell_orders: List[Dict[str, Any]] = []
        self.trades: List[Dict[str, Any]] = []
        self.clearing_price: float = 0.0

    def submit_bid(self, bid: Dict[str, Any]) -> None:
        """Submit a buy bid.

        Args:
            bid: Dict with id, price, quantity
        """
        self.buy_orders.append({
            "id": bid.get("prosumer_id", bid.get("id", 0)),
            "price": bid.get("price", 0.0),
            "quantity": bid.get("quantity", 0.0),
            "timestamp": bid.get("timestamp", 0),
        })

    def submit_ask(self, ask: Dict[str, Any]) -> None:
        """Submit a sell ask.

        Args:
            ask: Dict with id, price, quantity
        """
        self.sell_orders.append({
            "id": ask.get("prosumer_id", ask.get("id", 0)),
            "price": ask.get("price", 0.0),
            "quantity": ask.get("quantity", 0.0),
            "timestamp": ask.get("timestamp", 0),
        })

    def clear_market(self) -> Dict[str, Any]:
        """Clear the market and match orders.

        Returns:
            Dict with trades, clearing price, volume
        """
        self.buy_orders.sort(key=lambda x: (-x["price"], x["timestamp"]))
        self.sell_orders.sort(key=lambda x: (x["price"], x["timestamp"]))

        self.trades = []
        total_volume = 0.0
        prices = []

        buy_idx = 0
        sell_idx = 0

        while buy_idx < len(self.buy_orders) and sell_idx < len(self.sell_orders):
            buy = self.buy_orders[buy_idx]
            sell = self.sell_orders[sell_idx]

            if buy["price"] < sell["price"]:
                break

            trade_qty = min(buy["quantity"], sell["quantity"])
            if self.price_rule == "midpoint":
                trade_price = (buy["price"] + sell["price"]) / 2
            elif self.price_rule == "buy_bid":
                trade_price = buy["price"]
            elif self.price_rule == "sell_ask":
                trade_price = sell["price"]
            else:
                trade_price = (buy["price"] + sell["price"]) / 2

            self.trades.append({
                "buyer": buy["id"],
                "seller": sell["id"],
                "quantity_kwh": trade_qty,
                "price": trade_price,
            })
            total_volume += trade_qty
            prices.append(trade_price)

            buy["quantity"] -= trade_qty
            sell["quantity"] -= trade_qty

            if buy["quantity"] <= 0:
                buy_idx += 1
            if sell["quantity"] <= 0:
                sell_idx += 1

        if prices:
            self.clearing_price = sum(prices) / len(prices)

        return {
            "trades": self.trades,
            "clearing_price": self.clearing_price,
            "total_volume_kwh": total_volume,
            "n_trades": len(self.trades),
            "remaining_buy_demand": sum(b["quantity"] for b in self.buy_orders[buy_idx:]),
            "remaining_sell_supply": sum(s["quantity"] for s in self.sell_orders[sell_idx:]),
        }

    def reset(self) -> None:
        self.buy_orders = []
        self.sell_orders = []
        self.trades = []
        self.clearing_price = 0.0
