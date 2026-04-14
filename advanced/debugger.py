"""
AutoDebugger — LLM-assisted auto-debugging that analyses execution errors,
generates targeted fixes, and iterates until the code runs successfully
or a maximum iteration limit is reached.

Workflow per iteration:
  1. Analyse the error (traceback + relevant source) with the LLM.
  2. Generate file-level fixes (DebugFix objects).
  3. Apply fixes to the in-memory file dict.
  4. Re-execute via ExecutionSandbox.
  5. If resolved → return; else → loop.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from providers.base import BaseProvider, GenerationConfig, ModelCapability
from providers import get_provider
from advanced.executor import ExecutionResult, ExecutionSandbox


@dataclass
class DebugFix:
    """A single file-level fix produced by the debugger."""
    file_path: str = ""
    original_content: str = ""
    fixed_content: str = ""
    error_description: str = ""
    fix_description: str = ""


@dataclass
class DebugReport:
    """Report for a single debug iteration."""
    iteration: int = 0
    error_message: str = ""
    error_type: str = ""
    fixes: list[DebugFix] = field(default_factory=list)
    resolved: bool = False


class AutoDebugger:
    """
    Iteratively debugs a generated repository by feeding execution
    errors to an LLM and applying the suggested fixes.

    Args:
        provider: LLM provider for error analysis. Auto-detected if
            ``None``.
        max_iterations: Maximum number of fix-and-retry cycles.
    """

    PROMPT_FILE = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "prompts", "auto_debug.txt"
    )

    def __init__(
        self,
        provider: Optional[BaseProvider] = None,
        max_iterations: int = 5,
    ) -> None:
        self.provider = provider or get_provider(
            required_capability=ModelCapability.CODE_GENERATION
        )
        self.max_iterations = max_iterations
        self._sandbox = ExecutionSandbox(use_docker=False, timeout=120)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def debug(
        self,
        repo_dir: str,
        execution_result: ExecutionResult,
        generated_files: dict[str, str],
    ) -> tuple[dict[str, str], list[DebugReport]]:
        """
        Iteratively fix execution errors in *generated_files*.

        Args:
            repo_dir: Path to the repository on disk.
            execution_result: Initial (failed) execution result.
            generated_files: Mapping of ``relative_path -> content``
                for all generated source files.

        Returns:
            A tuple of ``(updated_files, debug_reports)`` where
            *updated_files* contains the final (possibly fixed) file
            contents, and *debug_reports* is the log of every iteration.
        """
        files = dict(generated_files)
        reports: list[DebugReport] = []
        current_result = execution_result

        for iteration in range(1, self.max_iterations + 1):
            if current_result.success:
                print(f"[AutoDebugger] Code runs successfully — no debugging needed.")
                break

            error_msg = current_result.stderr or "Unknown error"
            error_type = current_result.error_type or "UnknownError"

            print(f"[AutoDebugger] Iteration {iteration}/{self.max_iterations}: "
                  f"analyzing {error_type}...")

            # 1. Generate fixes
            fixes = self._analyze_error(error_msg, error_type, files)

            if not fixes:
                print(f"[AutoDebugger] No fixes suggested for {error_type}. Stopping.")
                reports.append(DebugReport(
                    iteration=iteration,
                    error_message=error_msg[:2000],
                    error_type=error_type,
                    fixes=[],
                    resolved=False,
                ))
                break

            # 2. Apply fixes and track changes
            old_files = files
            files = self._apply_fixes(files, fixes)

            # 3. Write only modified files to disk
            for rel_path, content in files.items():
                if rel_path not in old_files or old_files[rel_path] != content:
                    abs_path = os.path.join(repo_dir, rel_path)
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with open(abs_path, "w") as f:
                        f.write(content)

            # 4. Re-execute
            print(f"[AutoDebugger] Re-executing after applying {len(fixes)} fix(es)...")
            current_result = self._sandbox.execute(repo_dir)

            resolved = current_result.success
            reports.append(DebugReport(
                iteration=iteration,
                error_message=error_msg[:2000],
                error_type=error_type,
                fixes=fixes,
                resolved=resolved,
            ))

            if resolved:
                print(f"[AutoDebugger] Resolved after {iteration} iteration(s)!")
                break
        else:
            print(f"[AutoDebugger] Max iterations ({self.max_iterations}) reached. "
                  f"Some errors may remain.")

        return files, reports

    # ------------------------------------------------------------------
    # Error analysis
    # ------------------------------------------------------------------

    def _analyze_error(
        self,
        error_message: str,
        error_type: str,
        relevant_files: dict[str, str],
    ) -> list[DebugFix]:
        """Send error context + source files to the LLM and parse fixes.

        Args:
            error_message: Full stderr / traceback.
            error_type: Classified error category (e.g. ``"ImportError"``).
            relevant_files: Source files relevant to the error.

        Returns:
            List of :class:`DebugFix` objects suggested by the LLM.
        """
        # Narrow the file set to those actually referenced in the traceback
        focused_files = self._find_relevant_files(error_message, relevant_files)
        if not focused_files:
            focused_files = relevant_files  # fallback: send everything

        # Build prompt
        prompt = self._build_debug_prompt(error_message, error_type, focused_files)

        schema = {
            "type": "object",
            "properties": {
                "fixes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"},
                            "fixed_content": {"type": "string"},
                            "error_description": {"type": "string"},
                            "fix_description": {"type": "string"},
                        },
                        "required": ["file_path", "fixed_content"],
                    },
                },
            },
            "required": ["fixes"],
        }

        try:
            data = self.provider.generate_structured(
                prompt=prompt,
                schema=schema,
                system_prompt=(
                    "You are an expert Python debugger. Analyse the error and "
                    "produce minimal, targeted fixes. Return ONLY the corrected "
                    "full file contents — do not omit any code."
                ),
                config=GenerationConfig(temperature=0.1, max_output_tokens=16384),
            )
        except Exception as exc:
            print(f"[AutoDebugger] Structured generation failed ({exc}); trying text fallback...")
            data = self._text_fallback(prompt)

        return self._parse_fixes(data, relevant_files)

    def _find_relevant_files(
        self,
        error_message: str,
        all_files: dict[str, str],
    ) -> dict[str, str]:
        """Identify files mentioned in the traceback.

        Parses ``File "..."`` references from the traceback and returns
        only the matching subset of *all_files*.
        """
        # Extract file names from traceback lines like:
        #   File "/app/model.py", line 42, in forward
        mentioned = set()
        for match in re.finditer(r'File "([^"]+)"', error_message):
            path = match.group(1)
            basename = os.path.basename(path)
            mentioned.add(basename)
            mentioned.add(path)

        # Also look for module-style references like "model.py" or "utils/helpers.py"
        for match in re.finditer(r"(\w[\w/]*\.py)", error_message):
            mentioned.add(match.group(1))
            mentioned.add(os.path.basename(match.group(1)))

        relevant: dict[str, str] = {}
        for file_path, content in all_files.items():
            basename = os.path.basename(file_path)
            if basename in mentioned or file_path in mentioned:
                relevant[file_path] = content

        return relevant

    def _apply_fixes(
        self,
        files: dict[str, str],
        fixes: list[DebugFix],
    ) -> dict[str, str]:
        """Apply each :class:`DebugFix` to the files dictionary.

        Only overwrites a file if the fix provides non-empty
        ``fixed_content``.
        """
        updated = dict(files)
        for fix in fixes:
            if fix.file_path and fix.fixed_content:
                if fix.file_path in updated:
                    print(f"[AutoDebugger]   Fixing {fix.file_path}: {fix.fix_description}")
                    updated[fix.file_path] = fix.fixed_content
                else:
                    # The LLM may suggest creating a new file
                    print(f"[AutoDebugger]   Creating {fix.file_path}: {fix.fix_description}")
                    updated[fix.file_path] = fix.fixed_content
        return updated

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def _build_debug_prompt(
        self,
        error_message: str,
        error_type: str,
        files: dict[str, str],
    ) -> str:
        """Build the debug analysis prompt."""
        # Try loading from template
        prompt_template = self._load_prompt(self.PROMPT_FILE)

        files_section = ""
        for path, content in files.items():
            # Truncate extremely long files
            display = content if len(content) < 8000 else content[:8000] + "\n# ... (truncated)"
            files_section += f"\n### {path}\n```python\n{display}\n```\n"

        if prompt_template:
            prompt = prompt_template
            prompt = prompt.replace("{{error_type}}", error_type)
            prompt = prompt.replace("{{error_message}}", error_message[:4000])
            prompt = prompt.replace("{{source_files}}", files_section)
        else:
            prompt = self._default_debug_prompt(error_message, error_type, files_section)

        return prompt

    def _load_prompt(self, path: str) -> str:
        """Load a prompt template file, or return empty string."""
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
        return ""

    def _default_debug_prompt(
        self,
        error_message: str,
        error_type: str,
        files_section: str,
    ) -> str:
        return f"""The following Python code failed during execution.

