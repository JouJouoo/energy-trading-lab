---
name: grid_model
family: Base
display_name: Radial Grid Model
file_name: grid_model.py
description: |
  Radial distribution feeder model. Wraps a p2plab.grid.GridCase into a
  step-friendly interface for the simulator. Provides power-flow validation
  via the bundled SimplePowerFlowValidator.
affected_modules: []
inputs:
  grid_case_name: str
parameters:
  base_voltage_kv: 12.66
  voltage_limits: [0.95, 1.05]
tags: [base, grid, radial, validator]
---

# Radial Grid Model

> Family: **Base** — Always loaded; provides the network topology to every other template.

## 1. Inputs

| Field | Type | Description |
|---|---|---|
| `grid_case_name` | `str` | one of the discovered scenario names (e.g. `ieee33`, `ieee69`, `ieee123`) |

## 2. Outputs

A `GridModel` object that exposes:

- `buses`: list of bus indices
- `branches`: list of `Branch` records
- `validate(net_load_kw)`: runs `SimplePowerFlowValidator.validate`

## 3. Hyperparameters

- `base_voltage_kv`: line-to-line voltage at the substation; defaults to 12.66.
- `voltage_limits`: per-bus operating range; defaults to [0.95, 1.05] pu.

## 4. References

- Baran, M. E., Wu, F. F. (1989). *Network reconfiguration in distribution systems for loss reduction and load balancing*. IEEE Transactions on Power Delivery, 4(2), 1401-1407.
- Kersting, W. H. (2012). *Distribution System Modeling and Analysis* (3rd ed.). CRC Press.
