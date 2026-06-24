from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


def to_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    return value


@dataclass
class TraceEvent:
    step: str
    status: str
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class P2PModelSpec:
    title: str
    research_problem: str
    state_space: List[str]
    action_space: List[str]
    reward_or_objective: List[str]
    market_mechanism: str
    grid_constraints: List[str]
    baselines: List[str]
    metrics: List[str]
    source_type: str


@dataclass
class StrategySpec:
    family: str
    algorithm_name: str
    input_state: List[str]
    decision_variables: List[str]
    objective_or_reward: List[str]
    hyperparameters: Dict[str, Any]
    is_baseline: bool = True


@dataclass
class InnovationSpec:
    innovation_type: str
    base_algorithm: str
    code_modifications: List[str]
    custom_reward_terms: List[str]
    strategy_parameters: Dict[str, Any]
    rationale: str


@dataclass
class ReproductionGap:
    category: str
    severity: str
    evidence: str
    suggested_assumption: str


@dataclass
class ResearchHypothesis:
    statement: str
    independent_variable: str
    expected_direction: str
    validation_metrics: List[str]
    rationale: str


@dataclass
class ExperimentRecipe:
    name: str
    grid_case: str
    horizon_hours: int
    prosumer_count: int
    strategies: List[str]
    random_seed: int
    training_episodes: int
    voltage_limits: List[float]
    notes: str = ""
    innovation_tags: List[str] = field(default_factory=list)
    strategy_parameters: Dict[str, Any] = field(default_factory=dict)
    experiment_depth: str = "quick"
    training_log_interval: int = 50


@dataclass
class GridValidationResult:
    converged: bool
    min_voltage_pu: float
    max_voltage_pu: float
    voltage_violation_count: int
    network_loss_kwh: float
    line_loading_max_pct: float
    notes: str


@dataclass
class SimulationMetrics:
    strategy: str
    total_cost: float
    p2p_volume_kwh: float
    grid_import_kwh: float
    grid_export_kwh: float
    carbon_kg: float
    renewable_self_consumption_pct: float
    social_welfare: float
    fairness_index: float
    grid_validation: GridValidationResult
    cost_saving_pct: float = 0.0
    voltage_risk_score: float = 0.0
    strategy_explanation: str = ""
    training_episodes: int = 0
    training_elapsed_sec: float = 0.0
    training_final_reward: float = 0.0


@dataclass
class ResearchReport:
    title: str
    model_spec: P2PModelSpec
    strategies: List[StrategySpec]
    hypotheses: List[ResearchHypothesis]
    reproduction_gaps: List[ReproductionGap]
    recipe: ExperimentRecipe
    metrics: List[SimulationMetrics]
    conclusion: str
    limitations: List[str]


INNOVATION_LAYERS = [
    "reward_objective",
    "state_action_space",
    "strategy_update",
    "network_architecture",
    "algorithm_framework",
    "constraint",
    "novel_algorithm",
]

INNOVATION_LAYER_LABELS = {
    "reward_objective": "奖励/目标函数层",
    "state_action_space": "状态/动作空间层",
    "strategy_update": "策略更新层",
    "network_architecture": "网络结构层",
    "algorithm_framework": "算法框架层",
    "constraint": "约束层",
    "novel_algorithm": "全新算法",
}


@dataclass
class LayeredInnovation:
    layer: str
    description: str
    code_change_hint: str
    affected_modules: List[str] = field(default_factory=list)


@dataclass
class DetailedInnovationSpec:
    innovation_mode: str
    base_algorithm: str
    base_algorithm_family: str
    layered_innovations: List[LayeredInnovation]
    algorithm_description: str
    pseudocode: str
    rationale: str = ""


@dataclass
class GeneratedModule:
    module_name: str
    file_path: str
    code: str
    module_type: str
    status: str = "generated"
    validation_errors: List[str] = field(default_factory=list)
    repair_attempts: int = 0


@dataclass
class GeneratedProject:
    project_dir: str
    modules: List[GeneratedModule]
    algorithm_family: str
    innovation_mode: str
    integration_test_passed: bool = False
    integration_test_log: str = ""
