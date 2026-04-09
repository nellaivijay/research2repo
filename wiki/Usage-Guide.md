# Usage Guide

This guide covers everything you need to install, configure, and run Research2Repo -- from a single quick-start command through advanced multi-provider agent pipelines.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Quick Start](#3-quick-start)
4. [CLI Reference](#4-cli-reference)
5. [Usage Examples](#5-usage-examples)
6. [Understanding Output](#6-understanding-output)
7. [Environment Variables](#7-environment-variables)
8. [Programmatic Usage](#8-programmatic-usage)
9. [Choosing Between Classic and Agent Mode](#9-choosing-between-classic-and-agent-mode)

---

## 1. Prerequisites

### Required

- **Python 3.10 or higher** (3.10, 3.11, and 3.12 are tested).
- **At least one LLM provider** -- either a cloud API key or a local Ollama installation:
  - Google Gemini API key, **or**
  - OpenAI API key, **or**
  - Anthropic API key, **or**
  - Ollama installed and running locally.

### Optional

| Dependency | Purpose |
|------------|---------|
| **Docker** | Required for the execution sandbox when using `--execute` in agent mode. Falls back to local subprocess isolation if Docker is unavailable. |
| **PyMuPDF** (`fitz`) | Enables high-quality diagram extraction from PDF pages. Without it, vision-based diagram analysis is limited. |
| **GROBID server** | Provides structured TEI XML parsing for papers. Improves section boundary detection and metadata extraction. Used by the multi-backend `PaperParser`. |

---

## 2. Installation

### Clone and Install

```bash
git clone https://github.com/nellaivijay/Research2Repo.git
cd Research2Repo
pip install -r requirements.txt
```

Or install as an editable package:

```bash
pip install -e .
```

### Provider Setup

You need at least one provider configured. Set the appropriate environment variable and install the provider SDK.

**Google Gemini** (recommended -- 1M-2M token context, native vision, File Upload API):

```bash
export GEMINI_API_KEY="your_key_here"
pip install google-generativeai
```

**OpenAI GPT-4o / o3:**

```bash
export OPENAI_API_KEY="your_key_here"
pip install openai
```

**Anthropic Claude:**

```bash
export ANTHROPIC_API_KEY="your_key_here"
pip install anthropic
```

**Ollama** (local, free):

```bash
# Install Ollama from https://ollama.ai, then pull a model:
ollama pull deepseek-coder-v2
# Optionally set a custom host (defaults to http://localhost:11434):
export OLLAMA_HOST="http://localhost:11434"
```

### Optional Dependencies

Install all provider SDKs and optional libraries at once:

```bash
pip install -e ".[all]"
```

Install only vision support (PyMuPDF for diagram extraction):

```bash
pip install -e ".[vision]"
```

Install parsing support (PyMuPDF + lxml for GROBID TEI XML):

```bash
pip install -e ".[parsing]"
```

Install development tools (pytest, ruff):

```bash
pip install -e ".[dev]"
```

---

## 3. Quick Start

The simplest possible invocation requires only a PDF URL or a local PDF path:

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf"

# Or use a local PDF file
python main.py --pdf_path ./papers/attention.pdf
```

### What Happens Step by Step

When you run this command with default settings (classic mode), the pipeline executes 10 stages:

1. **Download PDF** -- Fetches the paper from the provided URL and saves it locally.
2. **Analyze Paper** -- Sends the entire paper to the LLM in a single long-context pass. Extracts the title, authors, abstract, equations, hyperparameters, architecture description, sections, and more into a structured `PaperAnalysis` object.
3. **Extract Equations** -- Runs a dedicated equation extraction pass using vision capabilities. Merges newly found equations with those from the analysis stage.
4. **Architect Repository** -- Designs the repository structure: file list, directory tree, module dependencies, and `requirements.txt`.
5. **Generate Config** -- Creates a `config.yaml` file from all hyperparameters found in the paper.
6. **Synthesize Code** -- Generates each source file in dependency order. Each file receives the full paper analysis, previously generated files, and the architecture plan as context.
7. **Generate Tests** -- Creates a pytest test suite covering the generated modules.
8. **Validate** -- Compares the generated code against the paper. Checks equation fidelity, hyperparameter coverage, dimension consistency, and loss function accuracy. Produces a score out of 100.
9. **Auto-Fix** -- If critical issues are found during validation, iteratively applies fixes and re-validates (up to 2 iterations by default).
10. **Save Repository** -- Writes all generated files to the output directory (default: `./generated_repo`), along with a `.r2r_metadata.json` file containing run metadata.

The auto-detected provider is chosen based on which API keys are set in your environment. If multiple are available, the priority order is: Gemini, OpenAI, Anthropic, Ollama.

---

## 4. CLI Reference

```
python main.py [OPTIONS]
```

### Core Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--pdf_url URL` | string | *(required)** | URL of the research paper PDF (arXiv, OpenReview, direct link, etc.). Either `--pdf_url` or `--pdf_path` must be provided (but not both). Not required when using `--list-providers` or `--clear-cache`. |
| `--pdf_path PATH` | string | *(required)** | Path to a local PDF file. Either `--pdf_url` or `--pdf_path` must be provided (but not both). Not required when using `--list-providers` or `--clear-cache`. |
| `--output_dir DIR` | string | `./generated_repo` | Target directory where the generated repository will be written. Created automatically if it does not exist. |
| `--mode MODE` | choice | `classic` | Pipeline mode. `classic` runs the original v2.0 10-stage linear pipeline. `agent` runs the enhanced v3.0 multi-agent pipeline with decomposed planning, per-file analysis, and optional execution sandbox. |

### Provider Selection

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--provider NAME` | choice | auto-detected | LLM provider to use. Choices: `gemini`, `openai`, `anthropic`, `ollama`. When omitted, the system auto-detects from available API keys. |
| `--model NAME` | string | provider default | Specific model name to use (e.g., `gpt-4o`, `gemini-2.5-pro-preview-05-06`, `claude-sonnet-4-20250514`). |
| `--vision-provider NAME` | choice | same as `--provider` | Separate provider for vision and diagram extraction tasks. Useful for mixing a fast text provider with a strong vision provider. Choices: `gemini`, `openai`, `anthropic`, `ollama`. |
| `--vision-model NAME` | string | provider default | Specific model for vision tasks. |

### Classic Pipeline Options

These options apply when `--mode classic` (the default).

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--skip-validation` | flag | `false` | Skip the validation pass entirely. Also skips the auto-fix stage. Useful for faster runs when you do not need quality scoring. |
| `--skip-tests` | flag | `false` | Skip automatic test suite generation. |
| `--skip-equations` | flag | `false` | Skip the dedicated equation extraction stage. Equations from the main analysis are still used. |
| `--max-fix-iterations N` | int | `2` | Maximum number of auto-fix attempts when validation finds critical issues. Set to `0` to disable auto-fix while keeping validation. |

### Agent Pipeline Options

These options apply when `--mode agent`.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--refine` | flag | `false` | Enable self-refine loops at each pipeline stage. Each artifact (plan, file analyses) goes through verify/refine cycles to catch errors early. |
| `--execute` | flag | `false` | Enable the execution sandbox. Generated code is actually run (in Docker or locally), and failures trigger the auto-debug loop. |
| `--evaluate` | flag | `false` | Enable reference-based evaluation scoring. Requires `--reference-dir` to compare against an existing implementation. |
| `--no-tests` | flag | `false` | Disable test generation in agent mode. |
| `--no-devops` | flag | `false` | Disable DevOps file generation (Dockerfile, Makefile, GitHub Actions CI, docker-compose, setup.py). |
| `--interactive` | flag | `false` | Pause after the planning stage to display the proposed architecture. You can review the directory tree, file list, and dependencies before continuing. Enter `q` to abort. |
| `--reference-dir DIR` | string | `None` | Path to a reference implementation directory. Used by `--evaluate` to score the generated repository against a known-good implementation. |
| `--max-refine-iterations N` | int | `2` | Maximum self-refine iterations per stage when `--refine` is enabled. |
| `--max-debug-iterations N` | int | `3` | Maximum auto-debug iterations when `--execute` is enabled and execution fails. |

### Cache Options

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--no-cache` | flag | `false` | Disable pipeline caching entirely. By default, analysis results, architecture plans, and generated files are cached to speed up re-runs on the same paper. |
| `--cache-dir DIR` | string | `.r2r_cache` | Custom directory for the pipeline cache. |
| `--clear-cache` | flag | -- | Clear all cached data and exit immediately. Does not run the pipeline. |

### Miscellaneous

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--list-providers` | flag | -- | List all registered providers, their availability status, supported models, capabilities, and pricing. Exits after printing. |
| `--verbose`, `-v` | flag | `false` | Enable verbose output. Shows the directory tree during architecture, individual file paths during save, and detailed validation issues. |

---

## 5. Usage Examples

### Basic Usage

**Auto-detect provider, default settings:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf"
```

**Use a local PDF file:**

```bash
python main.py --pdf_path ./papers/attention.pdf
```

**Custom output directory:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --output_dir ./my_transformer_repo
```

**Fast run -- skip validation, tests, and equation extraction:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --skip-validation --skip-tests --skip-equations
```

### Provider Selection

**Use Google Gemini explicitly:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --provider gemini --model gemini-2.5-pro-preview-05-06
```

**Use OpenAI GPT-4o:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --provider openai --model gpt-4o
```

**Use Anthropic Claude:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --provider anthropic --model claude-sonnet-4-20250514
```

**Use a local Ollama model:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --provider ollama --model deepseek-coder-v2:latest
```

### Agent Mode

**Basic agent mode with decomposed planning:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --mode agent
```

**Agent mode with self-refine loops:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --mode agent --refine
```

**Agent mode with execution sandbox and auto-debug:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --mode agent --execute
```

**Interactive planning review:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --mode agent --interactive
```

**Full agent pipeline -- all features enabled:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --mode agent --refine --execute --evaluate \
  --reference-dir ./reference_impl
```

### Advanced Patterns

**Mixed providers -- Gemini for text, Anthropic for vision:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --provider gemini --vision-provider anthropic
```

**Agent mode with evaluation and custom iteration limits:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --mode agent --refine --execute --evaluate \
  --reference-dir ./my_reference \
  --max-refine-iterations 3 --max-debug-iterations 5
```

**Disable caching for a fresh run:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --no-cache
```

**Use a custom cache directory:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --cache-dir /tmp/r2r_cache
```

**Agent mode without DevOps or tests (code generation only):**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --mode agent --no-tests --no-devops
```

**Verbose output for debugging:**

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --verbose
```

### Utility Commands

**List all available providers and models:**

```bash
python main.py --list-providers
```

**Clear the pipeline cache:**

```bash
python main.py --clear-cache
```

**Clear a specific cache directory:**

```bash
python main.py --clear-cache --cache-dir /tmp/r2r_cache
```

---

## 6. Understanding Output

### Generated Repository Structure

A typical generated repository looks like this:

```
generated_repo/
  config.yaml               # Hyperparameters extracted from the paper
  requirements.txt          # Python dependencies
  README.md                 # Generated documentation
  model.py                  # Core model implementation
  train.py                  # Training script
  evaluate.py               # Evaluation script
  data.py                   # Data loading and preprocessing
  utils.py                  # Utility functions
  tests/
    test_model.py           # Auto-generated test suite
    test_data.py
  .r2r_metadata.json        # Pipeline run metadata
```

In agent mode with DevOps enabled, additional files are generated:

```
  Dockerfile                # Container definition
  docker-compose.yaml       # Multi-service composition
  Makefile                  # Build/run/test targets
  setup.py                  # Package installation script
  .github/
    workflows/
      ci.yml                # GitHub Actions CI pipeline
```

### .r2r_metadata.json Contents

Every run produces a metadata file at the root of the output directory:

```json
{
  "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
  "provider": "gemini",
  "model": "gemini-2.5-pro-preview-05-06",
  "timestamp": "2025-01-15T14:30:22.123456",
  "elapsed_seconds": 187.3,
  "files_generated": 12,
  "paper_title": "Attention Is All You Need",
  "equations_found": 14,
  "hyperparams_found": 22
}
```

In agent mode, the metadata also includes:

```json
{
  "timings": {
    "parse": "12.3s",
    "plan": "45.1s",
    "file_analysis": "23.7s",
    "codegen": "67.2s",
    "tests": "18.4s",
    "validation": "15.6s",
    "execution": "32.1s",
    "devops": "8.9s",
    "save": "0.3s"
  },
  "config": {
    "enable_refine": true,
    "enable_execution": true,
    "enable_tests": true,
    "enable_evaluation": false,
    "enable_devops": true,
    "interactive": false,
    "max_debug_iterations": 3,
    "max_refine_iterations": 2,
    "max_fix_iterations": 2
  }
}
```

### Validation Report Interpretation

The validation stage produces a report with these key metrics:

| Metric | Description |
|--------|-------------|
| **Score** | Overall quality score on a 0-100 scale. |
| **Equation Coverage** | Percentage of paper equations that have corresponding code implementations. |
| **Hyperparam Coverage** | Percentage of paper hyperparameters that are configurable in the generated code (not hardcoded). |
| **Critical Count** | Number of critical issues found (missing loss functions, wrong dimensions, etc.). |
| **Warning Count** | Number of non-critical warnings (style issues, missing docstrings, etc.). |

**Score ranges:**

| Range | Interpretation |
|-------|---------------|
| 90-100 | Excellent -- all paper elements faithfully implemented. |
| 70-89 | Good -- most elements present, minor gaps. |
| 50-69 | Fair -- core architecture correct but significant missing pieces. |
| Below 50 | Needs attention -- major elements missing or incorrectly implemented. |

### Evaluation Scoring (Agent Mode)

When `--evaluate` is used with a `--reference-dir`, the evaluator produces a score on a 1-5 scale:

| Score | Meaning |
|-------|---------|
| 5 | Near-identical to reference implementation. |
| 4 | Functionally equivalent with minor differences. |
| 3 | Same approach but notable implementation differences. |
| 2 | Partially overlapping with significant gaps. |
| 1 | Substantially different from reference. |

---

## 7. Environment Variables

Research2Repo reads these environment variables. CLI arguments always take precedence over environment variables, which in turn take precedence over built-in defaults.

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GEMINI_API_KEY` | Google Gemini API key. | -- | For Gemini provider |
| `OPENAI_API_KEY` | OpenAI API key. | -- | For OpenAI provider |
| `ANTHROPIC_API_KEY` | Anthropic API key. | -- | For Anthropic provider |
| `OLLAMA_HOST` | Ollama server URL. | `http://localhost:11434` | For Ollama (if non-default host) |
| `R2R_PROVIDER` | Override the default provider selection. Values: `gemini`, `openai`, `anthropic`, `ollama`, `auto`. | `auto` | No |
| `R2R_MODEL` | Override the default model for the selected provider. | Provider default | No |
| `R2R_CACHE_DIR` | Custom cache directory path. | `.r2r_cache` | No |
| `R2R_SKIP_VALIDATION` | Set to `true` to disable validation by default. | `false` | No |
| `R2R_SKIP_TESTS` | Set to `true` to disable test generation by default. | `false` | No |
| `R2R_NO_CACHE` | Set to `true` to disable caching by default. | `false` | No |
| `R2R_VERBOSE` | Set to `true` to enable verbose output by default. | `false` | No |

**Example: Set defaults via environment:**

```bash
export GEMINI_API_KEY="your_key"
export R2R_PROVIDER="gemini"
export R2R_VERBOSE="true"
export R2R_CACHE_DIR="/tmp/r2r_cache"

# Now just:
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf"
```

---

## 8. Programmatic Usage

Research2Repo modules can be used directly in Python scripts for custom workflows.

### Get a Provider

```python
from providers import get_provider, ProviderRegistry

# Auto-detect the best available provider
provider = get_provider()

# Request a specific provider and model
provider = get_provider(provider_name="openai", model_name="gpt-4o")

# Get the best provider for a specific capability
from providers.base import ModelCapability
vision_provider = get_provider(required_capability=ModelCapability.VISION)

# List all registered providers and which are available
print(ProviderRegistry.list_providers())     # ['gemini', 'openai', 'anthropic', 'ollama']
print(ProviderRegistry.detect_available())   # ['gemini', 'openai'] (depends on env)
```

### Analyze a Paper

```python
from providers import get_provider
from core.analyzer import PaperAnalyzer

provider = get_provider()
analyzer = PaperAnalyzer(provider=provider)

# Upload and analyze a PDF
document = analyzer.upload_document("paper.pdf")
diagrams = analyzer.extract_diagrams_to_mermaid("paper.pdf")
analysis = analyzer.analyze(document, diagrams)

print(analysis.title)
print(analysis.equations)
print(analysis.hyperparameters)
```

### Design Architecture

```python
from core.architect import SystemArchitect

architect = SystemArchitect(provider=provider)
plan = architect.design_system(
    analysis=analysis,
    document=document,
    vision_context=diagrams,
)

print(plan.repo_name)
print(plan.directory_tree)
for f in plan.files:
    print(f"{f.path} -- {f.description}")
```

### Generate Code

```python
from core.coder import CodeSynthesizer

coder = CodeSynthesizer(provider=provider)
generated_files = coder.generate_codebase(
    analysis=analysis,
    plan=plan,
    document=document,
)

for filepath, content in generated_files.items():
    print(f"{filepath}: {len(content)} chars")
```

### Run the Full Agent Pipeline

```python
from providers import get_provider
from agents.orchestrator import AgentOrchestrator

provider = get_provider(provider_name="gemini")

config = {
    "enable_refine": True,
    "enable_execution": False,
    "enable_tests": True,
    "enable_evaluation": False,
    "enable_devops": True,
    "interactive": False,
    "max_refine_iterations": 2,
    "max_debug_iterations": 3,
}

orchestrator = AgentOrchestrator(provider=provider, config=config)
result = orchestrator.run(
    pdf_path="paper.pdf",
    output_dir="./output",
)

# Access results
print(result["metadata"]["paper_title"])
print(result["metadata"]["files_generated"])
print(result["validation_report"].score)
```

### Estimate Costs

```python
from providers import ProviderRegistry

cost = ProviderRegistry.estimate_cost(
    provider_name="openai",
    model_name="gpt-4o",
    input_tokens=50000,
    output_tokens=20000,
)
print(f"Estimated cost: ${cost:.4f}")
```

### Use Generation Config

```python
from providers.base import GenerationConfig

config = GenerationConfig(
    temperature=0.15,
    top_p=0.95,
    max_output_tokens=16384,
    response_format="json",
)

result = provider.generate(
    prompt="Analyze this paper...",
    system_prompt="You are a research paper analyst.",
    config=config,
)
print(result.text)
print(f"Tokens used: {result.input_tokens} in, {result.output_tokens} out")
```

---

## 9. Choosing Between Classic and Agent Mode

Research2Repo offers two pipeline modes. The right choice depends on your use case.

### Classic Mode (`--mode classic`)

The original v2.0 pipeline. Runs a linear 10-stage sequence: analyze, extract equations, architect, generate config, synthesize code, generate tests, validate, auto-fix, and save.

**Best for:**

- Quick prototyping when you need a repository fast.
- Simple or well-structured papers with clear architectures.
- Cost-sensitive runs (fewer LLM calls).
- When you want to mix vision and text providers (`--vision-provider`).

**Characteristics:**

- Single planning pass (one architecture step).
- No per-file deep analysis before code generation.
- No execution or auto-debug.
- Supports pipeline caching for faster re-runs.
- Typical run time: 2-5 minutes depending on paper length and provider.

### Agent Mode (`--mode agent`)

The v3.0 multi-agent pipeline. Features decomposed 4-stage planning, per-file analysis, optional self-refine loops, execution sandbox, DevOps generation, and reference evaluation.

**Best for:**

- Complex papers with many interacting components.
- When code correctness is critical (use `--refine --execute`).
- Papers with complex training pipelines that benefit from per-file specification.
- When you have a reference implementation to evaluate against.
- When you want production-ready output with Docker, CI, and Makefiles.

**Characteristics:**

- 4-stage decomposed planning (overall, architecture with UML, logic, config).
- Per-file deep analysis before code generation.
- Optional verify/refine cycles at each stage.
- Optional execution sandbox with auto-debug loop.
- Generates DevOps files by default.
- More LLM calls and higher cost, but significantly better output quality.
- Typical run time: 5-15 minutes depending on features enabled.

### Decision Matrix

| Criterion | Classic | Agent |
|-----------|---------|-------|
| Speed | Faster (2-5 min) | Slower (5-15 min) |
| Cost | Lower (fewer LLM calls) | Higher (more LLM calls) |
| Code quality | Good | Better (with `--refine`) |
| Simple papers | Sufficient | Overkill |
| Complex papers | May miss details | Thorough |
| Execution testing | Not available | Available (`--execute`) |
| DevOps output | Not available | Default |
| Interactive review | Not available | Available (`--interactive`) |
| Reference evaluation | Not available | Available (`--evaluate`) |
| Caching | Full support | Metadata only |
| Mixed providers | Full support | Primary provider only |

### Recommendations

- **Start with classic mode** for your first run on a paper. It is faster and cheaper, giving you a quick look at what the pipeline produces.
- **Switch to agent mode with `--refine`** when the classic output needs improvement. Self-refine loops catch planning errors and improve code coverage.
- **Add `--execute`** when you need the generated code to actually run. The auto-debug loop can fix common runtime errors automatically.
- **Use `--interactive`** when working on an important paper and you want to review the planned architecture before committing to code generation.
- **Use `--evaluate --reference-dir`** when you have a reference implementation and want a quantitative comparison.
