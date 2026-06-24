from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .llm import LLMError, call_chat_json
from .rag import extract_detailed_innovation
from .schemas import (
    DetailedInnovationSpec,
    InnovationSpec,
    LayeredInnovation,
    P2PModelSpec,
    ReproductionGap,
    ResearchHypothesis,
    StrategySpec,
    to_dict,
)


SYSTEM_PROMPT = """You are an expert AI research engineer for energy trading simulation.
Extract a paper-specific experiment design from P2P / energy trading academic text.
Return strict JSON only. Do not invent unavailable data; mark reproduction gaps explicitly.
The goal is to help an Agent generate simulation code, not to summarize casually."""


def refine_analysis_with_llm(
    source_text: str,
    source_type: str,
    fallback: Dict[str, Any],
    llm_config: Dict[str, Any] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    compact_text = source_text[:12000]
    prompt = {
        "task": "Refine Energy Trading Lab structured extraction.",
        "source_type": source_type,
        "paper_or_theory_text": compact_text,
        "fallback_extraction": fallback,
        "required_json_schema": {
            "model_spec": {
                "title": "string",
                "research_problem": "string",
                "state_space": ["string"],
                "action_space": ["string"],
                "reward_or_objective": ["string"],
                "market_mechanism": "string",
                "grid_constraints": ["string"],
                "baselines": ["string"],
                "metrics": ["string"],
                "source_type": source_type,
            },
            "strategy_spec": [
                {
                    "family": "RL/MARL | RL | Optimization | Auction | Game Theory | Heuristic | Rule-based | Other",
                    "algorithm_name": "string",
                    "input_state": ["string"],
                    "decision_variables": ["string"],
                    "objective_or_reward": ["string"],
                    "hyperparameters": {"key": "value"},
                    "is_baseline": True,
                }
            ],
            "innovation_spec": {
                "innovation_type": "string",
                "base_algorithm": "string",
                "code_modifications": ["concrete simulation/code changes"],
                "custom_reward_terms": ["string"],
                "strategy_parameters": {
                    "trading_aggressiveness": 0.82,
                    "rl_aggressiveness": 1.0,
                    "voltage_weight": 0.0,
                    "carbon_weight": 0.0,
                    "fairness_weight": 0.0,
                    "network_loss_weight": 0.0,
                    "risk_sensitivity": 0.0,
                    "price_leadership": 0.0,
                },
                "rationale": "string",
            },
            "reproduction_gaps": [
                {
                    "category": "string",
                    "severity": "low | medium | high",
                    "evidence": "string",
                    "suggested_assumption": "string",
                }
            ],
            "hypotheses": [
                {
                    "statement": "string",
                    "independent_variable": "string",
                    "expected_direction": "string",
                    "validation_metrics": ["string"],
                    "rationale": "string",
                }
            ],
        },
    }
    response = call_chat_json(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": str(prompt)},
        ],
        llm_config=llm_config,
    )
    parsed = parse_analysis_payload(response, source_type=source_type)
    meta = {
        "analysis_source": "llm",
        "llm_error": "",
    }
    return parsed, meta


def parse_analysis_payload(payload: Dict[str, Any], source_type: str) -> Dict[str, Any]:
    model = dict(payload.get("model_spec") or {})
    model.setdefault("source_type", source_type)
    strategy_spec = payload.get("strategy_spec") or []
    gaps = payload.get("reproduction_gaps") or []
    hypotheses = payload.get("hypotheses") or []
    innovation = dict(payload.get("innovation_spec") or {})
    params = dict(innovation.get("strategy_parameters") or {})
    default_params = {
        "trading_aggressiveness": 0.82,
        "rl_aggressiveness": 1.0,
        "voltage_weight": 0.0,
        "carbon_weight": 0.0,
        "fairness_weight": 0.0,
        "network_loss_weight": 0.0,
        "risk_sensitivity": 0.0,
        "price_leadership": 0.0,
    }
    default_params.update({key: safe_float(value, default_params.get(key, 0.0)) for key, value in params.items()})
    innovation["strategy_parameters"] = default_params
    return {
        "model_spec": P2PModelSpec(**model),
        "strategy_spec": [StrategySpec(**item) for item in strategy_spec[:8]],
        "innovation_spec": InnovationSpec(**innovation),
        "reproduction_gaps": [ReproductionGap(**item) for item in gaps[:8]],
        "hypotheses": [ResearchHypothesis(**item) for item in hypotheses[:5]],
    }


