# High-Level Design

This document describes the detailed design of **Research2Repo v3.0**, covering system decomposition, module responsibilities, pipeline architecture for both operating modes, integration points, configuration management, error handling, and key interaction sequences. It complements the [Architecture Overview](Architecture-Overview) with implementation-level detail.

---

## Table of Contents

- [1. System Decomposition](#1-system-decomposition)
- [2. Module Responsibilities](#2-module-responsibilities)
- [3. Pipeline Architecture](#3-pipeline-architecture)
- [4. Integration Points](#4-integration-points)
- [5. Configuration Management](#5-configuration-management)
- [6. Error Handling Strategy](#6-error-handling-strategy)
- [7. Sequence Diagrams](#7-sequence-diagrams)

---

## 1. System Decomposition

The system is organized into five horizontal layers. Each layer depends only on the layers below it (with one exception: the Orchestration layer references modules in both Core Processing and Advanced Services via lazy imports).

```
+================================================================+
|  Layer 1: PRESENTATION                                         |
|  CLI (argparse), banner, --list-providers, output formatting   |
+================================================================+
                              |
                              v
+================================================================+
|  Layer 2: ORCHESTRATION                                        |
|  main.py: run_classic(), run_agent()                           |
|  agents/orchestrator.py: AgentOrchestrator                     |
+================================================================+
                              |
                              v
+================================================================+
|  Layer 3: CORE PROCESSING                                      |
|  core/analyzer.py    core/architect.py    core/planner.py      |
|  core/file_analyzer.py  core/coder.py     core/validator.py    |
|  core/refiner.py     core/paper_parser.py                      |
+================================================================+
                              |
                              v
+================================================================+
|  Layer 4: ADVANCED SERVICES                                    |
|  advanced/executor.py      advanced/debugger.py                |
|  advanced/evaluator.py     advanced/devops.py                  |
|  advanced/equation_extractor.py  advanced/config_generator.py  |
|  advanced/test_generator.py      advanced/cache.py             |
+================================================================+
                              |
                              v
+================================================================+
|  Layer 5: INFRASTRUCTURE                                       |
|  providers/base.py    providers/registry.py                    |
|  providers/gemini.py  providers/openai_provider.py             |
|  providers/anthropic_provider.py  providers/ollama.py          |
|  config.py                                                     |
+================================================================+
```

### Layer Descriptions

| Layer | Responsibility | Key Modules |
|---|---|---|
| **Presentation** | Parse CLI arguments, display banners, format output, route to operating mode | `main.py` (argparse block, `print_banner`, `list_providers_cmd`) |
| **Orchestration** | Coordinate pipeline stages, manage timing, handle interactive mode, write final output | `main.py::run_classic`, `main.py::run_agent`, `agents/orchestrator.py::AgentOrchestrator` |
| **Core Processing** | Paper analysis, architecture design, decomposed planning, per-file analysis, code synthesis, validation, self-refinement | All modules in `core/` |
| **Advanced Services** | Execution sandbox, auto-debugging, evaluation scoring, DevOps generation, equation extraction, config generation, test generation, caching | All modules in `advanced/` |
| **Infrastructure** | LLM provider abstraction, model capability declarations, provider registry/factory, global configuration | All modules in `providers/`, `config.py` |

---

## 2. Module Responsibilities

### 2.1 Infrastructure Layer

#### `providers/base.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Define the abstract interface that all LLM providers implement |
| **Key Types** | `BaseProvider` (ABC), `ModelCapability` (enum), `ModelInfo`, `GenerationConfig`, `GenerationResult` |
| **Input** | N/A (abstract definitions) |
| **Output** | N/A (abstract definitions) |
| **Dependencies** | None (stdlib only: `abc`, `dataclasses`, `enum`) |

`BaseProvider` declares four abstract methods: `default_model()`, `available_models()`, `generate()`, and `generate_structured()`. It also provides concrete methods: `supports(capability)`, `upload_file(file_path)`, and `model_info()`.

`ModelCapability` enumerates seven capabilities: `TEXT_GENERATION`, `VISION`, `LONG_CONTEXT`, `STRUCTURED_OUTPUT`, `CODE_GENERATION`, `FILE_UPLOAD`, `STREAMING`.

#### `providers/registry.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Factory for creating providers by name; auto-detection of available providers; capability-based provider selection; cost estimation |
| **Key Types** | `ProviderRegistry` (static methods), `get_provider()` convenience function |
| **Input** | Provider name (str), optional API key, optional model name, optional required capability |
| **Output** | `BaseProvider` instance |
| **Dependencies** | `providers/base.py`, `importlib` (for lazy provider loading) |

The registry uses a `_PROVIDER_MAP` dict to map provider names to `(module_path, class_name)` tuples. `create()` uses `importlib.import_module()` for dynamic instantiation. `detect_available()` checks environment variables (and Ollama reachability) to determine which providers are configured. `best_for(capability)` returns the first available provider from a per-capability preference order.

#### `providers/gemini.py`, `openai_provider.py`, `anthropic_provider.py`, `ollama.py`

Each file implements `BaseProvider` for its respective LLM backend. They are imported only via `importlib` from the registry, never directly by pipeline modules.

#### `config.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Global configuration dataclass with environment variable overrides |
| **Key Types** | `R2RConfig` (18-field dataclass) |
| **Input** | Environment variables (`R2R_PROVIDER`, `R2R_MODEL`, `R2R_SKIP_VALIDATION`, etc.) |
| **Output** | `R2RConfig` instance |
| **Dependencies** | `os`, `dataclasses` |

### 2.2 Core Processing Layer

#### `core/paper_parser.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Multi-backend PDF parsing with graceful fallback chain |
| **Key Types** | `PaperParser`, `ParsedPaper` |
| **Input** | PDF file path |
| **Output** | `ParsedPaper` (title, authors, abstract, sections, figures, tables, equations, references, full_text) |
| **Dependencies** | Optional: `doc2json`, `requests` (GROBID), `fitz` (PyMuPDF), `PyPDF2` |
| **Integration** | Standalone utility; not directly called by the standard pipeline (the analyzer handles its own text extraction), but available for advanced use |

Backend priority: `doc2json` > `GROBID` > `PyMuPDF` > `PyPDF2`. Each backend is tried in order; `ImportError` and `ConnectionError` cause fallback to the next.

#### `core/analyzer.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Ingest PDF, extract text/diagrams, produce structured analysis via LLM |
| **Key Types** | `PaperAnalyzer`, `PaperAnalysis` |
| **Input** | PDF file path (via `upload_document`) |
| **Output** | `PaperAnalysis` dataclass with 13 fields |
| **Dependencies** | `providers/base.py`, `providers/__init__.py`, optional `PyPDF2`, optional `fitz` |
| **Integration** | First processing stage in both pipelines; output consumed by all downstream modules |

Strategy selection within the analyzer:
- Provider supports `FILE_UPLOAD` (Gemini): upload raw PDF for zero-RAG analysis
- Otherwise: extract text with `PyPDF2` and include in prompt
- Provider supports `VISION`: extract page images with `PyMuPDF`, send in batches of 4 for diagram-to-Mermaid conversion

#### `core/architect.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Design repository structure, file list, dependency graph, requirements |
| **Key Types** | `SystemArchitect`, `ArchitecturePlan`, `FileSpec` |
| **Input** | `PaperAnalysis`, optional document handle, optional vision context |
| **Output** | `ArchitecturePlan` with sorted `FileSpec` list, requirements, directory tree |
| **Dependencies** | `providers/base.py`, `providers/__init__.py`, `core/analyzer.py` |
| **Integration** | Used as fallback planner in agent mode; primary planner in classic mode |

After LLM generation, `_ensure_essentials()` guarantees that `config.yaml`, `README.md`, and `requirements.txt` are always in the file list. Files are sorted by priority (lower number = generated first).

#### `core/planner.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | 4-stage decomposed planning (Overall Plan, Architecture Design, Logic Design, Config Generation) |
| **Key Types** | `DecomposedPlanner`, `PlanningResult`, `OverallPlan`, `ArchitectureDesign`, `LogicDesign` |
| **Input** | `PaperAnalysis`, document handle, vision context |
| **Output** | `PlanningResult` wrapping all 4 sub-stages + backward-compatible `ArchitecturePlan` |
| **Dependencies** | `providers/base.py`, `providers/__init__.py`, `core/analyzer.py`, `core/architect.py` |
| **Integration** | Primary planner in agent mode (Stage 2); each sub-stage feeds context to the next |

The 4 sub-stages build progressively:
1. **Overall Plan**: extracts core components, methods, training objectives, data steps, evaluation protocols
2. **Architecture Design**: produces file list with Mermaid class and sequence diagrams
3. **Logic Design**: determines dependency graph, topological execution order, per-file logic
4. **Config Generation**: produces YAML config from hyperparameters + all prior context

#### `core/file_analyzer.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Generate detailed per-file specifications before code synthesis |
| **Key Types** | `FileAnalyzer`, `FileAnalysis` |
| **Input** | `ArchitecturePlan`, `PaperAnalysis` |
| **Output** | `dict[str, FileAnalysis]` mapping file paths to specifications |
| **Dependencies** | `providers/base.py`, `providers/__init__.py`, `core/analyzer.py`, `core/architect.py` |
| **Integration** | Agent mode Stage 3; output provides detailed specs for the code synthesizer |

Key design: files are analyzed in priority order, and each subsequent file receives the analyses of all preceding files as context. This ensures cross-file consistency (e.g., a training script knows the exact method signatures of the model it imports).

#### `core/coder.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Generate source code for each file in the architecture plan |
| **Key Types** | `CodeSynthesizer` |
| **Input** | `PaperAnalysis`, `ArchitecturePlan`, optional document handle |
| **Output** | `dict[str, str]` mapping file paths to generated content |
| **Dependencies** | `providers/base.py`, `providers/__init__.py`, `core/analyzer.py`, `core/architect.py` |
| **Integration** | Core generation stage in both pipelines |

Files are generated one at a time in dependency order. Each file generation includes:
- Paper context (equations, hyperparams, architecture description, Mermaid diagrams)
- Previously generated dependency files (direct dependencies + rolling window of last 3 files)
- File-specific instructions (path, description, requirements)

Output cleaning strips markdown fences and leading non-code lines from Python files. Token limits are adaptive: 16,384 for model/training files, 4,096 for config/docs.

#### `core/validator.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Validate generated code against the paper; auto-fix critical issues |
| **Key Types** | `CodeValidator`, `ValidationReport`, `ValidationIssue` |
| **Input** | `dict[str, str]` (generated files), `PaperAnalysis`, `ArchitecturePlan` |
| **Output** | `ValidationReport` (score 0-100, equation/hyperparam coverage, issues list) |
| **Dependencies** | `providers/base.py`, `providers/__init__.py`, `core/analyzer.py`, `core/architect.py` |
| **Integration** | Validation + auto-fix stages in both pipelines |

Validation checks: equation fidelity, dimension consistency, hyperparameter completeness, loss function accuracy, code quality. `fix_issues()` groups critical issues by file, sends each file + its issues to the LLM for correction, and returns the updated file dict. The caller (orchestrator) re-validates after each fix iteration.

#### `core/refiner.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | General-purpose verify-then-refine loops for any pipeline artifact |
| **Key Types** | `SelfRefiner`, `RefinementResult` |
| **Input** | Any artifact (dict, dataclass, or string), artifact type label, paper context |
| **Output** | `RefinementResult` (original, refined, critique, improvements, iteration count) |
| **Dependencies** | `providers/base.py`, `providers/__init__.py` |
| **Integration** | Optional refinement in agent mode after planning and file analysis stages |

Artifact types: `overall_plan`, `architecture_design`, `logic_design`, `file_analysis` (JSON); `config`, `code` (text). The loop: verify (produce critique + issues) -> if issues exist, refine -> repeat up to `max_iterations`. Stops early if verification finds no issues.

### 2.3 Advanced Services Layer

#### `advanced/executor.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Execute generated repositories in Docker or local subprocess sandbox |
| **Key Types** | `ExecutionSandbox`, `ExecutionResult` |
| **Input** | Repository directory path, entrypoint script name |
| **Output** | `ExecutionResult` (success, stdout, stderr, exit code, error type, duration, modified files) |
| **Dependencies** | `subprocess`, `shutil`, `os` (no LLM dependency) |
| **Integration** | Agent mode Stage 7; provides execution results to AutoDebugger |

Docker mode: generates a `Dockerfile` if missing, builds an image, runs with resource limits (`--memory 8g --cpus 4`). Falls back to local `subprocess.run()` if Docker is unavailable. Error classification via regex matching on stderr (22 known error patterns).

#### `advanced/debugger.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | LLM-assisted iterative debugging of execution failures |
| **Key Types** | `AutoDebugger`, `DebugFix`, `DebugReport` |
| **Input** | Repository directory, `ExecutionResult`, `dict[str, str]` (generated files) |
| **Output** | `(updated_files, list[DebugReport])` |
| **Dependencies** | `providers/base.py`, `providers/__init__.py`, `advanced/executor.py` |
| **Integration** | Agent mode Stage 7 (paired with ExecutionSandbox) |

Debug loop per iteration: (1) analyze error with LLM, narrowing to files mentioned in the traceback; (2) parse fix suggestions; (3) apply fixes to in-memory file dict; (4) write to disk; (5) re-execute. Loop continues until success or `max_iterations` reached.

#### `advanced/evaluator.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Score generated code against reference implementation and/or paper |
| **Key Types** | `ReferenceEvaluator`, `EvaluationScore` |
| **Input** | Generated files, optional reference directory, paper text |
| **Output** | `EvaluationScore` (1-5 overall, per-component scores, coverage, missing/extra components) |
| **Dependencies** | `providers/base.py`, `providers/__init__.py` |
| **Integration** | Agent mode Stage 9 (optional, requires `--evaluate`) |

Two modes: **with reference** (compares against a known-good implementation file by file) and **without reference** (uses only the paper to check component coverage). Runs `num_samples` (default 3) independent LLM evaluations and averages the scores for robustness.

#### `advanced/devops.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Generate production infrastructure files |
| **Key Types** | `DevOpsGenerator` |
| **Input** | `ArchitecturePlan`, `PaperAnalysis`, generated files dict |
| **Output** | `dict[str, str]` with 5 files: `Dockerfile`, `docker-compose.yml`, `Makefile`, `.github/workflows/ci.yml`, `setup.py` |
| **Dependencies** | `providers/__init__.py`, `providers/base.py` |
| **Integration** | Agent mode Stage 8 (enabled by default, disabled with `--no-devops`) |

Uses deterministic templates (not LLM-generated) with context-aware parameters extracted from the plan (Python version, requirements, entrypoints, GPU detection).

#### `advanced/equation_extractor.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Extract all mathematical equations and convert to LaTeX + PyTorch pseudocode |
| **Key Types** | `EquationExtractor`, `ExtractedEquation` |
| **Input** | Paper text (string) or page images (bytes) |
| **Output** | `list[ExtractedEquation]` with LaTeX, PyTorch code, variables, category |
| **Dependencies** | `providers/base.py`, `providers/__init__.py` |
| **Integration** | Classic mode Stage 3; results merged into `PaperAnalysis.equations` |

#### `advanced/config_generator.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Generate structured YAML config from paper hyperparameters |
| **Key Types** | `ConfigGenerator` |
| **Input** | `PaperAnalysis` |
| **Output** | YAML string content |
| **Dependencies** | `providers/base.py`, `providers/__init__.py`, `core/analyzer.py`, `pyyaml` |
| **Integration** | Classic mode Stage 5; also used as planner Step 4 in agent mode |

Groups hyperparameters into sections: model, training, data, regularization, infrastructure. Validates output with `yaml.safe_load()`; falls back to a deterministic template if LLM output is invalid YAML.

#### `advanced/test_generator.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Auto-generate pytest test suites for generated code |
| **Key Types** | `TestGenerator` |
| **Input** | Generated files dict, `PaperAnalysis`, `ArchitecturePlan` |
| **Output** | `dict[str, str]` mapping test file paths to content |
| **Dependencies** | `providers/base.py`, `providers/__init__.py`, `core/analyzer.py`, `core/architect.py` |
| **Integration** | Both pipelines (Stage 7 classic, Stage 5 agent) |

Generates separate test files for: model dimension/forward-pass tests, loss function tests, config validation tests, and integration tests.

#### `advanced/cache.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Content-addressed file-system cache for expensive pipeline operations |
| **Key Types** | `PipelineCache` |
| **Input** | PDF file path (used to compute SHA-256 hash key) |
| **Output** | Cached objects (analysis, architecture, generated files, validation, metadata) |
| **Dependencies** | `hashlib`, `json`, `pickle`, `pathlib` (no LLM dependency) |
| **Integration** | Classic mode (used at stages 2, 4, 6, 8-10); keyed on first 16 hex chars of PDF SHA-256 |

### 2.4 Agents Layer

#### `agents/base.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Abstract base class for pipeline agents with message-passing support |
| **Key Types** | `BaseAgent` (ABC), `AgentMessage` |
| **Input** | Agent name, optional provider |
| **Output** | Abstract `execute()` method; `communicate()` for inter-agent messages |
| **Dependencies** | `providers/__init__.py`, `providers/base.py` |
| **Integration** | Foundation for the agent system; `AgentOrchestrator` inherits the pattern |

#### `agents/orchestrator.py`

| Attribute | Detail |
|---|---|
| **Responsibility** | Master controller that coordinates all 10 agent pipeline stages |
| **Key Types** | `AgentOrchestrator` |
| **Input** | `BaseProvider`, config dict, PDF path, output directory |
| **Output** | Result dict with `files`, `plan`, `analysis`, `validation_report`, `execution_result`, `evaluation_score`, `metadata` |
| **Dependencies** | `providers/__init__.py`, `providers/base.py` (all other imports are lazy) |
| **Integration** | Called by `run_agent()` in `main.py` |

---

## 3. Pipeline Architecture

### 3.1 Classic Mode (10 Stages)

The classic pipeline is implemented as a single function `run_classic()` in `main.py`. It is the v2.0-compatible linear pipeline.

| Stage | Name | Module | Input | Output |
|---|---|---|---|---|
| 1 | Download PDF | `main.py::download_pdf()` | PDF URL | `source_paper.pdf` on disk |
| 2 | Analyze Paper | `PaperAnalyzer.analyze()` | PDF file path | `PaperAnalysis` |
| 3 | Extract Equations | `EquationExtractor.extract()` | Paper text from analysis | `list[ExtractedEquation]` (merged into analysis) |
| 4 | Architect Repository | `SystemArchitect.design_system()` | `PaperAnalysis`, document, diagrams | `ArchitecturePlan` |
| 5 | Generate Config | `ConfigGenerator.generate()` | `PaperAnalysis` | YAML string |
| 6 | Synthesize Code | `CodeSynthesizer.generate_codebase()` | `PaperAnalysis`, `ArchitecturePlan`, document | `dict[str, str]` |
| 7 | Generate Tests | `TestGenerator.generate_tests()` | Generated files, analysis, plan | `dict[str, str]` (merged) |
| 8 | Validate | `CodeValidator.validate()` | Generated files, analysis, plan | `ValidationReport` |
| 9 | Auto-Fix | `CodeValidator.fix_issues()` (loop) | Generated files, report, analysis | Updated `dict[str, str]` |
| 10 | Save Repository | File write loop | Generated files, output dir | Files on disk + `.r2r_metadata.json` |

**Stage interactions:**

```
Stage 1 ─> Stage 2 ─> Stage 3 ─> Stage 4 ─> Stage 5
  PDF        analysis    merged     plan       config.yaml
  file                   equations              (injected
                                                 into files)
                                       |
                                       v
                              Stage 6 ─> Stage 7 ─> Stage 8
                              code gen    test gen    validate
                                                       |
                                                       v
                                              Stage 9 ─> Stage 10
                                              auto-fix    save
                                              (loop)
```

Cacheable stages: 2 (analysis), 4 (architecture), 6 (generated files). Cache hits skip the LLM call entirely.

Skippable stages: 3 (`--skip-equations`), 7 (`--skip-tests`), 8-9 (`--skip-validation`).

### 3.2 Agent Mode (10 Stages)

The agent pipeline is implemented in `AgentOrchestrator.run()` with each stage delegated to a private `_stage_*` method.

| Stage | Name | Module(s) | Input | Output | Optional? |
|---|---|---|---|---|---|
| 1 | Parse Paper | `PaperAnalyzer` | PDF path | `PaperAnalysis`, document, vision context | No |
| 2 | Planning | `DecomposedPlanner` (4 sub-stages) + optional `SelfRefiner` | Analysis, document, vision context | `ArchitecturePlan` (via `PlanningResult`) | No |
| 3 | Per-File Analysis | `FileAnalyzer` + optional `SelfRefiner` | Plan, analysis | `dict[str, FileAnalysis]` | No |
| 4 | Code Generation | `CodeSynthesizer` | Analysis, plan, document | `dict[str, str]` | No |
| 5 | Test Generation | `TestGenerator` | Generated files, analysis, plan | `dict[str, str]` (merged) | Yes (`--no-tests`) |
| 6 | Validation + Auto-Fix | `CodeValidator` (validate + fix loop) | Generated files, analysis, plan | Updated files + `ValidationReport` | No |
| 7 | Execution + Auto-Debug | `ExecutionSandbox` + `AutoDebugger` (loop) | Generated files, output dir, plan, analysis | Updated files + `ExecutionResult` | Yes (`--execute`) |
| 8 | DevOps Generation | `DevOpsGenerator` | Plan, analysis, generated files | `dict[str, str]` (merged) | Yes (`--no-devops`) |
| 9 | Evaluation | `ReferenceEvaluator` | Generated files, reference dir | `EvaluationScore` | Yes (`--evaluate`) |
| 10 | Save Repository | `_stage_save()` | Generated files, output dir | Files on disk + `.r2r_metadata.json` | No |

**Agent mode sub-stages within Stage 2 (Planning):**

```
PaperAnalysis
     |
     v
+----+------------------------------------------+
| Step 1: Overall Plan                          |
|   -> core_components, methods, training_obj,  |
|      data_steps, eval_protocols, summary      |
+----+------------------------------------------+
     |
     v  (fed as context)
+----+------------------------------------------+
| Step 2: Architecture Design                   |
|   -> file_list, class_diagram_mermaid,        |
|      sequence_diagram_mermaid,                |
|      module_relationships                     |
+----+------------------------------------------+
     |
     v  (fed as context)
+----+------------------------------------------+
| Step 3: Logic Design                          |
|   -> execution_order, dependency_graph,       |
|      file_specifications (per-file logic)     |
+----+------------------------------------------+
     |
     v  (fed as context)
+----+------------------------------------------+
| Step 4: Config Generation                     |
|   -> YAML config string                       |
+----+------------------------------------------+
     |
     v
PlanningResult (wraps all 4 + ArchitecturePlan)
     |
     v  (if --refine)
SelfRefiner verify/refine loop
     |
     v
Final ArchitecturePlan
```

**Interactive gate:** After Stage 2, if `--interactive` is set, the orchestrator displays the planned architecture (directory tree, file list, dependency count) and waits for user confirmation. The user can press Enter to continue or `q` to abort.

---

## 4. Integration Points

### 4.1 LLM Provider Integration

**API Key Discovery:**

| Provider | Environment Variable | Fallback |
|---|---|---|
| Gemini | `GEMINI_API_KEY` | -- |
| OpenAI | `OPENAI_API_KEY` | -- |
| Anthropic | `ANTHROPIC_API_KEY` | -- |
| Ollama | (none) | Probes `http://localhost:11434/api/tags` |

**Provider Selection Priority:**

1. Explicit CLI flag: `--provider gemini --model gemini-2.5-pro-preview-05-06`
2. Auto-detection with capability routing: `get_provider(required_capability=ModelCapability.VISION)` returns the best available provider for that capability
3. Fallback ordering: uses the first available provider from `detect_available()` (which checks env vars in registration order: gemini, openai, anthropic, ollama)

**Capability-Based Preference Orders:**

| Capability | Preference Order |
|---|---|
| `LONG_CONTEXT` | gemini > anthropic > openai > ollama |
| `VISION` | gemini > openai > anthropic > ollama |
| `CODE_GENERATION` | anthropic > openai > gemini > ollama |
| `STRUCTURED_OUTPUT` | openai > gemini > anthropic > ollama |
| `FILE_UPLOAD` | gemini (only) |

**Cost Estimation:**

```python
ProviderRegistry.estimate_cost(
    provider_name="openai",
    model_name="gpt-4o",
    input_tokens=50000,
    output_tokens=8000,
)  # Returns estimated USD cost
```

Each `ModelInfo` includes `cost_per_1k_input` and `cost_per_1k_output` fields.

### 4.2 File System Integration

**Input paths:**

| Path | Purpose | Created By |
|---|---|---|
| `{output_dir}/source_paper.pdf` | Downloaded PDF | `download_pdf()` |

**Output paths:**

| Path | Purpose | Created By |
|---|---|---|
| `{output_dir}/` | Root of generated repository | Orchestrator / `run_classic` |
| `{output_dir}/<generated files>` | Model code, training scripts, configs, tests | `CodeSynthesizer`, `TestGenerator`, `DevOpsGenerator` |
| `{output_dir}/.r2r_metadata.json` | Run provenance (provider, model, timing, file count) | Orchestrator |
| `.r2r_cache/{hash}/` | Cached pipeline artifacts | `PipelineCache` |

### 4.3 Docker Integration

The `ExecutionSandbox` integrates with Docker as follows:

1. **Check availability:** `shutil.which("docker")` -- falls back to local execution if missing
2. **Generate Dockerfile:** If not present, creates a minimal `python:3.10-slim` based Dockerfile
3. **Build image:** `docker build -t r2r-sandbox:{repo_name} .` (10-minute timeout)
4. **Run container:** `docker run --rm --memory 8g --cpus 4 [--gpus all] {image} python {entrypoint}`
5. **Capture output:** stdout, stderr, exit code, duration
6. **Error classification:** Regex-based matching of 22 known Python error patterns in stderr

### 4.4 External Services (GROBID)

The `PaperParser` optionally connects to a GROBID server:

- Default URL: `http://localhost:8070/api/processFulltextDocument`
- Override via: `GROBID_URL` environment variable
- Protocol: POST multipart/form-data with the PDF file
- Response: TEI XML parsed with `xml.etree.ElementTree`
- Timeout: 120 seconds
- Fallback: If GROBID is unreachable, the parser falls to PyMuPDF or PyPDF2

---

## 5. Configuration Management

### 5.1 R2RConfig Dataclass

The `R2RConfig` dataclass in `config.py` holds 18 configuration fields organized into 6 groups:

```python
@dataclass
class R2RConfig:
    # Provider defaults
    default_provider: str = "auto"      # auto, gemini, openai, anthropic, ollama
    default_model: str = ""             # Empty = use provider default

    # Pipeline toggles
    enable_validation: bool = True
    enable_test_generation: bool = True
    enable_equation_extraction: bool = True
    enable_caching: bool = True
    max_fix_iterations: int = 2

    # Download settings
    pdf_timeout: int = 120              # seconds
    pdf_max_size_mb: int = 100

    # Generation settings
    code_temperature: float = 0.15
    analysis_temperature: float = 0.1
    max_code_tokens: int = 16384
    max_analysis_tokens: int = 8192

    # Vision settings
    max_diagram_pages: int = 30
    diagram_dpi: int = 150
    vision_batch_size: int = 4

    # Cache settings
    cache_dir: str = ".r2r_cache"

    # Output settings
    verbose: bool = False
```

### 5.2 Environment Variable Overrides

`R2RConfig.from_env()` reads these environment variables:

| Environment Variable | Config Field | Default |
|---|---|---|
| `R2R_PROVIDER` | `default_provider` | `"auto"` |
| `R2R_MODEL` | `default_model` | `""` |
| `R2R_SKIP_VALIDATION` | `enable_validation` (inverted) | `True` |
| `R2R_SKIP_TESTS` | `enable_test_generation` (inverted) | `True` |
| `R2R_NO_CACHE` | `enable_caching` (inverted) | `True` |
| `R2R_CACHE_DIR` | `cache_dir` | `".r2r_cache"` |
| `R2R_VERBOSE` | `verbose` | `False` |

### 5.3 CLI Argument Hierarchy

Configuration values are resolved in this priority order (highest wins):

```
CLI arguments (--provider, --model, --skip-validation, etc.)
    |
    v  (overrides)
Environment variables (R2R_PROVIDER, R2R_MODEL, etc.)
    |
    v  (overrides)
R2RConfig defaults (hardcoded in dataclass)
```

In practice, the current `main.py` reads CLI args via `argparse` and passes them directly to `run_classic()` or `run_agent()`. The `R2RConfig` dataclass exists for programmatic use but is not yet wired into the CLI flow (this is by design -- CLI args take precedence).

### 5.4 Agent Mode Configuration

The `AgentOrchestrator` uses its own config dict, merged from `_DEFAULT_CONFIG` and caller overrides:

```python
_DEFAULT_CONFIG = {
    "enable_refine": False,         # --refine
    "enable_execution": False,      # --execute
    "enable_tests": True,           # --no-tests (inverted)
    "enable_evaluation": False,     # --evaluate
    "enable_devops": True,          # --no-devops (inverted)
    "interactive": False,           # --interactive
    "max_debug_iterations": 3,      # --max-debug-iterations
    "max_refine_iterations": 2,     # --max-refine-iterations
    "max_fix_iterations": 2,        # --max-fix-iterations
    "reference_dir": None,          # --reference-dir
    "verbose": False,               # --verbose
}
```

The `run_agent()` function in `main.py` constructs a config dict from CLI args and passes it to `AgentOrchestrator.__init__()`, which merges it with `_DEFAULT_CONFIG` via `_merge_config()`.

---

## 6. Error Handling Strategy

### 6.1 Provider Fallback Chains

Multiple levels of fallback ensure the system works even when preferred providers or features are unavailable:

**Provider selection fallback:**

```
User-specified provider (--provider)
    |
    v  (if not specified)
Capability-matched provider (best_for(capability))
    |
    v  (if no match)
First available provider (detect_available()[0])
    |
    v  (if none available)
RuntimeError("No model providers available")
```

**Within-provider fallback (analyzer vision):**

```
Explicit vision_provider argument
    |
    v  (if not provided)
Primary provider (if it supports VISION)
    |
    v  (if primary lacks VISION)
Auto-detect best VISION provider
    |
    v  (if no VISION provider available)
Skip diagram extraction (return [])
```

### 6.2 Graceful ImportError Handling

All optional module imports in the orchestrator are wrapped:

```python
try:
    from core.planner import DecomposedPlanner
    # ... use planner
except ImportError:
    print("DecomposedPlanner not available, falling back to SystemArchitect.")
    from core.architect import SystemArchitect
    # ... use architect
```

This pattern appears for:
- `DecomposedPlanner` (falls back to `SystemArchitect`)
- `ExecutionSandbox` + `AutoDebugger` (skips execution stage)
- `DevOpsGenerator` (skips DevOps stage)
- `ReferenceEvaluator` (skips evaluation stage)
- `SelfRefiner` (returns artifact unchanged)

### 6.3 Auto-Fix Loop for Validation Failures

Both pipelines implement the same pattern:

```
generated_files, analysis, plan
        |
        v
CodeValidator.validate() -> report
        |
        v
while report.critical_count > 0 AND iteration < max_fix_iterations:
    |
    v
    CodeValidator.fix_issues(files, report, analysis) -> updated_files
    CodeValidator.validate(updated_files, analysis, plan) -> new_report
    report = new_report
    iteration += 1
        |
        v
Return (updated_files, final_report)
```

Default `max_fix_iterations` is 2. Each iteration sends critical issues grouped by file to the LLM, receives corrected file contents, and re-validates.

### 6.4 Auto-Debug Loop for Execution Failures

Agent mode Stage 7:

```
generated_files, output_dir, plan
        |
        v
ExecutionSandbox.execute() -> exec_result
        |
        v
while NOT exec_result.success AND iteration < max_debug_iterations:
    |
    v
    AutoDebugger._analyze_error(stderr, error_type, files)
        |
        v
    _find_relevant_files() -> subset of files mentioned in traceback
        |
        v
    LLM generates DebugFix objects (file_path, fixed_content)
        |
        v
    Apply fixes to in-memory dict + write to disk
        |
        v
    ExecutionSandbox.execute() -> new_exec_result
    exec_result = new_exec_result
    iteration += 1
        |
        v
Return (updated_files, exec_result)
```

Default `max_debug_iterations` is 3. The debugger narrows context by parsing `File "..."` references from the traceback and only sending relevant source files to the LLM.

### 6.5 Fallback JSON Parsing

Every module that expects JSON from the LLM implements the same multi-stage parsing:

```
1. Try generate_structured(prompt, schema)
   |
   v (if exception)
2. Fallback: generate(prompt + "Respond with ONLY a JSON object.")
   |
   v
3. Clean text: strip markdown fences (```json ... ```)
   |
   v
4. json.loads(cleaned_text)
   |
   v (if JSONDecodeError in some modules)
5. Return empty dict / default structure
```

This three-tier approach (structured -> text with JSON instruction -> clean and parse) ensures the pipeline rarely fails due to LLM output format issues.

---

## 7. Sequence Diagrams

### 7.1 Classic Pipeline End-to-End

```
User                 main.py            Providers    Core Modules     Advanced Modules    Disk
 |                     |                    |             |                 |               |
 |--pdf_url, args----->|                    |             |                 |               |
 |                     |                    |             |                 |               |
 |                     |--get_provider()--->|             |                 |               |
 |                     |<--provider---------|             |                 |               |
 |                     |                    |             |                 |               |
 |                     |--download_pdf()-----------------------------------+-------------->|
 |                     |<--pdf_path-----------------------------------------+--------------|
 |                     |                    |             |                 |               |
 |                     |--[cache check]-----|-------------|---------------->|               |
 |                     |                    |             |                 |               |
 |          [Stage 2]  |--PaperAnalyzer-----|------------>|                 |               |
 |                     |  .upload_document()|             |                 |               |
 |                     |  .analyze()------->|--generate-->|                 |               |
 |                     |<--PaperAnalysis----|-------------|                 |               |
 |                     |                    |             |                 |               |
 |          [Stage 3]  |--EquationExtractor-|-------------|---------------->|               |
 |                     |  .extract()------->|--generate-->|                 |               |
 |                     |<--equations--------|-------------|-----------------|               |
 |                     |                    |             |                 |               |
 |          [Stage 4]  |--SystemArchitect---|------------>|                 |               |
 |                     |  .design_system()--|--generate-->|                 |               |
 |                     |<--ArchitecturePlan-|-------------|                 |               |
 |                     |                    |             |                 |               |
 |          [Stage 5]  |--ConfigGenerator---|-------------|---------------->|               |
 |                     |  .generate()------>|--generate-->|                 |               |
 |                     |<--YAML string------|-------------|-----------------|               |
 |                     |                    |             |                 |               |
 |          [Stage 6]  |--CodeSynthesizer---|------------>|                 |               |
 |                     |  .generate_code()--|--generate-->|(per file, loop) |               |
 |                     |<--dict[str,str]----|-------------|                 |               |
 |                     |                    |             |                 |               |
 |          [Stage 7]  |--TestGenerator-----|-------------|---------------->|               |
 |                     |  .generate_tests()->|--generate->|                 |               |
 |                     |<--test files-------|-------------|-----------------|               |
 |                     |                    |             |                 |               |
 |          [Stage 8]  |--CodeValidator-----|------------>|                 |               |
 |                     |  .validate()------>|--generate-->|                 |               |
 |                     |<--ValidationReport-|-------------|                 |               |
 |                     |                    |             |                 |               |
 |          [Stage 9]  |  LOOP (max 2 iter):|             |                 |               |
 |                     |--fix_issues()----->|--generate-->|                 |               |
 |                     |--validate()------->|--generate-->|                 |               |
 |                     |<--updated report---|-------------|                 |               |
 |                     |                    |             |                 |               |
 |          [Stage 10] |--write files--------------------------------------+-------------->|
 |                     |--write metadata-----------------------------------+-------------->|
 |                     |                    |             |                 |               |
 |<--PIPELINE COMPLETE-|                    |             |                 |               |
```

### 7.2 Agent Pipeline with Self-Refine

```
User        main.py     Orchestrator    Providers    Core      Advanced     Disk
 |            |              |              |          |           |          |
 |--args----->|              |              |          |           |          |
 |            |--run_agent-->|              |          |           |          |
 |            |              |--get_prov.-->|          |           |          |
 |            |              |<-provider----|          |           |          |
 |            |              |              |          |           |          |
 |            |              |--download_pdf()--------|-----------|--------->|
 |            |              |              |          |           |          |
 |  [S1]      |              |--_stage_parse_paper()-->|           |          |
 |            |              |  PaperAnalyzer.analyze->|--gen----->|          |
 |            |              |<--analysis,doc,vision---|           |          |
 |            |              |              |          |           |          |
 |  [S2]      |              |--_stage_plan()--------->|           |          |
 |            |              |  DecomposedPlanner:     |           |          |
 |            |              |    step1(overall)------>|--gen----->|          |
 |            |              |    step2(arch_design)-->|--gen----->|          |
 |            |              |    step3(logic_design)->|--gen----->|          |
 |            |              |    step4(config)------->|--gen----->|          |
 |            |              |<--PlanningResult--------|           |          |
 |            |              |              |          |           |          |
 |            |              |  if --refine:|          |           |          |
 |            |              |--_refine_output()------>|           |          |
 |            |              |  SelfRefiner.verify()--->|--gen---->|          |
 |            |              |  SelfRefiner.refine()--->|--gen---->|          |
 |            |              |<--refined plan----------|           |          |
 |            |              |              |          |           |          |
 |            |              |  if --interactive:      |           |          |
 |            |              |--display plan---------->|           |          |
 |<-----------+--------------+--"Press Enter or q"----|-----------|----------|
 |--Enter---->|              |              |          |           |          |
 |            |              |              |          |           |          |
 |  [S3]      |              |--_stage_file_analysis-->|           |          |
 |            |              |  FileAnalyzer.analyze_all (per file, with     |
 |            |              |    accumulated context)->|--gen---->|          |
 |            |              |<--file_analyses---------|           |          |
 |            |              |              |          |           |          |
 |            |              |  if --refine:|          |           |          |
 |            |              |--_refine_output()------>|           |          |
 |            |              |<--refined analyses------|           |          |
 |            |              |              |          |           |          |
 |  [S4]      |              |--_stage_code_generation>|           |          |
 |            |              |  CodeSynthesizer (loop)->|--gen--->|          |
 |            |              |<--generated_files-------|           |          |
 |            |              |              |          |           |          |
 |  [S5]      |              |--_stage_test_generation>|---------->|          |
 |            |              |  TestGenerator.gen_tests>|--gen--->|           |
 |            |              |<--test_files------------|-----------|          |
 |            |              |              |          |           |          |
 |  [S6]      |              |--_stage_validation()--->|           |          |
 |            |              |  CodeValidator.validate->|--gen--->|           |
 |            |              |  LOOP: fix_issues()---->|--gen--->|           |
 |            |              |<--files, report---------|           |          |
 |            |              |              |          |           |          |
 |  [S7]      |              |--_stage_execution()-----|---------->|          |
 |  (optional)|              |  ExecutionSandbox.exec->|---------->|--------->|
 |            |              |  LOOP: AutoDebugger.--->|--gen---->|           |
 |            |              |         re-execute----->|---------->|--------->|
 |            |              |<--files, exec_result----|-----------|          |
 |            |              |              |          |           |          |
 |  [S8]      |              |--_stage_devops()--------|---------->|          |
 |            |              |  DevOpsGenerator.gen_all>|          |          |
 |            |              |<--devops_files-----------|----------|          |
 |            |              |              |          |           |          |
 |  [S9]      |              |--_stage_evaluation()-----|--------->|          |
 |  (optional)|              |  ReferenceEvaluator.eval>|--gen--->|          |
 |            |              |<--EvaluationScore---------|---------|          |
 |            |              |              |          |           |          |
 |  [S10]     |              |--_stage_save()-----------|---------|--------->|
 |            |              |--write metadata-----------|---------|--------->|
 |            |              |              |          |           |          |
 |<--result---+--------------+              |          |           |          |
```

### 7.3 Provider Selection Flow

```
get_provider(provider_name, model_name, api_key, required_capability)
    |
    v
provider_name specified?
    |            |
   Yes          No
    |            |
    v            v
Registry     required_capability specified?
.create()        |              |
    |           Yes             No
    |            |              |
    v            v              v
  Return    best_for()     detect_available()
  provider   |              |
             v              v
         provider_name    available = [list of providers with env vars]
         found?            |
          |    |           v
         Yes   No       available is empty?
          |    |          |         |
          v    v         Yes        No
       Registry  try     RuntimeError  Registry.create(available[0])
       .create() next       |              |
          |     in list     v              v
          v                 ERROR        Return provider
       Return
       provider
```

### 7.4 Auto-Debug Loop

```
AgentOrchestrator._stage_execution()
    |
    v
ExecutionSandbox.execute(files, output_dir, entrypoint)
    |
    v
exec_result = ExecutionResult(success=?, stderr=?, error_type=?)
    |
    v
+-- exec_result.success == True? ----> Return (files, exec_result)
|
No
|
v
iteration = 0
|
v
+----------- LOOP: iteration < max_debug_iterations --------+
|                                                             |
|  iteration += 1                                             |
|  |                                                          |
|  v                                                          |
|  AutoDebugger._analyze_error(stderr, error_type, files)     |
|  |                                                          |
|  v                                                          |
|  _find_relevant_files(stderr, all_files)                    |
|   -> Parse "File ..." from traceback                        |
|   -> Return matching subset of files                        |
|  |                                                          |
|  v                                                          |
|  _build_debug_prompt(error_msg, error_type, focused_files)  |
|  |                                                          |
|  v                                                          |
|  LLM.generate_structured(prompt, debug_schema)              |
|   -> {fixes: [{file_path, fixed_content, descriptions}]}   |
|  |                                                          |
|  v                                                          |
|  _parse_fixes() -> list[DebugFix]                           |
|  |                                                          |
|  v                                                          |
|  No fixes? -----> Break loop                                |
|  |                                                          |
|  Has fixes                                                  |
|  |                                                          |
|  v                                                          |
|  _apply_fixes(files, fixes) -> updated_files                |
|  Write updated files to disk                                |
|  |                                                          |
|  v                                                          |
|  ExecutionSandbox.execute(repo_dir) -> new_exec_result      |
|  |                                                          |
|  v                                                          |
|  new_exec_result.success == True? ----> Break loop          |
|  |                                                          |
|  No -> continue loop                                        |
|                                                             |
+-------------------------------------------------------------+
    |
    v
Return (updated_files, final_exec_result)
```

---

*Last updated: This document reflects the Research2Repo v3.0 codebase.*
