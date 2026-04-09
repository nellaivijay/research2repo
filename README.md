# Research2Repo v3.0

**Multi-model agentic framework that converts ML research papers into production-ready GitHub repositories.**

Inspired by [PaperCoder](https://arxiv.org/abs/2504.17192) — implements decomposed planning, per-file analysis, self-refine loops, execution sandbox, and multi-agent orchestration on top of Research2Repo's multi-model provider system.

Supports **Google Gemini**, **OpenAI GPT-4o/o3**, **Anthropic Claude**, and **Ollama** (local models). Uses long-context single-pass architecture — no RAG, no chunking, no lost context.

---

## What's New in v3.0

| Feature | Description |
|---------|-------------|
| **Decomposed Planning** | 4-stage planning: overall plan, architecture design (UML), logic design, config generation |
| **Per-File Analysis** | Deep per-file specification before code generation (+0.23 ablation improvement per PaperCoder) |
| **Self-Refine Loops** | Verify/refine cycles at every pipeline stage to catch errors early |
| **Execution Sandbox** | Docker/local sandbox to actually run generated code |
| **Auto-Debug** | Iterative error analysis + fix when execution fails (supports 19+ Python error types) |
| **DevOps Generation** | Auto-generates Dockerfile, docker-compose, Makefile, GitHub Actions CI, setup.py |
| **Reference Evaluation** | Score generated repo against a reference implementation |
| **Interactive Mode** | Pause after planning to review architecture before code generation |
| **Structured Paper Parsing** | Multi-backend PDF parsing (GROBID, doc2json, PyMuPDF, PyPDF2) |
| **Multi-Agent Architecture** | Pluggable agent system with base class, message passing, orchestrator |

---

## Architecture

### Classic Mode (v2.0 compatible)

```
PDF --> [Analyzer] --> [Equation Extractor] --> [Architect] --> [Coder] --> [Validator] --> Repo
           |                    |                    |              |             |
      Long-Context         Vision/LaTeX         Structured     Rolling       Self-Review
      + Multimodal         Extraction           JSON Output    Context       + Auto-Fix
```

### Agent Mode (v3.0)

```
PDF --> [Paper Parser] --> [Decomposed Planner] --> [Per-File Analyzer] --> [Coder] --> [Validator]
           |                    |                        |                    |             |
       Multi-backend     4-stage decomposed        Deep per-file         Rolling       Auto-Fix
       (GROBID/PyMuPDF)  + UML diagrams            specification        Context       Loop
                                |                        |                    |
                         [Self-Refine]             [Self-Refine]              |
                                                                             v
                                                                    [Execution Sandbox]
                                                                             |
                                                                    [Auto-Debugger]
                                                                             |
                                                                    [DevOps Generator]
                                                                             |
                                                                    [Evaluator] --> Repository
```

### Agent Mode Pipeline Stages

| Stage | Module | What It Does |
|-------|--------|-------------|
| 1 | `PaperAnalyzer` | Long-context analysis + vision diagram extraction |
| 2 | `DecomposedPlanner` | 4-stage planning: overall -> architecture (UML) -> logic -> config |
| 3 | `FileAnalyzer` | Per-file deep analysis with accumulated context |
| 4 | `CodeSynthesizer` | File-by-file code generation with rolling dependency context |
| 5 | `TestGenerator` | Auto-generated pytest suite |
| 6 | `CodeValidator` | Self-review + iterative auto-fix loop |
| 7 | `ExecutionSandbox` + `AutoDebugger` | Run code in Docker/local sandbox, auto-debug failures |
| 8 | `DevOpsGenerator` | Generate Dockerfile, Makefile, CI, docker-compose, setup.py |
| 9 | `ReferenceEvaluator` | Score against reference implementation (1-5 scale) |
| 10 | Save | Write all files + metadata to output directory |

### Self-Refine at Every Stage

Each planning/analysis artifact goes through a verify-then-refine loop:

```
Artifact --> [Verify] --> issues found? --> [Refine] --> re-verify --> ... (up to N iterations)
                |
                no issues --> pass through unchanged
```

### Multi-Model Provider System

```
providers/
  base.py              # Abstract interface + capabilities enum
  gemini.py            # Google Gemini (2.5 Pro, 2.0 Flash, 1.5 Pro)
  openai_provider.py   # OpenAI (GPT-4o, GPT-4-turbo, o3, o1)
  anthropic_provider.py # Anthropic (Claude Sonnet 4, Opus 4, 3.5 Sonnet)
  ollama.py            # Local models (DeepSeek, Llama, CodeLlama, Mistral)
  registry.py          # Auto-detection, fallback chains, cost estimation
```

**Key design:** Each provider implements `generate()`, `generate_structured()`, and optionally `upload_file()` + `generate_with_file()`. The registry auto-detects available providers from environment variables and picks the best one for each capability (long-context, vision, code generation, structured output).

---

## Installation

```bash
git clone https://github.com/nellaivijay/Research2Repo.git
cd Research2Repo
pip install -r requirements.txt
```

### Provider Setup (pick one or more)

```bash
# Google Gemini (recommended — 2M token context + vision)
export GEMINI_API_KEY="your_key_here"

# OpenAI GPT-4o
export OPENAI_API_KEY="your_key_here"
pip install openai

# Anthropic Claude
export ANTHROPIC_API_KEY="your_key_here"
pip install anthropic

# Ollama (local, free)
# Install from https://ollama.ai, then:
ollama pull deepseek-coder-v2
```

### Optional: Enhanced Vision (diagram extraction from PDF pages)

```bash
pip install PyMuPDF
```

### Install all providers at once

```bash
pip install -e ".[all]"
```

---

## Usage

### Classic Mode (v2.0 compatible)

```bash
# Auto-detect provider
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf"

# Use a local PDF file
python main.py --pdf_path ./papers/attention.pdf

# Specific provider and model
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --provider openai --model gpt-4o

# Mix providers
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --provider gemini --vision-provider anthropic

# Fast run (skip validation and tests)
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --skip-validation --skip-tests
```

### Agent Mode (v3.0)

```bash
# Basic agent mode with decomposed planning
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --mode agent

# With self-refine loops (verify/refine each stage)
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --mode agent --refine

# With execution sandbox + auto-debug
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --mode agent --execute

# Interactive planning review
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --mode agent --interactive

# Full pipeline with all features
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --mode agent \
  --refine --execute --evaluate --reference-dir ./reference_impl

# Evaluate against reference implementation
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --mode agent \
  --evaluate --reference-dir ./path/to/reference/repo
```

### Utility Commands

```bash
python main.py --list-providers     # List available providers and models
python main.py --clear-cache        # Clear all cached data
```

---

## Project Structure

```
Research2Repo/
  main.py                          # CLI entry point: classic + agent modes
  config.py                        # Global configuration

  providers/                       # Multi-model abstraction layer
    __init__.py
    base.py                        # BaseProvider ABC + ModelCapability enum
    gemini.py                      # Google Gemini provider
    openai_provider.py             # OpenAI GPT provider
    anthropic_provider.py          # Anthropic Claude provider
    ollama.py                      # Local Ollama provider
    registry.py                    # Auto-detection + factory

  core/                            # Pipeline stages
    __init__.py
    analyzer.py                    # PaperAnalyzer — PDF ingestion + structured analysis
    architect.py                   # SystemArchitect — repo structure design
    coder.py                       # CodeSynthesizer — file-by-file code generation
    validator.py                   # CodeValidator — self-review + auto-fix
    planner.py                     # DecomposedPlanner — 4-stage planning (v3.0)
    file_analyzer.py               # FileAnalyzer — per-file deep analysis (v3.0)
    refiner.py                     # SelfRefiner — verify/refine loops (v3.0)
    paper_parser.py                # PaperParser — multi-backend PDF parsing (v3.0)

  advanced/                        # Advanced capabilities
    __init__.py
    equation_extractor.py          # Dedicated equation extraction (LaTeX + PyTorch)
    config_generator.py            # YAML config from hyperparameters
    test_generator.py              # Auto pytest suite generation
    cache.py                       # Content-addressed pipeline cache
    executor.py                    # ExecutionSandbox — Docker/local runner (v3.0)
    debugger.py                    # AutoDebugger — iterative error fixing (v3.0)
    evaluator.py                   # ReferenceEvaluator — scoring (v3.0)
    devops.py                      # DevOpsGenerator — Dockerfile, CI, Makefile (v3.0)

  agents/                          # Multi-agent architecture (v3.0)
    __init__.py
    base.py                        # BaseAgent ABC + AgentMessage
    orchestrator.py                # AgentOrchestrator — master 10-stage controller

  prompts/                         # Externalized prompt templates
    analyzer.txt                   # Paper analysis prompt
    architect.txt                  # Repo design prompt
    coder.txt                      # Code generation prompt
    validator.txt                  # Validation prompt
    diagram_extractor.txt          # Vision diagram extraction prompt
    equation_extractor.txt         # Equation extraction prompt
    test_generator.txt             # Test generation prompt
    overall_plan.txt               # Overall plan extraction (v3.0)
    architecture_design.txt        # Architecture design with UML (v3.0)
    logic_design.txt               # Logic design + dependency graph (v3.0)
    file_analysis.txt              # Per-file analysis prompt (v3.0)
    self_refine_verify.txt         # Self-refine verification (v3.0)
    self_refine_refine.txt         # Self-refine refinement (v3.0)
    auto_debug.txt                 # Auto-debug prompt (v3.0)
    reference_eval.txt             # Reference evaluation prompt (v3.0)
    devops.txt                     # DevOps generation prompt (v3.0)

  tests/                           # Project tests
    __init__.py

  pyproject.toml                   # Package metadata + optional deps
  requirements.txt                 # Dependencies
  .gitignore
  LICENSE                          # Apache 2.0
```

---

## How It Works

### 1. Zero-RAG Long-Context Analysis

Traditional paper-to-code tools chunk the paper and use RAG, which disconnects hyperparameters (appendix) from equations (Section 3). Research2Repo sends the **entire paper** to the model in a single pass:

- **Gemini:** Uploads PDF via File API (2M+ token context)
- **OpenAI/Anthropic:** Extracts text via PyPDF2, fits within 128K-200K context
- **Ollama:** Extracts text, uses what fits in the local model's context window

### 2. Decomposed Planning (v3.0)

Instead of a single architecture pass, the planner decomposes into 4 stages:

1. **Overall Plan** — Extract core components, methods, training objectives, evaluation protocols
2. **Architecture Design** — File list + Mermaid class/sequence diagrams + module relationships
3. **Logic Design** — Execution order, dependency graph, per-file specifications
4. **Config Generation** — Structured YAML from hyperparameters

Each stage can be independently refined through the self-refine loop.

### 3. Per-File Analysis

Before code generation, each file in the plan gets a deep analysis that includes:
- Classes and functions to implement
- Import dependencies (internal + external)
- Algorithms from the paper to implement
- Input/output specifications
- Test criteria

This accumulated context feeds into the code generation stage, improving output quality (+0.23 in PaperCoder ablation studies).

### 4. Self-Refine Loops

Every artifact (plan, file analysis, generated code) can be verified and refined:

1. **Verify** — Critique the artifact for issues (with severity assessment)
2. **Refine** — If issues found, generate an improved version
3. **Iterate** — Repeat up to N times or until no issues remain

### 5. Execution Sandbox + Auto-Debug

Generated code is actually executed in a sandboxed environment:

- **Docker mode** — Builds a container, runs with resource limits
- **Local mode** — Fallback with subprocess isolation
- **Auto-debug** — When execution fails, analyzes the error, generates targeted fixes, and re-runs (supports 19+ Python error types including ImportError, TypeError, CudaOOMError)

### 6. Rolling Context Code Generation

Files are generated in dependency order (config -> utils -> model components -> training -> tests). Each file receives:
- Full paper analysis (equations, hyperparameters, architecture)
- Previously generated dependency files
- Architecture plan with file descriptions
- Per-file analysis results
- Mermaid diagrams

### 7. Self-Review Validation Loop

After generation, a separate validation pass compares every generated file against the paper:
- **Equation fidelity:** Every paper equation has a code counterpart
- **Dimension consistency:** Tensor shapes match the paper
- **Hyperparameter completeness:** All values are configurable, not hardcoded
- **Loss function accuracy:** Matches the paper's formulation

Critical issues are auto-fixed up to N iterations (default: 2).

---

## Supported Models

| Provider | Models | Context | Vision | Cost |
|----------|--------|---------|--------|------|
| **Gemini** | 2.5 Pro, 2.0 Flash, 1.5 Pro | 1M-2M | Yes | $0.0001-$0.01/1K |
| **OpenAI** | GPT-4o, GPT-4-turbo, o3, o1 | 128K-200K | Yes | $0.0025-$0.06/1K |
| **Anthropic** | Claude Sonnet 4, Opus 4, 3.5 Sonnet | 200K | Yes | $0.003-$0.075/1K |
| **Ollama** | DeepSeek, Llama 3.1, CodeLlama, Mistral, LLaVA | 4K-128K | Partial | Free |

---

## CLI Reference

```
python main.py [OPTIONS]

Required (one of):
  --pdf_url URL                URL of the research paper PDF
  --pdf_path PATH              Path to a local PDF file

Mode:
  --mode MODE                  classic (default) | agent

Provider:
  --provider NAME              gemini | openai | anthropic | ollama
  --model NAME                 Specific model name
  --vision-provider NAME       Separate provider for vision tasks
  --vision-model NAME          Specific vision model

Classic Pipeline Options:
  --output_dir DIR             Output directory (default: ./generated_repo)
  --skip-validation            Skip validation pass
  --skip-tests                 Skip test generation
  --skip-equations             Skip equation extraction
  --max-fix-iterations N       Max auto-fix attempts (default: 2)

Agent Pipeline Options (--mode agent):
  --refine                     Enable self-refine loops at each stage
  --execute                    Enable execution sandbox + auto-debug
  --evaluate                   Enable reference-based evaluation
  --no-tests                   Disable test generation
  --no-devops                  Disable DevOps file generation
  --interactive                Pause after planning for user review
  --reference-dir DIR          Reference implementation for evaluation
  --max-refine-iterations N    Max self-refine iterations (default: 2)
  --max-debug-iterations N     Max auto-debug iterations (default: 3)

Cache:
  --no-cache                   Disable caching
  --cache-dir DIR              Custom cache directory
  --clear-cache                Clear all cached data

Misc:
  --list-providers             Show available providers and models
  --verbose, -v                Verbose output
```

---

## Environment Variables

| Variable | Description | Required |
|----------|------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | For Gemini provider |
| `OPENAI_API_KEY` | OpenAI API key | For OpenAI provider |
| `ANTHROPIC_API_KEY` | Anthropic API key | For Anthropic provider |
| `OLLAMA_HOST` | Ollama server URL (default: `http://localhost:11434`) | For Ollama |
| `R2R_PROVIDER` | Default provider override | No |
| `R2R_MODEL` | Default model override | No |
| `R2R_CACHE_DIR` | Custom cache directory | No |

---

## Comparison with PaperCoder

| Feature | Research2Repo v3.0 | PaperCoder |
|---------|-------------------|------------|
| Multi-model support | Gemini, OpenAI, Anthropic, Ollama | GPT-4o only |
| Decomposed planning | 4-stage (overall/arch/logic/config) | 3-stage (overall/arch/logic) |
| Per-file analysis | Yes | Yes |
| Self-refine loops | All stages | Plan + code |
| UML diagrams | Mermaid class + sequence | PlantUML class + sequence |
| Vision/diagram extraction | Yes (multimodal) | No |
| Equation extraction | Dedicated pipeline | No |
| Execution sandbox | Docker + local | No |
| Auto-debug | Yes (19+ error types) | No |
| DevOps generation | Dockerfile, CI, Makefile | No |
| Reference evaluation | LLM-based scoring | No |
| Caching | Content-addressed | No |
| Local models | Ollama support | No |

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
