"""
ReferenceEvaluator — Reference-based (and reference-free) evaluation scoring
that compares generated repositories against ground-truth reference
implementations and/or the source paper.

Supports two modes:
  - **With reference**: compares generated code against a known-good
    implementation file-by-file, scoring structural and semantic fidelity.
  - **Without reference**: uses only the paper text to check whether key
    algorithmic components are implemented.

Runs multiple evaluation samples and averages scores for robustness.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from providers.base import BaseProvider, GenerationConfig, ModelCapability
from providers import get_provider


@dataclass
class EvaluationScore:
    """Aggregate evaluation result."""
    overall_score: float = 0.0                                 # 1–5 scale
    component_scores: dict[str, float] = field(default_factory=dict)  # e.g. {"method": 4.2}
    coverage: float = 0.0                                      # 0–100 %
    missing_components: list[str] = field(default_factory=list)
    extra_components: list[str] = field(default_factory=list)
    summary: str = ""
    severity_breakdown: dict[str, int] = field(default_factory=dict)  # {"high": 2, ...}


class ReferenceEvaluator:
    """
    Evaluates generated code against a reference implementation and/or
    the source research paper.

    Args:
        provider: LLM provider for evaluation. Auto-detected if ``None``.
        num_samples: Number of independent LLM evaluations to run and
            average (reduces variance).
    """

    PROMPT_FILE = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "prompts", "evaluator.txt"
    )

    def __init__(
        self,
        provider: Optional[BaseProvider] = None,
        num_samples: int = 3,
    ) -> None:
        self.provider = provider or get_provider(
            required_capability=ModelCapability.CODE_GENERATION
        )
        self.num_samples = max(1, num_samples)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_with_reference(
        self,
        generated_files: dict[str, str],
        reference_dir: str,
        paper_text: str,
    ) -> EvaluationScore:
        """
        Evaluate generated code against a reference implementation.

        Args:
            generated_files: ``{relative_path: content}`` of generated code.
            reference_dir: Path to the ground-truth reference repository.
            paper_text: Full text of the source paper (for context).

        Returns:
            Aggregated :class:`EvaluationScore`.
        """
        print("[ReferenceEvaluator] Loading reference files...")
        reference_files = self._load_reference_files(reference_dir)

        if not reference_files:
            print("[ReferenceEvaluator] No reference .py files found; "
                  "falling back to reference-free evaluation.")
            return self.evaluate_without_reference(generated_files, paper_text)

        print(f"[ReferenceEvaluator] Loaded {len(reference_files)} reference file(s).")

        prompt = self._build_eval_prompt(
            generated=generated_files,
            reference=reference_files,
            paper_text=paper_text,
            mode="with_reference",
        )

        scores = self._run_evaluations(prompt)
        aggregated = self._aggregate_scores(scores)

        print(f"[ReferenceEvaluator] With-reference score: "
              f"{aggregated.overall_score:.2f}/5 "
              f"(coverage {aggregated.coverage:.1f}%, "
              f"{len(aggregated.missing_components)} missing).")
        return aggregated

    def evaluate_without_reference(
        self,
        generated_files: dict[str, str],
        paper_text: str,
    ) -> EvaluationScore:
        """
        Reference-free evaluation using only the paper text.

        Identifies key algorithmic components described in the paper and
        checks whether the generated code implements them.

        Args:
            generated_files: ``{relative_path: content}`` of generated code.
            paper_text: Full text of the source paper.

        Returns:
            Aggregated :class:`EvaluationScore`.
        """
        print("[ReferenceEvaluator] Running reference-free evaluation...")

        prompt = self._build_eval_prompt(
            generated=generated_files,
            reference={},
            paper_text=paper_text,
            mode="without_reference",
        )

        scores = self._run_evaluations(prompt)
        aggregated = self._aggregate_scores(scores)

        print(f"[ReferenceEvaluator] Reference-free score: "
              f"{aggregated.overall_score:.2f}/5 "
              f"(coverage {aggregated.coverage:.1f}%, "
              f"{len(aggregated.missing_components)} missing).")
        return aggregated

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_reference_files(self, ref_dir: str) -> dict[str, str]:
        """Load all ``.py`` files from the reference directory.

        Returns:
            Dict mapping relative paths to file contents.
        """
        if not os.path.isdir(ref_dir):
            print(f"[ReferenceEvaluator] Reference directory not found: {ref_dir}")
            return {}

        files: dict[str, str] = {}
        for root, _dirs, filenames in os.walk(ref_dir):
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, ref_dir)
                try:
                    with open(full_path) as f:
                        files[rel_path] = f.read()
                except OSError:
                    pass

        return files

    def _build_eval_prompt(
        self,
        generated: dict[str, str],
        reference: dict[str, str],
        paper_text: str,
        mode: str,
    ) -> str:
        """Build the evaluation prompt for the LLM.

        Args:
            generated: Generated code files.
            reference: Reference code files (may be empty).
            paper_text: Source paper text.
            mode: ``"with_reference"`` or ``"without_reference"``.
        """
        # Try loading custom prompt
        prompt_template = self._load_prompt(self.PROMPT_FILE)

        # --- Paper section ---
        paper_section = f"## Source Paper (truncated)\n\n{paper_text[:30000]}\n"

        # --- Generated code section ---
        gen_section = "\n## Generated Code\n"
        for path, content in generated.items():
            display = content if len(content) < 6000 else content[:6000] + "\n# ... (truncated)"
            gen_section += f"\n### {path}\n```python\n{display}\n```\n"

        # --- Reference code section ---
        ref_section = ""
        if reference:
            ref_section = "\n## Reference Implementation\n"
            for path, content in reference.items():
                display = content if len(content) < 6000 else content[:6000] + "\n# ... (truncated)"
                ref_section += f"\n### {path}\n```python\n{display}\n```\n"

        if prompt_template:
            prompt = prompt_template
            prompt = prompt.replace("{{mode}}", mode)
            prompt = prompt.replace("{{paper_text}}", paper_section)
            prompt = prompt.replace("{{generated_code}}", gen_section)
            prompt = prompt.replace("{{reference_code}}", ref_section)
            return prompt

        # Default prompt
        if mode == "with_reference":
            return self._default_ref_prompt(paper_section, gen_section, ref_section)
        return self._default_noref_prompt(paper_section, gen_section)

    def _default_ref_prompt(
        self,
        paper_section: str,
        gen_section: str,
        ref_section: str,
    ) -> str:
        return f"""{paper_section}

