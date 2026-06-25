---
name: double_auction
family: Auction
display_name: Continuous Double Auction
file_name: double_auction.py
description: |
  Continuous double auction clearing. Each step collects bids and asks from
  the prosumer book, then matches them in price-time priority. P2P local
  trades first; the residual settles against the substation.
affected_modules: []
inputs:
  bids: list
  asks: list
parameters:
  min_spread: 0.01
  tie_break: price_time_priority
tags: [auction, double, baseline, market]
---

# Continuous Double Auction

> Family: **Auction** — Use as a market-mechanism baseline; the classical double auction with a substation residual.

## 1. Inputs

| Field | Type | Description |
|---|---|---|
| `bids` | `list[Bid]` | list of bid objects: `{prosumer_id, price, quantity_kw, ts}` |
| `asks` | `list[Ask]` | list of ask objects: `{prosumer_id, price, quantity_kw, ts}` |

## 2. Outputs

A list of `Trade` objects, each carrying `(buyer_id, seller_id, price, quantity_kw)`. The residual goes to the substation at the time-of-use price.

## 3. Hyperparameters

- `min_spread`: minimum spread between matched bid and ask, defaults to 0.01 CNY/kWh.
- `tie_break`: tie-break policy. `price_time_priority` (default) prefers the highest bid / lowest ask, then earliest timestamp.

## 4. References

- Vickrey, W. (1961). *Counterspeculation, Auctions, and Competitive Sealed Tenders*. The Journal of Finance, 16(1), 8-37.
- Mengelkamp, E. et al. (2018). *Designing microgrid energy markets — A case study: The Brooklyn Microgrid*. Applied Energy, 210, 870-880.
