from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .llm import call_chat_json, llm_status
from .module_validator import ModuleValidator
from .plugin_loader import discover_algorithm_templates
from .plugin_manifest import AlgorithmTemplate, family_directory
from .schemas import (
    DetailedInnovationSpec,
    GeneratedModule,
    LayeredInnovation,
    StrategySpec,
    to_dict,
)


TEMPLATE_DIR = Path(__file__).resolve().parent / "algorithm_templates"

BASE_MODULES = [
    ("grid_model", "grid_model", "grid_model"),
    ("market_env", "market_env", "market_env"),
]

# Back-compat fallback. The plugin system (`plugin_loader.discover_algorithm_templates`)
# is the primary source of truth; this map is used only when discovery returns
# no templates (e.g. in a misconfigured test environment). See
# `docs/skills-protocol.md` and `CHANGELOG.md` 0.2.0.
ALGORITHM_MODULE_MAP = {
    "RL": [
        ("reward", "reward", "reward"),
        ("q_learning", "agent", "q_learning"),
        ("training_loop", "training_loop", "training_loop"),
    ],
    "RL/MARL": [
        ("reward", "reward", "reward"),
        ("q_learning", "agent", "q_learning"),
        ("training_loop", "training_loop", "training_loop"),
    ],
    "Optimization": [
        ("optimizer", "optimizer", "optimizer"),
    ],
    "Auction": [
        ("double_auction", "auction_engine", "double_auction"),
    ],
    "Game Theory": [
        ("stackelberg_game", "game_engine", "stackelberg_game"),
    ],
    "Rule-based": [
        ("optimizer", "rules", "optimizer"),
    ],
}

LLM_CODE_SYSTEM_PROMPT = """You are an expert Python developer specializing in energy trading and power systems.
Generate clean, well-documented Python code that matches the paper's algorithm description.
Follow the existing code patterns and interfaces exactly.
Only return the code, no explanations or markdown formatting."""


