"""
CodeSynthesizer — Generates each source file according to the
ArchitecturePlan, using the full paper analysis as context.

Generates files one at a time in dependency order, feeding previously
generated files as context for later ones to ensure consistency.
"""

import json
import os
from typing import Optional

from providers.base import BaseProvider, GenerationConfig, ModelCapability
from providers import get_provider
from core.analyzer import PaperAnalysis
from core.architect import ArchitecturePlan, FileSpec


class CodeSynthesizer:
    """
    Synthesizes ML code from a paper analysis and architecture plan.

    Key design decisions:
      - Files are generated in priority/dependency order.
      - Previously generated files are included as context (rolling window).
      - Equations are embedded as comments in the code.
      - Hyperparameters reference the config file.
    """

    PROMPT_FILE = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "prompts", "coder.txt"
    )

    def __init__(self, provider: Optional[BaseProvider] = None):
        self.provider = provider or get_provider(
            required_capability=ModelCapability.CODE_GENERATION
        )

    def _load_prompt(self, path: str, **kwargs) -> str:
        if os.path.exists(path):
            with open(path) as f:
                template = f.read()
            for key, value in kwargs.items():
                template = template.replace(f"{{{{{key}}}}}", str(value))
            return template
        return ""

    def generate_codebase(
        self,
        analysis: PaperAnalysis,
        plan: ArchitecturePlan,
        document: Optional[object] = None,
    ) -> dict[str, str]:
        """
        Generate all files specified in the architecture plan.

        Args:
            analysis: Paper analysis with equations, hyperparams, etc.
            plan: Architecture plan with file specifications.
            document: Optional uploaded document handle (Gemini).

        Returns:
            Dict mapping file paths to their generated content.
        """
        print(f"  [Coder] Generating {len(plan.files)} files...")

        generated: dict[str, str] = {}

        for i, file_spec in enumerate(plan.files):
            print(f"  [Coder] ({i+1}/{len(plan.files)}) Generating {file_spec.path}...")

            content = self._generate_single_file(
                file_spec=file_spec,
                analysis=analysis,
                plan=plan,
                generated_so_far=generated,
                document=document,
            )
            generated[file_spec.path] = content

        print(f"  [Coder] Code generation complete: {len(generated)} files.")
        return generated

    def _generate_single_file(
        self,
        file_spec: FileSpec,
        analysis: PaperAnalysis,
        plan: ArchitecturePlan,
        generated_so_far: dict[str, str],
        document: Optional[object] = None,
    ) -> str:
        """Generate a single file with full context."""

        prompt = self._load_prompt(self.PROMPT_FILE)
        if not prompt:
            prompt = self._default_prompt()

        # Build context
        context_parts = [
            f"# Paper: {analysis.title}",
            f"\n## Architecture Description\n{analysis.architecture_description}",
        ]

        # Include relevant equations
        if analysis.equations:
            context_parts.append("\n## Key Equations (embed as comments where relevant)")
            for eq in analysis.equations:
                context_parts.append(f"  - {eq}")

        # Include hyperparameters
        if analysis.hyperparameters:
            context_parts.append("\n## Hyperparameters (use config.yaml references)")
            for k, v in analysis.hyperparameters.items():
                context_parts.append(f"  - {k}: {v}")

        # Include loss functions
        if analysis.loss_functions:
            context_parts.append("\n## Loss Functions")
            for lf in analysis.loss_functions:
                context_parts.append(f"  - {lf}")

        # Include architecture plan context
        context_parts.append(f"\n## Repository Structure\n{plan.directory_tree}")

        # Include dependency files (previously generated)
        dep_context = self._get_dependency_context(file_spec, generated_so_far)
        if dep_context:
            context_parts.append("\n## Already Generated Dependencies")
            context_parts.append(dep_context)

        # Include Mermaid diagrams
        if analysis.diagrams_mermaid:
            context_parts.append("\n## Architecture Diagrams")
            for d in analysis.diagrams_mermaid:
                context_parts.append(f"```mermaid\n{d}\n```")

        # File-specific instruction
        file_instruction = (
            f"\n---\n\n"
            f"## YOUR TASK\n"
            f"Generate the complete content for: **{file_spec.path}**\n\n"
            f"Description: {file_spec.description}\n\n"
            f"Requirements:\n"
            f"- Implement EXACTLY what the paper describes\n"
            f"- Include docstrings and type hints\n"
            f"- Embed relevant equations as comments (LaTeX in docstrings)\n"
            f"- Use config references for hyperparameters, not hardcoded values\n"
            f"- Follow PyTorch conventions where applicable\n"
            f"- Make imports explicit — reference files from the repo structure\n"
            f"- Output ONLY the file content, no explanations\n"
        )

        full_prompt = "\n".join(context_parts) + file_instruction + "\n\n" + prompt

        # Determine max tokens based on file type
        max_tokens = 8192
        if file_spec.path.endswith((".yaml", ".yml", ".toml", ".cfg", ".txt")):
            max_tokens = 4096
        elif file_spec.path.endswith(".md"):
            max_tokens = 4096
        elif "model" in file_spec.path or "train" in file_spec.path:
            max_tokens = 16384

        config = GenerationConfig(
            temperature=0.15,
            max_output_tokens=max_tokens,
        )

        # Use file-based context for Gemini if available
        if document and hasattr(self.provider, "generate_with_file"):
            result = self.provider.generate_with_file(
                uploaded_file=document,
                prompt=full_prompt,
                system_prompt=self._system_prompt(),
                config=config,
            )
        else:
            result = self.provider.generate(
                prompt=full_prompt,
                system_prompt=self._system_prompt(),
                config=config,
            )

        return self._clean_output(result.text, file_spec.path)

    def _get_dependency_context(
        self, file_spec: FileSpec, generated: dict[str, str]
    ) -> str:
        """Get content of dependency files for context."""
        parts = []

        # Direct dependencies
        for dep_path in file_spec.dependencies:
            if dep_path in generated:
                content = generated[dep_path]
                # Truncate very long files
                if len(content) > 3000:
                    content = content[:3000] + "\n# ... (truncated)"
                parts.append(f"\n### {dep_path}\n```python\n{content}\n```")

        # Also include recent files (rolling context window, last 3)
        recent_paths = [p for p in list(generated.keys())[-3:] if p not in file_spec.dependencies]
        for path in recent_paths:
            content = generated[path]
            if len(content) > 1500:
                content = content[:1500] + "\n# ... (truncated)"
            parts.append(f"\n### {path} (recent)\n```python\n{content}\n```")

        return "\n".join(parts) if parts else ""

    def _clean_output(self, text: str, file_path: str) -> str:
        """Clean model output — strip markdown fences, explanations."""
        text = text.strip()

        # Remove markdown code fences
        if text.startswith("```"):
            first_newline = text.index("\n") if "\n" in text else 3
            text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3].rstrip()

        # For non-code files, return as-is
        if not file_path.endswith(".py"):
            return text

        # For Python files, ensure it's valid-ish
        lines = text.split("\n")
        # Remove leading explanation lines that aren't code
        while lines and not (
            lines[0].startswith(("#", "import", "from", '"""', "'''", "class", "def", "@"))
            or lines[0].strip() == ""
        ):
            lines.pop(0)

        return "\n".join(lines)

    def _system_prompt(self) -> str:
        return (
            "You are an expert ML engineer writing production-quality Python code. "
            "You implement research papers faithfully, with exact equations, "
            "correct tensor dimensions, and proper loss functions. "
            "Output ONLY the file content — no explanations, no markdown fences."
        )

    def _default_prompt(self) -> str:
        return (
            "Generate the complete, production-quality file content. "
            "Follow all requirements above strictly."
        )
