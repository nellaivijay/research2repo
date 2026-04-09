# Architecture Overview

This document describes the architecture of **Research2Repo v3.0**, a multi-model agentic framework that converts machine-learning research papers into production-ready GitHub repositories. It is intended for contributors, integrators, and anyone who wants to understand how the system is structured before diving into the code.

---

## Table of Contents

- [1. System Context](#1-system-context)
- [2. Architecture Philosophy](#2-architecture-philosophy)
- [3. High-Level Component Diagram](#3-high-level-component-diagram)
- [4. Module Dependency Graph](#4-module-dependency-graph)
- [5. Data Flow](#5-data-flow)
- [6. Key Design Patterns](#6-key-design-patterns)
- [7. Cross-Cutting Concerns](#7-cross-cutting-concerns)
- [8. Technology Stack](#8-technology-stack)

---

## 1. System Context

Research2Repo sits between a researcher (who has a paper URL) and a complete, runnable repository (with training scripts, tests, CI, and Docker support). The researcher provides a PDF link; the system downloads the paper, analyses every equation, hyperparameter, and architectural detail, designs a repository layout, generates code, validates it against the paper, optionally executes and debugs it inside a sandbox, and writes the final files to disk.

### What the System Does

| Input | Output |
|---|---|
| PDF URL (arXiv, OpenReview, etc.) | Complete Python repository |
| Provider/model selection (optional) | `model/`, `data/`, `train.py`, `config.yaml`, `tests/` |
| Mode selection (classic or agent) | Dockerfile, Makefile, CI workflow, `setup.py` |
| Feature flags (`--refine`, `--execute`) | `.r2r_metadata.json` with run provenance |

### External Dependencies

The system communicates with several external services and tools, none of which are mandatory beyond at least one LLM provider:

```
+------------------+       +------------------+       +------------------+
|  LLM APIs        |       |  PDF Tools       |       |  Execution Env   |
|  - Gemini API    |       |  - PyPDF2        |       |  - Docker         |
|  - OpenAI API    |       |  - PyMuPDF       |       |  - subprocess     |
|  - Anthropic API |       |  - GROBID (REST) |       |  - python interp  |
|  - Ollama (local)|       |  - doc2json      |       |                  |
+------------------+       +------------------+       +------------------+
         |                          |                          |
         +--------------------------+--------------------------+
                                    |
                          +---------+---------+
                          |  Research2Repo    |
                          |  Pipeline Engine  |
                          +-------------------+
```

| Dependency | Required? | Purpose |
|---|---|---|
| At least one LLM API key | **Yes** | Paper analysis, architecture design, code generation, validation |
| `requests` | Yes | PDF download, GROBID/Ollama HTTP calls |
| `PyPDF2` | Yes | Baseline PDF text extraction |
| `PyMuPDF` (fitz) | No | Rich font-aware PDF parsing, page-image extraction for vision |
| GROBID server | No | High-quality TEI XML paper parsing |
| `doc2json` | No | Highest-quality structured paper parsing |
| Docker | No | Isolated execution sandbox |
| `pyyaml` | Yes | Config file generation and validation |

---

## 2. Architecture Philosophy

### Zero-RAG (Full-Context)

Research2Repo does **not** use Retrieval-Augmented Generation. Instead, the entire paper content is sent to the LLM in a single context window. For providers that support file upload (Gemini), the raw PDF is uploaded directly. For others, the full extracted text is included in the prompt. This avoids information loss from chunking and retrieval and leverages the 100K-1M token context windows available on modern models.

### Multi-Model Abstraction

All LLM interactions pass through a provider abstraction layer (`providers/base.py`). The system is not tied to any single vendor. Four backends are supported out of the box:

- **Google Gemini** -- native PDF upload, 1M+ context, vision
- **OpenAI GPT-4o/o3** -- structured output, strong code generation
- **Anthropic Claude** -- 200K context, excellent code reasoning
- **Ollama** -- local models, zero cost, no data leaves the machine

Providers are selected automatically based on available API keys or can be overridden via CLI flags.

### Capability-Based Routing

Rather than hardcoding which provider to use for each task, the system defines a `ModelCapability` enum (`TEXT_GENERATION`, `VISION`, `LONG_CONTEXT`, `STRUCTURED_OUTPUT`, `CODE_GENERATION`, `FILE_UPLOAD`, `STREAMING`). The `ProviderRegistry.best_for(capability)` method returns the best available provider for a given capability, consulting a per-capability preference order. This lets the system route vision tasks to Gemini while routing code generation tasks to Claude, all transparently.

### Lazy Imports

Every heavy module import inside the `AgentOrchestrator` is deferred to the method body that needs it. This is annotated with `# lazy` comments throughout. The reason is twofold:

1. **Avoid circular imports** -- modules in `core/` and `advanced/` import from each other; deferring prevents import cycles.
2. **Fast startup** -- if only a subset of stages is used (e.g., skipping execution or evaluation), the unused modules are never imported.

### Graceful Degradation

The system is designed to work with whatever is available. Every optional module import is wrapped in `try/except ImportError`, and fallback paths are provided:

- If `DecomposedPlanner` is not available, the orchestrator falls back to `SystemArchitect`.
- If `ExecutionSandbox` or `AutoDebugger` cannot be imported, the execution stage is skipped.
- If `DevOpsGenerator` or `ReferenceEvaluator` is missing, those stages are skipped.
- If `SelfRefiner` is not available, artifacts pass through unrefined.
- If structured generation fails, every module falls back to plain-text generation with JSON parsing.

---

## 3. High-Level Component Diagram

```
+============================================================================+
|                          CLI Entry Point (main.py)                         |
|                                                                            |
|    argparse -> mode routing                                                |
|    +-------------------+           +--------------------+                  |
|    | run_classic()     |           | run_agent()        |                  |
|    | (10-stage linear) |           | (AgentOrchestrator)|                  |
|    +--------+----------+           +---------+----------+                  |
+============+============================+====+=============================+
             |                            |
             v                            v
+============+============================+====+=============================+
|                     Provider Layer (providers/)                            |
|                                                                            |
|  +----------+  +---------+  +-----------+  +--------+  +-----------+      |
|  | registry |->| base.py |  | gemini.py |  | openai |  | anthropic |      |
|  | .py      |  | ABC     |  |           |  | _prov. |  | _provider |      |
|  +----------+  +---------+  +-----------+  +--------+  +-----------+      |
|       |                                                    +--------+      |
|       +--------------------------------------------------->| ollama |      |
|                                                            +--------+      |
|  Shared: BaseProvider, ModelCapability, GenerationConfig, GenerationResult |
+============================================================================+
             |                            |
             v                            v
+============+============================+====+=============================+
|                   Core Pipeline (core/)                                    |
|                                                                            |
|  +---------------+   +----------------+   +----------------+              |
|  | paper_parser  |   | analyzer       |   | architect      |              |
|  | (4 backends)  |   | (PaperAnalyzer |   | (SystemArchit. |              |
|  |               |   |  + vision)     |   |  ArchPlan)     |              |
|  +---------------+   +--------+-------+   +--------+-------+              |
|                               |                    |                      |
|  +---------------+   +--------v-------+   +--------v-------+              |
|  | planner       |   | file_analyzer  |   | coder          |              |
|  | (Decomposed   |   | (per-file spec |   | (CodeSynth.    |              |
|  |  4-stage)     |   |  with context) |   |  per-file gen) |              |
|  +---------------+   +----------------+   +--------+-------+              |
|                                                    |                      |
|  +---------------+                        +--------v-------+              |
|  | refiner       |<--(optional loops)---->| validator      |              |
|  | (SelfRefiner  |                        | (CodeValidator |              |
|  |  verify/ref.) |                        |  + auto-fix)   |              |
|  +---------------+                        +----------------+              |
+============================================================================+
             |                            |
             v                            v
+============+============================+====+=============================+
|                 Advanced Layer (advanced/)                                 |
|                                                                            |
|  +---------------+   +----------------+   +------------------+            |
|  | executor      |   | debugger       |   | evaluator        |            |
|  | (Docker/local |   | (AutoDebugger  |   | (ReferenceEval.  |            |
|  |  sandbox)     |   |  fix+retry)    |   |  with/without    |            |
|  +---------------+   +----------------+   |  reference)      |            |
|                                           +------------------+            |
|  +---------------+   +----------------+   +------------------+            |
|  | equation_     |   | config_        |   | test_generator   |            |
|  | extractor     |   | generator      |   | (pytest suites)  |            |
|  +---------------+   +----------------+   +------------------+            |
|                                                                            |
|  +---------------+   +----------------+                                   |
|  | devops        |   | cache          |                                   |
|  | (Dockerfile,  |   | (content-addr. |                                   |
|  |  CI, Makefile)|   |  by PDF hash)  |                                   |
|  +---------------+   +----------------+                                   |
+============================================================================+
             |
             v
+============+==============================================================+
|                      Agents Layer (agents/)                               |
|                                                                            |
|  +---------------+         +-----------------------------+                |
|  | base.py       |         | orchestrator.py             |                |
|  | (BaseAgent    |-------->| (AgentOrchestrator          |                |
|  |  ABC, msg     |         |  10-stage coordinator       |                |
|  |  passing)     |         |  lazy imports, refine loops |                |
|  +---------------+         |  interactive gate)          |                |
|                            +-----------------------------+                |
+============================================================================+
```

---

## 4. Module Dependency Graph

The following graph shows compile-time (import) dependencies. Runtime (lazy) imports are shown with dashed notation.

```
main.py
 |-- providers/
 |    |-- __init__.py
 |    |    |-- registry.py
 |    |    |    |-- base.py  (BaseProvider, ModelCapability, ModelInfo, ...)
 |    |    |    |-- gemini.py ............ (lazy via importlib)
 |    |    |    |-- openai_provider.py ... (lazy via importlib)
 |    |    |    |-- anthropic_provider.py  (lazy via importlib)
 |    |    |    |-- ollama.py ............ (lazy via importlib)
 |    |    |-- base.py
 |    |-- base.py
 |
 |-- (lazy in run_classic) ----+
 |                             |
 |   core/analyzer.py <--------+-- providers/base, providers/__init__
 |   core/architect.py <-----------  providers/base, providers/__init__,
 |        |                          core/analyzer (PaperAnalysis)
 |   core/planner.py <-------------  providers/base, providers/__init__,
 |        |                          core/analyzer, core/architect
 |   core/file_analyzer.py <-------  providers/base, providers/__init__,
 |        |                          core/analyzer, core/architect
 |   core/coder.py <---------------  providers/base, providers/__init__,
 |        |                          core/analyzer, core/architect
 |   core/validator.py <-----------  providers/base, providers/__init__,
 |        |                          core/analyzer, core/architect
 |   core/refiner.py <-------------  providers/base, providers/__init__
 |   core/paper_parser.py             (standalone, no provider dependency)
 |
 |   advanced/equation_extractor.py <- providers/base, providers/__init__
 |   advanced/config_generator.py <--- providers/base, providers/__init__,
 |        |                            core/analyzer
 |   advanced/test_generator.py <----- providers/base, providers/__init__,
 |        |                            core/analyzer, core/architect
 |   advanced/cache.py                 (standalone, uses hashlib/pickle/json)
 |   advanced/executor.py              (standalone, uses subprocess/docker)
 |   advanced/debugger.py <----------- providers/base, providers/__init__,
 |        |                            advanced/executor
 |   advanced/evaluator.py <---------- providers/base, providers/__init__
 |   advanced/devops.py <------------- providers/__init__,
 |                                     providers/base
 |
 |-- (lazy in run_agent) ------+
 |                             |
 |   agents/orchestrator.py <--+-- providers/__init__, providers/base
 |        |  (all other imports are LAZY inside method bodies)
 |        |  runtime: core/analyzer, core/planner, core/architect,
 |        |           core/file_analyzer, core/coder, core/validator,
 |        |           core/refiner, advanced/test_generator,
 |        |           advanced/executor, advanced/debugger,
 |        |           advanced/devops, advanced/evaluator
 |   agents/base.py <------------- providers/__init__, providers/base
 |
 |-- config.py                     (standalone, uses os + dataclasses)
```

Key observations:

- `providers/base.py` is the single most-depended-upon module.
- `core/analyzer.py` (specifically `PaperAnalysis`) is imported by nearly every `core/` and `advanced/` module.
- `core/architect.py` (specifically `ArchitecturePlan` and `FileSpec`) is the second most-shared data structure.
- `agents/orchestrator.py` has almost zero top-level imports from `core/` or `advanced/` -- everything is deferred to method bodies.

---

## 5. Data Flow

### 5.1 Classic Mode Data Flow

```
PDF URL
  |
  v
+------------------+
| download_pdf()   |  --> source_paper.pdf (on disk)
+--------+---------+
         |
         v
+------------------+
| PaperAnalyzer    |  upload_document() -> file handle or text
|  .analyze()      |  extract_diagrams_to_mermaid() -> list[str]
+--------+---------+
         |
         v
   PaperAnalysis
   (title, authors, equations[], hyperparameters{},
    architecture_description, sections{}, loss_functions[],
    diagrams_mermaid[], full_text)
         |
    +----+----+
    |         |
    v         v
+--------+ +------------------+
|Equation| |SystemArchitect   |
|Extract.| | .design_system() |
+---+----+ +--------+---------+
    |               |
    v               v
 merged         ArchitecturePlan
 equations      (repo_name, files[FileSpec], requirements[],
    |            directory_tree, training_entrypoint)
    |               |
    +-------+-------+
            |
            v
    +-------+--------+
    |ConfigGenerator  |
    | .generate()     |
    +-------+---------+
            |
            v
       config.yaml (string)
            |
            v
    +-------+---------+
    |CodeSynthesizer   |
    | .generate_       |
    |  codebase()      |
    +-------+----------+
            |
            v
    dict[str, str]  (file_path -> content)
            |
    +-------+-------+
    |               |
    v               v
+--------+  +------+------+
|TestGen |  |CodeValidator |
| .gen   |  | .validate() |
| tests()|  +------+------+
+---+----+         |
    |              v
    |      ValidationReport
    |      (score, equation_coverage,
    |       hyperparam_coverage, issues[])
    |              |
    +------+-------+
           |
           v   (if critical_count > 0)
    +------+------+
    |CodeValidator |<---+
    | .fix_issues()|    | loop up to
    +------+-------+    | max_fix_iterations
           |            |
           +--re-validate-+
           |
           v
    +------+------+
    | Save files  |
    | to output   |
    | directory   |
    +-------------+
```

### 5.2 Agent Mode Data Flow

```
PDF URL
  |
  v
+------------------+        +---------------------+
| download_pdf()   |------->| AgentOrchestrator   |
+------------------+        |   .run()            |
                            +----+----------------+
                                 |
  Stage 1                        v
  +--------------------------+---+---+
  | PaperAnalyzer            |       |
  |  .upload_document()      |       |
  |  .extract_diagrams()     |       |
  |  .analyze()              |       |
  +--------------------------+       |
         |                           |
         v                           |
    PaperAnalysis                    |
         |                           |
  Stage 2|                           |
         v                           |
  +--------------------------+       |
  | DecomposedPlanner        |       |
  |  Step 1: OverallPlan     |       |
  |  Step 2: ArchDesign      |       |
  |  Step 3: LogicDesign     |       |
  |  Step 4: Config          |       |
  +-----------+--------------+       |
              |                      |
              v (optional)           |
        +-----+------+              |
        | SelfRefiner |              |
        | verify ->   |              |
        | refine loop |              |
        +-----+------+              |
              |                      |
              v                      |
       ArchitecturePlan              |
              |                      |
  Stage 3     v                      |
  +--------------------------+       |
  | FileAnalyzer             |       |
  |  .analyze_all()          |       |
  |  (per-file, accumulated  |       |
  |   context from prior     |       |
  |   files)                 |       |
  +-----------+--------------+       |
              |                      |
              v (optional)           |
        +-----+------+              |
        | SelfRefiner |              |
        +-----+------+              |
              |                      |
              v                      |
  dict[str, FileAnalysis]            |
              |                      |
  Stage 4     v                      |
  +--------------------------+       |
  | CodeSynthesizer          |       |
  |  .generate_codebase()    |       |
  +-----------+--------------+       |
              |                      |
  Stage 5     v                      |
  +--------------------------+       |
  | TestGenerator            |       |
  |  .generate_tests()       |       |
  +-----------+--------------+       |
              |                      |
  Stage 6     v                      |
  +--------------------------+       |
  | CodeValidator            |       |
  |  .validate()             |       |
  |  .fix_issues() (loop)    |       |
  +-----------+--------------+       |
              |                      |
  Stage 7     v (if --execute)       |
  +--------------------------+       |
  | ExecutionSandbox         |       |
  |  .execute()              |       |
  |       |                  |       |
  |       v (if failed)      |       |
  |  AutoDebugger            |       |
  |   .debug() (loop)        |       |
  +-----------+--------------+       |
              |                      |
  Stage 8     v (if --devops)        |
  +--------------------------+       |
  | DevOpsGenerator          |       |
  |  .generate_all()         |       |
  |  -> Dockerfile, Makefile,|       |
  |     CI, docker-compose,  |       |
  |     setup.py             |       |
  +-----------+--------------+       |
              |                      |
  Stage 9     v (if --evaluate)      |
  +--------------------------+       |
  | ReferenceEvaluator       |       |
  |  .evaluate_with_ref()    |       |
  |  or .evaluate_without()  |       |
  +-----------+--------------+       |
              |                      |
  Stage 10    v                      |
  +--------------------------+       |
  | Save all files to disk   |       |
  | Write .r2r_metadata.json |       |
  +--------------------------+-------+
```

### 5.3 Key Data Structures in Transit

| Structure | Module | Description |
|---|---|---|
| `PaperAnalysis` | `core/analyzer.py` | Title, authors, equations, hyperparams, architecture, sections, diagrams |
| `ParsedPaper` | `core/paper_parser.py` | Lower-level parsed output with sections, figures, tables, raw equations |
| `OverallPlan` | `core/planner.py` | High-level roadmap: core components, methods, training objectives |
| `ArchitectureDesign` | `core/planner.py` | File list, Mermaid class/sequence diagrams, module relationships |
| `LogicDesign` | `core/planner.py` | Execution order, dependency graph, per-file logic descriptions |
| `PlanningResult` | `core/planner.py` | Aggregates all 4 planning sub-stages + backward-compatible `ArchitecturePlan` |
| `ArchitecturePlan` | `core/architect.py` | Repo blueprint: files[], requirements[], directory tree, entrypoints |
| `FileSpec` | `core/architect.py` | Single file spec: path, description, dependencies, priority |
| `FileAnalysis` | `core/file_analyzer.py` | Per-file: classes, functions, imports, algorithms, I/O spec, test criteria |
| `ValidationReport` | `core/validator.py` | Score (0-100), equation/hyperparam coverage, issues list |
| `ValidationIssue` | `core/validator.py` | Single issue: severity, file, description, suggestion, category |
| `ExecutionResult` | `advanced/executor.py` | Success/fail, stdout/stderr, exit code, error type, duration |
| `DebugFix` | `advanced/debugger.py` | File-level fix: original content, fixed content, descriptions |
| `DebugReport` | `advanced/debugger.py` | Per-iteration: error, fixes applied, resolved flag |
| `ExtractedEquation` | `advanced/equation_extractor.py` | Equation number, LaTeX, PyTorch pseudocode, variables, category |
| `EvaluationScore` | `advanced/evaluator.py` | Overall score (1-5), component scores, coverage, missing/extra components |
| `RefinementResult` | `core/refiner.py` | Original, refined artifact, critique, improvements list, iteration count |
| `R2RConfig` | `config.py` | 18-field global configuration dataclass |

---

## 6. Key Design Patterns

### 6.1 Strategy Pattern (Providers)

The provider layer implements a classic Strategy pattern. `BaseProvider` defines the interface (`generate()`, `generate_structured()`, `supports()`, `upload_file()`). Four concrete strategies implement this interface for different LLM backends. The client code (every `core/` and `advanced/` module) programs against the `BaseProvider` abstraction and never references a specific provider.

```
              BaseProvider (ABC)
              /    |    \     \
       Gemini  OpenAI  Anthropic  Ollama
      Provider Provider  Provider Provider
```

Switching providers requires zero code changes in the pipeline -- just a different API key or `--provider` flag.

### 6.2 Template Method (Prompt Loading)

Every module that interacts with an LLM follows the same prompt-loading pattern:

1. Define a `PROMPT_FILE` class attribute pointing to `prompts/<module>.txt`.
2. Implement `_load_prompt(path, **kwargs)` that reads the file and substitutes `{{key}}` placeholders.
3. Define a `_default_<kind>_prompt()` fallback method that returns a hardcoded prompt string.
4. At call time: try loading the external template; if the file does not exist, use the default.

This allows prompt engineering without touching Python code, and ensures the system works even if the `prompts/` directory is missing.

### 6.3 Pipeline Pattern (Sequential Stages)

Both classic and agent modes implement a sequential pipeline where each stage's output feeds into the next. The classic mode is a single function (`run_classic`) with 10 numbered stages. The agent mode is an `AgentOrchestrator.run()` method with 10 numbered stages, each delegated to a private `_stage_*` method.

The pipeline is not a generic framework -- each stage has different input/output types. But the consistent pattern of `header -> execute -> accumulate result -> timing -> print status` is uniform across all stages.

### 6.4 Observer / Fallback (Graceful Degradation)

Every module import in the orchestrator and every `generate_structured()` call is wrapped in a try/except:

```python
# Module-level fallback
try:
    from core.planner import DecomposedPlanner
    planner = DecomposedPlanner(provider=provider)
    plan = planner.plan(...)
except ImportError:
    from core.architect import SystemArchitect
    architect = SystemArchitect(provider=provider)
    plan = architect.design_system(...)

# API-level fallback
try:
    data = self.provider.generate_structured(prompt, schema, ...)
except Exception:
    data = self._fallback_generate(prompt)  # plain text -> JSON parse
```

This means the system degrades gracefully when optional dependencies are missing or when an LLM API call fails.

### 6.5 Factory (ProviderRegistry)

`ProviderRegistry` is a classic Factory that creates provider instances by name. Internally it stores a mapping of `name -> (module_path, class_name)` and uses `importlib.import_module()` for lazy, dynamic instantiation:

```python
_PROVIDER_MAP = {
    "gemini":    ("providers.gemini",             "GeminiProvider"),
    "openai":    ("providers.openai_provider",    "OpenAIProvider"),
    "anthropic": ("providers.anthropic_provider", "AnthropicProvider"),
    "ollama":    ("providers.ollama",             "OllamaProvider"),
}
```

The `register()` method allows adding custom providers at runtime without modifying the registry source code.

### 6.6 Lazy Loading (Deferred Imports)

All imports inside `AgentOrchestrator`'s stage methods are deferred to method-call time:

```python
@staticmethod
def _stage_parse_paper(...):
    from core.analyzer import PaperAnalyzer  # lazy
    ...

@staticmethod
def _stage_plan(...):
    try:
        from core.planner import DecomposedPlanner  # lazy
        ...
    except ImportError:
        from core.architect import SystemArchitect  # lazy
        ...
```

This is consistent throughout all 10 stages of the orchestrator. The `run_classic()` function in `main.py` also uses this pattern, placing all its imports inside the function body rather than at module level.

---

## 7. Cross-Cutting Concerns

### 7.1 Prompt Externalization

All LLM prompts are stored as plain-text files in the `prompts/` directory:

```
prompts/
  analyzer.txt
  architect.txt
  architecture_design.txt
  auto_debug.txt
  coder.txt
  devops.txt
  diagram_extractor.txt
  equation_extractor.txt
  file_analysis.txt
  logic_design.txt
  overall_plan.txt
  reference_eval.txt
  self_refine_refine.txt
  self_refine_verify.txt
  test_generator.txt
  validator.txt
```

Each module references its prompt file via a class-level `PROMPT_FILE` constant or a module-level path variable. Prompts support `{{placeholder}}` substitution. Every module also includes a `_default_*_prompt()` method as a fallback if the file is not found. This separation means:

- Prompts can be edited, version-controlled, and reviewed independently of logic.
- Non-developers (e.g., prompt engineers) can iterate on prompts without touching Python.
- The system still works if the `prompts/` directory is deleted.

### 7.2 Caching (Content-Addressed by PDF Hash)

`PipelineCache` (`advanced/cache.py`) implements a file-system cache keyed on the SHA-256 hash of the input PDF. The cache structure is:

```
.r2r_cache/
  {pdf_hash_prefix}/
    analysis.json         # Human-readable summary
    analysis.pkl          # Pickled PaperAnalysis
    architecture.pkl      # Pickled ArchitecturePlan
    files/                # Generated code files
      model/attention.py
      train.py
      ...
    files_manifest.json   # List of generated file paths
    validation.pkl        # Pickled ValidationReport
    metadata.json         # Run provenance (provider, model, timestamp)
```

The cache is used in classic mode to skip expensive LLM calls on re-runs of the same paper. The `--no-cache` flag disables it; `--clear-cache` wipes it.

### 7.3 Error Handling Philosophy

The project follows a pragmatic error handling approach:

1. **Never crash on optional features.** Every optional import and every LLM API call is wrapped in try/except with a fallback path.
2. **Structured generation with text fallback.** The `generate_structured()` method (JSON schema-constrained generation) is always tried first. If it fails, `_fallback_generate()` calls `generate()` with "Respond with ONLY a JSON object" appended, then parses the text.
3. **JSON parsing with progressive fallback.** Response text is cleaned (strip markdown fences, remove leading/trailing backticks) before `json.loads()`.
4. **Auto-fix and auto-debug loops.** Rather than failing on validation or execution errors, the system feeds the errors back to the LLM and iterates up to a configurable maximum.

### 7.4 Self-Refine Loops (Verify -> Refine -> Iterate)

The `SelfRefiner` (`core/refiner.py`) implements a general-purpose verify-then-refine loop applicable to any pipeline artifact:

```
Artifact --> [Verify] --> Critique + Issues
                |
                v
           Has issues?
           /         \
         No           Yes
         |             |
         v             v
       Done      [Refine] --> Refined Artifact
                      |
                      +---> loop (up to max_iterations)
```

Supported artifact types include `overall_plan`, `architecture_design`, `logic_design`, `file_analysis`, `config`, and `code`. JSON-type artifacts use `generate_structured()` for refinement; text-type artifacts use plain `generate()`. The refiner is stateless -- each call is self-contained.

In the agent pipeline, self-refinement is optionally applied after planning (Stage 2) and after per-file analysis (Stage 3), controlled by the `--refine` flag.

---

## 8. Technology Stack

### Runtime

| Category | Technology | Version | Purpose |
|---|---|---|---|
| Language | Python | 3.10+ | Core runtime |
| HTTP | `requests` | 2.31+ | PDF download, GROBID/Ollama HTTP |
| PDF (required) | `PyPDF2` | 3.0+ | Baseline text extraction |
| PDF (optional) | `PyMuPDF` (fitz) | 1.24+ | Rich font-aware parsing, page images |
| PDF (optional) | GROBID | -- | TEI XML structured parsing (REST API) |
| PDF (optional) | `doc2json` | -- | Highest-quality `s2orc` parsing |
| Image | `Pillow` | 10.2+ | Image handling for vision models |
| Config | `pyyaml` | 6.0+ | YAML generation and validation |
| Serialization | `dataclasses` | stdlib | All data structures |
| Serialization | `json` | stdlib | LLM response parsing, cache manifests |
| Serialization | `pickle` | stdlib | Cache persistence for complex objects |
| Execution | `subprocess` | stdlib | Local code execution |
| Execution | Docker | (external) | Isolated sandbox execution |
| XML | `xml.etree.ElementTree` | stdlib | GROBID TEI XML parsing |
| Hashing | `hashlib` | stdlib | Content-addressed cache keys |

### LLM Provider SDKs

| Provider | Package | Default Model | Key Capabilities |
|---|---|---|---|
| Google Gemini | `google-generativeai` 0.5+ | `gemini-2.5-pro-preview-05-06` | FILE_UPLOAD, VISION, LONG_CONTEXT, STRUCTURED_OUTPUT |
| OpenAI | `openai` 1.12+ | `gpt-4o` | VISION, STRUCTURED_OUTPUT, CODE_GENERATION |
| Anthropic | `anthropic` 0.25+ | `claude-sonnet-4-20250514` | LONG_CONTEXT, CODE_GENERATION |
| Ollama | HTTP API | `llama3` | TEXT_GENERATION (local, free) |

All provider SDKs are optional. Only the one(s) you intend to use need to be installed. Install groups are defined in `pyproject.toml`:

```
pip install research2repo[gemini]      # Google Gemini only
pip install research2repo[openai]      # OpenAI only
pip install research2repo[all]         # Everything
```

### Development

| Tool | Purpose |
|---|---|
| `pytest` 8.0+ | Test runner |
| `pytest-cov` 4.0+ | Coverage reporting |
| `ruff` 0.3+ | Linting |
| `mypy` 1.0+ | Type checking |
| `setuptools` 68+ | Build backend |

---

*Last updated: This document reflects the Research2Repo v3.0 codebase.*
