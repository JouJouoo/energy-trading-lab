from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Tuple

from .schemas import InnovationSpec, P2PModelSpec, ReproductionGap, ResearchHypothesis, StrategySpec


DOMAIN_TERMS = [
    "peer-to-peer",
    "p2p",
    "energy trading",
    "microgrid",
    "prosumer",
    "double auction",
    "reinforcement learning",
    "multi-agent",
    "q-learning",
    "dqn",
    "ppo",
    "maddpg",
    "optimization",
    "stackelberg",
    "game theory",
    "ieee 33",
    "ieee 69",
    "voltage",
    "network loss",
    "carbon",
    "battery",
]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> List[str]:
    clean = normalize_text(text)
    if not clean:
        return []
    chunks = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + chunk_size)
        chunks.append(clean[start:end])
        if end == len(clean):
            break
        start = max(0, end - overlap)
    return chunks


class KeywordRetriever:
    def __init__(self, chunks: List[str]):
        self.chunks = chunks

    def search(self, query: str, top_k: int = 4) -> List[Tuple[int, str, float]]:
        query_terms = set(tokenize(query))
        scored = []
        for index, chunk in enumerate(self.chunks):
            terms = tokenize(chunk)
            counts = Counter(terms)
            score = sum(counts.get(term, 0) for term in query_terms)
            score += sum(2 for term in DOMAIN_TERMS if term in chunk.lower() and term in query.lower())
            if score > 0:
                scored.append((index, chunk, float(score)))
        return sorted(scored, key=lambda item: item[2], reverse=True)[:top_k]


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_+-]+|[\u4e00-\u9fff]{2,}", text.lower())


