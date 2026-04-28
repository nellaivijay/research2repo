"""
SelfRefiner — Verify-then-refine loops for any pipeline stage output.

Implements a self-refinement pattern where the LLM first *critiques* an
artefact (plan, analysis, or code) against the paper context, then
*refines* it to address the identified issues.  The loop repeats up to a
configurable number of iterations, stopping early if no critical issues
remain.

Supported artefact types:
  - ``overall_plan``, ``architecture_design``, ``logic_design`` — JSON
  - ``file_analysis`` — JSON
  - ``config`` — YAML text
  - ``code`` — Python / generic text

Usage:
    from core.refiner import SelfRefiner
    refiner = SelfRefiner(max_iterations=2)
    result = refiner.refine(plan_dict, "overall_plan", paper_context)
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from providers.base import BaseProvider, GenerationConfig, ModelCapability
from providers import get_provider


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RefinementResult:
    """Outcome of a self-refine loop."""

    original: Any = None
    """The artefact as it was before refinement."""

    refined: Any = None
    """The artefact after refinement (same as *original* if no changes)."""

    critique: str = ""
    """The final critique text produced by the verification step."""

    improvements: list[str] = field(default_factory=list)
    """List of specific improvements made during refinement."""

    iterations: int = 0
    """How many refine iterations were actually executed."""

    improved: bool = False
    """Whether the artefact was modified at all."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_JSON_ARTIFACT_TYPES = frozenset({
    "overall_plan",
    "architecture_design",
    "logic_design",
    "file_analysis",
})

_TEXT_ARTIFACT_TYPES = frozenset({
    "config",
    "code",
})

_ALL_ARTIFACT_TYPES = _JSON_ARTIFACT_TYPES | _TEXT_ARTIFACT_TYPES

_PROMPT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
_VERIFY_PROMPT_FILE = os.path.join(_PROMPT_DIR, "self_refine_verify.txt")
_REFINE_PROMPT_FILE = os.path.join(_PROMPT_DIR, "self_refine_refine.txt")


# ---------------------------------------------------------------------------
# Default prompts
# ---------------------------------------------------------------------------

def _default_verify_prompt() -> str:
    return (
        "You are a rigorous ML reviewer.  Given the following artefact and "
        "the paper context, identify issues, inaccuracies, or missing "
        "elements.\n\n"
        "Return a JSON object with:\n"
        '  "critique": a free-text critique paragraph\n'
        '  "issues": a list of specific, actionable issues (strings)\n'
        '  "severity": one of "none", "minor", "major", "critical"\n\n'
        "Focus on:\n"
        "  - Missing equations or incorrect formulations\n"
        "  - Inconsistent tensor shapes or data types\n"
        "  - Missing hyperparameters or wrong defaults\n"
        "  - Dependency errors or import issues\n"
        "  - Deviations from the paper's described methodology\n\n"
        "If the artefact is correct and complete, set severity to 'none' "
        "and return an empty issues list.\n"
        "Respond with ONLY the JSON object."
    )


def _default_refine_prompt() -> str:
    return (
        "You are an expert ML engineer.  Given the artefact, the critique, "
        "and the paper context, produce a REFINED version that addresses "
        "every issue identified.\n\n"
        "Rules:\n"
        "  - Fix ALL issues listed in the critique\n"
        "  - Preserve correct parts unchanged\n"
        "  - Maintain the same structure / schema\n"
        "  - Be faithful to the paper's equations and methodology\n\n"
        "Return ONLY the refined artefact in the same format as the original."
    )


# ---------------------------------------------------------------------------
# Verification schema
# ---------------------------------------------------------------------------

_VERIFY_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "critique": {"type": "string"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "severity": {
            "type": "string",
            "enum": ["none", "minor", "major", "critical"],
        },
    },
}


# ---------------------------------------------------------------------------
# SelfRefiner
# ---------------------------------------------------------------------------

