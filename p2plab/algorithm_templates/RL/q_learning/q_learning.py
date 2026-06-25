from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple


class QLearningAgent:
    """Base Q-Learning agent for P2P energy trading bidding.

    Extend this class to add custom reward shaping, state representation,
    or exploration strategies.
    """

    def __init__(
        self,
        agent_id: int,
        state_size: int = 5,
        action_size: int = 5,
        learning_rate: float = 0.1,
        gamma: float = 0.95,
        epsilon: float = 0.18,
        epsilon_min: float = 0.01,
        epsilon_decay: float = 0.995,
        random_seed: int = 42,
    ):
        self.agent_id = agent_id
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.rng = random.Random(random_seed + agent_id)
        self.q_table: Dict[str, List[float]] = {}
        self.training_episodes = 0
        self.total_reward = 0.0

    def _state_key(self, state: Dict[str, Any]) -> str:
        """Convert state dict to a hashable key for Q-table lookup.

        Override this method for custom state discretization.
        """
        hour = state.get("hour_of_day", 0)
        net_load = state.get("net_load_kw", 0)
        price = state.get("grid_buy_price", 0.12)
        soc = state.get("battery_soc_kwh", 0)

        hour_bin = hour // 6
        load_bin = round(net_load / 0.5) * 0.5
        price_bin = round(price / 0.02) * 0.02
        soc_bin = round(soc / 1.0) * 1.0

        return f"{hour_bin}_{load_bin:.1f}_{price_bin:.2f}_{soc_bin:.0f}"

    def select_action(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Select action using epsilon-greedy policy.

        Returns action dict with bid_price_factor and battery_kw.
        """
        state_key = self._state_key(state)
        if state_key not in self.q_table:
            self.q_table[state_key] = [0.0] * self.action_size

        if self.rng.random() < self.epsilon:
            action_idx = self.rng.randint(0, self.action_size - 1)
        else:
            q_values = self.q_table[state_key]
            max_q = max(q_values)
            best_actions = [i for i, q in enumerate(q_values) if q == max_q]
            action_idx = self.rng.choice(best_actions)

        return self._action_from_idx(action_idx, state)

    def _action_from_idx(self, action_idx: int, state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert action index to concrete action values.

        Override for custom action space.
        """
        price_factors = [0.8, 0.9, 1.0, 1.1, 1.2]
        battery_actions = [-1.0, -0.5, 0.0, 0.5, 1.0]

        price_factor = price_factors[action_idx % len(price_factors)]
        battery_kw = battery_actions[action_idx // len(price_factors) % len(battery_actions)]

        buy_price = state.get("grid_buy_price", 0.12)
        sell_price = state.get("grid_sell_price", 0.06)
        net_load = state.get("net_load_kw", 0)

        if net_load > 0:
            bid_price = buy_price * price_factor
        else:
            bid_price = sell_price * price_factor

        return {
            "action_idx": action_idx,
            "bid_price": bid_price,
            "battery_kw": battery_kw,
        }

    def update(
        self,
        state: Dict[str, Any],
        action: Dict[str, Any],
        reward: float,
        next_state: Dict[str, Any],
        done: bool,
    ) -> None:
        """Q-learning update rule.

        Override for custom update logic (e.g., SARSA, expected SARSA).
        """
        state_key = self._state_key(state)
        next_state_key = self._state_key(next_state) if next_state else state_key
        action_idx = action.get("action_idx", 0)

        if state_key not in self.q_table:
            self.q_table[state_key] = [0.0] * self.action_size
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = [0.0] * self.action_size

        current_q = self.q_table[state_key][action_idx]
        next_max_q = max(self.q_table[next_state_key]) if not done else 0.0

        td_target = reward + self.gamma * next_max_q
        td_error = td_target - current_q

        self.q_table[state_key][action_idx] += self.learning_rate * td_error
        self.total_reward += reward

    def decay_epsilon(self) -> None:
        """Decay exploration rate after each episode."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        self.training_episodes += 1

    def save(self, path: str) -> None:
        """Save Q-table to file."""
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "q_table": self.q_table,
                "epsilon": self.epsilon,
                "training_episodes": self.training_episodes,
                "total_reward": self.total_reward,
            }, f, indent=2)

    def load(self, path: str) -> None:
        """Load Q-table from file."""
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.q_table = data["q_table"]
            self.epsilon = data["epsilon"]
            self.training_episodes = data["training_episodes"]
            self.total_reward = data["total_reward"]
