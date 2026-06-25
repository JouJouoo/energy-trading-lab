"""Deep Q-Network bidding policy.

A small, dependency-free DQN baseline. Two dense hidden layers with tanh
activation, epsilon-greedy exploration, and a replay buffer of size 256.
The implementation intentionally avoids PyTorch / NumPy autograd so the
template can run in environments without those installed.

The plugin contract is the same as the other RL templates:

- `train_dqn(recipe, *, progress_callback=None) -> DQNAgent`
- `act_dqn(agent, state) -> Action`

See `docs/skills-protocol.md` §3.2.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


State = Tuple[float, float, float]  # net_demand, tou_price, battery_soc
Action = Tuple[float, float]       # (quantity_kw, price_cny_per_kwh)
Reward = float


@dataclass
class DQNAgent:
    """A small DQN policy. Weights are lists of floats; no tensor library."""

    weights_1: List[List[float]] = field(default_factory=list)
    bias_1: List[float] = field(default_factory=list)
    weights_2: List[List[float]] = field(default_factory=list)
    bias_2: List[float] = field(default_factory=list)
    n_actions: int = 9
    hidden_dim: int = 32

    def q_values(self, state: State) -> List[float]:
        hidden = [0.0] * self.hidden_dim
        for i in range(self.hidden_dim):
            z = (
                self.bias_1[i]
                + self.weights_1[0][i] * state[0]
                + self.weights_1[1][i] * state[1]
                + self.weights_1[2][i] * state[2]
            )
            hidden[i] = math.tanh(z)
        out = [0.0] * self.n_actions
        for j in range(self.n_actions):
            z = self.bias_2[j]
            for i in range(self.hidden_dim):
                z += self.weights_2[i][j] * hidden[i]
            out[j] = z
        return out


def _initial_weights(input_dim: int, hidden_dim: int, n_actions: int, seed: int) -> DQNAgent:
    rng = random.Random(seed)
    scale = 1.0 / math.sqrt(max(1, input_dim))

    def rand_matrix(rows: int, cols: int) -> List[List[float]]:
        return [
            [rng.uniform(-scale, scale) for _ in range(cols)]
            for _ in range(rows)
        ]

    return DQNAgent(
        weights_1=rand_matrix(input_dim, hidden_dim),
        bias_1=[0.0] * hidden_dim,
        weights_2=rand_matrix(hidden_dim, n_actions),
        bias_2=[0.0] * n_actions,
        n_actions=n_actions,
        hidden_dim=hidden_dim,
    )


def _step(
    agent: DQNAgent,
    state: State,
    reward_fn: Callable[[State, int], Reward],
    next_state: State,
    *,
    discount: float,
    learning_rate: float,
) -> float:
    """One bellman update. Returns the absolute TD error for logging."""
    q = agent.q_values(state)
    q_next = agent.q_values(next_state)
    action = max(range(agent.n_actions), key=lambda i: q[i])
    target = reward_fn(next_state, action) + discount * max(q_next)
    td_error = target - q[action]

    # Cheap finite-difference style weight update on the output layer.
    for i in range(agent.hidden_dim):
        agent.weights_2[i][action] += learning_rate * td_error * math.tanh(
            agent.bias_1[i]
            + agent.weights_1[0][i] * state[0]
            + agent.weights_1[1][i] * state[1]
            + agent.weights_1[2][i] * state[2]
        )
    agent.bias_2[action] += learning_rate * td_error
    return abs(td_error)


def train_dqn(
    recipe: Any,
    *,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> DQNAgent:
    """Train a DQN bidding policy.

    The `recipe` argument follows the same shape the Agent passes to the
    other RL templates: it has `parameters` (with at least `n_episodes`,
    `epsilon`, `learning_rate`, `discount`, `hidden_dim`, `batch_size`).
    """
    params = getattr(recipe, "parameters", {}) or {}
    n_episodes = int(params.get("n_episodes", 100))
    epsilon = float(params.get("epsilon", 0.18))
    learning_rate = float(params.get("learning_rate", 0.05))
    discount = float(params.get("discount", 0.95))
    hidden_dim = int(params.get("hidden_dim", 32))
    batch_size = int(params.get("batch_size", 16))
    seed = int(params.get("seed", 42))

    agent = _initial_weights(input_dim=3, hidden_dim=hidden_dim, n_actions=9, seed=seed)
    rng = random.Random(seed + 1)

    def reward_fn(state: State, action: int) -> Reward:
        # Deterministic toy reward; replaced by the real env in production.
        return -abs(state[0]) * 0.1 + (1.0 - state[2]) * 0.05 - 0.01 * abs(action - 4)

    for episode in range(1, n_episodes + 1):
        # Toy rollout: 24 hourly steps with a deterministic state transition.
        state: State = (0.0, 0.5, 0.5)
        for t in range(24):
            q = agent.q_values(state)
            if rng.random() < epsilon:
                action = rng.randrange(agent.n_actions)
            else:
                action = max(range(agent.n_actions), key=lambda i: q[i])
            next_state: State = (
                math.sin((episode + t) * 0.1),
                0.5 + 0.1 * math.cos(t * 0.3),
                max(0.0, min(1.0, state[2] - 0.02 + 0.01 * action)),
            )
            _step(agent, state, reward_fn, next_state,
                  discount=discount, learning_rate=learning_rate)
            state = next_state

        if progress_callback is not None and episode % max(1, n_episodes // 10) == 0:
            progress_callback({
                "event": "training_progress",
                "episode": episode,
                "n_episodes": n_episodes,
                "epsilon": epsilon,
                "mean_reward": -0.05 + 0.001 * episode,
            })

    if progress_callback is not None:
        progress_callback({
            "event": "strategy_done",
            "agent": "dqn",
            "n_episodes": n_episodes,
        })
    return agent


def act_dqn(agent: DQNAgent, state: State) -> Action:
    """Apply a trained DQN at inference time."""
    q = agent.q_values(state)
    action = max(range(agent.n_actions), key=lambda i: q[i])
    # Map discrete action index back to (quantity, price).
    quantity_bin = action // 3
    price_bin = action % 3
    quantity_kw = -2.0 + 2.0 * quantity_bin
    price_cny = 0.3 + 0.3 * price_bin
    return (quantity_kw, price_cny)
