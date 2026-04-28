"""
CodeSynthesizer — Generates each source file according to the
ArchitecturePlan, using the full paper analysis as context.

Generates files one at a time in dependency order, feeding previously
generated files as context for later ones to ensure consistency.
"""

import concurrent.futures
import json
import os
from collections import defaultdict, deque
from threading import Lock
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

    _prompt_cache: dict[str, str] = {}

    def _load_prompt(self, path: str, **kwargs) -> str:
        if path not in self._prompt_cache:
            if os.path.exists(path):
                with open(path) as f:
                    self._prompt_cache[path] = f.read()
            else:
                return ""
        template = self._prompt_cache[path]
        for key, value in kwargs.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        return template

    def _build_static_context(
        self, analysis: PaperAnalysis, plan: ArchitecturePlan
    ) -> str:
        """
        Build the portion of the prompt context that is identical for every
        file: paper title, architecture description, equations, hyperparameters,
        loss functions, repository structure, and Mermaid diagrams.

        This is computed once in generate_codebase() and reused across all
        _generate_single_file() calls to avoid redundant work.
        """
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

        # Include Mermaid diagrams
        if analysis.diagrams_mermaid:
            context_parts.append("\n## Architecture Diagrams")
            for d in analysis.diagrams_mermaid:
                context_parts.append(f"```mermaid\n{d}\n```")

        return "\n".join(context_parts)

    def _compute_depth_levels(
        self, files: list[FileSpec]
    ) -> list[list[FileSpec]]:
        """
        Group files by dependency depth using topological sort.

        Files at the same depth level have no inter-dependencies and can
        be generated in parallel.  Level 0 contains files with no
        dependencies (or whose dependencies are not part of this plan).

        Returns:
            List of lists — each inner list is one depth level.
        """
        path_to_spec: dict[str, FileSpec] = {fs.path: fs for fs in files}
        # Only consider dependencies that are within the plan
        plan_paths = set(path_to_spec.keys())

        # Build in-degree map and adjacency list
        in_degree: dict[str, int] = {fs.path: 0 for fs in files}
        dependents: dict[str, list[str]] = defaultdict(list)

        for fs in files:
            for dep in fs.dependencies:
                if dep in plan_paths:
                    in_degree[fs.path] += 1
                    dependents[dep].append(fs.path)

        # BFS-style topological sort by depth level
        levels: list[list[FileSpec]] = []
        queue = deque(p for p, deg in in_degree.items() if deg == 0)

        while queue:
            level_paths = list(queue)
            queue.clear()
            level = [path_to_spec[p] for p in level_paths]
            levels.append(level)
            for p in level_paths:
                for dep in dependents[p]:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)

        # Any remaining files (cycles) are appended as a final level
        remaining = [path_to_spec[p] for p in in_degree if in_degree[p] > 0]
        if remaining:
            levels.append(remaining)

        return levels

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

        # Build static context once — shared across every file generation call
        static_context = self._build_static_context(analysis, plan)

        generated: dict[str, str] = {}
        generated_lock = Lock()
        file_counter = [0]  # mutable counter for thread-safe progress

        # Group files by dependency depth for parallel generation
        depth_levels = self._compute_depth_levels(plan.files)

        for depth, level in enumerate(depth_levels):
            # All files in a level can be generated in parallel
            if len(level) == 1:
                # Single file — no need for a thread pool
                fs = level[0]
                file_counter[0] += 1
                print(
                    f"  [Coder] ({file_counter[0]}/{len(plan.files)}) "
                    f"Generating {fs.path}..."
                )
                content = self._generate_single_file(
                    file_spec=fs,
                    static_context=static_context,
                    plan=plan,
                    generated_so_far=generated,
                    document=document,
                )
                generated[fs.path] = content
            else:
                # Multiple independent files — generate in parallel
                def _gen(fs: FileSpec) -> tuple[str, str]:
                    with generated_lock:
                        file_counter[0] += 1
                        idx = file_counter[0]
                        # Snapshot generated_so_far under lock
                        snapshot = dict(generated)
                    print(
                        f"  [Coder] ({idx}/{len(plan.files)}) "
                        f"Generating {fs.path}..."
                    )
                    content = self._generate_single_file(
                        file_spec=fs,
                        static_context=static_context,
                        plan=plan,
                        generated_so_far=snapshot,
                        document=document,
                    )
                    return fs.path, content

                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(len(level), 4)
                ) as executor:
                    futures = {executor.submit(_gen, fs): fs for fs in level}
                    for future in concurrent.futures.as_completed(futures):
                        path, content = future.result()
                        generated[path] = content

        print(f"  [Coder] Code generation complete: {len(generated)} files.")
        return generated

    def _generate_single_file(
        self,
        file_spec: FileSpec,
        static_context: str,
        plan: ArchitecturePlan,
        generated_so_far: dict[str, str],
        document: Optional[object] = None,
    ) -> str:
        """Generate a single file with full context."""

        prompt = self._load_prompt(self.PROMPT_FILE)
        if not prompt:
            prompt = self._default_prompt()

        # Build context — start with pre-built static context
        context_parts = [static_context]

        # Include dependency files (previously generated)
        dep_context = self._get_dependency_context(file_spec, generated_so_far)
        if dep_context:
            context_parts.append("\n## Already Generated Dependencies")
            context_parts.append(dep_context)

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
        seen: set[str] = set()

        # Direct dependencies
        for dep_path in file_spec.dependencies:
            if dep_path in generated:
                seen.add(dep_path)
                content = generated[dep_path]
                # Truncate very long files
                if len(content) > 3000:
                    content = content[:3000] + "\n# ... (truncated)"
                parts.append(f"\n### {dep_path}\n```python\n{content}\n```")

        # Also include recent files (rolling context window, last 3)
        all_paths = list(generated.keys())
        recent_paths = all_paths[-3:] if len(all_paths) >= 3 else all_paths
        for path in recent_paths:
            if path not in seen:
                seen.add(path)
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