def fallback_payload(
    model_spec: P2PModelSpec,
    strategies: List[StrategySpec],
    innovation: InnovationSpec,
    gaps: List[ReproductionGap],
    hypotheses: List[ResearchHypothesis],
) -> Dict[str, Any]:
    return {
        "model_spec": to_dict(model_spec),
        "strategy_spec": to_dict(strategies),
        "innovation_spec": to_dict(innovation),
        "reproduction_gaps": to_dict(gaps),
        "hypotheses": to_dict(hypotheses),
    }


def safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def refine_detailed_innovation_with_llm(
    source_text: str,
    strategies: List[StrategySpec],
    fallback: DetailedInnovationSpec,
    llm_config: Dict[str, Any] = None,
) -> Tuple[DetailedInnovationSpec, Dict[str, Any]]:
    compact_text = source_text[:12000]
    prompt = {
        "task": "Extract detailed algorithm structure and innovations from the paper.",
        "paper_text": compact_text,
        "detected_strategies": [to_dict(s) for s in strategies],
        "fallback_analysis": to_dict(fallback),
        "required_json_schema": {
            "innovation_mode": "improved | novel",
            "base_algorithm": "string (e.g., q_learning, double_auction, linear_programming, stackelberg)",
            "base_algorithm_family": "RL | RL/MARL | Optimization | Auction | Game Theory | Rule-based | Other",
            "layered_innovations": [
                {
                    "layer": "reward_objective | state_action_space | strategy_update | network_architecture | algorithm_framework | constraint | novel_algorithm",
                    "description": "string, detailed description of this innovation",
                    "code_change_hint": "string, concrete hint for code generation",
                    "affected_modules": ["string, file names"],
                }
            ],
            "algorithm_description": "string, 1-2 sentence summary of the algorithm",
            "pseudocode": "string, structured pseudocode of the algorithm",
            "rationale": "string",
        },
    }
    response = call_chat_json(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": str(prompt)},
        ],
        llm_config=llm_config,
    )
    parsed = parse_detailed_innovation(response)
    meta = {
        "analysis_source": "llm",
        "llm_error": "",
    }
    return parsed, meta


def parse_detailed_innovation(payload: Dict[str, Any]) -> DetailedInnovationSpec:
    mode = str(payload.get("innovation_mode", "improved"))
    base_algo = str(payload.get("base_algorithm", "q_learning"))
    base_family = str(payload.get("base_algorithm_family", "RL"))
    description = str(payload.get("algorithm_description", ""))
    pseudocode = str(payload.get("pseudocode", ""))
    rationale = str(payload.get("rationale", ""))

    layers_raw = payload.get("layered_innovations", [])
    layers = []
    for item in layers_raw:
        layers.append(LayeredInnovation(
            layer=str(item.get("layer", "reward_objective")),
            description=str(item.get("description", "")),
            code_change_hint=str(item.get("code_change_hint", "")),
            affected_modules=list(item.get("affected_modules", [])),
        ))

    if not layers:
        layers.append(LayeredInnovation(
            layer="reward_objective",
            description="Improved reward shaping for P2P energy trading",
            code_change_hint="Modify reward function with better incentives",
            affected_modules=["reward.py"],
        ))

    return DetailedInnovationSpec(
        innovation_mode=mode,
        base_algorithm=base_algo,
        base_algorithm_family=base_family,
        layered_innovations=layers,
        algorithm_description=description,
        pseudocode=pseudocode,
        rationale=rationale,
    )


def fallback_detailed_innovation(text: str, strategies: List[StrategySpec]) -> DetailedInnovationSpec:
    return extract_detailed_innovation(text, strategies)
