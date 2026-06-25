---
name: optimizer
family: Optimization
display_name: Linear / Mixed-Integer Clearing Optimizer
file_name: optimizer.py
description: |
  Deterministic clearing optimizer. Solves a small linear (or mixed-integer)
  clearing problem for one step. No LLM needed; the result is the
  cost-minimising P2P schedule.
affected_modules: []
inputs:
  net_demand_kw: float
  prosumer_count: int
parameters:
  solver: glpk
  time_limit_sec: 1.0
  tolerance: 1e-6
tags: [optimization, clearing, baseline]
---

# Linear / Mixed-Integer Clearing Optimizer

> Family: **Optimization** — Use as a deterministic baseline; the cost-minimising P2P schedule under the current bid / ask book.

## 1. Inputs

| Field | Type | Description |
|---|---|---|
| `net_demand_kw` | `float` | aggregate net demand at the current step |
| `prosumer_count` | `int` | number of prosumers in the simulation |

## 2. Outputs

A `ClearingResult` object with the cleared quantities and the dual prices.

## 3. Hyperparameters

- `solver`: defaults to `glpk`. The implementation auto-falls-back to a hand-rolled simplex for tiny problems when `glpk` is unavailable.
- `time_limit_sec`: solver time limit, defaults to 1.0.
- `tolerance`: optimality gap tolerance, defaults to 1e-6.

## 4. References

- Carrion, M., Arroyo, J. M. (2006). *A computationally efficient mixed-integer linear formulation for the thermal unit commitment problem*. IEEE Transactions on Power Systems, 21(3), 1371-1378.
