"""
CodeValidator — Self-review pass that verifies generated code against
the original paper. Checks equation fidelity, dimension consistency,
hyperparameter completeness, and code quality.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from providers.base import BaseProvider, GenerationConfig, ModelCapability
from providers import get_provider
from core.analyzer import PaperAnalysis
from core.architect import ArchitecturePlan


@dataclass
class ValidationIssue:
    """A single issue found during validation."""
    severity: str         # "critical", "warning", "info"
    file_path: str
    line_hint: str = ""   # Approximate location
    description: str = ""
    suggestion: str = ""
    category: str = ""    # "equation", "dimension", "hyperparameter", "style", "logic"


@dataclass
class ValidationReport:
    """Complete validation report."""
    issues: list[ValidationIssue] = field(default_factory=list)
    score: float = 0.0              # 0-100 fidelity score
    equation_coverage: float = 0.0  # % of paper equations found in code
    hyperparam_coverage: float = 0.0
    summary: str = ""
    passed: bool = False

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


class CodeValidator:
    """
    Validates generated code against the source paper.

    Checks:
      1. Equation fidelity — every paper equation has a code counterpart
      2. Dimension consistency — tensor shapes match the paper
      3. Hyperparameter completeness — all values are configurable
      4. Loss function accuracy — matches the paper's formulation
      5. Code quality — imports, types, docstrings
    """

    PROMPT_FILE = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "prompts", "validator.txt"
    )

    def __init__(self, provider: Optional[BaseProvider] = None):
        self.provider = provider or get_provider(
            required_capability=ModelCapability.CODE_GENERATION
        )

    def _load_prompt(self, path: str) -> str:
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
        return ""

    def validate(
        self,
        generated_files: dict[str, str],
        analysis: PaperAnalysis,
        plan: ArchitecturePlan,
    ) -> ValidationReport:
        """
        Run full validation of generated code against the paper.

        Args:
            generated_files: Dict of file_path -> content.
            analysis: Original paper analysis.
            plan: Architecture plan used for generation.

        Returns:
            ValidationReport with issues and scores.
        """
        print("  [Validator] Running code validation against paper...")

        prompt = self._load_prompt(self.PROMPT_FILE)
        if not prompt:
            prompt = self._default_prompt()

        # Build the validation context
        context = self._build_validation_context(generated_files, analysis)
        full_prompt = f"{context}\n\n---\n\n{prompt}"

        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "equation_coverage": {"type": "number"},
                "hyperparam_coverage": {"type": "number"},
                "summary": {"type": "string"},
                "passed": {"type": "boolean"},
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "severity": {"type": "string"},
                            "file_path": {"type": "string"},
                            "line_hint": {"type": "string"},
                            "description": {"type": "string"},
                            "suggestion": {"type": "string"},
                            "category": {"type": "string"},
                        },
                    },
                },
            },
        }

        try:
            data = self.provider.generate_structured(
                prompt=full_prompt,
                schema=schema,
                system_prompt=(
                    "You are a meticulous ML code reviewer. Compare generated "
                    "code against the original paper and find all discrepancies."
                ),
                config=GenerationConfig(temperature=0.1, max_output_tokens=8192),
            )
        except Exception as e:
            print(f"  [Validator] Structured validation failed ({e}), using text fallback.")
            data = self._fallback_validate(full_prompt)

        report = self._parse_report(data)
        print(f"  [Validator] Score: {report.score}/100 | "
              f"Critical: {report.critical_count} | Warnings: {report.warning_count}")
        return report

    def fix_issues(
        self,
        generated_files: dict[str, str],
        report: ValidationReport,
        analysis: PaperAnalysis,
    ) -> dict[str, str]:
        """
        Attempt to auto-fix critical issues identified in validation.

        Returns updated file dict with fixes applied.
        """
        critical_issues = [i for i in report.issues if i.severity == "critical"]
        if not critical_issues:
            print("  [Validator] No critical issues to fix.")
            return generated_files

        print(f"  [Validator] Attempting to fix {len(critical_issues)} critical issue(s)...")

        # Group issues by file
        issues_by_file: dict[str, list[ValidationIssue]] = {}
        for issue in critical_issues:
            issues_by_file.setdefault(issue.file_path, []).append(issue)

        fixed_files = dict(generated_files)
        for file_path, issues in issues_by_file.items():
            if file_path not in fixed_files:
                continue

            original_content = fixed_files[file_path]
            issue_descriptions = "\n".join(
                f"- [{i.category}] {i.description} (suggestion: {i.suggestion})"
                for i in issues
            )

            fix_prompt = (
                f"Fix the following critical issues in this file.\n\n"
                f"## Issues\n{issue_descriptions}\n\n"
                f"## Current File: {file_path}\n```python\n{original_content}\n```\n\n"
                f"## Paper Equations\n"
                + "\n".join(f"- {eq}" for eq in analysis.equations[:15])
                + "\n\n"
                f"Output ONLY the corrected file content. No explanations."
            )

            result = self.provider.generate(
                prompt=fix_prompt,
                system_prompt="You are an ML code fixer. Fix the issues while preserving all correct code.",
                config=GenerationConfig(temperature=0.1, max_output_tokens=16384),
            )

            fixed_content = result.text.strip()
            if fixed_content.startswith("```"):
                fixed_content = fixed_content.split("\n", 1)[1] if "\n" in fixed_content else fixed_content[3:]
            if fixed_content.endswith("```"):
                fixed_content = fixed_content[:-3].rstrip()

            fixed_files[file_path] = fixed_content
            print(f"  [Validator] Fixed {file_path} ({len(issues)} issue(s))")

        return fixed_files

    def _build_validation_context(
        self, generated_files: dict[str, str], analysis: PaperAnalysis
    ) -> str:
        """Build context for the validation prompt."""
        parts = [
            f"# Paper: {analysis.title}",
            f"\n## Paper Equations (ALL must be implemented)",
        ]
        for eq in analysis.equations:
            parts.append(f"  - {eq}")

        parts.append("\n## Paper Hyperparameters (ALL must be configurable)")
        for k, v in analysis.hyperparameters.items():
            parts.append(f"  - {k}: {v}")

        parts.append("\n## Paper Loss Functions")
        for lf in analysis.loss_functions:
            parts.append(f"  - {lf}")

        parts.append(f"\n## Architecture Description\n{analysis.architecture_description}")

        parts.append("\n\n# Generated Code Files")
        for path, content in generated_files.items():
            # Truncate extremely long files for the validation context
            display_content = content if len(content) < 5000 else content[:5000] + "\n# ... (truncated)"
            parts.append(f"\n## {path}\n```python\n{display_content}\n```")

        return "\n".join(parts)

    def _parse_report(self, data: dict) -> ValidationReport:
        """Parse validation data into a report."""
        issues = []
        for item in data.get("issues", []):
            issues.append(ValidationIssue(
                severity=item.get("severity", "info"),
                file_path=item.get("file_path", ""),
                line_hint=item.get("line_hint", ""),
                description=item.get("description", ""),
                suggestion=item.get("suggestion", ""),
                category=item.get("category", ""),
            ))

        return ValidationReport(
            issues=issues,
            score=data.get("score", 0.0),
            equation_coverage=data.get("equation_coverage", 0.0),
            hyperparam_coverage=data.get("hyperparam_coverage", 0.0),
            summary=data.get("summary", ""),
            passed=data.get("passed", False),
        )

    def _fallback_validate(self, prompt: str) -> dict:
        """Text-based fallback for validation."""
        result = self.provider.generate(
            prompt=prompt + "\n\nRespond with ONLY a JSON object.",
            system_prompt="You are a code reviewer. Respond only with valid JSON.",
            config=GenerationConfig(temperature=0.1, max_output_tokens=8192),
        )
        text = result.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

    def _default_prompt(self) -> str:
        return """Review the generated code files against the original paper.

For each file, check:
1. **Equation Fidelity**: Is every paper equation correctly implemented? Check tensor operations, reduction dimensions, normalization terms.
2. **Dimension Consistency**: Do tensor shapes match paper specifications? (e.g., d_model, d_k, d_v, num_heads)
3. **Hyperparameter Completeness**: Are ALL hyperparameters from the paper configurable (not hardcoded)?
4. **Loss Function Accuracy**: Does the loss match the paper's formulation exactly?
5. **Code Quality**: Proper imports, type hints, docstrings, no dead code.

Output a JSON object with:
- "score": 0-100 fidelity score
- "equation_coverage": 0-100 percentage of paper equations found in code
- "hyperparam_coverage": 0-100 percentage of paper hyperparameters that are configurable
- "summary": brief text summary
- "passed": true if score >= 80 and no critical issues
- "issues": array of objects with severity, file_path, line_hint, description, suggestion, category

Be thorough but fair. Score generously if the implementation is functionally correct even if style differs."""
