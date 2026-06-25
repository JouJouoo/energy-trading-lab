from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, List, Optional


class TrainingLoop:
    """Training loop for RL-based P2P energy trading experiments.

    Supports multiple agents, episodic training, and progress tracking.
    """

    def __init__(
        self,
        env,
        agents: List[Any],
        n_episodes: int = 100,
        log_interval: int = 10,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.env = env
        self.agents = agents
        self.n_episodes = n_episodes
        self.log_interval = log_interval
        self.progress_callback = progress_callback
        self.training_history: List[Dict[str, float]] = []

    def run(self) -> Dict[str, Any]:
        """Run the full training loop."""
        episode_rewards = []
        start_time = time.perf_counter()

        for episode in range(self.n_episodes):
            state = self.env.reset()
            total_reward = 0.0
            done = False
            step_count = 0

            while not done:
                actions = {}
                for agent in self.agents:
                    prosumer_state = self._get_prosumer_state(state, agent.agent_id)
                    action = agent.select_action(prosumer_state)
                    actions[agent.agent_id] = action

                next_state, rewards, done, info = self.env.step(actions)

                for agent in self.agents:
                    prosumer_state = self._get_prosumer_state(state, agent.agent_id)
                    next_prosumer_state = self._get_prosumer_state(next_state, agent.agent_id) if next_state else {}
                    reward = rewards.get(agent.agent_id, 0.0)
                    action = actions[agent.agent_id]
                    agent.update(prosumer_state, action, reward, next_prosumer_state, done)

                total_reward += rewards.get("total_cost", 0.0)
                state = next_state
                step_count += 1

            for agent in self.agents:
                agent.decay_epsilon()

            episode_rewards.append(total_reward)
            self.training_history.append({
                "episode": episode,
                "avg_reward": total_reward / max(step_count, 1),
                "total_reward": total_reward,
                "epsilon": self.agents[0].epsilon if self.agents else 0.0,
                "elapsed_sec": time.perf_counter() - start_time,
            })

            if self.progress_callback and (episode % self.log_interval == 0 or episode == self.n_episodes - 1):
                self.progress_callback({
                    "event": "training_progress",
                    "strategy": "q_learning",
                    "episode": episode,
                    "episodes": self.n_episodes,
                    "avg_reward": total_reward / max(step_count, 1),
                    "elapsed_sec": time.perf_counter() - start_time,
                })

        elapsed = time.perf_counter() - start_time
        return {
            "total_episodes": self.n_episodes,
            "total_reward": sum(episode_rewards),
            "avg_reward": sum(episode_rewards) / max(len(episode_rewards), 1),
            "final_epsilon": self.agents[0].epsilon if self.agents else 0.0,
            "elapsed_sec": elapsed,
            "training_history": self.training_history,
        }

    def _get_prosumer_state(self, state: Dict[str, Any], agent_id: int) -> Dict[str, Any]:
        """Extract per-prosumer state from global state."""
        prosumers = state.get("prosumers", [])
        prosumer = next((p for p in prosumers if p["id"] == agent_id), {})
        return {
            "hour_of_day": state.get("hour_of_day", 0),
            "grid_buy_price": state.get("grid_buy_price", 0.12),
            "grid_sell_price": state.get("grid_sell_price", 0.06),
            "net_load_kw": prosumer.get("net_load_kw", 0),
            "battery_soc_kwh": prosumer.get("battery_soc_kwh", 0),
            "battery_capacity_kwh": prosumer.get("battery_capacity_kwh", 0),
            "total_load_kw": state.get("total_load_kw", 0),
            "total_pv_kw": state.get("total_pv_kw", 0),
        }

    def evaluate(self, n_episodes: int = 5) -> Dict[str, Any]:
        """Evaluate trained agents without exploration."""
        original_epsilons = [agent.epsilon for agent in self.agents]
        for agent in self.agents:
            agent.epsilon = 0.0

        eval_rewards = []
        for _ in range(n_episodes):
            state = self.env.reset()
            total_reward = 0.0
            done = False
            while not done:
                actions = {}
                for agent in self.agents:
                    prosumer_state = self._get_prosumer_state(state, agent.agent_id)
                    action = agent.select_action(prosumer_state)
                    actions[agent.agent_id] = action
                next_state, rewards, done, info = self.env.step(actions)
                total_reward += rewards.get("total_cost", 0.0)
                state = next_state
            eval_rewards.append(total_reward)

        for agent, eps in zip(self.agents, original_epsilons):
            agent.epsilon = eps

        return {
            "n_eval_episodes": n_episodes,
            "avg_eval_reward": sum(eval_rewards) / max(len(eval_rewards), 1),
            "best_eval_reward": min(eval_rewards),
            "eval_rewards": eval_rewards,
        }
