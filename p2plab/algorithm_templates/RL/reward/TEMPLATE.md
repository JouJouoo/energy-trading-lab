---
name: reward
family: RL
display_name: Reward Function
file_name: reward.py
description: |
  Modular reward function used by all RL templates. Default: cost minimisation
  + self-consumption bonus + voltage safety penalty. Patches per paper are
  applied via the Agent's _apply_innovations_llm step.
affected_modules: []
inputs:
  cost: float
  self_consumption_kw: float
  min_voltage_pu: float
parameters:
  alpha_self_consumption: 0.4
  beta_voltage_safety: 0.3
tags: [rl, reward, shared]
---

# Reward Function

> Family: **RL** — Shared by `q_learning` and `dqn` templates.

## 1. Inputs

| Field | Type | Description |
|---|---|---|
| `cost` | `float` | settlement cost in CNY for the current step |
| `self_consumption_kw` | `float` | locally generated energy consumed by the same prosumer |
| `min_voltage_pu` | `float` | minimum bus voltage in the current snapshot |

## 2. Outputs

A single `float` reward in roughly `[-2, 2]`, scaled so that zero is the breakeven point.

## 3. Reward shape

`r = -cost / cost_normalisation + α * self_consumption_ratio + β * max(0, 0.95 - min_voltage_pu)`

## 4. Hyperparameters

- `alpha_self_consumption`: bonus weight for self-consumption, defaults to 0.4.
- `beta_voltage_safety`: penalty weight for under-voltage, defaults to 0.3.

## 5. References

Inherits the RL references in `q_learning/TEMPLATE.md`. No paper-specific patches in the base implementation.
