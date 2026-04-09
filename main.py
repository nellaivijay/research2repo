"""
Research2Repo: Multi-Model Agentic Pipeline
============================================
Converts ML research papers into production-ready GitHub repositories.

Supports: Google Gemini, OpenAI GPT-4o/o3, Anthropic Claude, Ollama (local).

Pipeline Stages:
  1. Download & Ingest PDF
  2. Analyze (long-context + vision extraction)
  3. Extract Equations (dedicated equation pipeline)
  4. Architect (repository structure design)
  5. Generate Config (structured YAML from hyperparameters)
  6. Synthesize Code (file-by-file with rolling context)
  7. Generate Tests (pytest suite)
  8. Validate (self-review against paper)
  9. Auto-Fix (repair critical issues)
  10. Save Repository

Usage:
  python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --output_dir ./generated_repo
  python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --provider openai --model gpt-4o
  python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --provider ollama --model deepseek-coder-v2:latest
"""

import argparse
import os
import sys
import time
from datetime import datetime
from typing import Optional

import requests

from providers import ProviderRegistry, get_provider
from providers.base import ModelCapability, GenerationConfig
from core.analyzer import PaperAnalyzer
from core.architect import SystemArchitect
from core.coder import CodeSynthesizer
from core.validator import CodeValidator
from advanced.equation_extractor import EquationExtractor
from advanced.config_generator import ConfigGenerator
from advanced.test_generator import TestGenerator
from advanced.cache import PipelineCache


