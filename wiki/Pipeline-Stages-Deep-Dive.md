# Pipeline Stages Deep Dive

This document provides a detailed walkthrough of every pipeline stage in Research2Repo v3.0, covering both **Classic Mode** (the original 10-stage linear pipeline) and **Agent Mode** (the enhanced multi-agent pipeline with decomposed planning, per-file analysis, self-refine loops, execution sandbox, DevOps generation, and reference-based evaluation).

---

## Table of Contents

1. [Classic Mode Pipeline](#classic-mode-pipeline)
   - [Stage 1: PDF Download](#stage-1-pdf-download)
   - [Stage 2: Paper Analysis](#stage-2-paper-analysis-paperanalyzer)
   - [Stage 3: Equation Extraction](#stage-3-equation-extraction-equationextractor)
   - [Stage 4: Architecture Design](#stage-4-architecture-design-systemarchitect)
   - [Stage 5: Config Generation](#stage-5-config-generation-configgenerator)
   - [Stage 6: Code Synthesis](#stage-6-code-synthesis-codesynthesizer)
   - [Stage 7: Test Generation](#stage-7-test-generation-testgenerator)
   - [Stage 8: Validation](#stage-8-validation-codevalidator)
   - [Stage 9: Auto-Fix](#stage-9-auto-fix)
   - [Stage 10: Save](#stage-10-save)
2. [Agent Mode Pipeline](#agent-mode-pipeline)
   - [Stage 1: Parse Paper](#agent-stage-1-parse-paper)
   - [Stage 2: Decomposed Planning](#agent-stage-2-decomposed-planning-decomposedplanner)
   - [Stage 3: Per-File Analysis](#agent-stage-3-per-file-analysis-fileanalyzer)
   - [Stage 4: Code Generation](#agent-stage-4-code-generation)
   - [Stage 5: Test Generation](#agent-stage-5-test-generation)
   - [Stage 6: Validation and Auto-Fix](#agent-stage-6-validation-and-auto-fix)
   - [Stage 7: Execution and Auto-Debug](#agent-stage-7-execution-and-auto-debug)
   - [Stage 8: DevOps Generation](#agent-stage-8-devops-generation-devopsgenerator)
   - [Stage 9: Reference Evaluation](#agent-stage-9-reference-evaluation-referenceevaluator)
   - [Stage 10: Save Repository](#agent-stage-10-save-repository)
3. [Self-Refine Mechanism](#self-refine-mechanism)
4. [Interactive Mode](#interactive-mode)
5. [Pipeline Comparison Summary](#pipeline-comparison-summary)

---

## Classic Mode Pipeline

The classic mode (`--mode classic`) implements the original v2.0 linear pipeline. It processes a research paper through 10 sequential stages, producing a complete repository. This mode is kept for backward compatibility and is the default when no mode is specified.

Entry point: `run_classic()` in `main.py` (line 90).

---

### Stage 1: PDF Download

**Function:** `download_pdf()` in `main.py`

Downloads the research paper PDF from a given URL (arXiv, OpenReview, or any direct link) with robust validation.

**Implementation details:**

- **User-Agent header:** Sends `Research2Repo/3.0 (Academic Tool; +https://github.com/nellaivijay/Research2Repo)` to ensure academic-site compatibility and avoid request rejection by servers that block generic user agents.
- **Content-type validation:** Checks the `content-type` response header for `"pdf"`. If the content-type does not contain `"pdf"` and the URL does not end in `.pdf`, a warning is printed (the download proceeds regardless, since some servers return incorrect content types).
- **Size limit:** Downloads in streaming mode with 8192-byte chunks. Total size is tracked against a configurable maximum (default: 100 MB). If the limit is exceeded, a `ValueError` is raised immediately.
- **Timeout:** The HTTP request uses a configurable timeout (default: 120 seconds).
- **Output:** The PDF is saved as `source_paper.pdf` in the output directory.

```
[1/10] Download PDF
  Downloading PDF from https://arxiv.org/pdf/1706.03762.pdf...
  Downloaded: 2.1 MB -> ./generated_repo/source_paper.pdf
```

After download, the classic pipeline checks the cache. If a previous run exists for this PDF (matching by file path), a message is printed showing the cached run's timestamp and provider. Use `--no-cache` to force re-processing.

---

### Stage 2: Paper Analysis (PaperAnalyzer)

**Module:** `core/analyzer.py` -- `PaperAnalyzer` class

This stage ingests the PDF and produces a structured `PaperAnalysis` containing 13 fields extracted from the paper. It has two sub-steps.

#### Sub-step 2a: `upload_document()`

The method used depends on the provider's capabilities:

| Provider Capability | Strategy | Details |
|---|---|---|
| `FILE_UPLOAD` (Gemini) | Native PDF processing | Calls `provider.upload_file(pdf_path)`, returns a file handle used directly in LLM calls. No text extraction needed; the model reads the PDF natively. |
| All other providers | PyPDF2 text extraction | Extracts text page-by-page using `PyPDF2.PdfReader`, joins with double newlines. Returns the full text string. |

#### Sub-step 2b: `extract_diagrams_to_mermaid()`

If a vision-capable provider is available (either the primary provider or a separate `--vision-provider`):

1. Converts PDF pages to PNG images using PyMuPDF (`fitz`) at 150 DPI, capped at 30 pages.
2. Processes images in batches of 4 pages (to respect vision model token limits).
3. Sends each batch with the `diagram_extractor.txt` prompt to the vision model.
4. Parses Mermaid diagram code blocks from the response (looks for ` ```mermaid ``` ` blocks, or `---`-separated sections).
5. Returns a list of Mermaid diagram strings.

If no vision provider is available, this sub-step is skipped and an empty list is returned.

#### Sub-step 2c: `analyze()`

Performs the main structured analysis:

1. Loads the `analyzer.txt` prompt (29 lines).
2. Appends any extracted Mermaid diagrams as context.
3. Requests JSON output with `response_format="json"` and `temperature=0.1`.
4. For Gemini (file upload): calls `generate_with_file()` with the uploaded file handle.
5. For other providers: prepends the extracted text to the prompt.
6. Parses the JSON response into a `PaperAnalysis` dataclass.

**`PaperAnalysis` fields (13):**

| # | Field | Type | Description |
|---|---|---|---|
| 1 | `title` | `str` | Paper title |
| 2 | `authors` | `list[str]` | Author names |
| 3 | `abstract` | `str` | Full abstract text |
| 4 | `sections` | `dict[str, str]` | Section name to content summary |
| 5 | `equations` | `list[str]` | LaTeX equation strings |
| 6 | `hyperparameters` | `dict[str, str]` | Hyperparameter names to values |
| 7 | `architecture_description` | `str` | Detailed architecture description |
| 8 | `key_contributions` | `list[str]` | Paper's main contributions |
| 9 | `datasets_mentioned` | `list[str]` | Datasets used or referenced |
| 10 | `loss_functions` | `list[str]` | Loss functions in LaTeX |
| 11 | `full_text` | `str` | Full extracted text (empty for Gemini) |
| 12 | `diagrams_mermaid` | `list[str]` | Mermaid diagram strings |
| 13 | `raw_token_count` | `int` | Total tokens used (input + output) |

---

### Stage 3: Equation Extraction (EquationExtractor)

**Module:** `advanced/equation_extractor.py` -- `EquationExtractor` class

A dedicated equation extraction pipeline, separate from the main analysis, designed to catch equations that the general analyzer might miss.

**How it works:**

1. Uses the vision-capable provider (or falls back to the primary provider).
2. Sends the paper text (truncated to 80,000 characters) with the `equation_extractor.txt` prompt.
3. For each equation, extracts:
   - `equation_number` -- The paper's equation label (e.g., "Eq. 1")
   - `section` -- Which paper section it appears in
   - `latex` -- LaTeX representation
   - `pytorch` -- PyTorch pseudocode for implementation
   - `description` -- Plain-English explanation
   - `variables` -- Dictionary mapping variable names to their meanings and dimensions
   - `category` -- One of: `forward_pass`, `loss`, `initialization`, `optimization`, `metric`
4. Optionally also extracts from page images using vision (processes in batches of 4 pages).
5. Deduplicates by LaTeX string (case-insensitive, stripped).

**Merge step:** The extracted equations are merged with the analysis equations from Stage 2. Deduplication is performed by maintaining a set of existing LaTeX strings and only adding new ones.

```
[3/10] Running dedicated equation extraction...
  Total equations after merge: 14
```

This stage can be skipped with `--skip-equations`.

---

### Stage 4: Architecture Design (SystemArchitect)

**Module:** `core/architect.py` -- `SystemArchitect` class

Takes the `PaperAnalysis` and any extracted diagrams and produces a complete `ArchitecturePlan` for the repository.

**Input context includes:**
- Paper title, authors, abstract
- Architecture description
- Up to 20 equations
- All hyperparameters
- Loss functions
- Key contributions
- Mermaid diagrams (from vision extraction)

**Output: `ArchitecturePlan` dataclass:**

| Field | Type | Description |
|---|---|---|
| `repo_name` | `str` | Short kebab-case repository name |
| `description` | `str` | One-line description |
| `python_version` | `str` | Python version (default: "3.10") |
| `files` | `list[FileSpec]` | List of file specifications |
| `requirements` | `list[str]` | pip packages |
| `directory_tree` | `str` | Visual tree string |
| `config_schema` | `dict` | JSON schema for config.yaml |
| `training_entrypoint` | `str` | Path to training script |
| `inference_entrypoint` | `str` | Path to inference script |
| `readme_outline` | `str` | Markdown outline for README |

Each `FileSpec` contains: `path`, `description`, `dependencies` (list of other file paths), and `priority` (integer, lower = generate first).

**Essential file guarantee:** After the LLM generates the plan, `_ensure_essentials()` checks that three files exist and adds them if missing:
- `config.yaml` (priority -2, generated first)
- `requirements.txt` (priority -1)
- `README.md` (priority 100, generated last)

Files are then sorted by priority.

Uses the `architect.txt` prompt (47 lines) with structured JSON output and `temperature=0.1`.

---

### Stage 5: Config Generation (ConfigGenerator)

**Module:** `advanced/config_generator.py` -- `ConfigGenerator` class

Generates a structured YAML configuration file from the paper's hyperparameters.

**Process:**

1. Builds a prompt containing all hyperparameters from the analysis plus key equations (for context on parameter roles).
2. Requests a YAML file organized into sections:
   - `model:` -- Architecture parameters (d_model, num_heads, etc.)
   - `training:` -- Optimization parameters (learning_rate, batch_size, etc.)
   - `data:` -- Data loading parameters (max_seq_len, vocab_size, etc.)
   - `regularization:` -- Dropout, weight_decay, label_smoothing
   - `infrastructure:` -- seed, device, logging, checkpointing
3. YAML comments reference the paper sections where each parameter is mentioned.
4. Validates the output with `yaml.safe_load()`. If invalid, falls back to a programmatic YAML generator that categorizes hyperparameters by keyword matching.

The generated config is injected into the file dict in Stage 6, replacing any LLM-generated config.yaml.

---

### Stage 6: Code Synthesis (CodeSynthesizer)

**Module:** `core/coder.py` -- `CodeSynthesizer` class

Generates every source file specified in the architecture plan, one at a time.

**Key design decisions:**

1. **Dependency-ordered generation:** Files are generated in the order defined by `FileSpec.priority` (set by the architect). Config and utility files come first; the training script and README come last.

2. **Rolling context window:** Each file's prompt includes:
   - Full paper context (title, architecture, equations, hyperparameters, loss functions, diagrams)
   - Repository directory tree
   - All direct dependency files (files listed in `FileSpec.dependencies`) -- truncated to 3,000 characters each
   - The 3 most recently generated files (rolling window) -- truncated to 1,500 characters each

3. **Adaptive token limits:** `max_output_tokens` varies by file type:
   - Model and training files: 16,384 tokens
   - Standard Python files: 8,192 tokens
   - Config, YAML, text, and markdown files: 4,096 tokens

4. **Output cleaning (`_clean_output()`):**
   - Strips markdown code fences (` ``` `) from the beginning and end
   - For Python files: removes leading non-code lines (lines that do not start with `#`, `import`, `from`, `"""`, `class`, `def`, `@`, or blank)
   - For non-Python files: returns content as-is after fence stripping

5. **Gemini optimization:** If the provider supports `generate_with_file()`, the uploaded PDF file handle is passed alongside the prompt for maximum context fidelity.

Uses the `coder.txt` prompt (36 lines) with `temperature=0.15`.

```
[6/10] Synthesizing code (12 files)...
  [Coder] (1/12) Generating config.yaml...
  [Coder] (2/12) Generating model/attention.py...
  ...
```

---

### Stage 7: Test Generation (TestGenerator)

**Module:** `advanced/test_generator.py` -- `TestGenerator` class

Generates a comprehensive pytest test suite for the generated code.

**Generated test files:**

| File | Focus | Details |
|---|---|---|
| `tests/conftest.py` | Shared fixtures | `device` fixture, `paper_config` fixture (paper hyperparameters), `small_config` fixture (reduced sizes for fast testing), `sample_batch` fixture |
| `tests/test_model.py` | Model tests | Dimension verification, forward pass shape checks. Generated only if model files exist. |
| `tests/test_loss.py` | Loss/training tests | Loss function correctness, gradient computation. Generated only if loss/training files exist. |
| `tests/test_integration.py` | Integration tests | Full forward pass, backward pass, single training step, model save/load, config defaults |
| `tests/__init__.py` | Package init | Empty file |

**Test categories covered:**
- **Dimension tests:** Input/output shape consistency, intermediate tensor shapes, batch dimension preservation
- **Equation tests:** Known input/output pairs, numerical stability (softmax with large values, log of small values), gradient flow (no NaN/Inf)
- **Config tests:** Model instantiation with different configs, default values match paper, invalid config detection
- **Integration tests:** Full forward pass, backward pass gradients for all parameters, training step reduces loss

Uses the `test_generator.txt` prompt (38 lines) with `temperature=0.15`.

Can be skipped with `--skip-tests`.

---

### Stage 8: Validation (CodeValidator)

**Module:** `core/validator.py` -- `CodeValidator` class

Compares the generated code against the original paper to check fidelity.

**Validation checks (6 categories):**

| Category | What is checked |
|---|---|
| `equation` | Every paper equation has a code counterpart; operations are correct (softmax dimension, reduction axis, normalization constants, scaling factors) |
| `dimension` | Tensor shapes match paper (d_model, d_ff, num_heads, d_k); reshape/view operations are correct |
| `hyperparameter` | All paper hyperparameters are configurable (not hardcoded); defaults match paper values |
| `loss` | Loss function matches paper formulation; label smoothing, weights, regularization included; correct reduction (mean vs sum) |
| `architecture` | Layer ordering (pre-norm vs post-norm); skip connections; activation functions; dropout placement |
| `style` | Missing imports, undefined variables, type errors, missing return statements |

**Output: `ValidationReport` dataclass:**

| Field | Type | Description |
|---|---|---|
| `score` | `float` | Overall fidelity score, 0--100 |
| `equation_coverage` | `float` | Percentage of paper equations found in code (0--100) |
| `hyperparam_coverage` | `float` | Percentage of paper hyperparameters that are configurable (0--100) |
| `issues` | `list[ValidationIssue]` | Individual issues found |
| `summary` | `str` | 2--3 sentence summary |
| `passed` | `bool` | `True` if score >= 80 AND no critical issues |

**Issue severity levels:**

| Severity | Meaning | Example |
|---|---|---|
| `critical` | Will produce incorrect results | Wrong equation, wrong dimensions, missing loss terms |
| `warning` | May affect quality | Missing dropout, hardcoded hyperparameter |
| `info` | Style issues, minor suggestions | Missing docstring, naming convention |

Uses the `validator.txt` prompt (52 lines) with structured JSON output and `temperature=0.1`.

Can be skipped with `--skip-validation`.

---

### Stage 9: Auto-Fix

**Location:** `run_classic()` in `main.py` (lines 292--306)

An iterative loop that attempts to fix critical issues found during validation.

**Flow:**

```
while critical_count > 0 and iteration < max_fix_iterations:
    1. Call validator.fix_issues(generated_files, report, analysis)
    2. Re-validate: validator.validate(generated_files, analysis, plan)
    3. Print updated score and critical count
```

**`fix_issues()` method details:**
- Groups critical issues by file path
- For each affected file, builds a fix prompt containing:
  - The issue descriptions with suggestions
  - The current file content
  - Paper equations (up to 15)
- The LLM generates a corrected file (complete replacement, not a diff)
- Output is cleaned (strip markdown fences)

**Configuration:**
- `--max-fix-iterations` (default: 2)
- Only runs if critical issues exist after Stage 8
- Skipped if `--skip-validation` is set

---

### Stage 10: Save

**Location:** `run_classic()` in `main.py` (lines 317--358)

Writes all generated files to the output directory and records metadata.

**Process:**

1. Iterates `generated_files` dictionary (path to content mapping).
2. Creates any necessary subdirectories with `os.makedirs()`.
3. Writes each file.
4. Saves `.r2r_metadata.json` containing:
   - `pdf_url`, `provider`, `model`, `timestamp`
   - `elapsed_seconds` (total pipeline time)
   - `files_generated` (count)
   - `paper_title`, `equations_found`, `hyperparams_found`
5. If caching is enabled, saves metadata to the cache directory.
6. Prints a summary block with paper title, provider, file count, output path, and elapsed time.

---

## Agent Mode Pipeline

The agent mode (`--mode agent`) implements an enhanced 10-stage pipeline coordinated by the `AgentOrchestrator` class in `agents/orchestrator.py`. It adds decomposed planning, per-file analysis, self-refine loops, execution sandbox, DevOps generation, and reference-based evaluation.

Entry point: `run_agent()` in `main.py` (line 369), which delegates to `AgentOrchestrator.run()`.

The orchestrator maintains a result accumulator dict with keys: `files`, `plan`, `analysis`, `file_analyses`, `validation_report`, `execution_result`, `evaluation_score`, `metadata`. Each stage populates its respective field, and per-stage timing is recorded.

---

### Agent Stage 1: Parse Paper

**Method:** `_stage_parse_paper()` in `AgentOrchestrator`

Identical to Classic Stages 1--2. Uses `PaperAnalyzer` to:
1. Upload/extract the document (`upload_document()`)
2. Extract diagrams via vision (`extract_diagrams_to_mermaid()`)
3. Run structured analysis (`analyze()`)

Supports pre-computed analysis (passed as arguments) to avoid redundant work.

---

### Agent Stage 2: Decomposed Planning (DecomposedPlanner)

**Module:** `core/planner.py` -- `DecomposedPlanner` class

This is the key differentiator from classic mode. Instead of generating a monolithic `ArchitecturePlan` in a single LLM call, planning is broken into four explicit sub-stages, each building on the output of the previous one.

#### Sub-stage 2a: Overall Plan (`_step1_overall_plan()`)

**Prompt:** `overall_plan.txt` (19 lines)

Extracts a high-level implementation roadmap. The LLM receives the full paper context (title, authors, abstract, architecture, equations, hyperparameters, loss functions, contributions, datasets, diagrams).

**Output: `OverallPlan` dataclass:**
- `core_components` -- Major components to implement (e.g., "Multi-Head Attention", "Positional Encoding")
- `methods_to_implement` -- Concrete algorithms from the paper
- `training_objectives` -- Loss functions and training goals
- `data_processing_steps` -- Dataset loading, preprocessing, augmentation
- `evaluation_protocols` -- Metrics, benchmarks, evaluation methodology
- `summary` -- One-paragraph implementation summary

#### Sub-stage 2b: Architecture Design (`_step2_architecture_design()`)

**Prompt:** `architecture_design.txt` (56 lines)

Designs the file structure and produces Mermaid class/sequence diagrams.

**Input context:** Paper context + full Overall Plan from Step 2a.

**Output: `ArchitectureDesign` dataclass:**
- `file_list` -- Array of `{path, description, module}` entries
- `class_diagram_mermaid` -- Mermaid classDiagram showing inheritance and composition
- `sequence_diagram_mermaid` -- Mermaid sequenceDiagram showing training/inference flow
- `module_relationships` -- Array of `{from, to, relationship}` entries

#### Sub-stage 2c: Logic Design (`_step3_logic_design()`)

**Prompt:** `logic_design.txt` (36 lines)

Determines the dependency graph and execution order.

**Input context:** Paper context + Overall Plan summary + Architecture Design (file list + class diagram).

**Output: `LogicDesign` dataclass:**
- `execution_order` -- Topologically sorted list of file paths (generation order)
- `dependency_graph` -- Dict mapping each file path to its dependency file paths
- `file_specifications` -- Array of `{path, logic_description, key_functions}` entries

#### Sub-stage 2d: Config Generation (`_step4_config_generation()`)

Generates a YAML configuration from hyperparameters. Similar to Classic Stage 5 but integrated into the planning pipeline.

#### Backward Compatibility

After all four sub-stages complete, `_to_architecture_plan()` converts the decomposed outputs into a single `ArchitecturePlan` compatible with downstream stages. This conversion:
- Builds `FileSpec` objects from the architecture design file list
- Assigns `priority` from the logic design execution order
- Merges logic descriptions into file descriptions
- Constructs a directory tree from file paths
- Detects training/inference entrypoints by filename pattern matching
- Infers pip requirements from core components

#### Optional: SelfRefiner Loop

If `--refine` is enabled, the plan is passed through the `SelfRefiner` (see [Self-Refine Mechanism](#self-refine-mechanism)) after this stage.

---

### Agent Stage 3: Per-File Analysis (FileAnalyzer)

**Module:** `core/file_analyzer.py` -- `FileAnalyzer` class

Before code generation begins, this stage produces a detailed specification for EACH file in the architecture plan. This is inspired by PaperCoder's analysis stage and provides a significant quality improvement.

**Process:**

1. Iterates over files in plan order (sorted by priority).
2. For each file, builds a prompt with:
   - Paper context (architecture, equations, hyperparameters, loss functions, contributions, diagrams)
   - Full plan context (repo name, directory tree, file list with priorities and dependencies)
   - **All prior file analyses** -- the accumulated context grows as more files are analyzed
   - File-specific section: path, description, dependencies, priority
3. Requests structured JSON output matching the `FileAnalysis` schema.

**Output: `dict[str, FileAnalysis]`**

Each `FileAnalysis` contains:

| Field | Type | Description |
|---|---|---|
| `file_path` | `str` | Path to the file |
| `classes` | `list[dict]` | Class specs: name, attributes, methods, base_classes |
| `functions` | `list[dict]` | Function specs: name, args, return_type, description |
| `imports` | `list[str]` | Explicit import statements |
| `dependencies` | `list[str]` | Other project files imported |
| `algorithms` | `list[str]` | Ordered algorithmic steps from the paper |
| `input_output_spec` | `dict` | Expected inputs and outputs with tensor shapes |
| `test_criteria` | `list[str]` | What should be verified: shapes, ranges, gradients |

**Key insight:** The accumulated context mechanism means later files benefit from seeing the full specifications of earlier files. This maintains cross-file consistency (e.g., ensuring that the encoder file's output shapes match what the decoder file expects as input).

Uses the `file_analysis.txt` prompt (44 lines) with `temperature=0.1`.

Optional: SelfRefiner loop on the complete file_analyses dict if `--refine` is enabled.

---

### Agent Stage 4: Code Generation

**Method:** `_stage_code_generation()` in `AgentOrchestrator`

Uses the same `CodeSynthesizer` as Classic Stage 6, with the same dependency-ordered generation and rolling context window.

---

### Agent Stage 5: Test Generation

**Method:** `_stage_test_generation()` in `AgentOrchestrator`

Uses the same `TestGenerator` as Classic Stage 7. Can be disabled with `--no-tests`.

---

### Agent Stage 6: Validation and Auto-Fix

**Method:** `_stage_validation()` in `AgentOrchestrator`

Uses the same `CodeValidator` as Classic Stages 8--9. The auto-fix loop is identical: iterate up to `max_fix_iterations` (default: 2) while critical issues remain.

---

### Agent Stage 7: Execution and Auto-Debug

**Modules:** `advanced/executor.py` -- `ExecutionSandbox`, `advanced/debugger.py` -- `AutoDebugger`

This stage is unique to agent mode and is enabled with `--execute`. It actually runs the generated code and iteratively fixes any runtime errors.

#### ExecutionSandbox

Supports two execution modes:

| Mode | Base Image | Details |
|---|---|---|
| **Docker** (default) | `python:3.10-slim` | Auto-generates Dockerfile if missing, builds image, runs with resource limits (`--memory 8g --cpus 4`). If `gpu=True`, passes `--gpus all`. |
| **Local** (fallback) | System Python | Runs via `subprocess` in the repo directory. Detects modified files by comparing mtimes before/after execution. |

Docker is the default but falls back to local if Docker is not found on PATH or if the Docker build/run fails.

**Execution timeout:** Configurable, default 300 seconds. Docker build timeout: 600 seconds.

**Output: `ExecutionResult` dataclass:**
- `success` (bool), `stdout`, `stderr`, `exit_code`
- `duration_seconds`, `error_type` (classified), `modified_files`

**Error classification (`_classify_error()`):** Matches stderr against 19 Python error patterns, ordered from most to least specific:

1. `ModuleNotFoundError`
2. `ImportError`
3. `SyntaxError`
4. `IndentationError`
5. `NameError`
6. `TypeError`
7. `ValueError`
8. `AttributeError`
9. `KeyError`
10. `IndexError`
11. `FileNotFoundError`
12. `ZeroDivisionError`
13. `RuntimeError`
14. `CudaOOMError` (matches "cuda.*out of memory" or "OOM")
15. `AssertionError`
16. `NotImplementedError`
17. `PermissionError`
18. `OSError`
19. `UnclassifiedError` (matches any "Traceback")

Falls back to `UnknownError` if no pattern matches.

#### AutoDebugger

Iterates a debug loop: parse error, generate fix, apply, re-execute.

**Per-iteration workflow:**

1. **Find relevant files:** Parses `File "..."` references from the traceback. Matches against the generated files by basename and full path. Falls back to all files if none match.
2. **Build debug prompt:** Uses `auto_debug.txt` (40 lines) with `{{error_type}}`, `{{error_message}}`, `{{source_files}}` template variables.
3. **LLM analysis:** Generates structured JSON with a `fixes` array. Each fix contains `file_path`, `fixed_content` (complete file), `error_description`, and `fix_description`.
4. **Apply fixes:** Overwrites files in the in-memory dict and writes to disk.
5. **Re-execute:** Runs the code again through the sandbox.

**Configuration:** `--max-debug-iterations` (default: 3). Stops early if the code runs successfully or if the LLM suggests no fixes.

---

### Agent Stage 8: DevOps Generation (DevOpsGenerator)

**Module:** `advanced/devops.py` -- `DevOpsGenerator` class

Generates 5 production-ready infrastructure files. Enabled by default; disable with `--no-devops`.

**Generated files:**

#### 1. `Dockerfile`

Multi-stage build with CPU and optional GPU variants:
- **CPU stage:** Based on `python:{version}-slim`. Installs system deps (`git`, `build-essential`, plus OpenCV deps if needed), copies requirements and source, installs pip packages.
- **GPU stage:** Based on `nvidia/cuda:12.1.0-runtime-ubuntu22.04`. Only generated if GPU packages are detected in requirements (`torch`, `pytorch`, `tensorflow`, `jax`, `cupy`).

#### 2. `docker-compose.yml`

Two services:
- `train` -- Builds from the Dockerfile (GPU target if applicable), mounts `./data`, `./checkpoints`, `./logs` as volumes.
- `inference` -- Same image, exposes port 8000, mounts `./checkpoints`.

If GPU packages are detected, includes the NVIDIA GPU runtime configuration with `deploy.resources.reservations`.

#### 3. `Makefile`

Targets: `install`, `train`, `evaluate`, `test`, `lint`, `clean`, `docker-build`, `docker-run`, `help`.

- `test` runs `pytest tests/ -v --tb=short`
- `lint` runs `ruff check .` then `mypy --ignore-missing-imports .`
- `clean` removes `__pycache__`, `.pytest_cache`, `.mypy_cache`, build artifacts
- `docker-build` and `docker-run` handle container operations

#### 4. `.github/workflows/ci.yml`

GitHub Actions CI pipeline:
1. Checkout repository (`actions/checkout@v4`)
2. Setup Python (`actions/setup-python@v5` with pip cache)
3. Install dependencies (requirements.txt + pytest, ruff, mypy)
4. Lint with ruff (`--output-format=github`)
5. Type-check with mypy (`|| true` to not fail the build)
6. Run tests with pytest

Triggers on push and PR to `main`/`master`.

#### 5. `setup.py`

Minimal `setup.py` with:
- Package name and version from the plan
- `find_packages()` excluding tests
- `install_requires` reads from `requirements.txt`
- `extras_require` with `dev` group (pytest, ruff, mypy)
- Console script entry point

---

### Agent Stage 9: Reference Evaluation (ReferenceEvaluator)

**Module:** `advanced/evaluator.py` -- `ReferenceEvaluator` class

Scores the generated code against a reference implementation and/or the paper itself. Enabled with `--evaluate` and optionally `--reference-dir`.

**Two modes:**

| Mode | Trigger | What it compares |
|---|---|---|
| `with_reference` | `--reference-dir` points to a valid directory | Generated code vs ground-truth reference implementation vs paper |
| `without_reference` | No reference dir, or directory contains no `.py` files | Generated code vs paper text only |

**Multi-sample evaluation:**

To reduce variance, the evaluator runs N independent LLM evaluations (default: `num_samples=3`) and aggregates the results:
- Numeric scores (overall, component, coverage) are averaged.
- Non-numeric fields (lists, strings) are taken from the first sample.
- Severity breakdown counts are averaged and rounded.
- Uses `temperature=0.3` for slight variance across samples.

**Output: `EvaluationScore` dataclass:**

| Field | Type | Description |
|---|---|---|
| `overall_score` | `float` | 1--5 scale |
| `component_scores` | `dict[str, float]` | Per-component scores (model_architecture, loss_functions, data_processing, training_loop, evaluation, configuration) |
| `coverage` | `float` | 0--100%, percentage of key components implemented |
| `missing_components` | `list[str]` | Components in reference but not in generated |
| `extra_components` | `list[str]` | Components in generated but not in reference |
| `summary` | `str` | Brief evaluation summary |
| `severity_breakdown` | `dict[str, int]` | Issue counts by severity (high, medium, low) |

Uses the `reference_eval.txt` prompt (39 lines).

---

### Agent Stage 10: Save Repository

**Method:** `_stage_save()` in `AgentOrchestrator`

Writes all generated files (code + tests + DevOps) to the output directory. Saves `.r2r_metadata.json` with extended metadata including per-stage timings, configuration flags, and evaluation score.

Prints a final summary with paper title, provider/model, file count, validation score, evaluation score, and per-stage timing breakdown.

---

## Self-Refine Mechanism

**Module:** `core/refiner.py` -- `SelfRefiner` class

The self-refine mechanism is used in Agent Mode when `--refine` is enabled. It wraps any pipeline artifact in a verify-then-refine loop.

### How It Works

```
for iteration in range(1, max_iterations + 1):
    critique, issues = verify(artifact, artifact_type, context)
    if no issues:
        break
    artifact = refine_artifact(artifact, critique, artifact_type, context)
```

### Step 1: Verify

**Prompt:** `self_refine_verify.txt` (47 lines)

The LLM critiques the artifact against the paper context, returning:
- `critique` -- Free-text assessment
- `issues` -- List of specific, actionable issues with severity (`none`, `minor`, `major`, `critical`)
- `score` -- 1--5 quality score
- `needs_refinement` -- Boolean

The verification checklist is artifact-type-specific (the prompt has separate sections for each type).

### Step 2: Refine

**Prompt:** `self_refine_refine.txt` (30 lines)

The LLM receives the artifact, the critique, and the paper context, and produces a refined version. Rules:
- Fix ALL critical and warning issues
- Preserve correct parts unchanged
- Maintain the same format/schema
- Output ONLY the refined artifact

### Supported Artifact Types

| Type | Format | When Used |
|---|---|---|
| `overall_plan` | JSON | After planning Step 2a |
| `architecture_design` | JSON | After planning Step 2b |
| `logic_design` | JSON | After planning Step 2c |
| `file_analysis` | JSON | After per-file analysis (Stage 3) |
| `config` | YAML text | After config generation |
| `code` | Python text | After code generation |

### Configuration

- `--max-refine-iterations` (default: 2)
- Each iteration adds 2 LLM calls (verify + refine), so `--refine` roughly doubles the total LLM calls
- Early exit: the loop stops if verification finds no issues

### Output: `RefinementResult` dataclass

Contains: `original`, `refined`, `critique`, `improvements` (list), `iterations` (count), `improved` (boolean).

---

## Interactive Mode

Enabled with `--interactive` (agent mode only). Pauses the pipeline after Stage 2 (Planning) to let the user review the planned architecture before committing to code generation.

**What is displayed:**

```
============================================================
  INTERACTIVE MODE -- Architecture Review
============================================================

  Paper : Attention Is All You Need
  Repo  : attention-is-all-you-need
  Files : 12
  Deps  : numpy, pyyaml, torch>=2.0

  <directory tree>

  Files to generate:
      1. config.yaml    -- Hyperparameter configuration file
      2. model/attention.py  -- Multi-Head Attention implementation
      3. model/encoder.py    -- Transformer Encoder
      ...

Press Enter to continue or 'q' to abort...
```

The user can:
- Press **Enter** to continue with code generation
- Type **q** and press Enter to abort the pipeline (raises `SystemExit(0)`)

---

## Pipeline Comparison Summary

| Feature | Classic Mode | Agent Mode |
|---|---|---|
| Planning | Single SystemArchitect call | 4-stage decomposed planning |
| Per-file analysis | None | Full FileAnalyzer pass |
| Self-refine | Not available | Optional verify/refine loops |
| Code generation | CodeSynthesizer | Same CodeSynthesizer |
| Test generation | TestGenerator | Same TestGenerator |
| Validation | CodeValidator + auto-fix | Same CodeValidator + auto-fix |
| Execution | Not available | ExecutionSandbox + AutoDebugger |
| DevOps | Not available | Dockerfile, Makefile, CI, setup.py |
| Evaluation | Not available | ReferenceEvaluator (with/without reference) |
| Interactive review | Not available | Optional pause after planning |
| Equation extraction | Dedicated EquationExtractor | Part of Stage 1 analysis |
| Config generation | Dedicated ConfigGenerator | Integrated into planning |
| Caching | Full cache support | Not yet implemented |
| Total stages | 10 | 10 |
| Typical LLM calls | ~15-20 | ~30-60 (varies with refine/debug) |
