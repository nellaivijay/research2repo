"""
AgentOrchestrator — Master controller for the Research2Repo multi-agent pipeline.

Coordinates specialised agents through the full paper-to-repository workflow:

  1.  Parse paper            (PaperAnalyzer)
  2.  Planning               (DecomposedPlanner + optional SelfRefiner)
  3.  Per-file analysis      (FileAnalyzer + optional SelfRefiner)
  4.  Code generation        (CodeSynthesizer)
  5.  Test generation        (TestGenerator)
  6.  Validation + auto-fix  (CodeValidator)
  7.  Execution + auto-debug (ExecutionSandbox + AutoDebugger)
  8.  DevOps generation      (DevOpsGenerator)
  9.  Evaluation             (ReferenceEvaluator)
 10.  Save files

All heavy module imports are deferred to method bodies to avoid circular
imports and to keep import time low when only a subset of stages is used.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Optional

from providers import get_provider
from providers.base import BaseProvider


# ── Default configuration ────────────────────────────────────────────────

_DEFAULT_CONFIG: dict[str, Any] = {
    "enable_refine": False,
    "enable_execution": False,
    "enable_tests": True,
    "enable_evaluation": False,
    "enable_devops": True,
    "interactive": False,
    "max_debug_iterations": 3,
    "max_refine_iterations": 2,
    "max_fix_iterations": 2,
    "reference_dir": None,
    "verbose": False,
}


# ── Helpers ──────────────────────────────────────────────────────────────

def _merge_config(user_config: Optional[dict] = None) -> dict[str, Any]:
    """Merge caller-supplied config over the defaults."""
    cfg = dict(_DEFAULT_CONFIG)
    if user_config:
        cfg.update(user_config)
    return cfg


def _header(title: str, step: int, total: int = 10) -> None:
    """Print a clearly-visible stage header."""
    print(f"\n{'─' * 60}")
    print(f"  [{step}/{total}] {title}")
    print(f"{'─' * 60}")


def _elapsed(start: float) -> str:
    """Return human-readable elapsed time since *start*."""
    secs = time.time() - start
    if secs < 60:
        return f"{secs:.1f}s"
    mins = int(secs // 60)
    return f"{mins}m {secs - mins * 60:.1f}s"


# ── Orchestrator ─────────────────────────────────────────────────────────

class AgentOrchestrator:
    """Master orchestrator that drives the entire paper → repo pipeline.

    Instantiate with an optional provider and configuration dict, then
    call :meth:`run` with a PDF path and output directory.

    Args:
        provider: Shared LLM provider for all agents.  Auto-detected when
                  *None*.
        config: Optional dict overriding default pipeline behaviour.  Keys
                include ``enable_refine``, ``enable_execution``,
                ``enable_tests``, ``enable_evaluation``, ``interactive``,
                ``max_debug_iterations``, ``max_refine_iterations``,
                ``reference_dir``, etc.
    """

    def __init__(
        self,
        provider: Optional[BaseProvider] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> None:
        self._provider = provider or get_provider()
        self._config = _merge_config(config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        pdf_path: str,
        output_dir: str,
        paper_analysis: Any = None,
        document: Any = None,
        vision_context: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Execute the full multi-agent pipeline.

        Args:
            pdf_path: Path to the source research-paper PDF.
            output_dir: Directory where the generated repository is saved.
            paper_analysis: Pre-computed ``PaperAnalysis``.  When *None* the
                            paper is analysed from scratch.
            document: Uploaded document handle (Gemini) or extracted text.
                      Computed automatically when *None*.
            vision_context: Pre-extracted Mermaid diagrams.  Computed
                            automatically when *None*.

        Returns:
            A result dict with keys ``files``, ``plan``, ``analysis``,
            ``validation_report``, ``execution_result``,
            ``evaluation_score``, ``metadata``.
        """
        pipeline_start = time.time()
        os.makedirs(output_dir, exist_ok=True)

        cfg = self._config
        provider = self._provider
        timings: dict[str, str] = {}

        # Accumulator for final results
        result: dict[str, Any] = {
            "files": {},
            "plan": None,
            "analysis": None,
            "file_analyses": None,
            "validation_report": None,
            "execution_result": None,
            "evaluation_score": None,
            "metadata": {},
        }

        # ==============================================================
        # Stage 1 — Parse paper
        # ==============================================================
        t0 = time.time()
        _header("Parse Paper", 1)

        analysis, document, vision_context = self._stage_parse_paper(
            pdf_path=pdf_path,
            paper_analysis=paper_analysis,
            document=document,
            vision_context=vision_context,
            provider=provider,
        )
        result["analysis"] = analysis
        timings["parse"] = _elapsed(t0)
        print(f"  ✓ Paper: {analysis.title}  ({timings['parse']})")

        # ==============================================================
        # Stage 2 — Planning (4-stage decomposed)
        # ==============================================================
        t0 = time.time()
        _header("Planning", 2)

        plan = self._stage_plan(analysis, document, vision_context, provider)

        if cfg["enable_refine"]:
            plan = self._refine_output(
                plan, "plan", provider, cfg["max_refine_iterations"],
            )

        result["plan"] = plan
        timings["plan"] = _elapsed(t0)
        print(f"  ✓ Plan: {len(plan.files)} files, "
              f"{len(plan.requirements)} deps  ({timings['plan']})")

        # Interactive gate — show plan & wait for user
        if cfg["interactive"]:
            self._run_interactive(plan, analysis)

        # ==============================================================
        # Stage 3 — Per-file analysis
        # ==============================================================
        t0 = time.time()
        _header("Per-File Analysis", 3)

        file_analyses = self._stage_file_analysis(plan, analysis, provider)

        if cfg["enable_refine"]:
            file_analyses = self._refine_output(
                file_analyses, "file_analyses", provider,
                cfg["max_refine_iterations"],
            )

        result["file_analyses"] = file_analyses
        timings["file_analysis"] = _elapsed(t0)
        print(f"  ✓ Analysed {len(file_analyses)} files  "
              f"({timings['file_analysis']})")

        # ==============================================================
        # Stage 4 — Code generation
        # ==============================================================
        t0 = time.time()
        _header("Code Generation", 4)

        generated_files = self._stage_code_generation(
            analysis, plan, document, provider,
        )
        result["files"] = generated_files
        timings["codegen"] = _elapsed(t0)
        print(f"  ✓ Generated {len(generated_files)} files  "
              f"({timings['codegen']})")

        # ==============================================================
        # Stage 5 — Test generation
        # ==============================================================
        if cfg["enable_tests"]:
            t0 = time.time()
            _header("Test Generation", 5)

            test_files = self._stage_test_generation(
                generated_files, analysis, plan, provider,
            )
            generated_files.update(test_files)
            result["files"] = generated_files
            timings["tests"] = _elapsed(t0)
            print(f"  ✓ Generated {len(test_files)} test files  "
                  f"({timings['tests']})")
        else:
            _header("Test Generation (skipped)", 5)

        # ==============================================================
        # Stage 6 — Validation + auto-fix
        # ==============================================================
        t0 = time.time()
        _header("Validation & Auto-Fix", 6)

        generated_files, report = self._stage_validation(
            generated_files, analysis, plan, provider,
            max_fix_iterations=cfg["max_fix_iterations"],
        )
        result["files"] = generated_files
        result["validation_report"] = report
        timings["validation"] = _elapsed(t0)
        print(f"  ✓ Score: {report.score}/100  "
              f"Critical: {report.critical_count}  "
              f"({timings['validation']})")

        # ==============================================================
        # Stage 7 — Execution + auto-debug
        # ==============================================================
        if cfg["enable_execution"]:
            t0 = time.time()
            _header("Execution & Auto-Debug", 7)

            generated_files, exec_result = self._stage_execution(
                generated_files, output_dir, plan, analysis, provider,
                max_debug_iterations=cfg["max_debug_iterations"],
            )
            result["files"] = generated_files
            result["execution_result"] = exec_result
            timings["execution"] = _elapsed(t0)
            print(f"  ✓ Execution complete  ({timings['execution']})")
        else:
            _header("Execution & Auto-Debug (skipped)", 7)

        # ==============================================================
        # Stage 8 — DevOps generation
        # ==============================================================
        if cfg.get("enable_devops", True):
            t0 = time.time()
            _header("DevOps Generation", 8)

            devops_files = self._stage_devops(
                plan, analysis, generated_files, provider,
            )
            generated_files.update(devops_files)
            result["files"] = generated_files
            timings["devops"] = _elapsed(t0)
            print(f"  ✓ Generated {len(devops_files)} DevOps files  "
                  f"({timings['devops']})")
        else:
            _header("DevOps Generation (skipped)", 8)

        # ==============================================================
        # Stage 9 — Evaluation
        # ==============================================================
        if cfg["enable_evaluation"] and cfg.get("reference_dir"):
            t0 = time.time()
            _header("Evaluation", 9)

            eval_score = self._stage_evaluation(
                generated_files, cfg["reference_dir"], provider,
            )
            result["evaluation_score"] = eval_score
            timings["evaluation"] = _elapsed(t0)
            print(f"  ✓ Evaluation score: {eval_score}  "
                  f"({timings['evaluation']})")
        else:
            _header("Evaluation (skipped)", 9)

        # ==============================================================
        # Stage 10 — Save files
        # ==============================================================
        t0 = time.time()
        _header("Save Repository", 10)

        files_written = self._stage_save(generated_files, output_dir)
        timings["save"] = _elapsed(t0)
        print(f"  ✓ Wrote {files_written} files to {output_dir}  "
              f"({timings['save']})")

        # ------ Metadata & summary ------------------------------------
        total_elapsed = time.time() - pipeline_start
        result["metadata"] = {
            "pdf_path": pdf_path,
            "output_dir": os.path.abspath(output_dir),
            "provider": self._provider.__class__.__name__,
            "model": self._provider.model_name,
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(total_elapsed, 1),
            "files_generated": files_written,
            "paper_title": analysis.title,
            "timings": timings,
            "config": {k: v for k, v in cfg.items() if not callable(v)},
        }

        # Persist metadata alongside the generated repo
        meta_path = os.path.join(output_dir, ".r2r_metadata.json")
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(result["metadata"], fh, indent=2)

        self._print_summary(result, total_elapsed)
        return result

    # ------------------------------------------------------------------
    # Interactive gate
    # ------------------------------------------------------------------

    def _run_interactive(self, plan: Any, analysis: Any) -> None:
        """Pause after planning so the user can inspect the architecture.

        Displays the directory tree and file list, then waits for the user
        to press Enter (or ``q`` to abort).
        """
        print(f"\n{'=' * 60}")
        print("  INTERACTIVE MODE — Architecture Review")
        print(f"{'=' * 60}")
        print(f"\n  Paper : {analysis.title}")
        print(f"  Repo  : {plan.repo_name}")
        print(f"  Files : {len(plan.files)}")
        print(f"  Deps  : {', '.join(plan.requirements[:10])}")

        if plan.directory_tree:
            print(f"\n{plan.directory_tree}")

        print("\n  Files to generate:")
        for i, f in enumerate(plan.files, 1):
            print(f"    {i:>3}. {f.path}  — {f.description[:60]}")

        print()
        user_input = input("Press Enter to continue or 'q' to abort... ")
        if user_input.strip().lower() == "q":
            print("Aborted by user.")
            raise SystemExit(0)

    # ------------------------------------------------------------------
    # Pipeline stages (each lazily imports its module)
    # ------------------------------------------------------------------

    @staticmethod
    def _stage_parse_paper(
        pdf_path: str,
        paper_analysis: Any,
        document: Any,
        vision_context: Optional[list[str]],
        provider: BaseProvider,
    ) -> tuple[Any, Any, list[str]]:
        """Stage 1 — Analyse the paper (or reuse pre-computed results)."""
        from core.analyzer import PaperAnalyzer  # lazy

        if paper_analysis is not None:
            # Caller supplied a pre-computed analysis
            return paper_analysis, document, vision_context or []

        analyzer = PaperAnalyzer(provider=provider)

        # Upload / extract text
        if document is None:
            document = analyzer.upload_document(pdf_path)

        # Diagram extraction
        if vision_context is None:
            vision_context = analyzer.extract_diagrams_to_mermaid(pdf_path)

        analysis = analyzer.analyze(document, vision_context)
        return analysis, document, vision_context

    @staticmethod
    def _stage_plan(
        analysis: Any,
        document: Any,
        vision_context: list[str],
        provider: BaseProvider,
    ) -> Any:
        """Stage 2 — Decomposed planning.

        Tries the ``DecomposedPlanner`` first; falls back to the
        ``SystemArchitect`` if the planner module is not yet available.
        """
        try:
            from core.planner import DecomposedPlanner  # lazy

            planner = DecomposedPlanner(provider=provider)
            planning_result = planner.plan(
                analysis=analysis,
                document=document,
                vision_context=vision_context,
            )
            # DecomposedPlanner.plan() returns a PlanningResult which wraps
            # an ArchitecturePlan.  Extract it for downstream use.
            plan = getattr(planning_result, "plan", planning_result)
            return plan
        except ImportError:
            # Fallback: use the existing SystemArchitect
            print("  [Orchestrator] DecomposedPlanner not available, "
                  "falling back to SystemArchitect.")
            from core.architect import SystemArchitect  # lazy

            architect = SystemArchitect(provider=provider)
            return architect.design_system(
                analysis=analysis,
                document=document,
                vision_context=vision_context,
            )

    @staticmethod
    def _stage_file_analysis(
        plan: Any,
        analysis: Any,
        provider: BaseProvider,
    ) -> dict[str, Any]:
        """Stage 3 — Per-file analysis."""
        from core.file_analyzer import FileAnalyzer  # lazy

        fa = FileAnalyzer(provider=provider)
        return fa.analyze_all(plan=plan, analysis=analysis)

    @staticmethod
    def _stage_code_generation(
        analysis: Any,
        plan: Any,
        document: Any,
        provider: BaseProvider,
    ) -> dict[str, str]:
        """Stage 4 — Code synthesis."""
        from core.coder import CodeSynthesizer  # lazy

        coder = CodeSynthesizer(provider=provider)
        return coder.generate_codebase(
            analysis=analysis,
            plan=plan,
            document=document,
        )

    @staticmethod
    def _stage_test_generation(
        generated_files: dict[str, str],
        analysis: Any,
        plan: Any,
        provider: BaseProvider,
    ) -> dict[str, str]:
        """Stage 5 — Test generation."""
        from advanced.test_generator import TestGenerator  # lazy

        tg = TestGenerator(provider=provider)
        return tg.generate_tests(
            generated_files=generated_files,
            analysis=analysis,
            plan=plan,
        )

    @staticmethod
    def _stage_validation(
        generated_files: dict[str, str],
        analysis: Any,
        plan: Any,
        provider: BaseProvider,
        max_fix_iterations: int = 2,
    ) -> tuple[dict[str, str], Any]:
        """Stage 6 — Validation with iterative auto-fix."""
        from core.validator import CodeValidator  # lazy

        validator = CodeValidator(provider=provider)
        report = validator.validate(generated_files, analysis, plan)

        iteration = 0
        while report.critical_count > 0 and iteration < max_fix_iterations:
            iteration += 1
            print(f"  [Orchestrator] Auto-fix iteration "
                  f"{iteration}/{max_fix_iterations} …")
            generated_files = validator.fix_issues(
                generated_files, report, analysis,
            )
            report = validator.validate(generated_files, analysis, plan)
            print(f"  [Orchestrator] Score after fix: {report.score}/100  "
                  f"Critical: {report.critical_count}")

        return generated_files, report

    @staticmethod
    def _stage_execution(
        generated_files: dict[str, str],
        output_dir: str,
        plan: Any,
        analysis: Any,
        provider: BaseProvider,
        max_debug_iterations: int = 3,
    ) -> tuple[dict[str, str], Any]:
        """Stage 7 — Sandbox execution with auto-debug loop."""
        try:
            from advanced.executor import ExecutionSandbox  # lazy
            from advanced.debugger import AutoDebugger      # lazy
        except ImportError:
            print("  [Orchestrator] ExecutionSandbox / AutoDebugger not "
                  "available — skipping execution stage.")
            return generated_files, None

        sandbox = ExecutionSandbox()
        debugger = AutoDebugger(provider=provider)

        exec_result = sandbox.execute(
            files=generated_files,
            output_dir=output_dir,
            entrypoint=getattr(plan, "training_entrypoint", "train.py"),
        )

        iteration = 0
        while not getattr(exec_result, "success", True) and iteration < max_debug_iterations:
            iteration += 1
            print(f"  [Orchestrator] Debug iteration "
                  f"{iteration}/{max_debug_iterations} …")
            fixed_files, diagnosis = debugger.debug(
                files=generated_files,
                error=exec_result,
                analysis=analysis,
            )
            generated_files = fixed_files
            exec_result = sandbox.execute(
                files=generated_files,
                output_dir=output_dir,
                entrypoint=getattr(plan, "training_entrypoint", "train.py"),
            )
            print(f"  [Orchestrator] Execution success: "
                  f"{getattr(exec_result, 'success', 'unknown')}")

        return generated_files, exec_result

    @staticmethod
    def _stage_devops(
        plan: Any,
        analysis: Any,
        generated_files: dict[str, str],
        provider: BaseProvider,
    ) -> dict[str, str]:
        """Stage 8 — Generate DevOps artefacts."""
        try:
            from advanced.devops import DevOpsGenerator  # lazy

            dg = DevOpsGenerator(provider=provider)
            return dg.generate_all(
                plan=plan,
                analysis=analysis,
                generated_files=generated_files,
            )
        except ImportError:
            print("  [Orchestrator] DevOpsGenerator not available — "
                  "skipping DevOps stage.")
            return {}

    @staticmethod
    def _stage_evaluation(
        generated_files: dict[str, str],
        reference_dir: str,
        provider: BaseProvider,
    ) -> Any:
        """Stage 9 — Evaluate against a reference implementation."""
        try:
            from advanced.evaluator import ReferenceEvaluator  # lazy
        except ImportError:
            print("  [Orchestrator] ReferenceEvaluator not available — "
                  "skipping evaluation stage.")
            return None

        evaluator = ReferenceEvaluator(provider=provider)

        if reference_dir and os.path.isdir(reference_dir):
            return evaluator.evaluate_with_reference(
                generated_files=generated_files,
                reference_dir=reference_dir,
            )
        return evaluator.evaluate_without_reference(
            generated_files=generated_files,
        )

    @staticmethod
    def _stage_save(
        generated_files: dict[str, str],
        output_dir: str,
    ) -> int:
        """Stage 10 — Write all generated files to disk."""
        files_written = 0
        for filepath, content in generated_files.items():
            full_path = os.path.join(output_dir, filepath)
            os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as fh:
                fh.write(content)
            files_written += 1
        return files_written

    # ------------------------------------------------------------------
    # Self-refine helper
    # ------------------------------------------------------------------

    @staticmethod
    def _refine_output(
        artifact: Any,
        artifact_label: str,
        provider: BaseProvider,
        max_iterations: int = 2,
    ) -> Any:
        """Optionally pass an artifact through :class:`SelfRefiner`.

        If the ``SelfRefiner`` module is not available the artifact is
        returned unchanged.
        """
        try:
            from core.refiner import SelfRefiner  # lazy
        except ImportError:
            print(f"  [Orchestrator] SelfRefiner not available — "
                  f"skipping refinement for {artifact_label}.")
            return artifact

        refiner = SelfRefiner(provider=provider)
        for i in range(1, max_iterations + 1):
            print(f"  [Orchestrator] Refinement pass {i}/{max_iterations} "
                  f"for {artifact_label} …")
            refinement = refiner.refine(artifact)
            # SelfRefiner.refine() returns a RefinementResult; extract the
            # refined payload via a conventional attribute name.
            refined = getattr(refinement, "refined", None)
            if refined is not None:
                artifact = refined
            else:
                # If the refiner doesn't expose .refined, treat the whole
                # result as the new artifact.
                artifact = refinement
        return artifact

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    @staticmethod
    def _print_summary(result: dict[str, Any], elapsed: float) -> None:
        """Print a final pipeline summary."""
        meta = result["metadata"]
        print(f"\n{'=' * 60}")
        print("  PIPELINE COMPLETE")
        print(f"{'=' * 60}")
        print(f"  Paper    : {meta.get('paper_title', 'N/A')}")
        print(f"  Provider : {meta.get('provider', 'N/A')} / "
              f"{meta.get('model', 'N/A')}")
        print(f"  Files    : {meta.get('files_generated', 0)}")
        print(f"  Output   : {meta.get('output_dir', 'N/A')}")
        print(f"  Time     : {elapsed:.1f}s")

        if result.get("validation_report"):
            rpt = result["validation_report"]
            print(f"  Score    : {rpt.score}/100  "
                  f"(eq {rpt.equation_coverage}% / "
                  f"hp {rpt.hyperparam_coverage}%)")

        if result.get("evaluation_score") is not None:
            print(f"  Eval     : {result['evaluation_score']}")

        timings = meta.get("timings", {})
        if timings:
            print(f"\n  Stage timings:")
            for stage, dur in timings.items():
                print(f"    {stage:<16} {dur}")

        print(f"{'=' * 60}\n")
