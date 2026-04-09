"""
SystemArchitect — Designs repository structure, module decomposition,
dependency list, and config files based on the paper analysis.

Uses structured output to produce a deterministic repo blueprint
that the CodeSynthesizer can implement file-by-file.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from providers.base import BaseProvider, GenerationConfig, ModelCapability
from providers import get_provider
from core.analyzer import PaperAnalysis


@dataclass
class FileSpec:
    """Specification for a single file to generate."""
    path: str                      # e.g., "model/transformer.py"
    description: str               # What this file should contain
    dependencies: list[str] = field(default_factory=list)  # Other FileSpecs it depends on
    priority: int = 0              # Generation order (lower = first)


@dataclass
class ArchitecturePlan:
    """Complete blueprint for the generated repository."""
    repo_name: str = ""
    description: str = ""
    python_version: str = "3.10"
    files: list[FileSpec] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)  # pip packages
    directory_tree: str = ""       # Visual tree string
    config_schema: dict = field(default_factory=dict)
    training_entrypoint: str = "train.py"
    inference_entrypoint: str = "inference.py"
    readme_outline: str = ""


class SystemArchitect:
    """
    Designs the software architecture for the generated ML repository.

    The Architect takes the PaperAnalysis and produces an ArchitecturePlan
    that specifies every file, its purpose, dependencies, and the overall
    project structure.
    """

    PROMPT_FILE = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "prompts", "architect.txt"
    )

    def __init__(self, provider: Optional[BaseProvider] = None):
        self.provider = provider or get_provider(
            required_capability=ModelCapability.STRUCTURED_OUTPUT
        )

    def _load_prompt(self, path: str, **kwargs) -> str:
        if os.path.exists(path):
            with open(path) as f:
                template = f.read()
            for key, value in kwargs.items():
                template = template.replace(f"{{{{{key}}}}}", str(value))
            return template
        return ""

    def design_system(
        self,
        analysis: PaperAnalysis,
        document: Optional[object] = None,
        vision_context: Optional[list[str]] = None,
    ) -> ArchitecturePlan:
        """
        Design the repository architecture from a paper analysis.

        Args:
            analysis: Structured paper analysis from PaperAnalyzer.
            document: Optional raw document handle for additional context.
            vision_context: Optional Mermaid diagrams.

        Returns:
            ArchitecturePlan with complete file specifications.
        """
        print("  [Architect] Designing repository structure...")

        prompt = self._load_prompt(self.PROMPT_FILE)
        if not prompt:
            prompt = self._default_prompt()

        # Build context from analysis
        context = self._build_context(analysis, vision_context)
        full_prompt = f"{context}\n\n---\n\n{prompt}"

        schema = {
            "type": "object",
            "properties": {
                "repo_name": {"type": "string"},
                "description": {"type": "string"},
                "python_version": {"type": "string"},
                "directory_tree": {"type": "string"},
                "training_entrypoint": {"type": "string"},
                "inference_entrypoint": {"type": "string"},
                "readme_outline": {"type": "string"},
                "requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "description": {"type": "string"},
                            "dependencies": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "priority": {"type": "integer"},
                        },
                    },
                },
                "config_schema": {"type": "object"},
            },
        }

        try:
            data = self.provider.generate_structured(
                prompt=full_prompt,
                schema=schema,
                system_prompt=(
                    "You are an expert ML engineer and software architect. "
                    "Design clean, modular, production-quality repository structures."
                ),
                config=GenerationConfig(temperature=0.1, max_output_tokens=8192),
            )
        except Exception as e:
            print(f"  [Architect] Structured generation failed ({e}), retrying with text...")
            data = self._fallback_generate(full_prompt)

        plan = self._parse_plan(data)

        # Ensure essential files exist
        plan = self._ensure_essentials(plan, analysis)

        print(f"  [Architect] Plan ready: {len(plan.files)} files, "
              f"{len(plan.requirements)} dependencies")
        return plan

    def _build_context(
        self, analysis: PaperAnalysis, vision_context: Optional[list[str]] = None
    ) -> str:
        """Build a context string from the paper analysis."""
        parts = [
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

        if vision_context:
            parts.append("\n## Architecture Diagrams (Mermaid)")
            for i, d in enumerate(vision_context, 1):
                parts.append(f"\n### Diagram {i}\n```mermaid\n{d}\n```")

        return "\n".join(parts)

    def _parse_plan(self, data: dict) -> ArchitecturePlan:
        """Convert JSON data to ArchitecturePlan."""
        files = []
        for f in data.get("files", []):
            files.append(FileSpec(
                path=f.get("path", ""),
                description=f.get("description", ""),
                dependencies=f.get("dependencies", []),
                priority=f.get("priority", 0),
            ))
        # Sort by priority
        files.sort(key=lambda f: f.priority)

        return ArchitecturePlan(
            repo_name=data.get("repo_name", "generated_repo"),
            description=data.get("description", ""),
            python_version=data.get("python_version", "3.10"),
            files=files,
            requirements=data.get("requirements", []),
            directory_tree=data.get("directory_tree", ""),
            config_schema=data.get("config_schema", {}),
            training_entrypoint=data.get("training_entrypoint", "train.py"),
            inference_entrypoint=data.get("inference_entrypoint", "inference.py"),
            readme_outline=data.get("readme_outline", ""),
        )

    def _ensure_essentials(
        self, plan: ArchitecturePlan, analysis: PaperAnalysis
    ) -> ArchitecturePlan:
        """Ensure the plan includes essential files."""
        existing_paths = {f.path for f in plan.files}
        essentials = [
            FileSpec(
                path="config.yaml",
                description="Hyperparameter configuration file with all values from the paper.",
                priority=-2,
            ),
            FileSpec(
                path="README.md",
                description=f"Project README for {analysis.title}.",
                priority=100,
            ),
            FileSpec(
                path="requirements.txt",
                description="Python dependencies.",
                priority=-1,
            ),
        ]
        for e in essentials:
            if e.path not in existing_paths:
                plan.files.append(e)

        # Re-sort
        plan.files.sort(key=lambda f: f.priority)
        return plan

    def _fallback_generate(self, prompt: str) -> dict:
        """Fallback: generate as text and parse JSON from response."""
        result = self.provider.generate(
            prompt=prompt + "\n\nRespond with ONLY a JSON object.",
            system_prompt="You are an expert ML software architect. Respond only with valid JSON.",
            config=GenerationConfig(temperature=0.1, max_output_tokens=8192),
        )
        text = result.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

    def _default_prompt(self) -> str:
        return """Based on the research paper analysis above, design a complete Python repository structure.

Requirements:
1. MODULAR design — separate files for model, data loading, training, evaluation, config, utils
2. Follow PyTorch conventions (Dataset, DataLoader, nn.Module, Optimizer)
3. Include config.yaml with ALL hyperparameters from the paper
4. Include proper __init__.py files
5. Include training script with logging (tensorboard/wandb)
6. Include inference/evaluation script
7. Include unit test stubs

For each file, specify:
- path: relative path in the repo
- description: what the file should contain and implement
- dependencies: list of other file paths this depends on
- priority: integer ordering (lower = generate first; config/utils before model before training)

Also specify:
- repo_name: short kebab-case name
- description: one-line description
- requirements: list of pip packages needed
- directory_tree: visual tree of the repo structure
- config_schema: JSON schema for the config.yaml
- training_entrypoint: path to training script
- inference_entrypoint: path to inference script
- readme_outline: markdown outline for the README

Respond with ONLY a JSON object."""
