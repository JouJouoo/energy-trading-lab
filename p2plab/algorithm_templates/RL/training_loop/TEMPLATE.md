---
name: training_loop
family: RL
display_name: RL Training Loop
file_name: training_loop.py
description: |
  Generic training loop for tabular and neural RL templates. Emits
  ETL_PROGRESS events with `episode`, `epsilon`, and `mean_reward` keys
  for streaming UI updates.
affected_modules: [reward.py]
inputs:
  n_episodes: int
  eval_every: int
parameters:
  n_episodes: 100
  eval_every: 10
  seed: 42
validation:
  smoke_test: training_loop_smoke.py
tags: [rl, training, shared]
---

# RL Training Loop

> Family: **RL** — Shared by `q_learning` and `dqn` templates.

## 1. Inputs

| Field | Type | Description |
|---|---|---|
| `n_episodes` | `int` | total training episodes |
| `eval_every` | `int` | run a deterministic eval every N episodes |
| `seed` | `int` | RNG seed; defaults to 42 |

## 2. Outputs

A trained policy object (depending on the family: a Q-table, a Q-network, or an actor-critic checkpoint).

## 3. Progress protocol

Each `eval_every` episodes the loop emits an `ETL_PROGRESS` line on stdout:

```
ETL_PROGRESS {"event": "training_progress", "episode": N, "epsilon": 0.18, "mean_reward": 0.42}
```

The Executor parses these lines and forwards them to the job queue, which the web UI's Agent Trace view subscribes to.

## 4. Hyperparameters

- `n_episodes`: defaults to 100 (quick), 3000 (research), 12000 (deep).
- `eval_every`: defaults to 10.
- `seed`: defaults to 42 for reproducibility.

## 5. References

- See `q_learning/TEMPLATE.md` for the parent RL references.