def has_any(text: str, terms: List[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def extract_title(text: str, fallback: str = "P2P Energy Trading Study") -> str:
    for line in text.splitlines():
        stripped = line.strip("# \t")
        if 8 <= len(stripped) <= 140 and not stripped.lower().startswith(("abstract", "keywords")):
            return stripped
    return fallback


def infer_market_mechanism(text: str) -> str:
    if has_any(text, ["double auction", "双边拍卖", "auction"]):
        return "double auction clearing"
    if has_any(text, ["stackelberg", "leader", "follower", "博弈"]):
        return "game-theoretic / Stackelberg pricing"
    if has_any(text, ["optimization", "mixed integer", "linear programming", "凸优化", "优化"]):
        return "optimization-based market clearing"
    return "rule-based P2P market clearing"


def classify_strategy_family(text: str) -> List[StrategySpec]:
    specs: List[StrategySpec] = []
    if has_any(text, ["marl", "multi-agent reinforcement", "multi agent reinforcement", "多智能体强化学习"]):
        specs.append(
            StrategySpec(
                family="RL/MARL",
                algorithm_name="Multi-agent reinforcement learning",
                input_state=["local demand", "PV generation", "battery SOC", "market price", "grid voltage"],
                decision_variables=["bid price", "bid quantity", "battery dispatch"],
                objective_or_reward=["minimize cost", "increase P2P trading", "penalize voltage violations"],
                hyperparameters={"episodes": 60, "learning_rate": 0.1, "epsilon": 0.18},
                is_baseline=False,
            )
        )
    elif has_any(text, ["reinforcement learning", "q-learning", "dqn", "ppo", "maddpg", "强化学习"]):
        specs.append(
            StrategySpec(
                family="RL",
                algorithm_name="Lightweight Q-learning / DQN-style bidding",
                input_state=["net demand", "time-of-use price", "battery SOC"],
                decision_variables=["buy/sell/hold", "quantity bin", "price bin"],
                objective_or_reward=["prosumer reward", "community cost", "carbon penalty"],
                hyperparameters={"episodes": 60, "epsilon": 0.18},
                is_baseline=False,
            )
        )
    if has_any(text, ["optimization", "linear programming", "mixed integer", "凸优化", "优化"]):
        specs.append(
            StrategySpec(
                family="Optimization",
                algorithm_name="Optimization clearing baseline",
                input_state=["supply", "demand", "grid buy/sell tariff"],
                decision_variables=["cleared quantity", "clearing price"],
                objective_or_reward=["minimize community energy cost", "maximize social welfare"],
                hyperparameters={"solver": "deterministic greedy approximation"},
                is_baseline=True,
            )
        )
    if has_any(text, ["auction", "double auction", "双边拍卖", "market clearing"]):
        specs.append(
            StrategySpec(
                family="Auction",
                algorithm_name="Rule-based double auction",
                input_state=["buyer bid", "seller ask", "available surplus"],
                decision_variables=["matched quantity", "clearing price"],
                objective_or_reward=["match feasible trades before grid fallback"],
                hyperparameters={"price_rule": "midpoint"},
                is_baseline=True,
            )
        )
    if has_any(text, ["stackelberg", "game", "博弈"]):
        specs.append(
            StrategySpec(
                family="Game Theory",
                algorithm_name="Stackelberg pricing scaffold",
                input_state=["leader price", "follower demand response"],
                decision_variables=["leader tariff", "prosumer response"],
                objective_or_reward=["leader revenue", "prosumer utility"],
                hyperparameters={"iterations": 20},
                is_baseline=True,
            )
        )
    specs.append(
        StrategySpec(
            family="Rule-based",
            algorithm_name="No trading / tariff fallback",
            input_state=["net demand", "grid tariff"],
            decision_variables=["grid import", "grid export"],
            objective_or_reward=["baseline comparison"],
            hyperparameters={},
            is_baseline=True,
        )
    )
    unique: Dict[str, StrategySpec] = {}
    for spec in specs:
        unique[spec.family + spec.algorithm_name] = spec
    return list(unique.values())


def extract_model_spec(text: str, source_type: str) -> P2PModelSpec:
    lowered = text.lower()
    state_space = ["prosumer load", "PV generation", "time-of-use tariff", "battery SOC"]
    if has_any(lowered, ["voltage", "ieee 33", "ieee 69", "network"]):
        state_space.append("bus voltage / network state")
    if has_any(lowered, ["carbon", "emission", "低碳", "碳"]):
        state_space.append("grid carbon intensity")

    action_space = ["buy/sell/hold", "bid price", "bid quantity"]
    if has_any(lowered, ["battery", "storage", "储能"]):
        action_space.append("battery charge/discharge")

    reward = ["energy cost saving", "P2P trading revenue"]
    if has_any(lowered, ["carbon", "emission", "低碳", "碳"]):
        reward.append("carbon emission penalty")
    if has_any(lowered, ["voltage", "network loss", "constraint", "潮流", "网损"]):
        reward.extend(["voltage violation penalty", "network loss penalty"])

    baselines = ["No Trading", "Rule-based Double Auction", "Optimization Clearing"]
    if has_any(lowered, ["reinforcement learning", "q-learning", "dqn", "marl", "强化学习"]):
        baselines.append("RL Bidding")

    metrics = [
        "total energy cost",
        "P2P trading volume",
        "grid import/export",
        "carbon emissions",
        "social welfare",
        "fairness index",
        "voltage violation",
        "network loss",
    ]

    problem = "Reproduce or generate experiments for P2P energy trading under distribution-network constraints."
    if source_type == "theory":
        problem = "Transform a Chinese research theory draft into an executable P2P energy trading experiment."

    return P2PModelSpec(
        title=extract_title(text, fallback="P2P Energy Trading Reproduction"),
        research_problem=problem,
        state_space=state_space,
        action_space=action_space,
        reward_or_objective=reward,
        market_mechanism=infer_market_mechanism(text),
        grid_constraints=["IEEE 33/69 radial feeder", "voltage limits", "network loss", "power-flow convergence"],
        baselines=baselines,
        metrics=metrics,
        source_type=source_type,
    )


def detect_reproduction_gaps(text: str) -> List[ReproductionGap]:
    lowered = text.lower()
    gaps: List[ReproductionGap] = []
    if not has_any(lowered, ["github", "code available", "source code", "代码"]):
        gaps.append(
            ReproductionGap(
                category="Missing code",
                severity="high",
                evidence="No explicit source-code availability statement detected.",
                suggested_assumption="Generate a transparent reproduction scaffold instead of claiming numeric replication.",
            )
        )
    if not has_any(lowered, ["ieee 33", "ieee-33", "33-bus", "ieee 69", "69-bus"]):
        gaps.append(
            ReproductionGap(
                category="Grid case mapping",
                severity="medium",
                evidence="The paper text does not clearly map prosumers to IEEE 33/69 nodes.",
                suggested_assumption="Use deterministic prosumer placement across load buses and report it as an Agent assumption.",
            )
        )
    if not has_any(lowered, ["learning rate", "epsilon", "episode", "hyperparameter", "超参数"]):
        gaps.append(
            ReproductionGap(
                category="Training details",
                severity="medium",
                evidence="RL/MARL hyperparameters are incomplete or not detected.",
                suggested_assumption="Use small local defaults and expose them in experiment_config.yaml.",
            )
        )
    if not has_any(lowered, ["load profile", "pv profile", "dataset", "data availability", "数据"]):
        gaps.append(
            ReproductionGap(
                category="Dataset",
                severity="high",
                evidence="Load/PV data source is not explicit.",
                suggested_assumption="Use synthetic 24h PV/load profiles for the first reproduction package.",
            )
        )
    if not has_any(lowered, ["reward", "objective", "目标函数", "奖励"]):
        gaps.append(
            ReproductionGap(
                category="Objective / reward",
                severity="medium",
                evidence="Reward or objective formula is not explicitly recoverable from the provided text.",
                suggested_assumption="Construct a decomposed cost + P2P volume + voltage penalty reward and mark it as inferred.",
            )
        )
    return gaps


def generate_hypotheses(text: str) -> List[ResearchHypothesis]:
    return [
        ResearchHypothesis(
            statement="A voltage-aware reward or objective can reduce voltage violations in IEEE 33/69 P2P trading experiments.",
            independent_variable="Add voltage violation and network-loss penalties to the trading strategy.",
            expected_direction="Voltage violations and network loss decrease, with a small trade-off in P2P volume.",
            validation_metrics=["voltage violation", "network loss", "P2P trading volume", "total cost"],
            rationale="P2P trading can shift injections across feeder nodes; network-aware incentives should discourage risky trades.",
        ),
        ResearchHypothesis(
            statement="RL bidding improves community cost compared with no trading and rule-based double auction under time-varying tariffs.",
            independent_variable="Replace static bid/ask margins with learned price aggressiveness.",
            expected_direction="Total cost decreases and social welfare increases.",
            validation_metrics=["total energy cost", "social welfare", "fairness index"],
            rationale="Prosumer bidding can adapt to surplus/deficit and tariff periods better than a fixed rule.",
        ),
        ResearchHypothesis(
            statement="Carbon-aware trading can reduce grid-import emissions while preserving most P2P trading volume.",
            independent_variable="Include grid carbon intensity in state and reward/objective.",
            expected_direction="Carbon emissions decrease while P2P volume remains comparable.",
            validation_metrics=["carbon emissions", "grid import", "P2P trading volume"],
            rationale="Carbon intensity varies over time, so trading and storage decisions can be shifted away from high-carbon periods.",
        ),
    ]


def extract_innovation_spec(text: str, strategies: List[StrategySpec]) -> InnovationSpec:
    lowered = text.lower()
    base_algorithm = "rule-based double auction"
    if any(spec.family in ("RL", "RL/MARL") for spec in strategies):
        base_algorithm = "lightweight MARL / Q-learning bidding"
    elif any(spec.family == "Optimization" for spec in strategies):
        base_algorithm = "optimization clearing"
    elif any(spec.family == "Game Theory" for spec in strategies):
        base_algorithm = "Stackelberg pricing scaffold"

    tags: List[str] = []
    modifications: List[str] = []
    reward_terms: List[str] = ["community cost saving", "P2P trading revenue"]
    params = {
        "trading_aggressiveness": 0.82,
        "rl_aggressiveness": 1.0,
        "voltage_weight": 0.0,
        "carbon_weight": 0.0,
        "fairness_weight": 0.0,
        "network_loss_weight": 0.0,
        "risk_sensitivity": 0.0,
        "price_leadership": 0.0,
    }

    if has_any(lowered, ["carbon", "emission", "低碳", "碳"]):
        tags.append("carbon-aware")
        reward_terms.append("carbon emission penalty")
        modifications.append("Inject time-varying carbon intensity into bid aggressiveness and reward evaluation.")
        params["carbon_weight"] = 0.35
        params["trading_aggressiveness"] += 0.06

    if has_any(lowered, ["voltage", "network loss", "潮流", "网损", "配电网", "distribution network"]):
        tags.append("network-aware")
        reward_terms.extend(["voltage violation penalty", "network loss penalty"])
        modifications.append("Reduce risky feeder-tail peak-hour trades and report voltage-risk score.")
        params["voltage_weight"] = 0.45
        params["network_loss_weight"] = 0.25
        params["risk_sensitivity"] = 0.38

    if has_any(lowered, ["fairness", "公平"]):
        tags.append("fairness-aware")
        reward_terms.append("fairness regularization")
        modifications.append("Penalize strategies that concentrate savings in a few prosumers.")
        params["fairness_weight"] = 0.25

    if has_any(lowered, ["stackelberg", "leader", "follower", "博弈"]):
        tags.append("game-theoretic")
        modifications.append("Add leader-follower price bias to the proposed strategy scaffold.")
        params["price_leadership"] = 0.18

    if has_any(lowered, ["privacy", "federated", "联邦", "隐私"]):
        tags.append("privacy-preserving")
        modifications.append("Restrict observation features to local state plus aggregate market signals.")
        params["risk_sensitivity"] += 0.08

    if not tags:
        tags.append("adaptive-bidding")
        modifications.append("Modify the classic double-auction baseline with adaptive RL-style bid margins.")
        params["rl_aggressiveness"] = 1.12

    innovation_type = "+".join(tags)
    rationale = (
        "The paper/theory text suggests a %s contribution on top of %s. "
        "The generated experiment therefore changes strategy parameters and reward terms instead of reusing a fixed algorithm."
        % (innovation_type, base_algorithm)
    )
    return InnovationSpec(
        innovation_type=innovation_type,
        base_algorithm=base_algorithm,
        code_modifications=modifications,
        custom_reward_terms=reward_terms,
        strategy_parameters=params,
        rationale=rationale,
    )


def retrieve_domain_context(text: str) -> Dict[str, List[str]]:
    chunks = chunk_text(text)
    retriever = KeywordRetriever(chunks)
    queries = {
        "strategy": "reinforcement learning optimization auction Stackelberg P2P energy trading",
        "grid": "IEEE 33 IEEE 69 voltage network loss distribution feeder",
        "metrics": "cost carbon emissions social welfare fairness P2P volume reward objective",
    }
    context: Dict[str, List[str]] = {}
    for key, query in queries.items():
        context[key] = [chunk for _idx, chunk, _score in retriever.search(query, top_k=3)]
    return context


BASE_ALGORITHM_KEYWORDS = {
    "q_learning": ["q-learning", "q learning", "qlearning", "q table", "q-table"],
    "dqn": ["dqn", "deep q-network", "deep q network", "deep q learning"],
    "ppo": ["ppo", "proximal policy optimization", "proximal policy"],
    "maddpg": ["maddpg", "multi-agent deep deterministic", "multi agent deep deterministic"],
    "ddpg": ["ddpg", "deep deterministic policy gradient"],
    "sac": ["sac", "soft actor-critic", "soft actor critic"],
    "a3c": ["a3c", "asynchronous advantage actor-critic"],
    "reinforce": ["reinforce", "policy gradient", "monte carlo policy"],
    "double_auction": ["double auction", "双边拍卖", "continuous double auction"],
    "uniform_price_auction": ["uniform price", "统一价格拍卖", "uniform auction"],
    "vickrey_auction": ["vickrey", "second price", "第二价格拍卖"],
    "linear_programming": ["linear programming", "线性规划", "lp problem"],
    "mixed_integer": ["mixed integer", "milp", "混合整数", "integer programming"],
    "convex_optimization": ["convex optimization", "凸优化", "quadratic programming"],
    "stackelberg": ["stackelberg", "leader-follower", "主从博弈", "leader follower"],
    "nash_equilibrium": ["nash equilibrium", "纳什均衡", "game theory"],
    "evolutionary_game": ["evolutionary game", "演化博弈", "replicator dynamics"],
}


def identify_base_algorithm(text: str, strategies: List[StrategySpec]) -> Tuple[str, str]:
    lowered = text.lower()
    rl_algos = ["q_learning", "dqn", "ppo", "maddpg", "ddpg", "sac", "a3c", "reinforce"]
    auction_algos = ["double_auction", "uniform_price_auction", "vickrey_auction"]
    opt_algos = ["linear_programming", "mixed_integer", "convex_optimization"]
    game_algos = ["stackelberg", "nash_equilibrium", "evolutionary_game"]

    best_match = None
    best_count = 0

    for algo, keywords in BASE_ALGORITHM_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in lowered)
        if count > best_count:
            best_count = count
            best_match = algo

    family = "Other"
    if best_match in rl_algos:
        family = "RL" if best_match not in ("maddpg",) else "RL/MARL"
    elif best_match in auction_algos:
        family = "Auction"
    elif best_match in opt_algos:
        family = "Optimization"
    elif best_match in game_algos:
        family = "Game Theory"
    elif strategies:
        family = strategies[0].family

    if best_match is None:
        if any(s.family in ("RL", "RL/MARL") for s in strategies):
            best_match = "q_learning"
            family = "RL"
        elif any(s.family == "Optimization" for s in strategies):
            best_match = "linear_programming"
            family = "Optimization"
        elif any(s.family == "Auction" for s in strategies):
            best_match = "double_auction"
            family = "Auction"
        elif any(s.family == "Game Theory" for s in strategies):
            best_match = "stackelberg"
            family = "Game Theory"
        else:
            best_match = "threshold_based"
            family = "Rule-based"

    return best_match, family


def extract_layered_innovations(
    text: str, strategies: List[StrategySpec], base_algorithm: str
) -> Tuple[str, List[LayeredInnovation], str]:
    from .schemas import LayeredInnovation

    lowered = text.lower()
    layers: List[LayeredInnovation] = []
    innovation_mode = "improved"

    if has_any(lowered, ["novel algorithm", "new algorithm", "propose a", "提出一种", "novel framework", "新的框架"]):
        if not has_any(lowered, ["baseline", "compared with", "基于", "on top of", "improve"]):
            innovation_mode = "novel"

    if has_any(lowered, ["carbon", "emission", "低碳", "碳"]):
        layers.append(LayeredInnovation(
            layer="reward_objective",
            description="Carbon-aware reward/objective with time-varying carbon intensity",
            code_change_hint="Add carbon emission penalty term to reward/objective function",
            affected_modules=["reward.py", "objective.py"],
        ))

    if has_any(lowered, ["voltage", "voltage violation", "电压越限", "电压约束"]):
        layers.append(LayeredInnovation(
            layer="constraint",
            description="Voltage constraint consideration in trading decisions",
            code_change_hint="Add voltage violation penalty and constraint checking before action execution",
            affected_modules=["agent.py", "optimizer.py", "auction_engine.py"],
        ))

    if has_any(lowered, ["network loss", "网损", "loss minimization"]):
        layers.append(LayeredInnovation(
            layer="reward_objective",
            description="Network loss minimization objective",
            code_change_hint="Add network loss term to reward/objective function",
            affected_modules=["reward.py", "objective.py"],
        ))

    if has_any(lowered, ["fairness", "公平", "equity"]):
        layers.append(LayeredInnovation(
            layer="reward_objective",
            description="Fairness-aware trading with equity constraints",
            code_change_hint="Add fairness regularization term to reward/objective",
            affected_modules=["reward.py", "objective.py"],
        ))

    if has_any(lowered, ["privacy", "federated", "联邦", "隐私", "differential privacy"]):
        layers.append(LayeredInnovation(
            layer="algorithm_framework",
            description="Privacy-preserving or federated learning framework",
            code_change_hint="Modify training loop to support federated/privacy-preserving updates",
            affected_modules=["training_loop.py", "agent.py"],
        ))

    if has_any(lowered, ["attention", "graph neural", "gnn", "注意力", "图神经"]):
        layers.append(LayeredInnovation(
            layer="network_architecture",
            description="Attention mechanism or graph neural network architecture",
            code_change_hint="Replace standard network with attention/GNN-based architecture",
            affected_modules=["agent.py", "policy.py"],
        ))

    if has_any(lowered, ["multi-agent", "多智能体", "marl", "multi agent"]):
        layers.append(LayeredInnovation(
            layer="algorithm_framework",
            description="Multi-agent framework with decentralized execution",
            code_change_hint="Extend single-agent algorithm to multi-agent framework",
            affected_modules=["training_loop.py", "agent.py"],
        ))

    if has_any(lowered, ["stackelberg", "leader-follower", "主从博弈", "leader follower"]):
        layers.append(LayeredInnovation(
            layer="algorithm_framework",
            description="Stackelberg game-theoretic pricing framework",
            code_change_hint="Implement leader-follower price dynamics and equilibrium seeking",
            affected_modules=["game_engine.py", "players.py"],
        ))

    if has_any(lowered, ["battery", "storage", "储能", "battery scheduling"]):
        layers.append(LayeredInnovation(
            layer="state_action_space",
            description="Battery storage state and charge/discharge action",
            code_change_hint="Add battery SOC to state space and charge/discharge to action space",
            affected_modules=["agent.py", "state_processor.py"],
        ))

    if has_any(lowered, ["learning rate", "epsilon decay", "学习率", "探索策略"]):
        layers.append(LayeredInnovation(
            layer="strategy_update",
            description="Modified learning rate schedule or exploration strategy",
            code_change_hint="Update learning rate scheduling and exploration policy",
            affected_modules=["training_loop.py", "agent.py"],
        ))

    if not layers:
        layers.append(LayeredInnovation(
            layer="reward_objective",
            description="Adaptive bidding strategy with improved reward shaping",
            code_change_hint="Modify reward function to better incentivize efficient trading",
            affected_modules=["reward.py"],
        ))

    pseudocode = _generate_pseudocode(base_algorithm, layers, innovation_mode)

    return innovation_mode, layers, pseudocode


def _generate_pseudocode(base_algorithm: str, layers: List[LayeredInnovation], mode: str) -> str:
    if mode == "novel":
        return f"""NOVEL ALGORITHM PSEUDOCODE:
Input: Market state, grid state, prosumer data
Output: Optimal trading decisions
1. Initialize algorithm parameters
2. For each time step:
   a. Observe current state (load, PV, price, grid conditions)
   b. Compute trading decisions using novel mechanism
   c. Execute trades and update market state
   d. Run power flow analysis
   e. Update internal state based on feedback
3. Return trading results and metrics
"""
    layer_lines = []
    for i, layer in enumerate(layers, 1):
        layer_lines.append(f"   {i}. Apply innovation: {layer.description}")

    return f"""IMPROVED ALGORITHM PSEUDOCODE (based on {base_algorithm}):
Input: Market state, grid state, prosumer data
Output: Optimal trading decisions
1. Initialize baseline {base_algorithm} parameters
2. For each episode/time step:
   a. Observe current state
{chr(10).join(layer_lines)}
   b. Compute action using modified strategy
   c. Execute action and observe reward/objective
   d. Update strategy parameters
   e. Run power flow validation
3. Return trained strategy and metrics
"""


def extract_detailed_innovation(
    text: str, strategies: List[StrategySpec]
) -> "DetailedInnovationSpec":
    from .schemas import DetailedInnovationSpec

    base_algo, family = identify_base_algorithm(text, strategies)
    mode, layers, pseudocode = extract_layered_innovations(text, strategies, base_algo)

    description = f"{'Novel' if mode == 'novel' else 'Improved'} algorithm for P2P energy trading"
    if layers:
        descriptions = [l.description for l in layers]
        description += ": " + "; ".join(descriptions[:3])

    rationale = (
        f"The paper presents a {'novel algorithm' if mode == 'novel' else f'{base_algo}-based approach'} "
        f"with {len(layers)} key innovation(s). "
        f"Generated code will {'be built from scratch' if mode == 'novel' else 'extend the baseline template'}."
    )

    return DetailedInnovationSpec(
        innovation_mode=mode,
        base_algorithm=base_algo,
        base_algorithm_family=family,
        layered_innovations=layers,
        algorithm_description=description,
        pseudocode=pseudocode,
        rationale=rationale,
    )
