---
name: dqn
family: RL
display_name: Deep Q-Network Bidding (PyTorch-free)
file_name: dqn.py
description: |
  Lightweight Deep Q-Network baseline using pure-Python dense layers
  (no PyTorch dependency). Replaces the Q-table with a 2-layer MLP
  and an epsilon-greedy policy. Demonstrates plugin extensibility:
  a 9th algorithm template added with no code change in
  p2plab/code_generator.py.
affected_modules: [reward.py, training_loop.py]
inputs:
  net_demand: float
  tou_price: float
  battery_soc: float
parameters:
  epsilon: 0.18
  learning_rate: 0.05
  discount: 0.95
  hidden_dim: 32
  batch_size: 16
  n_episodes: 100
validation:
  min_episodes: 50
tags: [rl, neural, dqn, plugin-demo]
---

# Deep Q-Network Bidding (PyTorch-free)

> Family: **RL** — Use when the Q-table is too small and a small neural policy is required, but the runtime should not depend on PyTorch.

## 1. Inputs

Same as `q_learning/TEMPLATE.md`:

| Field | Type | Description |
|---|---|---|
| `net_demand` | `float` | net demand in kW |
| `tou_price` | `float` | time-of-use price in CNY/kWh |
| `battery_soc` | `float` | battery SOC in [0, 1] |

## 2. Outputs

A discrete action index, decoded to a `(quantity_kw, price_cny_per_kwh)` tuple.

## 3. Architecture

A 2-layer MLP:

```
state (3 dims) → Dense(hidden_dim, tanh) → Dense(hidden_dim, tanh) → Q-values (n_actions)
```

Implemented in pure Python (no PyTorch, no NumPy autograd). Weights are stored as `list[list[float]]`. Training uses the bellman-update with gradient approximated by finite differences; this is intentionally small and easy to read for the demo. For research-grade work, swap the implementation file for a PyTorch / JAX version while keeping the `TEMPLATE.md` the same.

## 4. Hyperparameters

- `epsilon`: exploration rate, defaults to 0.18.
- `learning_rate`: MLP weight update step size, defaults to 0.05.
- `discount`: future reward discount, defaults to 0.95.
- `hidden_dim`: MLP hidden width, defaults to 32.
- `batch_size`: replay batch size, defaults to 16.
- `n_episodes`: training episodes, defaults to 100 (quick), 3000 (research), 12000 (deep).

## 5. References

- Mnih, V. et al. (2015). *Human-level control through deep reinforcement learning*. Nature, 518, 529-533.
- See `q_learning/TEMPLATE.md` for the parent RL references.

## 6. Why this is a plugin

This template exists to demonstrate that adding a new algorithm is a matter of dropping a folder at `p2plab/algorithm_templates/RL/dqn/` — no change to `p2plab/code_generator.py` is required. Restart the daemon and the Agent picks it up. See `docs/skills-protocol.md` and `CONTRIBUTING.md`.
