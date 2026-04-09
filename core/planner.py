"""
DecomposedPlanner — Structured 4-step planning pipeline inspired by
PaperCoder's decomposed planning approach.

Instead of generating a monolithic ``ArchitecturePlan`` in a single LLM
call, this module breaks the planning phase into four explicit sub-stages:

1. **Overall Plan** — high-level roadmap (components, methods, objectives).
2. **Architecture Design** — file list, Mermaid class/sequence diagrams.
3. **Logic Design** — dependency graph, execution order, per-file logic.
4. **Config Generation** — YAML configuration derived from hyperparameters.

The final ``PlanningResult`` carries all intermediate artefacts **and** a
backward-compatible ``ArchitecturePlan`` for downstream consumers.

Usage:
    from core.planner import DecomposedPlanner
    planner = DecomposedPlanner()
    result = planner.plan(paper_analysis)
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from providers.base import BaseProvider, GenerationConfig, ModelCapability
from providers import get_provider
from core.analyzer import PaperAnalysis
from core.architect import ArchitecturePlan, FileSpec


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class OverallPlan:
    """Step 1 output — high-level roadmap extracted from the paper."""

    core_components: list[str] = field(default_factory=list)
    """Major components to implement (e.g. 'Multi-Head Attention', 'Positional Encoding')."""

    methods_to_implement: list[str] = field(default_factory=list)
    """Concrete methods / algorithms referenced in the paper."""

    training_objectives: list[str] = field(default_factory=list)
    """Loss functions and training goals."""

    data_processing_steps: list[str] = field(default_factory=list)
    """Dataset loading, preprocessing, augmentation steps."""

    evaluation_protocols: list[str] = field(default_factory=list)
    """Metrics, benchmarks, evaluation methodology."""

    summary: str = ""
    """One-paragraph summary of the implementation plan."""


@dataclass
class ArchitectureDesign:
    """Step 2 output — structural design with Mermaid diagrams."""

    file_list: list[dict] = field(default_factory=list)
    """Each entry: {"path": str, "description": str, "module": str}."""

    class_diagram_mermaid: str = ""
    """Mermaid class diagram showing inheritance and composition."""

    sequence_diagram_mermaid: str = ""
    """Mermaid sequence diagram showing the training / inference flow."""

    module_relationships: list[dict] = field(default_factory=list)
    """Each entry: {"from": str, "to": str, "relationship": str}."""


@dataclass
class LogicDesign:
    """Step 3 output — dependency graph and per-file logic descriptions."""

    execution_order: list[str] = field(default_factory=list)
    """Ordered list of file paths (topologically sorted)."""

    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    """Mapping: file_path -> list of file paths it depends on."""

    file_specifications: list[dict] = field(default_factory=list)
    """Each entry: {"path": str, "logic_description": str,
                    "key_functions": list[str]}."""


@dataclass
class PlanningResult:
    """Aggregate output of the full 4-step planning pipeline."""

    overall_plan: OverallPlan = field(default_factory=OverallPlan)
    architecture_design: ArchitectureDesign = field(default_factory=ArchitectureDesign)
    logic_design: LogicDesign = field(default_factory=LogicDesign)
    config_content: str = ""
    """Generated YAML configuration string."""

    combined_plan: ArchitecturePlan = field(default_factory=ArchitecturePlan)
    """Backward-compatible ``ArchitecturePlan`` for downstream consumers."""


# ---------------------------------------------------------------------------
# Prompt / schema helpers
# ---------------------------------------------------------------------------

_PROMPT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")

_OVERALL_PLAN_PROMPT = os.path.join(_PROMPT_DIR, "overall_plan.txt")
_ARCH_DESIGN_PROMPT = os.path.join(_PROMPT_DIR, "architecture_design.txt")
_LOGIC_DESIGN_PROMPT = os.path.join(_PROMPT_DIR, "logic_design.txt")


def _default_overall_plan_prompt() -> str:
    return (
        "Based on the paper analysis below, extract a high-level "
        "implementation roadmap.\n\n"
        "Return a JSON object with these keys:\n"
        '  "core_components": list of major components to implement\n'
        '  "methods_to_implement": list of concrete algorithms / methods\n'
        '  "training_objectives": list of loss functions and training goals\n'
        '  "data_processing_steps": list of data loading / preprocessing steps\n'
        '  "evaluation_protocols": list of evaluation metrics and procedures\n'
        '  "summary": one-paragraph implementation summary\n\n'
        "Be specific and comprehensive.  Respond with ONLY the JSON object."
    )


def _default_arch_design_prompt() -> str:
    return (
        "Based on the paper analysis and overall plan below, design the "
        "software architecture.\n\n"
        "Return a JSON object with these keys:\n"
        '  "file_list": list of {"path": str, "description": str, "module": str}\n'
        '  "class_diagram_mermaid": Mermaid classDiagram code\n'
        '  "sequence_diagram_mermaid": Mermaid sequenceDiagram code\n'
        '  "module_relationships": list of {"from": str, "to": str, '
        '"relationship": str}\n\n'
        "Create a clean, modular structure following PyTorch conventions.\n"
        "Respond with ONLY the JSON object."
    )


def _default_logic_design_prompt() -> str:
    return (
        "Based on the paper analysis, overall plan, and architecture design "
        "below, determine the implementation logic for each file.\n\n"
        "Return a JSON object with these keys:\n"
        '  "execution_order": topologically sorted list of file paths '
        "(generate-first order)\n"
        '  "dependency_graph": dict mapping file_path -> list of file paths '
        "it imports from\n"
        '  "file_specifications": list of {"path": str, '
        '"logic_description": str, "key_functions": list[str]}\n\n'
        "The execution_order should respect dependencies: a file must come "
        "after all files it depends on.\n"
        "Respond with ONLY the JSON object."
    )


# JSON schemas for structured generation -----------------------------------

_OVERALL_PLAN_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "core_components": {"type": "array", "items": {"type": "string"}},
        "methods_to_implement": {"type": "array", "items": {"type": "string"}},
        "training_objectives": {"type": "array", "items": {"type": "string"}},
        "data_processing_steps": {"type": "array", "items": {"type": "string"}},
        "evaluation_protocols": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
}

_ARCH_DESIGN_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "file_list": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "description": {"type": "string"},
                    "module": {"type": "string"},
                },
            },
        },
        "class_diagram_mermaid": {"type": "string"},
        "sequence_diagram_mermaid": {"type": "string"},
        "module_relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "relationship": {"type": "string"},
                },
            },
        },
    },
}

_LOGIC_DESIGN_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "execution_order": {"type": "array", "items": {"type": "string"}},
        "dependency_graph": {"type": "object"},
        "file_specifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "logic_description": {"type": "string"},
                    "key_functions": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}


# ---------------------------------------------------------------------------
# DecomposedPlanner
# ---------------------------------------------------------------------------

class DecomposedPlanner:
    """
    Produces a complete ``PlanningResult`` through four explicit sub-stages.

    Each stage feeds its output as context into the next, allowing the LLM
    to build progressively on earlier decisions.  The final result includes
    a backward-compatible ``ArchitecturePlan`` so that existing downstream
    stages (``CodeSynthesizer``, ``CodeValidator``) work without changes.
    """

    def __init__(self, provider: Optional[BaseProvider] = None) -> None:
        """
        Args:
            provider: LLM provider for structured generation.  If *None*,
                      auto-detects the best provider with STRUCTURED_OUTPUT.
        """
        self.provider: BaseProvider = provider or get_provider(
            required_capability=ModelCapability.STRUCTURED_OUTPUT
        )

    # ------------------------------------------------------------------
    # Prompt loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_prompt(path: str, **kwargs: object) -> str:
        """Load a prompt template and substitute ``{{key}}`` placeholders."""
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                template = fh.read()
            for key, value in kwargs.items():
                template = template.replace(f"{{{{{key}}}}}", str(value))
            return template
        return ""

    # ------------------------------------------------------------------
    # Paper context builder (shared across steps)
    # ------------------------------------------------------------------

    @staticmethod
    def _paper_context(analysis: PaperAnalysis) -> str:
        """Build a compact paper summary for inclusion in prompts."""
        parts: list[str] = [
            f"# Paper: {analysis.title}",
            f"\n## Authors: {', '.join(analysis.authors)}",
            f"\n## Abstract\n{analysis.abstract}",
            f"\n## Architecture\n{analysis.architecture_description}",
        ]

        if analysis.equations:
            parts.append("\n## Key Equations")
            for eq in analysis.equations[:20]:
                parts.append(f"  - {eq}")

        if analysis.hyperparameters:
            parts.append("\n## Hyperparameters")
            for k, v in analysis.hyperparameters.items():
                parts.append(f"  - {k}: {v}")

        if analysis.loss_functions:
            parts.append("\n## Loss Functions")
            for lf in analysis.loss_functions:
                parts.append(f"  - {lf}")

        if analysis.key_contributions:
            parts.append("\n## Key Contributions")
            for c in analysis.key_contributions:
                parts.append(f"  - {c}")

        if analysis.datasets_mentioned:
            parts.append("\n## Datasets")
            for ds in analysis.datasets_mentioned:
                parts.append(f"  - {ds}")

        if analysis.diagrams_mermaid:
            parts.append("\n## Diagrams (Mermaid)")
            for i, d in enumerate(analysis.diagrams_mermaid, 1):
                parts.append(f"\n### Diagram {i}\n```mermaid\n{d}\n```")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Fallback JSON generation
    # ------------------------------------------------------------------

    def _fallback_generate(self, prompt: str) -> dict:
        """Generate as plain text and extract JSON from the response."""
        result = self.provider.generate(
            prompt=prompt + "\n\nRespond with ONLY a JSON object.",
            system_prompt="You are an expert ML architect.  Respond only with valid JSON.",
            config=GenerationConfig(temperature=0.1, max_output_tokens=8192),
        )
        text = result.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

    # ------------------------------------------------------------------
    # Step 1 — Overall Plan
    # ------------------------------------------------------------------

    def _step1_overall_plan(self, analysis: PaperAnalysis) -> OverallPlan:
        """Extract a high-level implementation roadmap from the paper."""
        print("  [Planner] Step 1/4: Generating overall plan...")

        prompt_template = self._load_prompt(_OVERALL_PLAN_PROMPT)
        if not prompt_template:
            prompt_template = _default_overall_plan_prompt()

        paper_ctx = self._paper_context(analysis)
        full_prompt = f"{paper_ctx}\n\n---\n\n{prompt_template}"

        try:
            data: dict = self.provider.generate_structured(
                prompt=full_prompt,
                schema=_OVERALL_PLAN_SCHEMA,
                system_prompt=(
                    "You are an expert ML researcher and engineer.  "
                    "Extract a precise implementation roadmap from the paper."
                ),
                config=GenerationConfig(temperature=0.1, max_output_tokens=4096),
            )
        except Exception as exc:
            print(f"  [Planner] Step 1 structured generation failed ({exc}), retrying as text...")
            data = self._fallback_generate(full_prompt)

        plan = OverallPlan(
            core_components=data.get("core_components", []),
            methods_to_implement=data.get("methods_to_implement", []),
            training_objectives=data.get("training_objectives", []),
            data_processing_steps=data.get("data_processing_steps", []),
            evaluation_protocols=data.get("evaluation_protocols", []),
            summary=data.get("summary", ""),
        )
        print(f"  [Planner] Step 1 complete: {len(plan.core_components)} core components identified.")
        return plan

    # ------------------------------------------------------------------
    # Step 2 — Architecture Design
    # ------------------------------------------------------------------

    def _step2_architecture_design(
        self,
        analysis: PaperAnalysis,
        overall_plan: OverallPlan,
    ) -> ArchitectureDesign:
        """Design file structure and Mermaid class/sequence diagrams."""
        print("  [Planner] Step 2/4: Designing architecture...")

        prompt_template = self._load_prompt(_ARCH_DESIGN_PROMPT)
        if not prompt_template:
            prompt_template = _default_arch_design_prompt()

        paper_ctx = self._paper_context(analysis)
        plan_ctx = (
            "\n## Overall Plan\n"
            f"Core components: {', '.join(overall_plan.core_components)}\n"
            f"Methods: {', '.join(overall_plan.methods_to_implement)}\n"
            f"Training objectives: {', '.join(overall_plan.training_objectives)}\n"
            f"Data steps: {', '.join(overall_plan.data_processing_steps)}\n"
            f"Evaluation: {', '.join(overall_plan.evaluation_protocols)}\n"
            f"Summary: {overall_plan.summary}\n"
        )
        full_prompt = f"{paper_ctx}\n{plan_ctx}\n---\n\n{prompt_template}"

        try:
            data: dict = self.provider.generate_structured(
                prompt=full_prompt,
                schema=_ARCH_DESIGN_SCHEMA,
                system_prompt=(
                    "You are an expert ML software architect.  "
                    "Design clean, modular repository structures with "
                    "Mermaid diagrams for documentation."
                ),
                config=GenerationConfig(temperature=0.1, max_output_tokens=8192),
            )
        except Exception as exc:
            print(f"  [Planner] Step 2 structured generation failed ({exc}), retrying as text...")
            data = self._fallback_generate(full_prompt)

        design = ArchitectureDesign(
            file_list=data.get("file_list", []),
            class_diagram_mermaid=data.get("class_diagram_mermaid", ""),
            sequence_diagram_mermaid=data.get("sequence_diagram_mermaid", ""),
            module_relationships=data.get("module_relationships", []),
        )
        print(f"  [Planner] Step 2 complete: {len(design.file_list)} files, "
              f"{len(design.module_relationships)} relationships.")
        return design

    # ------------------------------------------------------------------
    # Step 3 — Logic Design
    # ------------------------------------------------------------------

    def _step3_logic_design(
        self,
        analysis: PaperAnalysis,
        overall_plan: OverallPlan,
        arch_design: ArchitectureDesign,
    ) -> LogicDesign:
        """Determine dependency graph, execution order, and per-file logic."""
        print("  [Planner] Step 3/4: Designing logic and dependencies...")

        prompt_template = self._load_prompt(_LOGIC_DESIGN_PROMPT)
        if not prompt_template:
            prompt_template = _default_logic_design_prompt()

        paper_ctx = self._paper_context(analysis)
        plan_summary = f"\n## Overall Plan Summary\n{overall_plan.summary}\n"

        arch_ctx_parts: list[str] = ["\n## Architecture Design\n### File List"]
        for f in arch_design.file_list:
            arch_ctx_parts.append(
                f"  - {f.get('path', '?')}: {f.get('description', '')} "
                f"(module: {f.get('module', 'core')})"
            )
        if arch_design.class_diagram_mermaid:
            arch_ctx_parts.append(
                f"\n### Class Diagram\n```mermaid\n{arch_design.class_diagram_mermaid}\n```"
            )
        arch_ctx = "\n".join(arch_ctx_parts)

        full_prompt = f"{paper_ctx}\n{plan_summary}\n{arch_ctx}\n\n---\n\n{prompt_template}"

        try:
            data: dict = self.provider.generate_structured(
                prompt=full_prompt,
                schema=_LOGIC_DESIGN_SCHEMA,
                system_prompt=(
                    "You are an expert ML engineer.  Determine the correct "
                    "generation order and per-file implementation logic."
                ),
                config=GenerationConfig(temperature=0.1, max_output_tokens=8192),
            )
        except Exception as exc:
            print(f"  [Planner] Step 3 structured generation failed ({exc}), retrying as text...")
            data = self._fallback_generate(full_prompt)

        logic = LogicDesign(
            execution_order=data.get("execution_order", []),
            dependency_graph=data.get("dependency_graph", {}),
            file_specifications=data.get("file_specifications", []),
        )
        print(f"  [Planner] Step 3 complete: {len(logic.execution_order)} files ordered, "
              f"{len(logic.dependency_graph)} dependency entries.")
        return logic

    # ------------------------------------------------------------------
    # Step 4 — Config Generation
    # ------------------------------------------------------------------

    def _step4_config_generation(
        self,
        analysis: PaperAnalysis,
        overall_plan: OverallPlan,
        arch_design: ArchitectureDesign,
        logic_design: LogicDesign,
    ) -> str:
        """Generate a YAML configuration file from the paper's hyperparameters."""
        print("  [Planner] Step 4/4: Generating configuration...")

        hp_section = ""
        if analysis.hyperparameters:
            hp_lines = [f"  {k}: {v}" for k, v in analysis.hyperparameters.items()]
            hp_section = "\n## Hyperparameters from Paper\n" + "\n".join(hp_lines)

        training_section = ""
        if overall_plan.training_objectives:
            training_section = (
                "\n## Training Objectives\n"
                + "\n".join(f"  - {t}" for t in overall_plan.training_objectives)
            )

        prompt = (
            f"# Paper: {analysis.title}\n"
            f"{hp_section}\n"
            f"{training_section}\n\n"
            f"---\n\n"
            "Generate a complete YAML configuration file for this ML project.\n"
            "Include ALL hyperparameters from the paper organized into sections:\n"
            "  model, training, data, evaluation, logging.\n"
            "Use the exact values from the paper.  Add comments explaining each.\n"
            "Output ONLY the YAML content, no markdown fences or explanations."
        )

        result = self.provider.generate(
            prompt=prompt,
            system_prompt=(
                "You are an expert ML engineer.  Generate a clean, well-commented "
                "YAML configuration file."
            ),
            config=GenerationConfig(temperature=0.1, max_output_tokens=4096),
        )

        config_text = result.text.strip()
        # Strip markdown fences if present
        if config_text.startswith("```"):
            first_nl = config_text.index("\n") if "\n" in config_text else 3
            config_text = config_text[first_nl + 1:]
        if config_text.endswith("```"):
            config_text = config_text[:-3].rstrip()

        print("  [Planner] Step 4 complete: config generated.")
        return config_text

    # ------------------------------------------------------------------
    # Backward-compatibility converter
    # ------------------------------------------------------------------

    def _to_architecture_plan(
        self,
        analysis: PaperAnalysis,
        overall_plan: OverallPlan,
        arch_design: ArchitectureDesign,
        logic_design: LogicDesign,
        config_content: str,
    ) -> ArchitecturePlan:
        """
        Convert the decomposed planning outputs into a single
        ``ArchitecturePlan`` for backward compatibility with
        ``CodeSynthesizer`` and other downstream stages.
        """
        # Build FileSpec list from architecture + logic design
        # Use logic_design.execution_order for priority assignment
        order_map: dict[str, int] = {
            path: idx for idx, path in enumerate(logic_design.execution_order)
        }

        # Build a lookup from logic design for descriptions
        logic_lookup: dict[str, dict] = {
            spec.get("path", ""): spec
            for spec in logic_design.file_specifications
        }

        files: list[FileSpec] = []
        for file_entry in arch_design.file_list:
            path = file_entry.get("path", "")
            if not path:
                continue
            deps = logic_design.dependency_graph.get(path, [])
            logic_spec = logic_lookup.get(path, {})
            description = (
                file_entry.get("description", "")
                + ("\n\nLogic: " + logic_spec["logic_description"]
                   if logic_spec.get("logic_description") else "")
            )
            files.append(FileSpec(
                path=path,
                description=description,
                dependencies=deps,
                priority=order_map.get(path, 99),
            ))

        files.sort(key=lambda f: f.priority)

        # Build a simple directory tree from file paths
        tree_lines: list[str] = [f"{analysis.title or 'repo'}/"]
        seen_dirs: set[str] = set()
        for fs in files:
            parts = fs.path.split("/")
            for i in range(len(parts) - 1):
                dir_path = "/".join(parts[: i + 1])
                if dir_path not in seen_dirs:
                    indent = "  " * (i + 1)
                    tree_lines.append(f"{indent}{parts[i]}/")
                    seen_dirs.add(dir_path)
            indent = "  " * len(parts)
            tree_lines.append(f"{indent}{parts[-1]}")
        directory_tree = "\n".join(tree_lines)

        # Determine entrypoints
        training_entrypoint = "train.py"
        inference_entrypoint = "inference.py"
        for fs in files:
            lower = fs.path.lower()
            if "train" in lower and lower.endswith(".py"):
                training_entrypoint = fs.path
            if any(kw in lower for kw in ("infer", "eval", "predict")) and lower.endswith(".py"):
                inference_entrypoint = fs.path

        # Extract requirements from the architecture
        requirements: list[str] = ["torch>=2.0", "pyyaml", "numpy"]
        for comp in overall_plan.core_components:
            comp_lower = comp.lower()
            if "transformers" in comp_lower or "huggingface" in comp_lower:
                requirements.append("transformers")
            if "wandb" in comp_lower:
                requirements.append("wandb")
            if "tensorboard" in comp_lower:
                requirements.append("tensorboard")

        return ArchitecturePlan(
            repo_name=analysis.title.lower().replace(" ", "-")[:40] if analysis.title else "generated-repo",
            description=overall_plan.summary or analysis.abstract[:200],
            python_version="3.10",
            files=files,
            requirements=sorted(set(requirements)),
            directory_tree=directory_tree,
            config_schema={"type": "object", "description": "See config.yaml"},
            training_entrypoint=training_entrypoint,
            inference_entrypoint=inference_entrypoint,
            readme_outline=(
                f"# {analysis.title}\n\n"
                f"## Overview\n{overall_plan.summary}\n\n"
                f"## Components\n"
                + "\n".join(f"- {c}" for c in overall_plan.core_components)
                + "\n\n## Training\n```bash\npython {training_entrypoint}\n```\n"
            ),
        )

    # ------------------------------------------------------------------
    # Main orchestrator
    # ------------------------------------------------------------------

    def plan(
        self,
        analysis: PaperAnalysis,
        document: Optional[object] = None,
        vision_context: Optional[list[str]] = None,
    ) -> PlanningResult:
        """
        Execute the full 4-step planning pipeline.

        Args:
            analysis: Structured paper analysis from ``PaperAnalyzer``.
            document: Optional raw document handle (unused directly, reserved
                      for future Gemini-style file-context planning).
            vision_context: Optional Mermaid diagram strings (already captured
                            in ``analysis.diagrams_mermaid``).

        Returns:
            ``PlanningResult`` with all intermediate artefacts and a
            backward-compatible ``ArchitecturePlan``.
        """
        print("[Planner] Starting decomposed planning pipeline (4 steps)...")

        # Step 1
        overall_plan = self._step1_overall_plan(analysis)

        # Step 2
        arch_design = self._step2_architecture_design(analysis, overall_plan)

        # Step 3
        logic_design = self._step3_logic_design(analysis, overall_plan, arch_design)

        # Step 4
        config_content = self._step4_config_generation(
            analysis, overall_plan, arch_design, logic_design,
        )

        # Combine into backward-compatible plan
        combined = self._to_architecture_plan(
            analysis, overall_plan, arch_design, logic_design, config_content,
        )

        print(f"[Planner] Planning complete: {len(combined.files)} files planned.")

        return PlanningResult(
            overall_plan=overall_plan,
            architecture_design=arch_design,
            logic_design=logic_design,
            config_content=config_content,
            combined_plan=combined,
        )
