---
name: market_env
family: Base
display_name: P2P Market Environment
file_name: market_env.py
description: |
  Per-step market environment that holds the prosumer state, the bid / ask
  book, and the settlement ledger. The simulator and every algorithm
  template consult this object.
affected_modules: []
inputs:
  horizon_hours: int
  prosumer_count: int
parameters:
  horizon_hours: 168
  prosumer_count: 12
  settlement_step_hours: 1
tags: [base, market, environment]
---

# P2P Market Environment

> Family: **Base** — Always loaded; the simulator and every algorithm template consult this object.

## 1. Inputs

| Field | Type | Description |
|---|---|---|
| `horizon_hours` | `int` | total simulation horizon |
| `prosumer_count` | `int` | number of prosumers in the simulation |
| `settlement_step_hours` | `int` | how often the market settles; defaults to 1 hour |

## 2. Outputs

A `MarketEnv` object that exposes:

- `step(action)`: advance one settlement step
- `observe()`: return the current `MarketState`
- `metrics()`: return the per-step metrics
- `finalize()`: close the ledger and produce the `Metrics` aggregate

## 3. Hyperparameters

- `horizon_hours`: defaults to 48 (quick), 168 (research), 336 (deep).
- `prosumer_count`: defaults to 12 for IEEE 33, 20 for IEEE 69.

## 4. References

Inherits the references in `grid_model/TEMPLATE.md`.