{ref_section}

{gen_section}

## Evaluation Task

Compare the **Generated Code** against both the **Reference Implementation**
and the **Source Paper**.

Score each of the following components on a 1–5 scale:
  - **method**: Core algorithm / model architecture
  - **training**: Training loop, optimizer, scheduler
  - **data**: Data loading, preprocessing, augmentation
  - **evaluation**: Metrics, evaluation loop
  - **utils**: Configuration, logging, utilities
  - **reproducibility**: Seeds, determinism, config files

Also assess:
  - **coverage** (0–100): What percentage of the reference components are
    present in the generated code?
  - **missing_components**: List any reference components NOT in the
    generated code.
  - **extra_components**: List any generated components NOT in the reference.
  - **severity_breakdown**: Count issues by severity (high, medium, low).

Return a JSON object:
{{
  "overall_score": <float 1-5>,
  "component_scores": {{"method": <float>, "training": <float>, ...}},
  "coverage": <float 0-100>,
  "missing_components": [<str>, ...],
  "extra_components": [<str>, ...],
  "summary": "<brief text summary>",
  "severity_breakdown": {{"high": <int>, "medium": <int>, "low": <int>}}
}}
"""

    def _default_noref_prompt(self, paper_section: str, gen_section: str) -> str:
        return f"""{paper_section}

{gen_section}

## Evaluation Task (Reference-Free)

Evaluate the **Generated Code** against the **Source Paper** only.

1. Identify the key algorithmic components described in the paper
   (model architecture, loss functions, training procedure, data pipeline,
   evaluation metrics).
2. For each component, check whether the generated code implements it
   correctly.
3. Score each component on a 1–5 scale.

Also assess:
  - **coverage** (0–100): What percentage of the paper's described
    components are implemented?
  - **missing_components**: Paper components NOT found in the code.
  - **extra_components**: Code components NOT described in the paper.
  - **severity_breakdown**: Count issues by severity (high, medium, low).