## Error Type
{error_type}

## Full Error / Traceback
```
{error_message[:4000]}
```

## Source Files
{files_section}

## Instructions
1. Identify the root cause of the error.
2. For each file that needs to be fixed, provide the COMPLETE corrected
   file content (do NOT omit any unchanged code).
3. Provide a brief description of what was wrong and what you fixed.

Return a JSON object with a "fixes" array. Each element must have:
  - "file_path": relative path of the file
  - "fixed_content": the full corrected file content
  - "error_description": what went wrong
  - "fix_description": what you changed
"""

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_fixes(
        self,
        data: dict,
        all_files: dict[str, str],
    ) -> list[DebugFix]:
        """Parse the LLM response into :class:`DebugFix` objects."""
        fixes: list[DebugFix] = []
        for item in data.get("fixes", []):
            if not isinstance(item, dict):
                continue
            file_path = item.get("file_path", "")
            fixed_content = item.get("fixed_content", "")
            if not file_path or not fixed_content:
                continue

            original = all_files.get(file_path, "")

            fixes.append(DebugFix(
                file_path=file_path,
                original_content=original,
                fixed_content=fixed_content,
                error_description=item.get("error_description", ""),
                fix_description=item.get("fix_description", ""),
            ))

        return fixes

    def _text_fallback(self, prompt: str) -> dict:
        """Fallback: generate plain text and attempt to parse as JSON."""
        result = self.provider.generate(
            prompt=prompt + "\n\nRespond with ONLY a JSON object.",
            system_prompt="You are a Python debugger. Respond only with valid JSON.",
            config=GenerationConfig(temperature=0.1, max_output_tokens=16384),
        )
        text = result.text.strip()
        # Strip markdown code fences
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return {"fixes": []}
