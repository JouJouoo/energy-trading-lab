---
name: stackelberg_game
family: GameTheory
display_name: Stackelberg Game Pricing
file_name: stackelberg_game.py
description: |
  Two-stage Stackelberg game. The substation publishes a price (leader);
  the prosumers respond with their optimal consumption / production
  (followers). Solved by alternating best response.
affected_modules: []
inputs:
  leader_prices: list
  follower_utility: str
parameters:
  n_iterations: 20
  tolerance: 1e-4
  price_floor: 0.2
  price_ceiling: 1.5
tags: [game-theory, stackelberg, baseline]
---

# Stackelberg Game Pricing

> Family: **GameTheory** — Use as a price-formation baseline; the substation is the leader, the prosumers are the followers.

## 1. Inputs

| Field | Type | Description |
|---|---|---|
| `leader_prices` | `list[float]` | substation price candidates in CNY/kWh |
| `follower_utility` | `str` | identifier of the prosumer utility function (e.g. `quasi_linear`) |

## 2. Outputs

A list of `Equilibrium` snapshots, one per iteration. The last snapshot is the converged price-quantity pair.

## 3. Hyperparameters

- `n_iterations`: max iterations, defaults to 20.
- `tolerance`: convergence threshold on the price delta, defaults to 1e-4.
- `price_floor`: minimum substation price, defaults to 0.2 CNY/kWh.
- `price_ceiling`: maximum substation price, defaults to 1.5 CNY/kWh.

## 4. References

- Maharjan, S. et al. (2013). *Dependable Demand Response Management in the Smart Grid: A Stackelberg Game Approach*. IEEE Transactions on Smart Grid, 4(1), 120-132.
- Yu, M., Hong, S. H. (2016). *A real-time demand-response trading system for the smart grid*. Applied Energy, 178, 843-855.
