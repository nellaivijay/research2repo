"""
FileAnalyzer — Per-file analysis phase inspired by PaperCoder's Analysis stage.

Before code generation begins, this module produces detailed specifications
for EACH file in the architecture plan.  The specifications include class
hierarchies, function signatures, import lists, algorithmic steps extracted
from the paper, and test criteria.  These analyses feed into the
CodeSynthesizer so that every generated file is faithful to the paper.

Usage:
    from core.file_analyzer import FileAnalyzer
    fa = FileAnalyzer()
    analyses = fa.analyze_all(plan, paper_analysis)
"""

import concurrent.futures
import json
import os
from dataclasses import dataclass, field
from typing import Optional

from providers.base import BaseProvider, GenerationConfig, ModelCapability
from providers import get_provider
from core.analyzer import PaperAnalysis
from core.architect import ArchitecturePlan, FileSpec


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FileAnalysis:
    """Detailed specification for a single source file."""

    file_path: str = ""

    classes: list[dict] = field(default_factory=list)
    """Each entry: {"name": str, "attributes": list[str],
                    "methods": list[str], "base_classes": list[str]}"""

    functions: list[dict] = field(default_factory=list)
    """Each entry: {"name": str, "args": list[str],
                    "return_type": str, "description": str}"""

    imports: list[str] = field(default_factory=list)
    """Explicit import statements, e.g. 'import torch' or 'from model.encoder import Encoder'."""

    dependencies: list[str] = field(default_factory=list)
    """Other project file paths this file imports from."""

    algorithms: list[str] = field(default_factory=list)
    """Ordered algorithmic steps extracted from the paper."""

    input_output_spec: dict = field(default_factory=dict)
    """Expected inputs and outputs, e.g. {"input": "Tensor[B, S, D]", "output": "Tensor[B, S, V]"}."""

    test_criteria: list[str] = field(default_factory=list)
    """What to verify: dimensions, numerical ranges, reproducibility, etc."""


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

_PROMPT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
_PROMPT_FILE = os.path.join(_PROMPT_DIR, "file_analysis.txt")


def _default_prompt() -> str:
    """Fallback prompt used when prompts/file_analysis.txt does not exist."""
    return (
        "You are an expert ML engineer performing pre-generation analysis.\n"
        "Given the paper analysis, architecture plan, and the specific file "
        "described below, produce a DETAILED specification for that file.\n\n"
        "Return a JSON object with these keys:\n"
        '  "classes": list of objects with keys name, attributes (list[str]), '
        "methods (list[str]), base_classes (list[str])\n"
        '  "functions": list of objects with keys name, args (list[str]), '
        "return_type (str), description (str)\n"
        '  "imports": list of full import statements (e.g. "import torch")\n'
        '  "dependencies": list of project file paths this file imports from\n'
        '  "algorithms": ordered list of algorithmic steps from the paper '
        "that this file must implement\n"
        '  "input_output_spec": dict describing expected inputs and outputs '
        "(tensor shapes, data types, etc.)\n"
        '  "test_criteria": list of things to test (output shapes, loss '
        "ranges, gradient flow, etc.)\n\n"
        "Be thorough — extract EVERY relevant detail from the paper.\n"
        "Respond with ONLY the JSON object."
    )


# ---------------------------------------------------------------------------
# Schema for structured generation
# ---------------------------------------------------------------------------

_FILE_ANALYSIS_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "classes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "attributes": {"type": "array", "items": {"type": "string"}},
                    "methods": {"type": "array", "items": {"type": "string"}},
                    "base_classes": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "functions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "args": {"type": "array", "items": {"type": "string"}},
                    "return_type": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        },
        "imports": {"type": "array", "items": {"type": "string"}},
        "dependencies": {"type": "array", "items": {"type": "string"}},
        "algorithms": {"type": "array", "items": {"type": "string"}},
        "input_output_spec": {"type": "object"},
        "test_criteria": {"type": "array", "items": {"type": "string"}},
    },
}


# ---------------------------------------------------------------------------
# FileAnalyzer
# ---------------------------------------------------------------------------