class CodeGenerator:
    """Generate code modules for paper reproduction.

    Supports:
    - Improved algorithms: load template + apply innovations via LLM
    - Novel algorithms: generate from scratch via LLM
    - Multi-algorithm types: RL, Optimization, Auction, Game Theory
    """

    def __init__(
        self,
        llm_config: Optional[Dict[str, Any]] = None,
        max_repair_attempts: int = 3,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        templates: Optional[List[AlgorithmTemplate]] = None,
    ):
        self.llm_config = llm_config
        self.validator = ModuleValidator(max_repair_attempts=max_repair_attempts)
        self.progress_callback = progress_callback
        self.use_llm = llm_status(llm_config).get("enabled", False)
        # Plugin-system source of truth. If the caller did not pass a list,
        # the loader scans the configured roots. See `docs/skills-protocol.md`.
        if templates is None:
            self._templates = discover_algorithm_templates()
        else:
            self._templates = list(templates)
        # When discovery returns nothing, fall back to the legacy
        # ALGORITHM_MODULE_MAP so the MVP still runs.
        self._use_legacy_map = len(self._templates) == 0

    def plan_modules(
        self,
        algorithm_family: str,
        innovation_spec: DetailedInnovationSpec,
    ) -> List[Dict[str, str]]:
        """Plan which modules to generate based on algorithm type.

        Returns list of dicts with: module_name, file_name, template_type

        When the plugin system has discovered templates for the family, the
        plan is built from those templates' `affected_modules` and `file_name`
        fields. Otherwise the legacy `ALGORITHM_MODULE_MAP` is consulted.
        """
        modules: List[Dict[str, str]] = []
        for module_name, file_name, template_type in BASE_MODULES:
            modules.append({
                "module_name": module_name,
                "file_name": file_name + ".py",
                "template_type": template_type,
                "category": "base",
            })

        family_templates = self._resolve_family_templates(algorithm_family)
        if family_templates:
            for template in family_templates:
                modules.append({
                    "module_name": template.name,
                    "file_name": template.file_name,
                    "template_type": template.name,
                    "category": "algorithm",
                })
            return modules

        algo_modules = ALGORITHM_MODULE_MAP.get(algorithm_family, [])
        for module_name, file_name, template_type in algo_modules:
            modules.append({
                "module_name": module_name,
                "file_name": file_name + ".py",
                "template_type": template_type,
                "category": "algorithm",
            })
        return modules

    def _resolve_family_templates(
        self,
        algorithm_family: str,
    ) -> List[AlgorithmTemplate]:
        """Return the discovered templates for the given family, or []."""
        if self._use_legacy_map:
            return []
        canonical = family_directory(algorithm_family)
        return [t for t in self._templates if t.family in (algorithm_family, canonical)]

    def resolve_template(
        self,
        algorithm_family: str,
        template_name: str,
    ) -> Optional[AlgorithmTemplate]:
        """Return the discovered template by name within a family, or None."""
        if self._use_legacy_map:
            return None
        for template in self._resolve_family_templates(algorithm_family):
            if template.name == template_name:
                return template
        return None

    def generate_all_modules(
        self,
        algorithm_family: str,
        innovation_spec: DetailedInnovationSpec,
        model_spec: Any,
        strategies: List[StrategySpec],
        paper_text: str,
    ) -> List[GeneratedModule]:
        """Generate all code modules for the paper."""
        module_plans = self.plan_modules(algorithm_family, innovation_spec)
        generated_modules = []

        for plan in module_plans:
            self._emit_progress({
                "event": "module_generation_start",
                "module": plan["module_name"],
                "category": plan["category"],
            })

            module = self._generate_single_module(
                plan=plan,
                innovation_spec=innovation_spec,
                model_spec=model_spec,
                strategies=strategies,
                paper_text=paper_text,
            )
            generated_modules.append(module)

            self._emit_progress({
                "event": "module_generation_done",
                "module": plan["module_name"],
                "status": module.status,
                "repair_attempts": module.repair_attempts,
            })

        return generated_modules

    def _generate_single_module(
        self,
        plan: Dict[str, str],
        innovation_spec: DetailedInnovationSpec,
        model_spec: Any,
        strategies: List[StrategySpec],
        paper_text: str,
    ) -> GeneratedModule:
        """Generate a single code module with validation and repair."""
        module_name = plan["module_name"]
        template_type = plan["template_type"]
        category = plan["category"]

        if category == "base":
            code = self._load_base_template(template_type)
            module = GeneratedModule(
                module_name=module_name,
                file_path=plan["file_name"],
                code=code,
                module_type=module_name,
                status="generated",
            )
            ok, errors, details = self.validator.validate_module(
                code, module_name, module_name
            )
            if not ok:
                module.status = "validation_failed"
                module.validation_errors = errors
            else:
                module.status = "validated"
            return module

        if innovation_spec.innovation_mode == "novel":
            code = self._generate_novel_module_llm(
                module_name=module_name,
                template_type=template_type,
                innovation_spec=innovation_spec,
                model_spec=model_spec,
                strategies=strategies,
                paper_text=paper_text,
            )
        else:
            code = self._generate_improved_module(
                module_name=module_name,
                template_type=template_type,
                innovation_spec=innovation_spec,
                model_spec=model_spec,
                strategies=strategies,
                paper_text=paper_text,
            )

        module = GeneratedModule(
            module_name=module_name,
            file_path=plan["file_name"],
            code=code,
            module_type=template_type,
            status="generated",
        )

        ok, errors, details = self.validator.validate_module(
            code, module_name, template_type
        )
        if not ok and self.use_llm:
            for attempt in range(1, self.validator.max_repair_attempts + 1):
                self._emit_progress({
                    "event": "module_repair",
                    "module": module_name,
                    "attempt": attempt,
                    "errors": errors[:3],
                })
                code = self._repair_module_llm(
                    code=code,
                    module_name=module_name,
                    module_type=template_type,
                    errors=errors,
                    innovation_spec=innovation_spec,
                )
                module.code = code
                module.repair_attempts = attempt
                ok, errors, details = self.validator.validate_module(
                    code, module_name, template_type
                )
                if ok:
                    break

        if ok:
            module.status = "validated"
        else:
            module.status = "validation_failed"
            module.validation_errors = errors

        return module

    def _load_base_template(self, template_type: str) -> str:
        """Load a base module template."""
        template_path = TEMPLATE_DIR / "Base" / f"{template_type}.py"
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        return f"# Template for {template_type} not found\n"

    def _load_algorithm_template(self, algorithm_family: str, template_type: str) -> str:
        """Load an algorithm template.

        Looks up the discovered template by name first; falls back to the
        legacy `algorithm_templates/<family>/<template_type>.py` disk path
        when discovery has no match. The legacy path is also used as a
        safety net for back-compat tests.
        """
        family_dirs = {
            "RL": "RL",
            "RL/MARL": "RL",
            "Optimization": "Optimization",
            "Auction": "Auction",
            "Game Theory": "GameTheory",
            "Rule-based": "RuleBased",
        }
        if not self._use_legacy_map:
            for template in self._resolve_family_templates(algorithm_family):
                if template.name == template_type and template.source:
                    impl_path = Path(template.source) / template.file_name
                    if impl_path.exists():
                        with open(impl_path, "r", encoding="utf-8") as f:
                            return f.read()
        family_dir = family_dirs.get(algorithm_family, "RL")
        template_path = TEMPLATE_DIR / family_dir / f"{template_type}.py"
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        return f"# Template for {template_type} not found\n"

    def _generate_improved_module(
        self,
        module_name: str,
        template_type: str,
        innovation_spec: DetailedInnovationSpec,
        model_spec: Any,
        strategies: List[StrategySpec],
        paper_text: str,
    ) -> str:
        """Generate an improved module based on template + innovations."""
        base_code = self._load_algorithm_template(
            innovation_spec.base_algorithm_family, template_type
        )

        relevant_innovations = [
            inv for inv in innovation_spec.layered_innovations
            if self._innovation_affects_module(inv, module_name)
        ]

        if not relevant_innovations or not self.use_llm:
            return base_code

        return self._apply_innovations_llm(
            base_code=base_code,
            module_name=module_name,
            module_type=template_type,
            innovations=relevant_innovations,
            innovation_spec=innovation_spec,
            model_spec=model_spec,
            paper_text=paper_text,
        )

    def _generate_novel_module_llm(
        self,
        module_name: str,
        template_type: str,
        innovation_spec: DetailedInnovationSpec,
        model_spec: Any,
        strategies: List[StrategySpec],
        paper_text: str,
    ) -> str:
        """Generate a novel algorithm module from scratch using LLM."""
        if not self.use_llm:
            return self._load_algorithm_template(
                innovation_spec.base_algorithm_family, template_type
            )

        prompt = {
            "task": "Generate Python code for a novel P2P energy trading algorithm module.",
            "module_name": module_name,
            "module_type": template_type,
            "paper_algorithm_description": innovation_spec.algorithm_description,
            "pseudocode": innovation_spec.pseudocode,
            "innovation_details": [to_dict(inv) for inv in innovation_spec.layered_innovations],
            "model_spec": to_dict(model_spec),
            "paper_excerpt": paper_text[:4000],
            "requirements": f"""
Generate a complete Python module implementing the {module_name} for the novel algorithm described in the paper.
The module must follow standard P2P energy trading patterns and include proper class/method interfaces.
Make sure the code is self-contained and can run with the base grid/market modules.
Include proper type hints and docstrings.
""",
        }

        try:
            response = call_chat_json(
                [
                    {"role": "system", "content": LLM_CODE_SYSTEM_PROMPT},
                    {"role": "user", "content": str(prompt)},
                ],
                llm_config=self.llm_config,
            )
            code = response.get("code", "") if isinstance(response, dict) else str(response)
            if not code or len(code) < 100:
                return self._load_algorithm_template(
                    innovation_spec.base_algorithm_family, template_type
                )
            return code
        except Exception:
            return self._load_algorithm_template(
                innovation_spec.base_algorithm_family, template_type
            )

    def _apply_innovations_llm(
        self,
        base_code: str,
        module_name: str,
        module_type: str,
        innovations: List[LayeredInnovation],
        innovation_spec: DetailedInnovationSpec,
        model_spec: Any,
        paper_text: str,
    ) -> str:
        """Apply innovations to base code using LLM."""
        if not self.use_llm:
            return base_code

        prompt = {
            "task": "Modify the base algorithm code to apply the paper's innovations.",
            "module_name": module_name,
            "module_type": module_type,
            "base_algorithm": innovation_spec.base_algorithm,
            "base_code": base_code,
            "innovations_to_apply": [
                {
                    "layer": inv.layer,
                    "description": inv.description,
                    "code_change_hint": inv.code_change_hint,
                }
                for inv in innovations
            ],
            "paper_algorithm_description": innovation_spec.algorithm_description,
            "model_spec": to_dict(model_spec),
            "paper_excerpt": paper_text[:3000],
            "instructions": """
Modify the base code to implement the innovations.
Keep the same class/function names and interfaces.
Add the innovation changes clearly marked with comments like '# === Paper Innovation: ... ==='.
Make sure all existing functionality still works.
Return only the modified Python code as a string in a 'code' field.
""",
        }

        try:
            response = call_chat_json(
                [
                    {"role": "system", "content": LLM_CODE_SYSTEM_PROMPT},
                    {"role": "user", "content": str(prompt)},
                ],
                llm_config=self.llm_config,
            )
            code = response.get("code", "") if isinstance(response, dict) else str(response)
            if not code or len(code) < len(base_code) * 0.5:
                return base_code
            return code
        except Exception:
            return base_code

    def _repair_module_llm(
        self,
        code: str,
        module_name: str,
        module_type: str,
        errors: List[str],
        innovation_spec: DetailedInnovationSpec,
    ) -> str:
        """Repair a failing module using LLM."""
        if not self.use_llm:
            return code

        prompt = {
            "task": "Fix the Python code that failed validation.",
            "module_name": module_name,
            "module_type": module_type,
            "code": code,
            "errors": errors,
            "instructions": """
Fix the errors in the code while preserving the algorithm logic.
Keep the same class/function names and interfaces.
Return only the fixed Python code as a string in a 'code' field.
""",
        }

        try:
            response = call_chat_json(
                [
                    {"role": "system", "content": LLM_CODE_SYSTEM_PROMPT},
                    {"role": "user", "content": str(prompt)},
                ],
                llm_config=self.llm_config,
            )
            fixed_code = response.get("code", "") if isinstance(response, dict) else str(response)
            if not fixed_code or len(fixed_code) < 100:
                return code
            return fixed_code
        except Exception:
            return code

    def _innovation_affects_module(self, innovation: LayeredInnovation, module_name: str) -> bool:
        """Check if an innovation affects a specific module."""
        affected = [f.lower() for f in innovation.affected_modules]
        module_file = module_name.lower() + ".py"
        return module_file in affected or module_name.lower() in str(innovation.description).lower()

    def _emit_progress(self, payload: Dict[str, Any]) -> None:
        if self.progress_callback:
            self.progress_callback(payload)
