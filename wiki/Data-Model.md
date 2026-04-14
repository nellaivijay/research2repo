# Data Model

This document provides a comprehensive reference for all dataclasses, enums, and data structures in Research2Repo v3.0. It covers 1 enum, 22 dataclasses, data flow through the pipeline, entity relationships, JSON schema examples, and the full configuration schema.

---

## Table of Contents

1. [Enum Definitions](#1-enum-definitions)
2. [Dataclass Specifications (22 Total)](#2-dataclass-specifications)
3. [Data Flow Diagram](#3-data-flow-diagram)
4. [Entity Relationship Diagram](#4-entity-relationship-diagram)
5. [JSON Schema Examples](#5-json-schema-examples)
6. [Configuration Schema](#6-configuration-schema)

---

## 1. Enum Definitions

### `ModelCapability` -- `providers/base.py`

Enumerates the capabilities a model provider may support. Used for provider selection, capability matching, and feature gating throughout the pipeline.

```python
class ModelCapability(Enum):
    TEXT_GENERATION    = auto()  # Basic text generation (all providers)
    VISION            = auto()  # Image/diagram understanding
    LONG_CONTEXT      = auto()  # >100K token context window
    STRUCTURED_OUTPUT = auto()  # JSON mode / function calling
    CODE_GENERATION   = auto()  # Optimized for code output
    FILE_UPLOAD       = auto()  # Direct file upload (Gemini File API)
    STREAMING         = auto()  # Stream responses token-by-token
```

**Usage Contexts:**

| Capability | Used By | Purpose |
|------------|---------|---------|
| `TEXT_GENERATION` | All modules | Baseline capability for any LLM interaction |
| `VISION` | `PaperAnalyzer`, `EquationExtractor` | Diagram extraction, equation extraction from rendered pages |
| `LONG_CONTEXT` | `PaperAnalyzer` | Full-paper analysis without chunking |
| `STRUCTURED_OUTPUT` | `SystemArchitect`, `DecomposedPlanner`, `FileAnalyzer`, `SelfRefiner` | JSON-mode generation for structured outputs |
| `CODE_GENERATION` | `CodeSynthesizer`, `CodeValidator`, `AutoDebugger`, `TestGenerator`, `ReferenceEvaluator` | Code synthesis, validation, debugging, test generation |
| `FILE_UPLOAD` | `PaperAnalyzer` | Gemini File API for zero-RAG PDF processing |
| `STREAMING` | (Reserved) | Not currently used in pipeline |

**Capability by Provider:**

| Provider | TEXT | VISION | LONG_CTX | STRUCT | CODE | FILE_UP | STREAM |
|----------|------|--------|----------|--------|------|---------|--------|
| Gemini 2.5 Pro | Y | Y | Y | Y | Y | Y | Y |
| Gemini 2.0 Flash | Y | Y | Y | N | Y | Y | Y |
| Gemini 1.5 Pro | Y | Y | Y | Y | Y | Y | Y |
| GPT-4o | Y | Y | Y | Y | Y | N | Y |
| GPT-4-turbo | Y | Y | Y | Y | Y | N | Y |
| o3 | Y | Y | Y | Y | Y | N | Y |
| o1 | Y | N | Y | N | Y | N | N |
| Claude Sonnet 4 | Y | Y | Y | Y | Y | N | Y |
| Claude Opus 4 | Y | Y | Y | Y | Y | N | Y |
| Claude 3.5 Sonnet | Y | Y | Y | Y | Y | N | Y |
| deepseek-coder-v2 | Y | N | Y | N | Y | N | N |
| llama3.1:70b | Y | N | Y | N | Y | N | N |
| codellama:34b | Y | N | N | N | Y | N | N |
| llava:13b | Y | Y | N | N | N | N | N |
| mistral:latest | Y | N | N | N | Y | N | N |

---

## 2. Dataclass Specifications

### DC-1: `R2RConfig` -- `config.py`

Top-level configuration for the Research2Repo pipeline. Controls provider selection, pipeline toggles, generation parameters, vision settings, caching, and output behavior.

```python
@dataclass
class R2RConfig:
    # Provider defaults
    default_provider: str = "auto"       # "auto", "gemini", "openai", "anthropic", "ollama"
    default_model: str = ""              # Empty = use provider default

    # Pipeline toggles
    enable_validation: bool = True
    enable_test_generation: bool = True
    enable_equation_extraction: bool = True
    enable_caching: bool = True
    max_fix_iterations: int = 2

    # Download settings
    pdf_timeout: int = 120               # seconds
    pdf_max_size_mb: int = 100           # megabytes

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

| Field | Type | Default | Env Var Override | Description |
|-------|------|---------|-----------------|-------------|
| `default_provider` | `str` | `"auto"` | `R2R_PROVIDER` | Provider selection strategy |
| `default_model` | `str` | `""` | `R2R_MODEL` | Model name override (empty = provider default) |
| `enable_validation` | `bool` | `True` | `R2R_SKIP_VALIDATION` (inverted) | Enable code validation stage |
| `enable_test_generation` | `bool` | `True` | `R2R_SKIP_TESTS` (inverted) | Enable test generation stage |
| `enable_equation_extraction` | `bool` | `True` | -- | Enable dedicated equation extraction |
| `enable_caching` | `bool` | `True` | `R2R_NO_CACHE` (inverted) | Enable pipeline stage caching |
| `max_fix_iterations` | `int` | `2` | -- | Maximum auto-fix cycles |
| `pdf_timeout` | `int` | `120` | -- | PDF download timeout (seconds) |
| `pdf_max_size_mb` | `int` | `100` | -- | Maximum PDF file size (MB) |
| `code_temperature` | `float` | `0.15` | -- | Temperature for code generation |
| `analysis_temperature` | `float` | `0.1` | -- | Temperature for analysis/planning |
| `max_code_tokens` | `int` | `16384` | -- | Max output tokens for code generation |
| `max_analysis_tokens` | `int` | `8192` | -- | Max output tokens for analysis |
| `max_diagram_pages` | `int` | `30` | -- | Max PDF pages for diagram extraction |
| `diagram_dpi` | `int` | `150` | -- | DPI for page-to-image conversion |
| `vision_batch_size` | `int` | `4` | -- | Images per vision API call |
| `cache_dir` | `str` | `".r2r_cache"` | `R2R_CACHE_DIR` | Cache directory path |
| `verbose` | `bool` | `False` | `R2R_VERBOSE` | Enable verbose output |

#### Adaptive Token Limits

`R2RConfig.max_tokens_for_file(file_path: str) -> int` returns an appropriate token budget based on file type:

| File Pattern | Token Limit |
|-------------|-------------|
| `.yaml`, `.yml`, `.toml`, `.cfg`, `.txt` | 2,048 |
| `.md` | 2,048 |
| `model`, `network`, `encoder`, `decoder` in path | 12,288 |
| `train`, `trainer` in path | 10,240 |
| `test` in path | 6,144 |
| `config`, `utils`, `__init__` in path | 4,096 |
| Default | 8,192 |

**Produced by:** `R2RConfig.from_env()` classmethod or direct instantiation.
**Consumed by:** `main.py` classic pipeline, passed as parameters to individual modules.

---

### DC-2: `ModelInfo` -- `providers/base.py`

Metadata about a specific model. Defined as class-level constants in each provider.

```python
@dataclass
class ModelInfo:
    name: str                                        # e.g., "gpt-4o"
    provider: str                                    # e.g., "openai"
    max_context_tokens: int                          # e.g., 128000
    max_output_tokens: int                           # e.g., 16384
    capabilities: list[ModelCapability] = field(default_factory=list)
    cost_per_1k_input: float = 0.0                   # USD per 1K input tokens
    cost_per_1k_output: float = 0.0                  # USD per 1K output tokens
```

**Produced by:** `BaseProvider.available_models()` in each provider subclass.
**Consumed by:** `BaseProvider.supports()`, `BaseProvider.model_info()`, `ProviderRegistry.estimate_cost()`, `get_provider()`, provider listing CLI.

---

### DC-3: `GenerationConfig` -- `providers/base.py`

Common generation parameters across all providers.

```python
@dataclass
class GenerationConfig:
    temperature: float = 0.2
    top_p: float = 0.95
    max_output_tokens: int = 8192
    stop_sequences: list[str] = field(default_factory=list)
    response_format: Optional[str] = None            # "json" or None
```

**Produced by:** Each pipeline module when calling `provider.generate()` or `provider.generate_structured()`.
**Consumed by:** All provider `generate()` and `generate_structured()` methods.

**Provider-Specific Mapping:**

| Field | Gemini | OpenAI | Anthropic | Ollama |
|-------|--------|--------|-----------|--------|
| `temperature` | `temperature` | `temperature` | `temperature` | `options.temperature` |
| `top_p` | `top_p` | `top_p` | `top_p` | `options.top_p` |
| `max_output_tokens` | `max_output_tokens` | `max_tokens` | `max_tokens` | `options.num_predict` |
| `stop_sequences` | `stop_sequences` | `stop` | `stop_sequences` | -- |
| `response_format="json"` | `response_mime_type="application/json"` | `response_format={"type":"json_object"}` | -- (prompt only) | `format="json"` |

---

### DC-4: `GenerationResult` -- `providers/base.py`

Standardized response from any provider.

```python
@dataclass
class GenerationResult:
    text: str                                        # Generated text content
    model: str                                       # Model name that produced this
    input_tokens: int = 0                            # Prompt tokens consumed
    output_tokens: int = 0                           # Completion tokens generated
    finish_reason: str = "stop"                      # "stop", "length", etc.
    raw_response: Optional[object] = None            # Provider-native response object
```

**Produced by:** All provider `generate()` methods.
**Consumed by:** All pipeline modules that call `provider.generate()`. `text` is the primary field used; token counts are for cost tracking and metadata.

---

### DC-5: `PaperAnalysis` -- `core/analyzer.py`

Structured output from paper analysis. The most widely consumed dataclass in the system.

```python
@dataclass
class PaperAnalysis:
    title: str = ""
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    sections: dict[str, str] = field(default_factory=dict)         # section_name -> content
    equations: list[str] = field(default_factory=list)              # LaTeX strings
    hyperparameters: dict[str, str] = field(default_factory=dict)  # name -> value
    architecture_description: str = ""
    key_contributions: list[str] = field(default_factory=list)
    datasets_mentioned: list[str] = field(default_factory=list)
    loss_functions: list[str] = field(default_factory=list)
    full_text: str = ""                                            # Complete extracted text
    diagrams_mermaid: list[str] = field(default_factory=list)      # Mermaid.js diagram strings
    raw_token_count: int = 0                                       # Total tokens used
```

| Field | Type | Description |
|-------|------|-------------|
| `title` | `str` | Paper title |
| `authors` | `list[str]` | List of author names |
| `abstract` | `str` | Full abstract text |
| `sections` | `dict[str, str]` | Map of section names to content summaries |
| `equations` | `list[str]` | All mathematical equations in LaTeX format |
| `hyperparameters` | `dict[str, str]` | Hyperparameter names to values/descriptions |
| `architecture_description` | `str` | Detailed model architecture description |
| `key_contributions` | `list[str]` | Paper's main contributions |
| `datasets_mentioned` | `list[str]` | Datasets used or referenced |
| `loss_functions` | `list[str]` | Loss functions in LaTeX format |
| `full_text` | `str` | Complete extracted text (empty if Gemini file upload used) |
| `diagrams_mermaid` | `list[str]` | Mermaid.js diagrams extracted via vision |
| `raw_token_count` | `int` | Total tokens consumed during analysis |

**Produced by:** `PaperAnalyzer.analyze()` (Stage 1).
**Consumed by:** `SystemArchitect.design_system()`, `DecomposedPlanner.plan()`, `FileAnalyzer.analyze_all()`, `CodeSynthesizer.generate_codebase()`, `CodeValidator.validate()`, `CodeValidator.fix_issues()`, `TestGenerator.generate_tests()`, `ConfigGenerator.generate()`, `EquationExtractor` (merged equations), `DevOpsGenerator.generate_all()`, `AgentOrchestrator` (all stages).

---

### DC-6: `FileSpec` -- `core/architect.py`

Specification for a single file to generate.

```python
@dataclass
class FileSpec:
    path: str                                        # e.g., "model/transformer.py"
    description: str                                 # What this file should contain
    dependencies: list[str] = field(default_factory=list)  # Other file paths it depends on
    priority: int = 0                                # Generation order (lower = first)
```

**Produced by:** `SystemArchitect._parse_plan()`, `DecomposedPlanner._to_architecture_plan()`.
**Consumed by:** `CodeSynthesizer._generate_single_file()`, `FileAnalyzer.analyze_file()`, `_ensure_essentials()`.
**Contained in:** `ArchitecturePlan.files` (as a list).

---

### DC-7: `ArchitecturePlan` -- `core/architect.py`

Complete blueprint for the generated repository.

```python
@dataclass
class ArchitecturePlan:
    repo_name: str = ""                              # Short kebab-case name
    description: str = ""                            # One-line description
    python_version: str = "3.10"                     # Target Python version
    files: list[FileSpec] = field(default_factory=list)  # Ordered file specs
    requirements: list[str] = field(default_factory=list) # pip packages
    directory_tree: str = ""                         # Visual tree string
    config_schema: dict = field(default_factory=dict)     # JSON schema for config.yaml
    training_entrypoint: str = "train.py"            # Path to training script
    inference_entrypoint: str = "inference.py"       # Path to inference script
    readme_outline: str = ""                         # Markdown outline for README
```

**Produced by:** `SystemArchitect.design_system()` (Stage 2 classic), `DecomposedPlanner._to_architecture_plan()` (Stage 2 agent).
**Consumed by:** `CodeSynthesizer.generate_codebase()`, `FileAnalyzer.analyze_all()`, `CodeValidator.validate()`, `TestGenerator.generate_tests()`, `DevOpsGenerator.generate_all()`, `ExecutionSandbox` (entrypoint), `AgentOrchestrator`.

---

### DC-8: `ValidationIssue` -- `core/validator.py`

A single issue found during validation.

```python
@dataclass
class ValidationIssue:
    severity: str                                    # "critical", "warning", "info"
    file_path: str                                   # Path of affected file
    line_hint: str = ""                              # Approximate location
    description: str = ""                            # What is wrong
    suggestion: str = ""                             # How to fix it
    category: str = ""                               # "equation", "dimension",
                                                     # "hyperparameter", "style", "logic"
```

**Produced by:** `CodeValidator._parse_report()`.
**Consumed by:** `CodeValidator.fix_issues()` (groups by file, filters critical).
**Contained in:** `ValidationReport.issues` (as a list).

---

### DC-9: `ValidationReport` -- `core/validator.py`

Complete validation report with scores and issues.

```python
@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)
    score: float = 0.0                               # 0-100 fidelity score
    equation_coverage: float = 0.0                   # 0-100 percentage
    hyperparam_coverage: float = 0.0                 # 0-100 percentage
    summary: str = ""                                # Brief text summary
    passed: bool = False                             # True if score >= 80, no critical issues

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")
```

**Produced by:** `CodeValidator.validate()` (Stage 6).
**Consumed by:** `CodeValidator.fix_issues()`, `AgentOrchestrator._stage_validation()` (loop condition: `critical_count > 0`), `_print_summary()`.

---

### DC-10: `OverallPlan` -- `core/planner.py`

Step 1 output from the decomposed planning pipeline -- high-level roadmap.

```python
@dataclass
class OverallPlan:
    core_components: list[str] = field(default_factory=list)
    methods_to_implement: list[str] = field(default_factory=list)
    training_objectives: list[str] = field(default_factory=list)
    data_processing_steps: list[str] = field(default_factory=list)
    evaluation_protocols: list[str] = field(default_factory=list)
    summary: str = ""
```

| Field | Type | Example |
|-------|------|---------|
| `core_components` | `list[str]` | `["Multi-Head Attention", "Positional Encoding", "Feed-Forward Network"]` |
| `methods_to_implement` | `list[str]` | `["Scaled Dot-Product Attention", "Layer Normalization"]` |
| `training_objectives` | `list[str]` | `["Cross-entropy loss with label smoothing"]` |
| `data_processing_steps` | `list[str]` | `["BPE tokenization", "Sequence padding to max_len"]` |
| `evaluation_protocols` | `list[str]` | `["BLEU score", "Perplexity"]` |
| `summary` | `str` | One-paragraph implementation summary |

**Produced by:** `DecomposedPlanner._step1_overall_plan()`.
**Consumed by:** `DecomposedPlanner._step2_architecture_design()`, `_step3_logic_design()`, `_step4_config_generation()`, `_to_architecture_plan()`.
**Contained in:** `PlanningResult.overall_plan`.

---

### DC-11: `ArchitectureDesign` -- `core/planner.py`

Step 2 output -- structural design with Mermaid diagrams.

```python
@dataclass
class ArchitectureDesign:
    file_list: list[dict] = field(default_factory=list)
    class_diagram_mermaid: str = ""
    sequence_diagram_mermaid: str = ""
    module_relationships: list[dict] = field(default_factory=list)
```

| Field | Type | Structure |
|-------|------|-----------|
| `file_list` | `list[dict]` | Each: `{"path": str, "description": str, "module": str}` |
| `class_diagram_mermaid` | `str` | Mermaid classDiagram code |
| `sequence_diagram_mermaid` | `str` | Mermaid sequenceDiagram code |
| `module_relationships` | `list[dict]` | Each: `{"from": str, "to": str, "relationship": str}` |

**Produced by:** `DecomposedPlanner._step2_architecture_design()`.
**Consumed by:** `DecomposedPlanner._step3_logic_design()`, `_to_architecture_plan()`.
**Contained in:** `PlanningResult.architecture_design`.

---

### DC-12: `LogicDesign` -- `core/planner.py`

Step 3 output -- dependency graph and per-file logic descriptions.

```python
@dataclass
class LogicDesign:
    execution_order: list[str] = field(default_factory=list)
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    file_specifications: list[dict] = field(default_factory=list)
```

| Field | Type | Structure |
|-------|------|-----------|
| `execution_order` | `list[str]` | Topologically sorted file paths (generate-first order) |
| `dependency_graph` | `dict[str, list[str]]` | Maps `file_path` to list of file paths it imports from |
| `file_specifications` | `list[dict]` | Each: `{"path": str, "logic_description": str, "key_functions": list[str]}` |

**Produced by:** `DecomposedPlanner._step3_logic_design()`.
**Consumed by:** `DecomposedPlanner._to_architecture_plan()`.
**Contained in:** `PlanningResult.logic_design`.

---

### DC-13: `PlanningResult` -- `core/planner.py`

Aggregate output of the full 4-step planning pipeline.

```python
@dataclass
class PlanningResult:
    overall_plan: OverallPlan = field(default_factory=OverallPlan)
    architecture_design: ArchitectureDesign = field(default_factory=ArchitectureDesign)
    logic_design: LogicDesign = field(default_factory=LogicDesign)
    config_content: str = ""                         # Generated YAML string
    combined_plan: ArchitecturePlan = field(default_factory=ArchitecturePlan)
```

**Produced by:** `DecomposedPlanner.plan()` (Stage 2 agent).
**Consumed by:** `AgentOrchestrator._stage_plan()` extracts `combined_plan` (the `ArchitecturePlan`) for downstream stages.

**Relationships:**
- Contains `OverallPlan` (DC-10)
- Contains `ArchitectureDesign` (DC-11)
- Contains `LogicDesign` (DC-12)
- Contains `ArchitecturePlan` (DC-7) as `combined_plan`

---

### DC-14: `FileAnalysis` -- `core/file_analyzer.py`

Detailed specification for a single source file, produced before code generation.

```python
@dataclass
class FileAnalysis:
    file_path: str = ""
    classes: list[dict] = field(default_factory=list)
    functions: list[dict] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    algorithms: list[str] = field(default_factory=list)
    input_output_spec: dict = field(default_factory=dict)
    test_criteria: list[str] = field(default_factory=list)
```

| Field | Type | Structure |
|-------|------|-----------|
| `file_path` | `str` | Relative file path |
| `classes` | `list[dict]` | Each: `{"name": str, "attributes": list[str], "methods": list[str], "base_classes": list[str]}` |
| `functions` | `list[dict]` | Each: `{"name": str, "args": list[str], "return_type": str, "description": str}` |
| `imports` | `list[str]` | Full import statements, e.g., `"import torch"`, `"from model.encoder import Encoder"` |
| `dependencies` | `list[str]` | Project file paths this file imports from |
| `algorithms` | `list[str]` | Ordered algorithmic steps from the paper |
| `input_output_spec` | `dict` | E.g., `{"input": "Tensor[B, S, D]", "output": "Tensor[B, S, V]"}` |
| `test_criteria` | `list[str]` | What to verify: dimensions, ranges, reproducibility |

**Produced by:** `FileAnalyzer.analyze_file()` (Stage 3 agent).
**Consumed by:** `FileAnalyzer._build_prior_context()` (accumulated context for later files). Not yet directly consumed by `CodeSynthesizer` (future integration point).

---

### DC-15: `ParsedPaper` -- `core/paper_parser.py`

Structured representation of a parsed research paper from any backend.

```python
@dataclass
class ParsedPaper:
    title: str = ""
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    sections: list[dict] = field(default_factory=list)        # [{name, content, subsections}]
    figures: list[dict] = field(default_factory=list)          # [{caption, page_num}]
    tables: list[dict] = field(default_factory=list)           # [{caption, content}]
    equations_raw: list[str] = field(default_factory=list)     # Raw LaTeX strings
    references: list[str] = field(default_factory=list)        # Reference titles
    full_text: str = ""
    metadata: dict = field(default_factory=dict)               # Parser-specific metadata
```

| Field | Type | Description |
|-------|------|-------------|
| `title` | `str` | Paper title (extraction quality varies by backend) |
| `authors` | `list[str]` | Author names (best from doc2json/GROBID, empty from PyMuPDF/PyPDF2) |
| `abstract` | `str` | Abstract text (regex-extracted for PyMuPDF/PyPDF2) |
| `sections` | `list[dict]` | Each: `{"name": str, "content": str, "subsections": list}` |
| `figures` | `list[dict]` | Each: `{"caption": str, "page_num": int}` |
| `tables` | `list[dict]` | Each: `{"caption": str, "content": str}` |
| `equations_raw` | `list[str]` | LaTeX equations extracted via regex from full text |
| `references` | `list[str]` | Referenced paper titles (from GROBID/doc2json) |
| `full_text` | `str` | Complete concatenated text |
| `metadata` | `dict` | E.g., `{"parser": "pymupdf", "page_count": 12}` |

**Produced by:** `PaperParser.parse()`.
**Consumed by:** Not directly consumed by the main pipeline (the pipeline uses `PaperAnalyzer` instead). Available as an alternative structured parsing pathway.

---

### DC-16: `RefinementResult` -- `core/refiner.py`

Outcome of a self-refine loop.

```python
@dataclass
class RefinementResult:
    original: Any = None                             # Artifact before refinement
    refined: Any = None                              # Artifact after refinement
    critique: str = ""                               # Final critique text
    improvements: list[str] = field(default_factory=list)  # Specific improvements made
    iterations: int = 0                              # Actual iterations executed
    improved: bool = False                           # Whether artifact was modified
```

**Produced by:** `SelfRefiner.refine()`.
**Consumed by:** `AgentOrchestrator._refine_output()` -- extracts `.refined` attribute.

---

### DC-17: `ExtractedEquation` -- `advanced/equation_extractor.py`

A single equation extracted from the paper with full metadata.

```python
@dataclass
class ExtractedEquation:
    equation_number: str = ""                        # e.g., "Eq. 1", "3.2"
    section: str = ""                                # e.g., "3.1 Multi-Head Attention"
    latex: str = ""                                  # LaTeX source
    pytorch: str = ""                                # PyTorch pseudocode equivalent
    description: str = ""                            # Natural language description
    variables: dict[str, str] = field(default_factory=dict)  # {symbol: meaning}
    category: str = ""                               # "forward_pass", "loss",
                                                     # "initialization", "optimization", "metric"
```

**Produced by:** `EquationExtractor.extract_from_text()`, `EquationExtractor.extract_from_images()`.
**Consumed by:** `EquationExtractor.map_to_files()`, merged into `PaperAnalysis.equations` in the classic pipeline.

---

### DC-18: `EvaluationScore` -- `advanced/evaluator.py`

Aggregate evaluation result from reference-based or reference-free evaluation.

```python
@dataclass
class EvaluationScore:
    overall_score: float = 0.0                       # 1-5 scale
    component_scores: dict[str, float] = field(default_factory=dict)
    coverage: float = 0.0                            # 0-100 percentage
    missing_components: list[str] = field(default_factory=list)
    extra_components: list[str] = field(default_factory=list)
    summary: str = ""
    severity_breakdown: dict[str, int] = field(default_factory=dict)
```

| Field | Type | Description |
|-------|------|-------------|
| `overall_score` | `float` | 1.0-5.0 aggregate score (averaged across `num_samples` evaluations) |
| `component_scores` | `dict[str, float]` | Per-component scores: `method`, `training`, `data`, `evaluation`, `utils`, `reproducibility` |
| `coverage` | `float` | 0-100% of reference/paper components found in generated code |
| `missing_components` | `list[str]` | Components present in reference/paper but absent in generated code |
| `extra_components` | `list[str]` | Components in generated code not described in reference/paper |
| `summary` | `str` | Brief text summary of evaluation |
| `severity_breakdown` | `dict[str, int]` | Issue counts: `{"high": int, "medium": int, "low": int}` |

**Produced by:** `ReferenceEvaluator.evaluate_with_reference()`, `ReferenceEvaluator.evaluate_without_reference()`.
**Consumed by:** `AgentOrchestrator._print_summary()`.

---

### DC-19: `ExecutionResult` -- `advanced/executor.py`

Outcome of running a generated repository's entrypoint.

```python
@dataclass
class ExecutionResult:
    success: bool = False
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    duration_seconds: float = 0.0
    error_type: str = ""                             # Empty if success, else classified error
    modified_files: list[str] = field(default_factory=list)  # Files changed during execution
```

**Produced by:** `ExecutionSandbox.execute()`, `ExecutionSandbox._run_in_docker()`, `ExecutionSandbox._run_locally()`.
**Consumed by:** `AutoDebugger.debug()` (loop condition: `success == False`), `AgentOrchestrator._stage_execution()`.

---

### DC-20: `DebugFix` -- `advanced/debugger.py`

A single file-level fix produced by the debugger.

```python
@dataclass
class DebugFix:
    file_path: str = ""                              # Relative path of fixed file
    original_content: str = ""                       # Content before fix
    fixed_content: str = ""                          # Content after fix
    error_description: str = ""                      # What went wrong
    fix_description: str = ""                        # What was changed
```

**Produced by:** `AutoDebugger._parse_fixes()`.
**Consumed by:** `AutoDebugger._apply_fixes()`.
**Contained in:** `DebugReport.fixes` (as a list).

---

### DC-21: `DebugReport` -- `advanced/debugger.py`

Report for a single debug iteration.

```python
@dataclass
class DebugReport:
    iteration: int = 0                               # 1-based iteration number
    error_message: str = ""                          # Truncated stderr (max 2000 chars)
    error_type: str = ""                             # Classified error category
    fixes: list[DebugFix] = field(default_factory=list)
    resolved: bool = False                           # True if execution succeeded after fixes
```

**Produced by:** `AutoDebugger.debug()` (one per iteration).
**Consumed by:** `AgentOrchestrator._stage_execution()` (returned as part of the result).

---

### DC-22: `AgentMessage` -- `agents/base.py`

A simple message exchanged between agents.

```python
@dataclass
class AgentMessage:
    role: str                                        # Sender role/identifier
    content: str                                     # Message body (free-form text or serialized data)
    metadata: dict[str, Any] = field(default_factory=dict)  # Structured side-channel info
```

**Produced by:** `BaseAgent.communicate()` -- creates acknowledgement messages.
**Consumed by:** `BaseAgent.communicate()` -- passed as the message parameter. Currently used for synchronous in-process agent-to-agent communication.

---

## 3. Data Flow Diagram

### Pipeline Stage Data Flow

| Stage | Step | Input | Output | Key Dataclass(es) |
|-------|------|-------|--------|--------------------|
| 1 | Download PDF | URL string | PDF file on disk | -- |
| 2a | Upload Document | PDF path | File handle or text string | -- |
| 2b | Extract Diagrams | PDF path | Mermaid diagram strings | -- |
| 2c | Analyze Paper | File handle/text + diagrams | Structured analysis | `PaperAnalysis` |
| 3a | Overall Plan | `PaperAnalysis` | High-level roadmap | `OverallPlan` |
| 3b | Architecture Design | `PaperAnalysis` + `OverallPlan` | File structure + Mermaid diagrams | `ArchitectureDesign` |
| 3c | Logic Design | `PaperAnalysis` + `OverallPlan` + `ArchitectureDesign` | Dependency graph + execution order | `LogicDesign` |
| 3d | Config Generation | `PaperAnalysis` + `OverallPlan` + `ArchitectureDesign` + `LogicDesign` | YAML string | -- |
| 3e | Combine Plan | All step 3 outputs | Backward-compatible plan | `PlanningResult`, `ArchitecturePlan` |
| 4 | Per-File Analysis | `ArchitecturePlan` + `PaperAnalysis` | Per-file specifications | `dict[str, FileAnalysis]` |
| 5 | Code Generation | `PaperAnalysis` + `ArchitecturePlan` + document | Generated source files | `dict[str, str]` |
| 6 | Test Generation | `dict[str, str]` + `PaperAnalysis` + `ArchitecturePlan` | Test files | `dict[str, str]` |
| 7 | Validation | `dict[str, str]` + `PaperAnalysis` + `ArchitecturePlan` | Validation report | `ValidationReport`, `ValidationIssue` |
| 8 | Auto-Fix | `dict[str, str]` + `ValidationReport` + `PaperAnalysis` | Fixed files | `dict[str, str]` |
| 9 | Execution | `dict[str, str]` + repo_dir + entrypoint | Execution result | `ExecutionResult` |
| 10 | Auto-Debug | `dict[str, str]` + `ExecutionResult` | Fixed files + debug reports | `DebugFix`, `DebugReport` |
| 11 | DevOps | `ArchitecturePlan` + `PaperAnalysis` + `dict[str, str]` | Infrastructure files | `dict[str, str]` |
| 12 | Evaluation | `dict[str, str]` + reference_dir + paper_text | Evaluation scores | `EvaluationScore` |
| 13 | Save Files | `dict[str, str]` + output_dir | Files on disk | -- |

### Simplified Data Flow

```
PDF
 |
 v
[PaperAnalyzer] ──> PaperAnalysis ──────────────────────────────────┐
 |                       |                                          |
 v                       v                                          |
[DecomposedPlanner] ──> PlanningResult                              |
 |                       |                                          |
 |                  ArchitecturePlan <── combined_plan               |
 |                       |                                          |
 v                       v                                          |
[FileAnalyzer] ──> dict[str, FileAnalysis]                          |
                         |                                          |
                         v                                          |
                  [CodeSynthesizer] ──> dict[str, str] (files)      |
                         |                      |                   |
                         v                      v                   |
                  [TestGenerator]         [CodeValidator]            |
                         |                      |                   |
                         v                      v                   |
                  test files ──>         ValidationReport           |
                         |                      |                   |
                         v                      v                   |
                  [merged files] <── [fix_issues loop] ─────────────┘
                         |
                    ┌────┴────────────────┐
                    v                     v
             [ExecutionSandbox]   [DevOpsGenerator]
                    |                     |
                    v                     v
             ExecutionResult      DevOps files
                    |
                    v
             [AutoDebugger] ──> DebugReport(s)
                    |
                    v
             [ReferenceEvaluator] ──> EvaluationScore
                    |
                    v
             [Save to disk]
```

---

## 4. Entity Relationship Diagram

```
                              +-------------------+
                              |    R2RConfig      |
                              |  (18 fields)      |
                              +-------------------+
                                       |
                                 configures
                                       |
                                       v
+------------------+         +-------------------+        +-----------------+
| GenerationConfig |-------->|   BaseProvider    |------->| GenerationResult|
| (5 fields)       | used by | (generates)       | returns| (6 fields)      |
+------------------+         +---+---+---+---+---+        +-----------------+
                                 |   |   |   |
                 +---------------+   |   |   +---------------+
                 |                   |   |                   |
                 v                   v   v                   v
          +-----------+    +-----------+ +-----------+  +-----------+
          |  Gemini   |    |  OpenAI   | | Anthropic |  |  Ollama   |
          | Provider  |    | Provider  | | Provider  |  | Provider  |
          +-----------+    +-----------+ +-----------+  +-----------+
                 |                   |
                 +----->  ModelInfo  |
                          (7 fields)
                 per-model metadata

==========================================================================

PaperAnalysis (13 fields) ◄──── PaperAnalyzer.analyze()
   |
   |  consumed by almost everything
   |
   +──────────> SystemArchitect.design_system()
   |                      |
   |                      v
   |             ArchitecturePlan (10 fields) ◄──┐
   |               |                             |
   |               +-- files: list[FileSpec]     | backward-
   |               |     (4 fields each)         | compatible
   |               |                             |
   +──────────> DecomposedPlanner.plan()         |
   |               |                             |
   |               v                             |
   |         PlanningResult (5 fields) ──────────┘
   |           |-- overall_plan: OverallPlan (6 fields)
   |           |-- architecture_design: ArchitectureDesign (4 fields)
   |           |-- logic_design: LogicDesign (3 fields)
   |           |-- config_content: str
   |           +-- combined_plan: ArchitecturePlan
   |
   +──────────> FileAnalyzer.analyze_all()
   |               |
   |               v
   |         dict[str, FileAnalysis] (8 fields each)
   |
   +──────────> CodeSynthesizer.generate_codebase()
   |               |
   |               v
   |         dict[str, str] (file_path -> content)
   |               |
   |               +──> CodeValidator.validate()
   |               |         |
   |               |         v
   |               |    ValidationReport (6 fields + 2 properties)
   |               |      +-- issues: list[ValidationIssue] (6 fields each)
   |               |
   |               +──> TestGenerator.generate_tests()
   |               |         |
   |               |         v
   |               |    dict[str, str] (test files)
   |               |
   |               +──> ExecutionSandbox.execute()
   |               |         |
   |               |         v
   |               |    ExecutionResult (7 fields)
   |               |         |
   |               |         v
   |               |    AutoDebugger.debug()
   |               |         |
   |               |         v
   |               |    list[DebugReport] (5 fields each)
   |               |      +-- fixes: list[DebugFix] (5 fields each)
   |               |
   |               +──> DevOpsGenerator.generate_all()
   |               |         |
   |               |         v
   |               |    dict[str, str] (devops files)
   |               |
   |               +──> ReferenceEvaluator.evaluate_*()
   |                         |
   |                         v
   |                    EvaluationScore (7 fields)
   |
   +──────────> EquationExtractor.extract()
   |               |
   |               v
   |         list[ExtractedEquation] (7 fields each)
   |
   +──────────> ConfigGenerator.generate()
                   |
                   v
             str (YAML content)


SelfRefiner.refine(artifact, ...) ──> RefinementResult (6 fields)
   Wraps: OverallPlan, ArchitectureDesign, LogicDesign,
          FileAnalysis, config (str), code (str)


BaseAgent ◄──── communicate() ──> AgentMessage (3 fields)
   |
   v
AgentOrchestrator (drives all stages)
```

### Containment Relationships

```
PlanningResult
  +-- OverallPlan
  +-- ArchitectureDesign
  +-- LogicDesign
  +-- ArchitecturePlan
        +-- list[FileSpec]

ValidationReport
  +-- list[ValidationIssue]

DebugReport
  +-- list[DebugFix]

RefinementResult
  +-- original: Any (wrapped artifact)
  +-- refined: Any (wrapped artifact)
```

---

## 5. JSON Schema Examples

### 5.1 PaperAnalysis

Example JSON produced by `PaperAnalyzer.analyze()`:

```json
{
  "title": "Attention Is All You Need",
  "authors": [
    "Ashish Vaswani",
    "Noam Shazeer",
    "Niki Parmar",
    "Jakob Uszkoreit",
    "Llion Jones",
    "Aidan N. Gomez",
    "Lukasz Kaiser",
    "Illia Polosukhin"
  ],
  "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely...",
  "sections": {
    "Introduction": "The dominant sequence transduction models are based on...",
    "Background": "The goal of reducing sequential computation...",
    "Model Architecture": "Most competitive neural sequence transduction models...",
    "Why Self-Attention": "In this section we compare various aspects...",
    "Training": "This section describes the training regime...",
    "Results": "On the WMT 2014 English-to-German translation task...",
    "Conclusion": "In this work, we presented the Transformer..."
  },
  "equations": [
    "\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V",
    "\\text{MultiHead}(Q, K, V) = \\text{Concat}(\\text{head}_1, ..., \\text{head}_h)W^O",
    "\\text{head}_i = \\text{Attention}(QW_i^Q, KW_i^K, VW_i^V)",
    "\\text{FFN}(x) = \\max(0, xW_1 + b_1)W_2 + b_2",
    "PE_{(pos, 2i)} = \\sin(pos / 10000^{2i/d_{\\text{model}}})",
    "PE_{(pos, 2i+1)} = \\cos(pos / 10000^{2i/d_{\\text{model}}})",
    "L_{ls} = -(1 - \\epsilon) \\log p(y) - \\epsilon \\sum_k \\frac{1}{K} \\log p(k)"
  ],
  "hyperparameters": {
    "d_model": "512",
    "d_ff": "2048",
    "num_heads": "8",
    "num_layers": "6",
    "d_k": "64",
    "d_v": "64",
    "dropout": "0.1",
    "learning_rate": "varies (warmup schedule)",
    "warmup_steps": "4000",
    "batch_size": "25000 tokens",
    "label_smoothing": "0.1",
    "optimizer": "Adam",
    "adam_beta1": "0.9",
    "adam_beta2": "0.98",
    "adam_epsilon": "1e-9"
  },
  "architecture_description": "The Transformer follows an encoder-decoder structure using stacked self-attention and point-wise, fully connected layers for both the encoder and decoder. The encoder maps an input sequence of symbol representations to a sequence of continuous representations. Given z, the decoder then generates an output sequence of symbols one element at a time. At each step the model is auto-regressive, consuming the previously generated symbols as additional input when generating the next.",
  "key_contributions": [
    "First sequence transduction model based entirely on attention",
    "Multi-head attention mechanism for jointly attending to information from different representation subspaces",
    "Achieves state-of-the-art BLEU on WMT 2014 English-to-German (28.4) and English-to-French (41.0)",
    "Trains significantly faster than architectures based on recurrent or convolutional layers"
  ],
  "datasets_mentioned": [
    "WMT 2014 English-German",
    "WMT 2014 English-French"
  ],
  "loss_functions": [
    "L_{ls} = -(1 - \\epsilon) \\log p(y) - \\epsilon \\sum_k \\frac{1}{K} \\log p(k)"
  ]
}
```

### 5.2 ArchitecturePlan

Example JSON produced by `SystemArchitect.design_system()` or `DecomposedPlanner._to_architecture_plan()`:

```json
{
  "repo_name": "attention-is-all-you-need",
  "description": "PyTorch implementation of the Transformer architecture from 'Attention Is All You Need'",
  "python_version": "3.10",
  "files": [
    {
      "path": "config.yaml",
      "description": "Hyperparameter configuration file with all values from the paper.",
      "dependencies": [],
      "priority": -2
    },
    {
      "path": "requirements.txt",
      "description": "Python dependencies.",
      "dependencies": [],
      "priority": -1
    },
    {
      "path": "model/attention.py",
      "description": "Multi-head attention mechanism. Implements scaled dot-product attention and multi-head attention with learned projections W^Q, W^K, W^V, W^O.",
      "dependencies": [],
      "priority": 1
    },
    {
      "path": "model/positional_encoding.py",
      "description": "Sinusoidal positional encoding using sin/cos functions at different frequencies.",
      "dependencies": [],
      "priority": 1
    },
    {
      "path": "model/feed_forward.py",
      "description": "Position-wise feed-forward network: FFN(x) = max(0, xW1+b1)W2+b2.",
      "dependencies": [],
      "priority": 2
    },
    {
      "path": "model/encoder.py",
      "description": "Transformer encoder: N=6 identical layers, each with multi-head attention + FFN + residual connections + layer norm.",
      "dependencies": ["model/attention.py", "model/feed_forward.py", "model/positional_encoding.py"],
      "priority": 3
    },
    {
      "path": "model/decoder.py",
      "description": "Transformer decoder: N=6 identical layers with masked multi-head attention, encoder-decoder attention, and FFN.",
      "dependencies": ["model/attention.py", "model/feed_forward.py", "model/positional_encoding.py"],
      "priority": 3
    },
    {
      "path": "model/transformer.py",
      "description": "Complete Transformer model combining encoder and decoder with final linear + softmax layer.",
      "dependencies": ["model/encoder.py", "model/decoder.py"],
      "priority": 4
    },
    {
      "path": "data/dataset.py",
      "description": "WMT translation dataset loader with BPE tokenization and batching by approximate sequence length.",
      "dependencies": [],
      "priority": 2
    },
    {
      "path": "train.py",
      "description": "Training loop with Adam optimizer, learning rate warmup schedule, label smoothing cross-entropy loss, and gradient clipping.",
      "dependencies": ["model/transformer.py", "data/dataset.py"],
      "priority": 6
    },
    {
      "path": "inference.py",
      "description": "Beam search inference with trained Transformer model.",
      "dependencies": ["model/transformer.py"],
      "priority": 8
    },
    {
      "path": "README.md",
      "description": "Project README for Attention Is All You Need.",
      "dependencies": [],
      "priority": 100
    }
  ],
  "requirements": [
    "numpy",
    "pyyaml",
    "tensorboard",
    "torch>=2.0",
    "torchtext"
  ],
  "directory_tree": "attention-is-all-you-need/\n  config.yaml\n  requirements.txt\n  model/\n    __init__.py\n    attention.py\n    positional_encoding.py\n    feed_forward.py\n    encoder.py\n    decoder.py\n    transformer.py\n  data/\n    dataset.py\n  train.py\n  inference.py\n  README.md",
  "config_schema": {
    "type": "object",
    "description": "See config.yaml"
  },
  "training_entrypoint": "train.py",
  "inference_entrypoint": "inference.py",
  "readme_outline": "# Attention Is All You Need\n\n## Overview\nPyTorch implementation of the Transformer.\n\n## Training\n```bash\npython train.py\n```"
}
```

### 5.3 ValidationReport

Example JSON produced by `CodeValidator.validate()`:

```json
{
  "score": 82.0,
  "equation_coverage": 85.7,
  "hyperparam_coverage": 93.3,
  "summary": "The implementation is largely faithful to the paper. All major architectural components are present. Minor issues with attention mask handling and missing warm-up schedule details.",
  "passed": true,
  "issues": [
    {
      "severity": "critical",
      "file_path": "model/attention.py",
      "line_hint": "line 45-50",
      "description": "Scaled dot-product attention divides by sqrt(d_model) instead of sqrt(d_k). The paper specifies d_k = d_model / h.",
      "suggestion": "Change the scaling factor from math.sqrt(self.d_model) to math.sqrt(self.d_k) where d_k = d_model // num_heads.",
      "category": "equation"
    },
    {
      "severity": "warning",
      "file_path": "train.py",
      "line_hint": "line 80-90",
      "description": "Learning rate warmup schedule uses linear warmup but the paper specifies: lr = d_model^{-0.5} * min(step^{-0.5}, step * warmup^{-1.5}).",
      "suggestion": "Implement the exact Noam learning rate schedule from the paper.",
      "category": "hyperparameter"
    },
    {
      "severity": "warning",
      "file_path": "model/decoder.py",
      "line_hint": "line 30",
      "description": "Decoder self-attention mask is not applied, allowing the model to attend to future positions.",
      "suggestion": "Add a causal mask (upper triangular) to the decoder self-attention.",
      "category": "logic"
    },
    {
      "severity": "info",
      "file_path": "model/transformer.py",
      "line_hint": "line 15",
      "description": "Missing type hints for forward() method parameters.",
      "suggestion": "Add type hints: def forward(self, src: Tensor, tgt: Tensor, src_mask: Optional[Tensor] = None, ...) -> Tensor",
      "category": "style"
    }
  ]
}
```

### 5.4 PlanningResult

Example JSON structure (conceptual -- PlanningResult wraps dataclasses, not raw JSON):

```json
{
  "overall_plan": {
    "core_components": [
      "Multi-Head Attention",
      "Positional Encoding",
      "Position-wise Feed-Forward Network",
      "Encoder Stack (N=6)",
      "Decoder Stack (N=6)",
      "Label Smoothing Cross-Entropy Loss"
    ],
    "methods_to_implement": [
      "Scaled Dot-Product Attention",
      "Multi-Head Attention with projections",
      "Noam Learning Rate Schedule",
      "Beam Search Decoding",
      "BPE Tokenization"
    ],
    "training_objectives": [
      "Cross-entropy loss with label smoothing (epsilon=0.1)",
      "Adam optimizer with beta1=0.9, beta2=0.98, epsilon=1e-9"
    ],
    "data_processing_steps": [
      "Load WMT 2014 EN-DE/EN-FR parallel corpus",
      "Apply BPE tokenization with shared vocabulary",
      "Batch by approximate sequence length (~25000 tokens per batch)",
      "Apply padding and create attention masks"
    ],
    "evaluation_protocols": [
      "BLEU score on newstest2014",
      "Perplexity on validation set",
      "Beam search with beam_size=4 and length_penalty=0.6"
    ],
    "summary": "Implement the Transformer architecture: a fully attention-based encoder-decoder model with 6 layers each, 8 attention heads, d_model=512, d_ff=2048. Train on WMT 2014 EN-DE using Adam with warmup schedule and label smoothing."
  },
  "architecture_design": {
    "file_list": [
      {"path": "model/attention.py", "description": "Scaled dot-product and multi-head attention", "module": "model"},
      {"path": "model/encoder.py", "description": "Transformer encoder stack", "module": "model"},
      {"path": "model/decoder.py", "description": "Transformer decoder stack", "module": "model"},
      {"path": "train.py", "description": "Training loop with warmup schedule", "module": "training"}
    ],
    "class_diagram_mermaid": "classDiagram\n  class MultiHeadAttention {\n    +int d_model\n    +int num_heads\n    +forward(Q, K, V, mask)\n  }\n  class TransformerEncoder {\n    +int num_layers\n    +forward(src, src_mask)\n  }\n  TransformerEncoder --> MultiHeadAttention",
    "sequence_diagram_mermaid": "sequenceDiagram\n  participant Trainer\n  participant Encoder\n  participant Decoder\n  Trainer->>Encoder: encode(src)\n  Encoder-->>Trainer: memory\n  Trainer->>Decoder: decode(tgt, memory)\n  Decoder-->>Trainer: output",
    "module_relationships": [
      {"from": "model/encoder.py", "to": "model/attention.py", "relationship": "imports"},
      {"from": "model/decoder.py", "to": "model/attention.py", "relationship": "imports"},
      {"from": "train.py", "to": "model/transformer.py", "relationship": "imports"}
    ]
  },
  "logic_design": {
    "execution_order": [
      "model/attention.py",
      "model/positional_encoding.py",
      "model/feed_forward.py",
      "model/encoder.py",
      "model/decoder.py",
      "model/transformer.py",
      "data/dataset.py",
      "train.py",
      "inference.py"
    ],
    "dependency_graph": {
      "model/attention.py": [],
      "model/positional_encoding.py": [],
      "model/feed_forward.py": [],
      "model/encoder.py": ["model/attention.py", "model/feed_forward.py", "model/positional_encoding.py"],
      "model/decoder.py": ["model/attention.py", "model/feed_forward.py", "model/positional_encoding.py"],
      "model/transformer.py": ["model/encoder.py", "model/decoder.py"],
      "data/dataset.py": [],
      "train.py": ["model/transformer.py", "data/dataset.py"],
      "inference.py": ["model/transformer.py"]
    },
    "file_specifications": [
      {
        "path": "model/attention.py",
        "logic_description": "Implement ScaledDotProductAttention and MultiHeadAttention classes. Attention(Q,K,V)=softmax(QK^T/sqrt(d_k))V. MultiHead projects Q,K,V with learned W^Q,W^K,W^V matrices, applies h parallel attention heads, concatenates, projects with W^O.",
        "key_functions": ["scaled_dot_product_attention", "MultiHeadAttention.__init__", "MultiHeadAttention.forward"]
      }
    ]
  },
  "config_content": "# Transformer config from 'Attention Is All You Need'\nmodel:\n  d_model: 512\n  d_ff: 2048\n  num_heads: 8\n  num_layers: 6\n  d_k: 64\n  d_v: 64\n  dropout: 0.1\n\ntraining:\n  learning_rate: 0.0001\n  warmup_steps: 4000\n  batch_size: 25000\n  label_smoothing: 0.1\n  optimizer: adam\n  adam_beta1: 0.9\n  adam_beta2: 0.98\n  adam_epsilon: 1.0e-9"
}
```

---

## 6. Configuration Schema

### R2RConfig Full Reference

```yaml
# ── Provider Configuration ──────────────────────────────────────

# Provider selection: "auto", "gemini", "openai", "anthropic", "ollama"
# "auto" triggers the auto-detection algorithm (see Low-Level Design)
# Env: R2R_PROVIDER
default_provider: "auto"

# Model name override. Empty string uses the provider's default model.
# Examples: "gpt-4o", "gemini-2.5-pro-preview-05-06", "claude-sonnet-4-20250514"
# Env: R2R_MODEL
default_model: ""


# ── Pipeline Toggles ────────────────────────────────────────────

# Enable the code validation stage (equation fidelity, dimension checks)
# Env: R2R_SKIP_VALIDATION (set to "true" to disable)
enable_validation: true

# Enable automatic test suite generation (pytest)
# Env: R2R_SKIP_TESTS (set to "true" to disable)
enable_test_generation: true

# Enable dedicated equation extraction (vision + text)
enable_equation_extraction: true

# Enable pipeline stage caching (avoids redundant API calls)
# Env: R2R_NO_CACHE (set to "true" to disable)
enable_caching: true

# Maximum validation -> auto-fix cycles
max_fix_iterations: 2


# ── Download Settings ───────────────────────────────────────────

# HTTP timeout for PDF download (seconds)
pdf_timeout: 120

# Maximum PDF file size (megabytes)
pdf_max_size_mb: 100


# ── Generation Settings ─────────────────────────────────────────

# Temperature for code generation (lower = more deterministic)
code_temperature: 0.15

# Temperature for analysis and planning
analysis_temperature: 0.1

# Maximum output tokens for code generation
max_code_tokens: 16384

# Maximum output tokens for analysis/planning
max_analysis_tokens: 8192


# ── Vision Settings ─────────────────────────────────────────────

# Maximum PDF pages to convert to images for diagram extraction
max_diagram_pages: 30

# DPI for PDF page-to-image conversion
diagram_dpi: 150

# Number of page images per vision API call
vision_batch_size: 4


# ── Cache Settings ──────────────────────────────────────────────

# Cache directory path (relative to working directory)
# Env: R2R_CACHE_DIR
cache_dir: ".r2r_cache"


# ── Output Settings ─────────────────────────────────────────────

# Enable verbose logging (file-by-file progress, validation details)
# Env: R2R_VERBOSE (set to "true" to enable)
verbose: false
```

### AgentOrchestrator Config (Agent Mode Only)

The `AgentOrchestrator` uses a separate config dict with these defaults:

```yaml
# Enable self-refine verify/refine loops after planning and file analysis
enable_refine: false

# Enable execution sandbox (runs generated code in Docker or locally)
enable_execution: false

# Enable test generation stage
enable_tests: true

# Enable reference-based or reference-free evaluation
enable_evaluation: false

# Enable DevOps file generation (Dockerfile, Makefile, CI, setup.py)
enable_devops: true

# Pause after planning for user review (shows architecture, waits for Enter)
interactive: false

# Maximum auto-debug iterations (execution -> LLM fix -> re-execute)
max_debug_iterations: 3

# Maximum self-refine iterations per artifact
max_refine_iterations: 2

# Maximum validation -> auto-fix iterations
max_fix_iterations: 2

# Path to reference implementation directory (for evaluation)
reference_dir: null

# Enable verbose logging
verbose: false
```

### Environment Variable Summary

| Env Variable | Config Field | Default | Description |
|-------------|-------------|---------|-------------|
| `R2R_PROVIDER` | `default_provider` | `"auto"` | Provider name |
| `R2R_MODEL` | `default_model` | `""` | Model name |
| `R2R_SKIP_VALIDATION` | `enable_validation` (inverted) | `"false"` | Set `"true"` to skip |
| `R2R_SKIP_TESTS` | `enable_test_generation` (inverted) | `"false"` | Set `"true"` to skip |
| `R2R_NO_CACHE` | `enable_caching` (inverted) | `"false"` | Set `"true"` to disable |
| `R2R_CACHE_DIR` | `cache_dir` | `".r2r_cache"` | Cache directory |
| `R2R_VERBOSE` | `verbose` | `"false"` | Set `"true"` to enable |
| `GEMINI_API_KEY` | -- | -- | Gemini provider API key |
| `OPENAI_API_KEY` | -- | -- | OpenAI provider API key |
| `ANTHROPIC_API_KEY` | -- | -- | Anthropic provider API key |
| `OLLAMA_HOST` | -- | `http://localhost:11434` | Ollama server URL |
| `GROBID_URL` | -- | `http://localhost:8070/api/processFulltextDocument` | GROBID server URL |