class SelfRefiner:
    """
    Wraps any pipeline artefact in a verify → refine loop.

    The refiner is intentionally stateless: each call to ``refine()``
    is self-contained, so multiple artefacts can be refined in parallel
    if needed.
    """

    def __init__(
        self,
        provider: Optional[BaseProvider] = None,
        max_iterations: int = 2,
    ) -> None:
        """
        Args:
            provider: LLM provider.  If *None*, auto-detects the best
                      provider with STRUCTURED_OUTPUT capability.
            max_iterations: Maximum number of refine cycles.  Set to 0 to
                            perform verification only (no refinement).
        """
        self.provider: BaseProvider = provider or get_provider(
            required_capability=ModelCapability.STRUCTURED_OUTPUT
        )
        self.max_iterations: int = max(0, max_iterations)

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
    # Artefact serialization
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_artifact(artifact: Any, artifact_type: str) -> str:
        """Convert an artefact to a string suitable for prompt inclusion."""
        if artifact_type in _JSON_ARTIFACT_TYPES:
            if isinstance(artifact, dict):
                return json.dumps(artifact, indent=2, default=str)
            # Dataclass or other object — attempt dict conversion
            try:
                return json.dumps(artifact.__dict__, indent=2, default=str)
            except (AttributeError, TypeError):
                return json.dumps(artifact, indent=2, default=str)
        # Text artefacts (config, code)
        return str(artifact)

    # ------------------------------------------------------------------
    # Verification (Step 1)
    # ------------------------------------------------------------------

    def verify(
        self,
        artifact: Any,
        artifact_type: str,
        context: str,
    ) -> tuple[str, list[str]]:
        """
        Critique an artefact against the paper context.

        Args:
            artifact: The artefact to verify (dict, dataclass, or string).
            artifact_type: One of the supported artefact types.
            context: Paper context string for grounding the critique.

        Returns:
            Tuple of (critique_text, list_of_issues).
        """
        print(f"  [SelfRefiner] Verifying {artifact_type}...")

        prompt_template = self._load_prompt(_VERIFY_PROMPT_FILE)
        if not prompt_template:
            prompt_template = _default_verify_prompt()

        artifact_str = self._serialize_artifact(artifact, artifact_type)

        full_prompt = (
            f"## Paper Context\n{context}\n\n"
            f"## Artefact Type: {artifact_type}\n\n"
            f"## Artefact\n```\n{artifact_str}\n```\n\n"
            f"---\n\n{prompt_template}"
        )

        try:
            data: dict = self.provider.generate_structured(
                prompt=full_prompt,
                schema=_VERIFY_SCHEMA,
                system_prompt=(
                    "You are a rigorous ML paper reviewer verifying that an "
                    "implementation artefact is faithful to the source paper."
                ),
                config=GenerationConfig(temperature=0.2, max_output_tokens=4096),
            )
        except Exception as exc:
            print(f"  [SelfRefiner] Structured verify failed ({exc}), retrying as text...")
            data = self._fallback_json_generate(full_prompt)

        critique = data.get("critique", "")
        issues = data.get("issues", [])
        severity = data.get("severity", "none")

        print(f"  [SelfRefiner] Verification result: severity={severity}, "
              f"{len(issues)} issue(s) found.")
        return critique, issues

    # ------------------------------------------------------------------
    # Refinement (Step 2)
    # ------------------------------------------------------------------

    def refine_artifact(
        self,
        artifact: Any,
        critique: str,
        artifact_type: str,
        context: str,
        schema: Optional[dict] = None,
    ) -> Any:
        """
        Produce a refined version of the artefact addressing the critique.

        Args:
            artifact: The artefact to refine.
            critique: Critique text from the verification step.
            artifact_type: One of the supported artefact types.
            context: Paper context string.
            schema: Optional JSON schema for structured artefacts.

        Returns:
            The refined artefact (dict for JSON types, str for text types).
        """
        prompt_template = self._load_prompt(_REFINE_PROMPT_FILE)
        if not prompt_template:
            prompt_template = _default_refine_prompt()

        artifact_str = self._serialize_artifact(artifact, artifact_type)

        full_prompt = (
            f"## Paper Context\n{context}\n\n"
            f"## Critique\n{critique}\n\n"
            f"## Original Artefact ({artifact_type})\n```\n{artifact_str}\n```\n\n"
            f"---\n\n{prompt_template}"
        )

        # JSON artefacts → structured generation
        if artifact_type in _JSON_ARTIFACT_TYPES:
            effective_schema = schema or {"type": "object"}
            try:
                return self.provider.generate_structured(
                    prompt=full_prompt,
                    schema=effective_schema,
                    system_prompt=(
                        "You are an expert ML engineer refining an "
                        "implementation artefact.  Output ONLY the corrected "
                        "JSON object."
                    ),
                    config=GenerationConfig(temperature=0.15, max_output_tokens=8192),
                )
            except Exception as exc:
                print(f"  [SelfRefiner] Structured refine failed ({exc}), retrying as text...")
                return self._fallback_json_generate(full_prompt)

        # Text artefacts → plain generation
        result = self.provider.generate(
            prompt=full_prompt,
            system_prompt=(
                "You are an expert ML engineer refining an implementation "
                "artefact.  Output ONLY the corrected artefact, no explanations."
            ),
            config=GenerationConfig(temperature=0.15, max_output_tokens=8192),
        )
        refined_text = result.text.strip()

        # Strip markdown fences if present
        if refined_text.startswith("```"):
            first_nl = refined_text.index("\n") if "\n" in refined_text else 3
            refined_text = refined_text[first_nl + 1:]
        if refined_text.endswith("```"):
            refined_text = refined_text[:-3].rstrip()

        return refined_text

    # ------------------------------------------------------------------
    # Full refine loop
    # ------------------------------------------------------------------

    def refine(
        self,
        artifact: Any,
        artifact_type: str,
        context: str,
        schema: Optional[dict] = None,
    ) -> RefinementResult:
        """
        Execute the full verify → refine loop.

        Args:
            artifact: The artefact to refine (dict, dataclass, or string).
            artifact_type: One of ``"overall_plan"``, ``"architecture_design"``,
                ``"logic_design"``, ``"config"``, ``"file_analysis"``,
                ``"code"``.
            context: Paper context string for grounding critiques.
            schema: Optional JSON schema for structured artefacts.  Passed
                    through to ``generate_structured`` during refinement.

        Returns:
            ``RefinementResult`` with original, refined artefact, critique,
            and metadata.

        Raises:
            ValueError: If *artifact_type* is not recognised.
        """
        if artifact_type not in _ALL_ARTIFACT_TYPES:
            raise ValueError(
                f"Unknown artifact_type '{artifact_type}'.  "
                f"Expected one of: {sorted(_ALL_ARTIFACT_TYPES)}"
            )

        print(f"[SelfRefiner] Starting refinement loop for '{artifact_type}' "
              f"(max {self.max_iterations} iteration(s))...")

        current = artifact
        all_improvements: list[str] = []
        last_critique = ""
        iterations_done = 0

        for iteration in range(1, self.max_iterations + 1):
            # --- Verify ---
            critique, issues = self.verify(current, artifact_type, context)
            last_critique = critique

            if not issues:
                print(f"  [SelfRefiner] No issues found — skipping refinement.")
                break

            # Early exit if only minor issues remain after first iteration
            if iteration > 1:
                critical_keywords = {"critical", "major", "missing", "incorrect", "wrong"}
                has_critical = any(
                    any(kw in issue.lower() for kw in critical_keywords)
                    for issue in issues
                )
                if not has_critical:
                    print(f"  [SelfRefiner] Only minor issues remain — stopping early.")
                    break

            # --- Refine ---
            print(f"  [SelfRefiner] Refining (iteration {iteration})...")
            refined = self.refine_artifact(
                artifact=current,
                critique=critique,
                artifact_type=artifact_type,
                context=context,
                schema=schema,
            )

            all_improvements.extend(issues)
            current = refined
            iterations_done = iteration

        improved = iterations_done > 0

        print(f"[SelfRefiner] Refinement {'applied' if improved else 'skipped'} "
              f"after {iterations_done} iteration(s), "
              f"{len(all_improvements)} improvement(s).")

        return RefinementResult(
            original=artifact,
            refined=current,
            critique=last_critique,
            improvements=all_improvements,
            iterations=iterations_done,
            improved=improved,
        )

    # ------------------------------------------------------------------
    # Fallback helper
    # ------------------------------------------------------------------

    def _fallback_json_generate(self, prompt: str) -> dict:
        """Generate plain text and parse JSON from the response."""
        result = self.provider.generate(
            prompt=prompt + "\n\nRespond with ONLY a JSON object.",
            system_prompt="You are an expert ML engineer.  Respond only with valid JSON.",
            config=GenerationConfig(temperature=0.15, max_output_tokens=4096),
        )
        text = result.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