class FileAnalyzer:
    """
    Generates per-file specifications before code synthesis.

    For every ``FileSpec`` in an ``ArchitecturePlan``, the analyzer produces a
    ``FileAnalysis`` containing class/function signatures, import lists,
    algorithmic steps from the paper, and test criteria.  Previously analyzed
    files are fed back as context so that later files maintain consistency.
    """

    def __init__(self, provider: Optional[BaseProvider] = None) -> None:
        """
        Args:
            provider: LLM provider for structured generation.  If *None*,
                      the best available provider with STRUCTURED_OUTPUT is
                      selected automatically.
        """
        self.provider: BaseProvider = provider or get_provider(
            required_capability=ModelCapability.STRUCTURED_OUTPUT
        )

    # ------------------------------------------------------------------
    # Prompt loading
    # ------------------------------------------------------------------

    _prompt_cache: dict[str, str] = {}

    @staticmethod
    def _load_prompt(path: str, **kwargs: object) -> str:
        """Load a prompt template and substitute ``{{key}}`` placeholders."""
        if path not in FileAnalyzer._prompt_cache:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    FileAnalyzer._prompt_cache[path] = fh.read()
            else:
                return ""
        template = FileAnalyzer._prompt_cache[path]
        for key, value in kwargs.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        return template

    # ------------------------------------------------------------------
    # Context builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_paper_context(analysis: PaperAnalysis) -> str:
        """Build a compact string summarising the paper for prompts."""
        parts: list[str] = [
            f"# Paper: {analysis.title}",
            f"\n## Architecture\n{analysis.architecture_description}",
        ]

        if analysis.equations:
            parts.append("\n## Equations")
            for eq in analysis.equations[:30]:
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

        if analysis.diagrams_mermaid:
            parts.append("\n## Diagrams (Mermaid)")
            for i, d in enumerate(analysis.diagrams_mermaid, 1):
                parts.append(f"\n### Diagram {i}\n```mermaid\n{d}\n```")

        return "\n".join(parts)

    @staticmethod
    def _build_plan_context(plan: ArchitecturePlan) -> str:
        """Summarise the architecture plan for prompts."""
        parts: list[str] = [
            f"## Repository: {plan.repo_name}",
            f"Description: {plan.description}",
            f"\n## Directory Tree\n{plan.directory_tree}",
            "\n## File List",
        ]
        for fs in plan.files:
            deps = ", ".join(fs.dependencies) if fs.dependencies else "(none)"
            parts.append(f"  - {fs.path} [priority {fs.priority}]: {fs.description}  deps={deps}")
        return "\n".join(parts)

    @staticmethod
    def _build_prior_context(prior_analyses: dict[str, "FileAnalysis"]) -> str:
        """Summarise previously analysed files for cross-file consistency.

        Uses a compact format: class names, top-5 function names, and
        top-5 imports per file to keep the context concise.
        """
        if not prior_analyses:
            return ""
        parts: list[str] = ["\n## Previously Analyzed Files"]
        for path, fa in prior_analyses.items():
            parts.append(f"\n### {path}")
            if fa.classes:
                class_names = [cls.get("name", "?") for cls in fa.classes]
                parts.append(f"  classes: {', '.join(class_names)}")
            if fa.functions:
                fn_names = [fn.get("name", "?") for fn in fa.functions[:5]]
                suffix = f" (+{len(fa.functions) - 5} more)" if len(fa.functions) > 5 else ""
                parts.append(f"  functions: {', '.join(fn_names)}{suffix}")
            if fa.imports:
                parts.append(f"  imports: {', '.join(fa.imports[:5])}")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Core analysis
    # ------------------------------------------------------------------

    def analyze_file(
        self,
        file_spec: FileSpec,
        analysis: PaperAnalysis,
        plan: ArchitecturePlan,
        prior_analyses: dict[str, "FileAnalysis"],
        paper_context: Optional[str] = None,
        plan_context: Optional[str] = None,
    ) -> FileAnalysis:
        """
        Produce a ``FileAnalysis`` for a single file.

        Args:
            file_spec: The file to analyse.
            analysis: Full paper analysis (equations, hyperparams, etc.).
            plan: The architecture plan containing all files.
            prior_analyses: Analyses computed for earlier files, keyed by
                            file path.
            paper_context: Pre-built paper context string.  If *None*, it
                           is built on the fly (for backward compatibility).
            plan_context: Pre-built plan context string.  If *None*, it is
                          built on the fly (for backward compatibility).

        Returns:
            A populated ``FileAnalysis`` instance.
        """
        prompt_template = self._load_prompt(_PROMPT_FILE)
        if not prompt_template:
            prompt_template = _default_prompt()

        # Use pre-built contexts when available; fall back to building them.
        _paper_ctx = paper_context if paper_context is not None else self._build_paper_context(analysis)
        _plan_ctx = plan_context if plan_context is not None else self._build_plan_context(plan)

        context = "\n\n".join(
            filter(None, [
                _paper_ctx,
                _plan_ctx,
                self._build_prior_context(prior_analyses),
            ])
        )

        file_section = (
            f"\n---\n\n## Target File\n"
            f"Path: {file_spec.path}\n"
            f"Description: {file_spec.description}\n"
            f"Dependencies: {', '.join(file_spec.dependencies) if file_spec.dependencies else '(none)'}\n"
            f"Priority: {file_spec.priority}\n"
        )

        full_prompt = f"{context}{file_section}\n\n{prompt_template}"

        config = GenerationConfig(
            temperature=0.1,
            max_output_tokens=4096,
            response_format="json",
        )

        try:
            data: dict = self.provider.generate_structured(
                prompt=full_prompt,
                schema=_FILE_ANALYSIS_SCHEMA,
                system_prompt=(
                    "You are an expert ML engineer performing pre-generation "
                    "file analysis for a paper-to-code pipeline.  Be thorough "
                    "and precise with types, shapes, and algorithmic steps."
                ),
                config=config,
            )
        except Exception as exc:
            print(f"  [FileAnalyzer] Structured generation failed for {file_spec.path} ({exc}), "
                  f"retrying as plain text...")
            data = self._fallback_generate(full_prompt)

        return FileAnalysis(
            file_path=file_spec.path,
            classes=data.get("classes", []),
            functions=data.get("functions", []),
            imports=data.get("imports", []),
            dependencies=data.get("dependencies", []),
            algorithms=data.get("algorithms", []),
            input_output_spec=data.get("input_output_spec", {}),
            test_criteria=data.get("test_criteria", []),
        )

    def analyze_all(
        self,
        plan: ArchitecturePlan,
        analysis: PaperAnalysis,
    ) -> dict[str, FileAnalysis]:
        """
        Analyze every file in the plan, accumulating context as we go.

        Files are analysed in the order they appear in ``plan.files``
        (which is typically sorted by priority).  Each subsequent file
        receives the analyses of all preceding files as additional context.

        Files are processed in batches of up to 4 concurrently using a
        thread pool.  All files within a batch share the same snapshot of
        prior analyses so that they can run in parallel without conflicts.

        Args:
            plan: The architecture plan with ordered file specs.
            analysis: The full paper analysis.

        Returns:
            Dict mapping file path to its ``FileAnalysis``.
        """
        results: dict[str, FileAnalysis] = {}
        total = len(plan.files)

        print(f"[FileAnalyzer] Starting per-file analysis for {total} files...")

        # Pre-build static contexts once (identical for every file).
        paper_ctx = self._build_paper_context(analysis)
        plan_ctx = self._build_plan_context(plan)

        BATCH_SIZE = 4
        file_list = list(plan.files)

        for batch_start in range(0, total, BATCH_SIZE):
            batch = file_list[batch_start : batch_start + BATCH_SIZE]

            # Snapshot prior_analyses so every file in the batch sees the
            # same context (results accumulated from previous batches).
            prior_snapshot = dict(results)

            def _analyze_one(file_spec: FileSpec, _idx: int = batch_start) -> FileAnalysis:
                idx = file_list.index(file_spec) + 1
                print(f"[FileAnalyzer] Analyzing {file_spec.path}... ({idx}/{total})")
                return self.analyze_file(
                    file_spec=file_spec,
                    analysis=analysis,
                    plan=plan,
                    prior_analyses=prior_snapshot,
                    paper_context=paper_ctx,
                    plan_context=plan_ctx,
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                futures = {
                    executor.submit(_analyze_one, fs): fs for fs in batch
                }
                for future in concurrent.futures.as_completed(futures):
                    fs = futures[future]
                    fa = future.result()
                    results[fs.path] = fa

        print(f"[FileAnalyzer] Per-file analysis complete: {len(results)} files analyzed.")
        return results

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _fallback_generate(self, prompt: str) -> dict:
        """Generate as plain text and parse JSON from the response."""
        result = self.provider.generate(
            prompt=prompt + "\n\nRespond with ONLY a JSON object.",
            system_prompt=(
                "You are an expert ML engineer.  Respond only with valid JSON."
            ),
            config=GenerationConfig(temperature=0.1, max_output_tokens=4096),
        )
        text = result.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