Return a JSON object:
{{
  "overall_score": <float 1-5>,
  "component_scores": {{"method": <float>, "training": <float>, ...}},
  "coverage": <float 0-100>,
  "missing_components": [<str>, ...],
  "extra_components": [<str>, ...],
  "summary": "<brief text summary>",
  "severity_breakdown": {{"high": <int>, "medium": <int>, "low": <int>}}
}}
"""

    # ------------------------------------------------------------------
    # LLM interaction
    # ------------------------------------------------------------------

    def _run_evaluations(self, prompt: str) -> list[dict]:
        """Run *num_samples* evaluation calls and collect raw results."""
        schema = {
            "type": "object",
            "properties": {
                "overall_score": {"type": "number"},
                "component_scores": {"type": "object"},
                "coverage": {"type": "number"},
                "missing_components": {"type": "array", "items": {"type": "string"}},
                "extra_components": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"},
                "severity_breakdown": {"type": "object"},
            },
            "required": [
                "overall_score", "component_scores", "coverage",
                "missing_components", "summary", "severity_breakdown",
            ],
        }

        results: list[dict] = []
        for i in range(1, self.num_samples + 1):
            print(f"[ReferenceEvaluator] Evaluation sample {i}/{self.num_samples}...")
            try:
                data = self.provider.generate_structured(
                    prompt=prompt,
                    schema=schema,
                    system_prompt=(
                        "You are a meticulous ML code reviewer. Evaluate the "
                        "generated code faithfully and provide detailed scores."
                    ),
                    config=GenerationConfig(
                        temperature=0.3,  # slight variance across samples
                        max_output_tokens=4096,
                    ),
                )
                results.append(data)
            except Exception as exc:
                print(f"[ReferenceEvaluator] Sample {i} failed ({exc}); trying text fallback...")
                data = self._text_fallback(prompt)
                if data:
                    results.append(data)

        if not results:
            print("[ReferenceEvaluator] All evaluation samples failed.")
            return [{}]

        return results

    def _aggregate_scores(self, scores: list[dict]) -> EvaluationScore:
        """Average numeric scores across multiple samples.

        Non-numeric fields (lists, strings) are taken from the first
        sample.
        """
        if not scores:
            return EvaluationScore()

        n = len(scores)

        # Average overall score
        overall = sum(s.get("overall_score", 0.0) for s in scores) / n

        # Average component scores
        all_component_keys: set[str] = set()
        for s in scores:
            all_component_keys.update(s.get("component_scores", {}).keys())

        component_avg: dict[str, float] = {}
        for key in sorted(all_component_keys):
            vals = [
                s.get("component_scores", {}).get(key, 0.0)
                for s in scores
                if key in s.get("component_scores", {})
            ]
            component_avg[key] = sum(vals) / len(vals) if vals else 0.0

        # Average coverage
        coverage = sum(s.get("coverage", 0.0) for s in scores) / n

        # Aggregate severity breakdown (average, rounded to int)
        severity_keys = {"high", "medium", "low"}
        for s in scores:
            severity_keys.update(s.get("severity_breakdown", {}).keys())
        severity_avg: dict[str, int] = {}
        for key in sorted(severity_keys):
            vals = [
                s.get("severity_breakdown", {}).get(key, 0)
                for s in scores
            ]
            severity_avg[key] = round(sum(vals) / n)

        # Take lists/strings from the first sample
        first = scores[0]

        return EvaluationScore(
            overall_score=round(overall, 2),
            component_scores=component_avg,
            coverage=round(coverage, 1),
            missing_components=first.get("missing_components", []),
            extra_components=first.get("extra_components", []),
            summary=first.get("summary", ""),
            severity_breakdown=severity_avg,
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _load_prompt(self, path: str) -> str:
        """Load a prompt template file, or return empty string."""
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
        return ""

    def _text_fallback(self, prompt: str) -> dict:
        """Fallback: generate plain text and attempt to parse as JSON."""
        try:
            result = self.provider.generate(
                prompt=prompt + "\n\nRespond with ONLY a JSON object.",
                system_prompt="You are an ML code evaluator. Respond only with valid JSON.",
                config=GenerationConfig(temperature=0.3, max_output_tokens=4096),
            )
            text = result.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except (json.JSONDecodeError, Exception):
            return {}