def download_pdf(url: str, save_path: str, timeout: int = 120, max_size_mb: int = 100) -> str:
    """
    Download a research paper PDF with validation.

    Args:
        url: URL of the PDF (arXiv, OpenReview, etc.).
        save_path: Local path to save the file.
        timeout: Request timeout in seconds.
        max_size_mb: Maximum file size to download.

    Returns:
        Path to the saved PDF.
    """
    print(f"[1/10] Downloading PDF from {url}...")

    headers = {
        "User-Agent": "Research2Repo/2.0 (Academic Tool; +https://github.com/nellaivijay/Research2Repo)"
    }
    response = requests.get(url, stream=True, timeout=timeout, headers=headers)
    response.raise_for_status()

    # Validate content type
    content_type = response.headers.get("content-type", "")
    if "pdf" not in content_type and not url.endswith(".pdf"):
        print(f"  Warning: Content-Type is '{content_type}', expected PDF.")

    # Download with size check
    total_size = 0
    max_bytes = max_size_mb * 1024 * 1024
    with open(save_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            total_size += len(chunk)
            if total_size > max_bytes:
                raise ValueError(f"PDF exceeds {max_size_mb}MB limit.")
            f.write(chunk)

    size_mb = total_size / (1024 * 1024)
    print(f"  Downloaded: {size_mb:.1f} MB -> {save_path}")
    return save_path


def print_provider_info(provider_name: str, model_name: str) -> None:
    """Print provider and model information."""
    print(f"\n{'='*60}")
    print(f"  Research2Repo v2.0 — Multi-Model Pipeline")
    print(f"  Provider: {provider_name}")
    print(f"  Model: {model_name}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")


def main(
    pdf_url: str,
    output_dir: str,
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    vision_provider_name: Optional[str] = None,
    vision_model_name: Optional[str] = None,
    skip_validation: bool = False,
    skip_tests: bool = False,
    skip_equations: bool = False,
    max_fix_iterations: int = 2,
    use_cache: bool = True,
    cache_dir: Optional[str] = None,
    verbose: bool = False,
) -> None:
    """
    Run the full Research2Repo pipeline.

    Args:
        pdf_url: URL of the research paper PDF.
        output_dir: Directory to generate the repository in.
        provider_name: LLM provider ('gemini', 'openai', 'anthropic', 'ollama').
        model_name: Specific model to use (provider-dependent).
        vision_provider_name: Provider for diagram extraction (defaults to primary).
        vision_model_name: Model for vision tasks.
        skip_validation: Skip the validation pass.
        skip_tests: Skip test generation.
        skip_equations: Skip dedicated equation extraction.
        max_fix_iterations: Max auto-fix attempts for critical issues.
        use_cache: Enable pipeline caching.
        cache_dir: Custom cache directory.
        verbose: Verbose output.
    """

    start_time = time.time()
    os.makedirs(output_dir, exist_ok=True)
    temp_pdf_path = os.path.join(output_dir, "source_paper.pdf")

    # --- Initialize providers ---
    primary_provider = get_provider(
        provider_name=provider_name,
        model_name=model_name,
    )
    actual_provider = provider_name or primary_provider.__class__.__name__.replace("Provider", "").lower()
    actual_model = primary_provider.model_name
    print_provider_info(actual_provider, actual_model)

    # Vision provider (may differ from primary)
    vision_provider = None
    if vision_provider_name:
        vision_provider = get_provider(
            provider_name=vision_provider_name,
            model_name=vision_model_name,
        )
    elif primary_provider.supports(ModelCapability.VISION):
        vision_provider = primary_provider

    # Cache
    cache = PipelineCache(cache_dir) if use_cache else None

    try:
        # ============================================================
        # STAGE 1: Download PDF
        # ============================================================
        download_pdf(pdf_url, temp_pdf_path)

        # Check cache
        if cache and cache.has_generated_files(temp_pdf_path):
            cached_meta = cache.load_metadata(temp_pdf_path)
            if cached_meta:
                print(f"\n[Cache] Found cached run from {cached_meta.get('timestamp', 'unknown')}")
                print(f"[Cache] Provider: {cached_meta.get('provider', 'unknown')}")
                print("[Cache] To force re-run, use --no-cache\n")

        # ============================================================
        # STAGE 2: Analyze Paper
        # ============================================================
        print(f"\n[2/10] Analyzing paper (long-context + multimodal)...")
        analyzer = PaperAnalyzer(
            provider=primary_provider,
            vision_provider=vision_provider,
        )

        # Upload/extract document
        uploaded_doc = analyzer.upload_document(temp_pdf_path)

        # Extract diagrams via vision
        diagrams = analyzer.extract_diagrams_to_mermaid(temp_pdf_path)

        # Run structured analysis
        if cache and cache.has_analysis(temp_pdf_path):
            analysis = cache.load_analysis(temp_pdf_path)
        else:
            analysis = analyzer.analyze(uploaded_doc, diagrams)
            if cache:
                cache.save_analysis(temp_pdf_path, analysis)

        print(f"  Paper: {analysis.title}")
        print(f"  Authors: {', '.join(analysis.authors[:5])}")
        print(f"  Equations: {len(analysis.equations)} | Hyperparams: {len(analysis.hyperparameters)}")
        print(f"  Diagrams: {len(diagrams)} | Sections: {len(analysis.sections)}")

        # ============================================================
        # STAGE 3: Extract Equations (Advanced)
        # ============================================================
        if not skip_equations:
            print(f"\n[3/10] Running dedicated equation extraction...")
            eq_extractor = EquationExtractor(provider=vision_provider or primary_provider)
            paper_text = analysis.full_text or (uploaded_doc if isinstance(uploaded_doc, str) else "")
            extracted_eqs = eq_extractor.extract(paper_text)

            # Merge with analysis equations
            existing_latex = set(analysis.equations)
            for eq in extracted_eqs:
                if eq.latex and eq.latex not in existing_latex:
                    analysis.equations.append(eq.latex)
                    existing_latex.add(eq.latex)
            print(f"  Total equations after merge: {len(analysis.equations)}")
        else:
            print(f"\n[3/10] Skipping equation extraction (--skip-equations)")

        # ============================================================
        # STAGE 4: Architect Repository
        # ============================================================
        print(f"\n[4/10] Designing repository architecture...")
        if cache and cache.has_architecture(temp_pdf_path):
            plan = cache.load_architecture(temp_pdf_path)
        else:
            architect = SystemArchitect(provider=primary_provider)
            plan = architect.design_system(
                analysis=analysis,
                document=uploaded_doc,
                vision_context=diagrams,
            )
            if cache:
                cache.save_architecture(temp_pdf_path, plan)

        print(f"  Repo: {plan.repo_name}")
        print(f"  Files: {len(plan.files)} | Dependencies: {len(plan.requirements)}")
        if verbose:
            print(f"\n{plan.directory_tree}")

        # ============================================================
        # STAGE 5: Generate Config
        # ============================================================
        print(f"\n[5/10] Generating config.yaml from hyperparameters...")
        config_gen = ConfigGenerator(provider=primary_provider)
        config_content = config_gen.generate(analysis)

        # ============================================================
        # STAGE 6: Synthesize Code
        # ============================================================
        print(f"\n[6/10] Synthesizing code ({len(plan.files)} files)...")
        if cache and cache.has_generated_files(temp_pdf_path):
            generated_files = cache.load_generated_files(temp_pdf_path)
        else:
            coder = CodeSynthesizer(provider=primary_provider)
            generated_files = coder.generate_codebase(
                analysis=analysis,
                plan=plan,
                document=uploaded_doc,
            )
            if cache:
                cache.save_generated_files(temp_pdf_path, generated_files)

        # Inject the generated config
        generated_files["config.yaml"] = config_content

        # Write requirements.txt
        generated_files["requirements.txt"] = "\n".join(plan.requirements) + "\n"

        # ============================================================
        # STAGE 7: Generate Tests
        # ============================================================
        if not skip_tests:
            print(f"\n[7/10] Generating test suite...")
            test_gen = TestGenerator(provider=primary_provider)
            test_files = test_gen.generate_tests(generated_files, analysis, plan)
            generated_files.update(test_files)
            print(f"  Generated {len(test_files)} test files")
        else:
            print(f"\n[7/10] Skipping test generation (--skip-tests)")

        # ============================================================
        # STAGE 8: Validate
        # ============================================================
        if not skip_validation:
            print(f"\n[8/10] Validating code against paper...")
            validator = CodeValidator(provider=primary_provider)
            report = validator.validate(generated_files, analysis, plan)

            print(f"  Score: {report.score}/100")
            print(f"  Equation Coverage: {report.equation_coverage}%")
            print(f"  Hyperparam Coverage: {report.hyperparam_coverage}%")
            print(f"  Critical Issues: {report.critical_count}")
            print(f"  Warnings: {report.warning_count}")

            if verbose and report.issues:
                print("\n  Issues:")
                for issue in report.issues[:10]:
                    print(f"    [{issue.severity}] {issue.file_path}: {issue.description}")

            # ============================================================
            # STAGE 9: Auto-Fix Critical Issues
            # ============================================================
            iteration = 0
            while report.critical_count > 0 and iteration < max_fix_iterations:
                iteration += 1
                print(f"\n[9/10] Auto-fix iteration {iteration}/{max_fix_iterations}...")
                generated_files = validator.fix_issues(generated_files, report, analysis)

                # Re-validate
                report = validator.validate(generated_files, analysis, plan)
                print(f"  Score after fix: {report.score}/100 | Critical: {report.critical_count}")

            if report.passed:
                print(f"\n  Validation PASSED (score: {report.score}/100)")
            else:
                print(f"\n  Validation completed with score {report.score}/100")
                if report.critical_count > 0:
                    print(f"  Warning: {report.critical_count} critical issue(s) remain.")

            if cache:
                cache.save_validation(temp_pdf_path, report)
        else:
            print(f"\n[8/10] Skipping validation (--skip-validation)")
            print(f"[9/10] Skipping auto-fix (validation skipped)")

        # ============================================================
        # STAGE 10: Save Repository
        # ============================================================
        print(f"\n[10/10] Writing repository to {output_dir}...")
        files_written = 0
        for filepath, content in generated_files.items():
            full_path = os.path.join(output_dir, filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
            files_written += 1
            if verbose:
                print(f"  -> {filepath}")

        # Save pipeline metadata
        elapsed = time.time() - start_time
        metadata = {
            "pdf_url": pdf_url,
            "provider": actual_provider,
            "model": actual_model,
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "files_generated": files_written,
            "paper_title": analysis.title,
            "equations_found": len(analysis.equations),
            "hyperparams_found": len(analysis.hyperparameters),
        }
        if cache:
            cache.save_metadata(temp_pdf_path, metadata)

        # Save metadata to output dir too
        import json
        with open(os.path.join(output_dir, ".r2r_metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

        # ============================================================
        # Summary
        # ============================================================
        print(f"\n{'='*60}")
        print(f"  PIPELINE COMPLETE")
        print(f"  Paper: {analysis.title}")
        print(f"  Provider: {actual_provider} / {actual_model}")
        print(f"  Files Generated: {files_written}")
        print(f"  Output: {os.path.abspath(output_dir)}")
        print(f"  Time: {elapsed:.1f}s")
        print(f"{'='*60}\n")

    finally:
        # Cleanup temp PDF (keep it if caching is enabled)
        if not use_cache and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)


def list_providers_cmd() -> None:
    """List available providers and models."""
    print("\nAvailable Providers:")
    print("-" * 60)

    available = ProviderRegistry.detect_available()
    all_providers = ProviderRegistry.list_providers()

    for name in all_providers:
        status = "READY" if name in available else "NOT CONFIGURED"
        print(f"\n  {name.upper()} [{status}]")

        if name in available:
            try:
                provider = ProviderRegistry.create(name)
                for model in provider.available_models():
                    caps = ", ".join(c.name for c in model.capabilities)
                    cost = f"${model.cost_per_1k_input}/{model.cost_per_1k_output} per 1K tok"
                    if model.cost_per_1k_input == 0:
                        cost = "FREE (local)"
                    ctx = f"{model.max_context_tokens:,} ctx"
                    default = " (default)" if model.name == provider.model_name else ""
                    print(f"    - {model.name}{default}")
                    print(f"      {ctx} | {cost}")
                    print(f"      Capabilities: {caps}")
            except Exception as e:
                print(f"    Error listing models: {e}")
        else:
            env_keys = {
                "gemini": "GEMINI_API_KEY",
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "ollama": "(start Ollama server)",
            }
            print(f"    Set {env_keys.get(name, 'API key')} to enable.")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Research2Repo: Convert ML papers to GitHub repositories.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect provider (uses first available)
  python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf"

  # Use specific provider and model
  python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --provider openai --model gpt-4o

  # Use Gemini for analysis, Claude for coding
  python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --provider gemini --vision-provider anthropic

  # Use local Ollama model
  python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --provider ollama --model deepseek-coder-v2:latest

  # Fast run (skip validation and tests)
  python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --skip-validation --skip-tests

  # List available providers
  python main.py --list-providers
        """,
    )

    # Core arguments
    parser.add_argument("--pdf_url", type=str, help="URL of the research paper PDF.")
    parser.add_argument("--output_dir", type=str, default="./generated_repo",
                        help="Target directory for generated repo (default: ./generated_repo)")

    # Provider selection
    provider_group = parser.add_argument_group("Model Provider")
    provider_group.add_argument("--provider", type=str, default=None,
                                choices=["gemini", "openai", "anthropic", "ollama"],
                                help="LLM provider to use (auto-detected if not set)")
    provider_group.add_argument("--model", type=str, default=None,
                                help="Specific model name (e.g., gpt-4o, gemini-2.5-pro-preview-05-06)")
    provider_group.add_argument("--vision-provider", type=str, default=None,
                                choices=["gemini", "openai", "anthropic", "ollama"],
                                help="Provider for vision/diagram tasks (defaults to primary)")
    provider_group.add_argument("--vision-model", type=str, default=None,
                                help="Model for vision tasks")

    # Pipeline control
    pipeline_group = parser.add_argument_group("Pipeline Options")
    pipeline_group.add_argument("--skip-validation", action="store_true",
                                help="Skip the validation pass")
    pipeline_group.add_argument("--skip-tests", action="store_true",
                                help="Skip test generation")
    pipeline_group.add_argument("--skip-equations", action="store_true",
                                help="Skip dedicated equation extraction")
    pipeline_group.add_argument("--max-fix-iterations", type=int, default=2,
                                help="Max auto-fix attempts (default: 2)")

    # Cache control
    cache_group = parser.add_argument_group("Cache")
    cache_group.add_argument("--no-cache", action="store_true",
                             help="Disable pipeline caching")
    cache_group.add_argument("--cache-dir", type=str, default=None,
                             help="Custom cache directory")
    cache_group.add_argument("--clear-cache", action="store_true",
                             help="Clear all cached data and exit")

    # Misc
    parser.add_argument("--list-providers", action="store_true",
                        help="List available providers and models")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")

    args = parser.parse_args()

    # Handle utility commands
    if args.list_providers:
        list_providers_cmd()
        sys.exit(0)

    if args.clear_cache:
        cache = PipelineCache(args.cache_dir)
        cache.clear()
        print("Cache cleared.")
        sys.exit(0)

    # Validate required args
    if not args.pdf_url:
        parser.error("--pdf_url is required (or use --list-providers / --clear-cache)")

    # Run pipeline
    main(
        pdf_url=args.pdf_url,
        output_dir=args.output_dir,
        provider_name=args.provider,
        model_name=args.model,
        vision_provider_name=args.vision_provider,
        vision_model_name=args.vision_model,
        skip_validation=args.skip_validation,
        skip_tests=args.skip_tests,
        skip_equations=args.skip_equations,
        max_fix_iterations=args.max_fix_iterations,
        use_cache=not args.no_cache,
        cache_dir=args.cache_dir,
        verbose=args.verbose,
    )
