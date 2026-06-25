---
name: q_learning
family: RL
display_name: Tabular Q-Learning Bidding
file_name: q_learning.py
description: |
  Lightweight tabular Q-learning agent for P2P energy bidding.
  State: net demand, time-of-use price, battery SOC.
  Action: buy/sell/hold × quantity bin × price bin.
affected_modules: [reward.py, training_loop.py]
inputs:
  net_demand: float
  tou_price: float
  battery_soc: float
parameters:
  epsilon: 0.18
  learning_rate: 0.1
  discount: 0.95
  n_episodes: 100
validation:
  min_episodes: 50
tags: [rl, tabular, baseline]
---

# Tabular Q-Learning Bidding

> Family: **RL** — Use when a single-agent tabular Q-learning baseline is sufficient and the state space is small.

## 1. Inputs

| Field | Type | Description |
|---|---|---|
| `net_demand` | `float` | net demand in kW (positive = buy, negative = sell) |
| `tou_price` | `float` | time-of-use price in CNY/kWh |
| `battery_soc` | `float` | battery state of charge in [0, 1] |

## 2. Outputs

A discrete action index from the bid table, decoded to a `(quantity_kw, price_cny_per_kwh)` tuple.

## 3. Reward / objective

`r = -cost + α * self_consumption + β * voltage_safety`

`α` and `β` are tuned to bias the agent toward self-consumption and to penalize voltage violation risk.

## 4. Hyperparameters

- `epsilon`: exploration rate, defaults to 0.18.
- `learning_rate`: Q-table update step size, defaults to 0.1.
- `discount`: future reward discount factor, defaults to 0.95.
- `n_episodes`: training episodes, defaults to 100 (quick), 3000 (research), 12000 (deep).

## 5. References

- Sutton, R. S., Barto, A. G. (2018). *Reinforcement Learning: An Introduction* (2nd ed.). MIT Press.
- Wei, H. et al. (2021). *Multi-agent reinforcement learning for distributed energy trading in distribution networks*. Applied Energy, 295, 116985.
