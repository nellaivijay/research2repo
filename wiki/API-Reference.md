# API Reference

This document covers the programmatic Python API for Research2Repo v3.0. Use these APIs to integrate Research2Repo into your own scripts, notebooks, or automation pipelines instead of (or in addition to) the CLI.

---

## Table of Contents

- [1. Quick Start (Programmatic)](#1-quick-start-programmatic)
- [2. Provider API](#2-provider-api)
  - [get\_provider()](#get_provider)
  - [BaseProvider Interface](#baseprovider-interface)
  - [ProviderRegistry](#providerregistry)
  - [Data Classes](#provider-data-classes)
- [3. Core API](#3-core-api)
  - [PaperAnalyzer](#paperanalyzer)
  - [SystemArchitect](#systemarchitect)
  - [DecomposedPlanner](#decomposedplanner)
  - [FileAnalyzer](#fileanalyzer)
  - [CodeSynthesizer](#codesynthesizer)
  - [CodeValidator](#codevalidator)
  - [SelfRefiner](#selfrefiner)
  - [PaperParser](#paperparser)
- [4. Advanced API](#4-advanced-api)
  - [ExecutionSandbox](#executionsandbox)
  - [AutoDebugger](#autodebugger)
  - [ReferenceEvaluator](#referenceevaluator)
  - [DevOpsGenerator](#devopsgenerator)
- [5. Agent API (Highest Level)](#5-agent-api-highest-level)
  - [AgentOrchestrator](#agentorchestrator)
- [6. Cache API](#6-cache-api)
- [7. Return Type Reference](#7-return-type-reference)

---

## 1. Quick Start (Programmatic)

The simplest way to run the full pipeline from Python:

```python
from providers import get_provider
from core.analyzer import PaperAnalyzer
from core.architect import SystemArchitect
from core.coder import CodeSynthesizer
from core.validator import CodeValidator

# 1. Obtain a provider (auto-detects from environment)
provider = get_provider()

# 2. Analyze the paper
analyzer = PaperAnalyzer(provider=provider)
document = analyzer.upload_document("paper.pdf")
diagrams = analyzer.extract_diagrams_to_mermaid("paper.pdf")
analysis = analyzer.analyze(document, diagrams)

# 3. Design the architecture
architect = SystemArchitect(provider=provider)
plan = architect.design_system(analysis, document, diagrams)

# 4. Generate code
coder = CodeSynthesizer(provider=provider)
files = coder.generate_codebase(analysis, plan, document)

# 5. Validate and auto-fix
validator = CodeValidator(provider=provider)
report = validator.validate(files, analysis, plan)
if report.critical_count > 0:
    files = validator.fix_issues(files, report, analysis)

# 6. Write files to disk
import os
output_dir = "./output"
for path, content in files.items():
    full_path = os.path.join(output_dir, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)
```

For the highest-level, fully automated experience (agent mode), see [AgentOrchestrator](#agentorchestrator).

---

## 2. Provider API

The provider layer abstracts all LLM interactions behind a uniform interface. Every provider (Gemini, OpenAI, Anthropic, Ollama) implements the same `BaseProvider` abstract class.

### get_provider()

**Module:** `providers`

The convenience factory function that returns the best available provider.

```python
from providers import get_provider
from providers.base import ModelCapability

provider = get_provider(
    provider_name=None,       # "gemini", "openai", "anthropic", "ollama", or None for auto
    model_name=None,          # Override the provider's default model
    api_key=None,             # Override the API key (otherwise read from env)
    required_capability=None, # ModelCapability enum to influence auto-selection
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `provider_name` | `Optional[str]` | `None` | Explicit provider name. If `None`, auto-detects based on available credentials and `required_capability`. |
| `model_name` | `Optional[str]` | `None` | Override the default model for the chosen provider. |
| `api_key` | `Optional[str]` | `None` | API key override. If `None`, reads from the corresponding environment variable (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). |
| `required_capability` | `Optional[ModelCapability]` | `None` | When auto-detecting, prefer providers that support this capability. |

**Returns:** `BaseProvider` -- An initialized provider instance.

**Raises:** `RuntimeError` if no providers are available (no API keys set, no Ollama running).

**Auto-detection priority by capability:**

| Capability | Priority Order |
|---|---|
| `LONG_CONTEXT` | gemini, anthropic, openai, ollama |
| `VISION` | gemini, openai, anthropic, ollama |
| `CODE_GENERATION` | anthropic, openai, gemini, ollama |
| `STRUCTURED_OUTPUT` | openai, gemini, anthropic, ollama |
| `FILE_UPLOAD` | gemini |

**Example:**

```python
# Auto-detect best provider for vision tasks
vision_provider = get_provider(required_capability=ModelCapability.VISION)

# Explicitly use OpenAI with a specific model
openai_provider = get_provider(provider_name="openai", model_name="gpt-4o")

# Use Ollama with a local model
local_provider = get_provider(provider_name="ollama", model_name="codellama:34b")
```

---

### BaseProvider Interface

**Module:** `providers.base`

All provider implementations inherit from `BaseProvider`. This is the contract every provider must satisfy.

```python
from providers.base import BaseProvider
```

#### Constructor

```python
BaseProvider(
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
)
```

If `model_name` is `None`, the provider's `default_model()` is used.

#### Abstract Methods (must be implemented by every provider)

##### generate()

Generate text from a prompt.

```python
result: GenerationResult = provider.generate(
    prompt: str,                            # The user prompt / input text
    system_prompt: Optional[str] = None,    # System-level instruction
    config: Optional[GenerationConfig] = None,  # Generation parameters
    images: Optional[list[bytes]] = None,   # Image bytes for vision models
)
```

**Returns:** `GenerationResult` containing the model's text response plus token usage metadata.

**Example:**

```python
from providers.base import GenerationConfig

result = provider.generate(
    prompt="Explain the attention mechanism in transformers.",
    system_prompt="You are an ML expert.",
    config=GenerationConfig(temperature=0.2, max_output_tokens=4096),
)
print(result.text)
print(f"Tokens used: {result.input_tokens} in, {result.output_tokens} out")
```

##### generate_structured()

Generate structured JSON output conforming to a schema.

```python
data: dict = provider.generate_structured(
    prompt: str,                            # The user prompt
    schema: dict,                           # JSON schema the output must conform to
    system_prompt: Optional[str] = None,    # System instruction
    config: Optional[GenerationConfig] = None,  # Generation parameters
)
```

**Returns:** `dict` -- Parsed JSON matching the provided schema.

**Example:**

```python
schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "authors": {"type": "array", "items": {"type": "string"}},
    },
}
data = provider.generate_structured(
    prompt="Extract the title and authors from this paper excerpt: ...",
    schema=schema,
)
print(data["title"])    # "Attention Is All You Need"
print(data["authors"])  # ["Vaswani", "Shazeer", ...]
```

##### available_models()

List all models available through this provider.

```python
models: list[ModelInfo] = provider.available_models()
```

**Returns:** `list[ModelInfo]` -- Metadata for each supported model.

##### default_model()

Return the default model name for this provider.

```python
name: str = provider.default_model()
```

#### Concrete Methods (provided by BaseProvider)

##### supports()

Check if the current model supports a given capability.

```python
can_see: bool = provider.supports(ModelCapability.VISION)
```

##### upload_file()

Upload a file for use in prompts (if the provider supports `FILE_UPLOAD`).

```python
file_handle: object = provider.upload_file("paper.pdf")
```

**Raises:** `NotImplementedError` if the provider does not support file uploads. Currently only GeminiProvider supports this via the Gemini File API.

##### model_info()

Get metadata for the currently selected model.

```python
info: Optional[ModelInfo] = provider.model_info()
if info:
    print(f"Max context: {info.max_context_tokens} tokens")
    print(f"Cost: ${info.cost_per_1k_input}/1K input, ${info.cost_per_1k_output}/1K output")
```

---

### ProviderRegistry

**Module:** `providers.registry`

A static registry for creating and discovering providers.

```python
from providers.registry import ProviderRegistry
```

#### ProviderRegistry.list_providers()

Return the names of all registered providers.

```python
names: list[str] = ProviderRegistry.list_providers()
# ["gemini", "openai", "anthropic", "ollama"]
```

#### ProviderRegistry.create()

Create a provider instance by name.

```python
provider: BaseProvider = ProviderRegistry.create(
    provider_name: str,                 # "gemini", "openai", "anthropic", "ollama"
    api_key: Optional[str] = None,      # Override API key
    model_name: Optional[str] = None,   # Override default model
    **kwargs,                           # Extra args passed to the provider constructor
)
```

**Raises:** `ValueError` if `provider_name` is not recognized.

#### ProviderRegistry.detect_available()

Detect which providers have credentials configured in the environment.

```python
available: list[str] = ProviderRegistry.detect_available()
# e.g. ["gemini", "ollama"]
```

Checks `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` environment variables. For Ollama, pings `http://localhost:11434/api/tags`.

#### ProviderRegistry.best_for()

Return the best available provider name for a given capability.

```python
best: Optional[str] = ProviderRegistry.best_for(ModelCapability.VISION)
# e.g. "gemini"
```

#### ProviderRegistry.estimate_cost()

Estimate cost in USD for a given usage.

```python
cost: float = ProviderRegistry.estimate_cost(
    provider_name="openai",
    model_name="gpt-4o",
    input_tokens=50000,
    output_tokens=10000,
)
print(f"Estimated cost: ${cost:.4f}")
```

#### ProviderRegistry.register()

Register a custom provider at runtime.

```python
ProviderRegistry.register(
    name="my_provider",
    module_path="my_package.provider",
    class_name="MyProvider",
    env_key="MY_API_KEY",
)
```

---

### Provider Data Classes

**Module:** `providers.base`

#### ModelCapability

Enum of capabilities a model provider may support.

```python
from providers.base import ModelCapability

class ModelCapability(Enum):
    TEXT_GENERATION = auto()
    VISION = auto()              # Image/diagram understanding
    LONG_CONTEXT = auto()        # 100K+ token context windows
    STRUCTURED_OUTPUT = auto()   # JSON-mode / function calling
    CODE_GENERATION = auto()     # Optimized for code
    FILE_UPLOAD = auto()         # Native file upload API (Gemini)
    STREAMING = auto()           # Streaming responses
```

#### ModelInfo

Metadata about a specific model.

```python
from providers.base import ModelInfo

@dataclass
class ModelInfo:
    name: str                                   # e.g. "gemini-2.5-pro"
    provider: str                               # e.g. "gemini"
    max_context_tokens: int                     # e.g. 2_000_000
    max_output_tokens: int                      # e.g. 65536
    capabilities: list[ModelCapability] = []
    cost_per_1k_input: float = 0.0              # USD per 1K input tokens
    cost_per_1k_output: float = 0.0             # USD per 1K output tokens
```

#### GenerationConfig

Common generation parameters across all providers.

```python
from providers.base import GenerationConfig

@dataclass
class GenerationConfig:
    temperature: float = 0.2
    top_p: float = 0.95
    max_output_tokens: int = 8192
    stop_sequences: list[str] = []
    response_format: Optional[str] = None       # "json" or None
```

#### GenerationResult

Standardized response from any provider.

```python
from providers.base import GenerationResult

@dataclass
class GenerationResult:
    text: str                                   # The generated text
    model: str                                  # Model name that produced it
    input_tokens: int = 0                       # Prompt tokens consumed
    output_tokens: int = 0                      # Completion tokens generated
    finish_reason: str = "stop"                 # "stop", "length", etc.
    raw_response: Optional[object] = None       # Provider-specific raw response
```

---

## 3. Core API

The core modules implement the main pipeline stages: analysis, architecture design, planning, file analysis, code generation, validation, refinement, and paper parsing.

### PaperAnalyzer

**Module:** `core.analyzer`

Ingests a PDF, extracts text, identifies sections, extracts architecture diagrams via vision, and produces a structured `PaperAnalysis`.

```python
from core.analyzer import PaperAnalyzer, PaperAnalysis
```

#### Constructor

```python
analyzer = PaperAnalyzer(
    provider: Optional[BaseProvider] = None,         # Primary text provider (auto-detected if None)
    vision_provider: Optional[BaseProvider] = None,  # Vision provider for diagrams (auto-detected if None)
)
```

If `vision_provider` is not given, falls back to the primary provider if it supports VISION, or auto-detects a vision-capable provider.

#### upload_document()

Upload or extract text from a PDF.

```python
document: object = analyzer.upload_document("paper.pdf")
```

- If the provider supports `FILE_UPLOAD` (Gemini): uploads via the File API and returns a file handle.
- Otherwise: extracts text locally with PyPDF2 and returns the text string.

#### extract_diagrams_to_mermaid()

Extract architecture diagrams from the PDF and convert them to Mermaid.js.

```python
diagrams: list[str] = analyzer.extract_diagrams_to_mermaid("paper.pdf")
```

- Requires a vision-capable provider.
- Converts PDF pages to images via PyMuPDF (at 150 DPI, capped at 30 pages).
- Processes images in batches of 4 pages.
- Returns a list of Mermaid diagram strings. Returns an empty list if no vision provider is available.

#### analyze()

Perform full structured analysis of the paper.

```python
analysis: PaperAnalysis = analyzer.analyze(
    document: object,              # File handle or extracted text from upload_document()
    vision_context: list[str],     # Mermaid diagrams from extract_diagrams_to_mermaid()
)
```

**Returns:** `PaperAnalysis` dataclass with all extracted information.

#### PaperAnalysis Fields

```python
@dataclass
class PaperAnalysis:
    title: str                          # Paper title
    authors: list[str]                  # Author names
    abstract: str                       # Full abstract
    sections: dict[str, str]            # section_name -> content summary
    equations: list[str]                # LaTeX equation strings
    hyperparameters: dict[str, str]     # name -> value/description
    architecture_description: str       # Detailed model architecture description
    key_contributions: list[str]        # Main contributions
    datasets_mentioned: list[str]       # Referenced datasets
    loss_functions: list[str]           # Loss functions in LaTeX
    full_text: str                      # Full extracted text (empty for file-upload mode)
    diagrams_mermaid: list[str]         # Mermaid diagram strings
    raw_token_count: int                # Total tokens used for analysis
```

---

### SystemArchitect

**Module:** `core.architect`

Designs repository structure, module decomposition, and dependency lists from a paper analysis. Produces an `ArchitecturePlan` in a single LLM call.

```python
from core.architect import SystemArchitect, ArchitecturePlan, FileSpec
```

#### Constructor

```python
architect = SystemArchitect(
    provider: Optional[BaseProvider] = None,  # Auto-detected if None
)
```

#### design_system()

Design the repository architecture from a paper analysis.

```python
plan: ArchitecturePlan = architect.design_system(
    analysis: PaperAnalysis,                        # Structured paper analysis
    document: Optional[object] = None,              # Raw document handle for extra context
    vision_context: Optional[list[str]] = None,     # Mermaid diagrams
)
```

**Returns:** `ArchitecturePlan` with complete file specifications. Automatically ensures essential files (config.yaml, README.md, requirements.txt) are included.

#### ArchitecturePlan Fields

```python
@dataclass
class ArchitecturePlan:
    repo_name: str                      # Short kebab-case name
    description: str                    # One-line description
    python_version: str = "3.10"        # Target Python version
    files: list[FileSpec]               # Ordered file specifications
    requirements: list[str]             # pip packages needed
    directory_tree: str                 # Visual tree string
    config_schema: dict                 # JSON schema for config.yaml
    training_entrypoint: str            # e.g. "train.py"
    inference_entrypoint: str           # e.g. "inference.py"
    readme_outline: str                 # Markdown outline for README
```

#### FileSpec Fields

```python
@dataclass
class FileSpec:
    path: str                           # e.g. "model/transformer.py"
    description: str                    # What this file should contain
    dependencies: list[str] = []        # Other file paths this depends on
    priority: int = 0                   # Generation order (lower = first)
```

---

### DecomposedPlanner

**Module:** `core.planner`

A structured 4-step planning pipeline inspired by PaperCoder's decomposed planning approach. Breaks planning into Overall Plan, Architecture Design, Logic Design, and Config Generation.

```python
from core.planner import DecomposedPlanner, PlanningResult
```

#### Constructor

```python
planner = DecomposedPlanner(
    provider: Optional[BaseProvider] = None,  # Auto-detected if None
)
```

#### plan()

Execute the full 4-step planning pipeline.

```python
result: PlanningResult = planner.plan(
    analysis: PaperAnalysis,                        # From PaperAnalyzer
    document: Optional[object] = None,              # Reserved for future use
    vision_context: Optional[list[str]] = None,     # Already in analysis.diagrams_mermaid
)
```

**Returns:** `PlanningResult` containing all intermediate artefacts and a backward-compatible `ArchitecturePlan`.

#### PlanningResult Fields

```python
@dataclass
class PlanningResult:
    overall_plan: OverallPlan               # Step 1: high-level roadmap
    architecture_design: ArchitectureDesign  # Step 2: file list + Mermaid diagrams
    logic_design: LogicDesign               # Step 3: dependency graph + per-file logic
    config_content: str                     # Step 4: generated YAML configuration
    combined_plan: ArchitecturePlan         # Backward-compatible plan for downstream use
```

#### OverallPlan Fields

```python
@dataclass
class OverallPlan:
    core_components: list[str]          # Major components to implement
    methods_to_implement: list[str]     # Concrete algorithms
    training_objectives: list[str]      # Loss functions and goals
    data_processing_steps: list[str]    # Data loading/preprocessing steps
    evaluation_protocols: list[str]     # Metrics, benchmarks
    summary: str                        # One-paragraph implementation summary
```

#### ArchitectureDesign Fields

```python
@dataclass
class ArchitectureDesign:
    file_list: list[dict]               # [{"path": str, "description": str, "module": str}]
    class_diagram_mermaid: str          # Mermaid class diagram
    sequence_diagram_mermaid: str       # Mermaid sequence diagram
    module_relationships: list[dict]    # [{"from": str, "to": str, "relationship": str}]
```

#### LogicDesign Fields

```python
@dataclass
class LogicDesign:
    execution_order: list[str]          # Topologically sorted file paths
    dependency_graph: dict[str, list[str]]  # file_path -> [dependency paths]
    file_specifications: list[dict]     # [{"path", "logic_description", "key_functions"}]
```

---

### FileAnalyzer

**Module:** `core.file_analyzer`

Per-file analysis phase that produces detailed specifications for each file before code generation begins. Includes class hierarchies, function signatures, import lists, algorithmic steps, and test criteria.

```python
from core.file_analyzer import FileAnalyzer, FileAnalysis
```

#### Constructor

```python
fa = FileAnalyzer(
    provider: Optional[BaseProvider] = None,  # Auto-detected if None
)
```

#### analyze_all()

Analyze every file in the plan, accumulating context as each file is processed.

```python
file_analyses: dict[str, FileAnalysis] = fa.analyze_all(
    plan: ArchitecturePlan,
    analysis: PaperAnalysis,
)
```

Files are analyzed in the order they appear in `plan.files` (sorted by priority). Each subsequent file receives the analyses of all preceding files as additional context for cross-file consistency.

**Returns:** Dict mapping file path to `FileAnalysis`.

#### analyze_file()

Analyze a single file.

```python
fa_result: FileAnalysis = fa.analyze_file(
    file_spec: FileSpec,
    analysis: PaperAnalysis,
    plan: ArchitecturePlan,
    prior_analyses: dict[str, FileAnalysis],    # Previously analyzed files
)
```

#### FileAnalysis Fields

```python
@dataclass
class FileAnalysis:
    file_path: str
    classes: list[dict]         # [{"name", "attributes", "methods", "base_classes"}]
    functions: list[dict]       # [{"name", "args", "return_type", "description"}]
    imports: list[str]          # ["import torch", "from model.encoder import Encoder"]
    dependencies: list[str]     # Other project file paths this imports from
    algorithms: list[str]       # Ordered algorithmic steps from the paper
    input_output_spec: dict     # {"input": "Tensor[B, S, D]", "output": "Tensor[B, S, V]"}
    test_criteria: list[str]    # What to verify: dimensions, numerical ranges, etc.
```

---

### CodeSynthesizer

**Module:** `core.coder`

Generates each source file according to the `ArchitecturePlan`, using the full paper analysis as context. Files are generated one at a time in dependency order, with previously generated files fed as context.

```python
from core.coder import CodeSynthesizer
```

#### Constructor

```python
coder = CodeSynthesizer(
    provider: Optional[BaseProvider] = None,  # Auto-detected if None
)
```

#### generate_codebase()

Generate all files specified in the architecture plan.

```python
files: dict[str, str] = coder.generate_codebase(
    analysis: PaperAnalysis,                    # Paper analysis with equations, hyperparams
    plan: ArchitecturePlan,                     # Architecture plan with file specifications
    document: Optional[object] = None,          # Uploaded document handle (Gemini)
)
```

**Returns:** Dict mapping file paths to their generated content.

**Token allocation per file type:**

| File Type | Max Output Tokens |
|---|---|
| Config files (`.yaml`, `.yml`, `.toml`, `.txt`) | 4,096 |
| Markdown files (`.md`) | 4,096 |
| Model and training files | 16,384 |
| All other Python files | 8,192 |

---

### CodeValidator

**Module:** `core.validator`

Self-review pass that verifies generated code against the original paper. Checks equation fidelity, dimension consistency, hyperparameter completeness, loss function accuracy, and code quality.

```python
from core.validator import CodeValidator, ValidationReport, ValidationIssue
```

#### Constructor

```python
validator = CodeValidator(
    provider: Optional[BaseProvider] = None,  # Auto-detected if None
)
```

#### validate()

Run full validation of generated code against the paper.

```python
report: ValidationReport = validator.validate(
    generated_files: dict[str, str],    # file_path -> content
    analysis: PaperAnalysis,            # Original paper analysis
    plan: ArchitecturePlan,             # Architecture plan
)
```

**Returns:** `ValidationReport` with issues and scores.

#### fix_issues()

Attempt to auto-fix critical issues identified in validation.

```python
fixed_files: dict[str, str] = validator.fix_issues(
    generated_files: dict[str, str],
    report: ValidationReport,
    analysis: PaperAnalysis,
)
```

**Returns:** Updated file dict with fixes applied. Only files containing critical issues are modified.

#### ValidationReport Fields

```python
@dataclass
class ValidationReport:
    issues: list[ValidationIssue]       # All issues found
    score: float                        # 0-100 fidelity score
    equation_coverage: float            # % of paper equations found in code
    hyperparam_coverage: float          # % of paper hyperparams that are configurable
    summary: str                        # Text summary
    passed: bool                        # True if score >= 80 and no critical issues

    @property
    def critical_count(self) -> int     # Number of critical-severity issues

    @property
    def warning_count(self) -> int      # Number of warning-severity issues
```

#### ValidationIssue Fields

```python
@dataclass
class ValidationIssue:
    severity: str           # "critical", "warning", "info"
    file_path: str
    line_hint: str          # Approximate location
    description: str
    suggestion: str
    category: str           # "equation", "dimension", "hyperparameter", "style", "logic"
```

---

### SelfRefiner

**Module:** `core.refiner`

Implements a verify-then-refine loop for any pipeline stage output. The LLM first critiques an artefact against the paper context, then refines it. The loop repeats up to `max_iterations`, stopping early if no issues remain.

```python
from core.refiner import SelfRefiner, RefinementResult
```

#### Constructor

```python
refiner = SelfRefiner(
    provider: Optional[BaseProvider] = None,  # Auto-detected if None
    max_iterations: int = 2,                  # Max refine cycles (0 = verify only)
)
```

#### refine()

Execute the full verify-then-refine loop.

```python
result: RefinementResult = refiner.refine(
    artifact: Any,              # The artefact (dict, dataclass, or string)
    artifact_type: str,         # See supported types below
    context: str,               # Paper context string for grounding
    schema: Optional[dict] = None,  # JSON schema for structured artefacts
)
```

**Supported artifact types:**

| Type | Format | Description |
|---|---|---|
| `"overall_plan"` | JSON | High-level implementation roadmap |
| `"architecture_design"` | JSON | File structure and diagrams |
| `"logic_design"` | JSON | Dependency graph and per-file logic |
| `"file_analysis"` | JSON | Per-file specifications |
| `"config"` | Text | YAML configuration |
| `"code"` | Text | Python source code |

**Raises:** `ValueError` if `artifact_type` is not recognized.

#### verify()

Critique an artefact without refining it.

```python
critique: str, issues: list[str] = refiner.verify(
    artifact: Any,
    artifact_type: str,
    context: str,
)
```

#### refine_artifact()

Produce a single refined version of an artefact given a critique (no loop).

```python
refined: Any = refiner.refine_artifact(
    artifact: Any,
    critique: str,
    artifact_type: str,
    context: str,
    schema: Optional[dict] = None,
)
```

#### RefinementResult Fields

```python
@dataclass
class RefinementResult:
    original: Any               # Artefact before refinement
    refined: Any                # Artefact after refinement
    critique: str               # Final critique text
    improvements: list[str]     # Specific improvements made
    iterations: int             # Number of iterations executed
    improved: bool              # Whether any changes were made
```

---

### PaperParser

**Module:** `core.paper_parser`

Multi-backend paper parser that converts PDF files into structured `ParsedPaper` objects. Tries parsing backends in order of quality: doc2json, GROBID, PyMuPDF, PyPDF2. Falls back gracefully when a backend is unavailable.

```python
from core.paper_parser import PaperParser, ParsedPaper
```

#### Constructor

```python
parser = PaperParser()
```

No arguments required. The parser automatically selects the best available backend.

#### parse()

Parse a PDF into a structured `ParsedPaper`.

```python
parsed: ParsedPaper = parser.parse("paper.pdf")
```

**Raises:**
- `FileNotFoundError` if the PDF does not exist.
- `RuntimeError` if every parsing backend fails.

**Backend priority:**

| Priority | Backend | Quality | Requirements |
|---|---|---|---|
| 1 | s2orc-doc2json | Highest | `pip install s2orc-doc2json` |
| 2 | GROBID REST API | High | Running GROBID server at `localhost:8070` |
| 3 | PyMuPDF (fitz) | Good | `pip install PyMuPDF` |
| 4 | PyPDF2 | Basic | `pip install PyPDF2` (included in core deps) |

#### ParsedPaper Fields

```python
@dataclass
class ParsedPaper:
    title: str
    authors: list[str]
    abstract: str
    sections: list[dict]        # [{"name": str, "content": str, "subsections": list}]
    figures: list[dict]         # [{"caption": str, "page_num": int}]
    tables: list[dict]          # [{"caption": str, "content": str}]
    equations_raw: list[str]    # Raw LaTeX strings
    references: list[str]       # Referenced paper titles
    full_text: str
    metadata: dict              # Backend-specific metadata
```

---

## 4. Advanced API

Advanced modules provide execution sandboxing, auto-debugging, evaluation, and DevOps generation.

### ExecutionSandbox

**Module:** `advanced.executor`

Docker-based (or local) execution sandbox for testing generated repositories. Builds a Docker image, runs the entrypoint with configurable timeout, captures output, and classifies errors.

```python
from advanced.executor import ExecutionSandbox, ExecutionResult
```

#### Constructor

```python
sandbox = ExecutionSandbox(
    use_docker: bool = True,    # Use Docker isolation (falls back to local if unavailable)
    timeout: int = 300,         # Maximum execution time in seconds
    gpu: bool = False,          # Pass --gpus all to docker run
)
```

If `use_docker=True` but Docker is not found on PATH, automatically falls back to local execution.

#### execute()

Execute the generated repository's entrypoint.

```python
result: ExecutionResult = sandbox.execute(
    repo_dir: str,                      # Path to the generated repository root
    entrypoint: str = "train.py",       # Script to run (relative to repo_dir)
    args: Optional[list[str]] = None,   # Extra CLI arguments
)
```

**Returns:** `ExecutionResult` with success/failure status, output, timing, and error classification.

**Docker mode:**
- Auto-generates a Dockerfile if one does not exist.
- Builds with `docker build -t r2r-sandbox:<name> .` (10-minute build timeout).
- Runs with `docker run --rm --memory 8g --cpus 4`.
- GPU mode adds `--gpus all`.

**Local mode:**
- Runs via `subprocess` with the given timeout.
- Tracks file modifications during execution.

#### ExecutionResult Fields

```python
@dataclass
class ExecutionResult:
    success: bool                   # True if exit code == 0
    stdout: str                     # Captured stdout
    stderr: str                     # Captured stderr
    exit_code: int                  # Process exit code (-1 for timeout)
    duration_seconds: float         # Wall-clock time
    error_type: str                 # Classified error (empty if success)
    modified_files: list[str]       # Files changed during execution (local mode only)
```

**Error classification:** The sandbox automatically classifies errors from stderr into categories such as `ModuleNotFoundError`, `ImportError`, `SyntaxError`, `TypeError`, `CudaOOMError`, `TimeoutError`, and others.

---

### AutoDebugger

**Module:** `advanced.debugger`

LLM-assisted auto-debugging that analyzes execution errors, generates targeted fixes, and iterates until the code runs or a maximum iteration limit is reached.

```python
from advanced.debugger import AutoDebugger, DebugReport, DebugFix
```

#### Constructor

```python
debugger = AutoDebugger(
    provider: Optional[BaseProvider] = None,  # Auto-detected if None
    max_iterations: int = 5,                  # Max fix-and-retry cycles
)
```

#### debug()

Iteratively fix execution errors in generated files.

```python
fixed_files: dict[str, str], reports: list[DebugReport] = debugger.debug(
    repo_dir: str,                              # Path to the repository on disk
    execution_result: ExecutionResult,           # Initial failed execution result
    generated_files: dict[str, str],            # relative_path -> content
)
```

**Returns:** A tuple of `(updated_files, debug_reports)`.

**Workflow per iteration:**
1. Analyze the error (traceback + relevant source) with the LLM.
2. Generate file-level fixes (`DebugFix` objects).
3. Apply fixes to the in-memory file dict.
4. Write updated files to disk.
5. Re-execute via a local `ExecutionSandbox`.
6. If resolved, return. Otherwise, loop.

#### DebugReport Fields

```python
@dataclass
class DebugReport:
    iteration: int
    error_message: str
    error_type: str
    fixes: list[DebugFix]
    resolved: bool
```

#### DebugFix Fields

```python
@dataclass
class DebugFix:
    file_path: str
    original_content: str
    fixed_content: str
    error_description: str
    fix_description: str
```

---

### ReferenceEvaluator

**Module:** `advanced.evaluator`

Reference-based (and reference-free) evaluation scoring. Compares generated repositories against ground-truth implementations and/or the source paper.

```python
from advanced.evaluator import ReferenceEvaluator, EvaluationScore
```

#### Constructor

```python
evaluator = ReferenceEvaluator(
    provider: Optional[BaseProvider] = None,  # Auto-detected if None
    num_samples: int = 3,                     # Number of LLM evaluations to average
)
```

#### evaluate_with_reference()

Evaluate generated code against a reference implementation.

```python
score: EvaluationScore = evaluator.evaluate_with_reference(
    generated_files: dict[str, str],    # {relative_path: content}
    reference_dir: str,                 # Path to ground-truth repository
    paper_text: str,                    # Full paper text for context
)
```

Loads all `.py` files from `reference_dir`, runs `num_samples` independent LLM evaluations, and averages the scores. Falls back to reference-free evaluation if no `.py` files are found.

#### evaluate_without_reference()

Reference-free evaluation using only the paper text.

```python
score: EvaluationScore = evaluator.evaluate_without_reference(
    generated_files: dict[str, str],
    paper_text: str,
)
```

#### EvaluationScore Fields

```python
@dataclass
class EvaluationScore:
    overall_score: float                # 1-5 scale
    component_scores: dict[str, float]  # {"method": 4.2, "training": 3.8, ...}
    coverage: float                     # 0-100 percentage
    missing_components: list[str]       # Components not found in generated code
    extra_components: list[str]         # Generated components not in reference
    summary: str                        # Text summary
    severity_breakdown: dict[str, int]  # {"high": 2, "medium": 3, "low": 5}
```

**Component scoring dimensions:** method (core algorithm), training (loop/optimizer/scheduler), data (loading/preprocessing), evaluation (metrics/eval loop), utils (config/logging), reproducibility (seeds/determinism).

---

### DevOpsGenerator

**Module:** `advanced.devops`

Produces Docker, CI/CD, build, and packaging files for the generated ML repository.

```python
from advanced.devops import DevOpsGenerator
```

#### Constructor

```python
devops = DevOpsGenerator(
    provider: Optional[BaseProvider] = None,  # Used for optional LLM-enhanced generation
)
```

#### generate_all()

Produce every DevOps file and return them as a path-to-content dict.

```python
devops_files: dict[str, str] = devops.generate_all(
    plan: ArchitecturePlan,
    analysis: PaperAnalysis,
    generated_files: dict[str, str],    # Already-generated source files
)
```

**Returns:** Dict with these files:

| File | Description |
|---|---|
| `Dockerfile` | Multi-stage with CPU and GPU variants (`python:3.10-slim` / `nvidia/cuda:12.1.0`) |
| `docker-compose.yml` | Training and inference services, GPU reservations, volume mounts |
| `Makefile` | Targets: install, train, evaluate, test, lint, clean, docker-build, docker-run, help |
| `.github/workflows/ci.yml` | GitHub Actions: checkout, setup-python, install, ruff, mypy, pytest |
| `setup.py` | setuptools with find_packages, console scripts, dev extras |

---

## 5. Agent API (Highest Level)

### AgentOrchestrator

**Module:** `agents.orchestrator`

The highest-level API. Coordinates all pipeline stages in sequence, including optional self-refinement, test generation, execution, auto-debugging, DevOps generation, and evaluation.

```python
from agents.orchestrator import AgentOrchestrator
```

#### Constructor

```python
orchestrator = AgentOrchestrator(
    provider: Optional[BaseProvider] = None,     # Shared LLM provider (auto-detected if None)
    config: Optional[dict[str, Any]] = None,     # Override default pipeline behavior
)
```

**Configuration keys and defaults:**

| Key | Type | Default | Description |
|---|---|---|---|
| `enable_refine` | `bool` | `False` | Enable verify/refine loops on plans and analyses |
| `enable_execution` | `bool` | `False` | Enable sandbox execution + auto-debug |
| `enable_tests` | `bool` | `True` | Generate test files |
| `enable_evaluation` | `bool` | `False` | Run reference-based evaluation |
| `enable_devops` | `bool` | `True` | Generate DevOps files (Dockerfile, CI, etc.) |
| `interactive` | `bool` | `False` | Pause after planning for user review |
| `max_debug_iterations` | `int` | `3` | Max auto-debug cycles |
| `max_refine_iterations` | `int` | `2` | Max self-refine cycles per stage |
| `max_fix_iterations` | `int` | `2` | Max validation auto-fix cycles |
| `reference_dir` | `Optional[str]` | `None` | Path to reference implementation (for evaluation) |
| `verbose` | `bool` | `False` | Enable verbose output |

#### run()

Execute the full multi-agent pipeline.

```python
result: dict[str, Any] = orchestrator.run(
    pdf_path: str,                                  # Path to the PDF
    output_dir: str,                                # Where to save the generated repo
    paper_analysis: Optional[PaperAnalysis] = None, # Pre-computed analysis (skip stage 1)
    document: Optional[object] = None,              # Pre-uploaded document handle
    vision_context: Optional[list[str]] = None,     # Pre-extracted diagrams
)
```

**Returns:** A result dict with these keys:

| Key | Type | Description |
|---|---|---|
| `files` | `dict[str, str]` | All generated file contents |
| `plan` | `ArchitecturePlan` | The architecture plan |
| `analysis` | `PaperAnalysis` | The paper analysis |
| `file_analyses` | `dict[str, FileAnalysis]` | Per-file analysis results |
| `validation_report` | `ValidationReport` | Code validation report |
| `execution_result` | `Optional[ExecutionResult]` | Sandbox execution result (if enabled) |
| `evaluation_score` | `Optional[EvaluationScore]` | Evaluation score (if enabled) |
| `metadata` | `dict` | Run metadata (provider, model, timings, config) |

**Pipeline stages (in order):**

| Stage | Component | Skippable |
|---|---|---|
| 1 | Parse Paper (`PaperAnalyzer`) | Via pre-computed `paper_analysis` |
| 2 | Planning (`DecomposedPlanner`, falls back to `SystemArchitect`) | No |
| 3 | Per-File Analysis (`FileAnalyzer`) | No |
| 4 | Code Generation (`CodeSynthesizer`) | No |
| 5 | Test Generation (`TestGenerator`) | `enable_tests=False` |
| 6 | Validation + Auto-Fix (`CodeValidator`) | No |
| 7 | Execution + Auto-Debug (`ExecutionSandbox` + `AutoDebugger`) | `enable_execution=False` |
| 8 | DevOps Generation (`DevOpsGenerator`) | `enable_devops=False` |
| 9 | Evaluation (`ReferenceEvaluator`) | `enable_evaluation=False` |
| 10 | Save Files to Disk | No |

**Full example:**

```python
from providers import get_provider
from agents.orchestrator import AgentOrchestrator

provider = get_provider(provider_name="gemini")

orchestrator = AgentOrchestrator(
    provider=provider,
    config={
        "enable_refine": True,
        "enable_execution": True,
        "enable_tests": True,
        "enable_evaluation": False,
        "enable_devops": True,
        "interactive": False,
        "max_debug_iterations": 3,
        "max_refine_iterations": 2,
        "max_fix_iterations": 2,
        "reference_dir": None,
        "verbose": False,
    },
)

result = orchestrator.run(
    pdf_path="paper.pdf",
    output_dir="./output",
)

print(f"Generated {len(result['files'])} files")
print(f"Validation score: {result['validation_report'].score}/100")
print(f"Total time: {result['metadata']['elapsed_seconds']}s")
```

**Metadata output:** A `.r2r_metadata.json` file is automatically saved in the output directory with full run metadata including per-stage timings, provider info, and configuration.

---

## 6. Cache API

**Module:** `advanced.cache`

File-system cache for expensive pipeline stages. Uses content-addressed caching keyed on SHA-256 file hashes.

```python
from advanced.cache import PipelineCache
```

#### Constructor

```python
cache = PipelineCache(
    cache_dir: Optional[str] = None,  # Defaults to ".r2r_cache"
)
```

#### Cache Structure

```
.r2r_cache/
  {pdf_hash}/
    analysis.json       # Human-readable summary
    analysis.pkl        # Pickled PaperAnalysis
    architecture.pkl    # Pickled ArchitecturePlan
    files/              # Generated code files
      model/attention.py
      ...
    files_manifest.json # List of generated file paths
    validation.pkl      # Pickled ValidationReport
    metadata.json       # Run metadata
```

#### Methods

```python
# Analysis caching
cache.has_analysis(pdf_path: str) -> bool
cache.save_analysis(pdf_path: str, analysis: object) -> None
cache.load_analysis(pdf_path: str) -> Optional[object]

# Architecture caching
cache.has_architecture(pdf_path: str) -> bool
cache.save_architecture(pdf_path: str, plan: object) -> None
cache.load_architecture(pdf_path: str) -> Optional[object]

# Generated file caching
cache.has_generated_files(pdf_path: str) -> bool
cache.save_generated_files(pdf_path: str, files: dict[str, str]) -> None
cache.load_generated_files(pdf_path: str) -> Optional[dict[str, str]]

# Validation caching
cache.save_validation(pdf_path: str, report: object) -> None
cache.load_validation(pdf_path: str) -> Optional[object]

# Metadata
cache.save_metadata(pdf_path: str, metadata: dict) -> None
cache.load_metadata(pdf_path: str) -> Optional[dict]

# Cache management
cache.clear(pdf_path: Optional[str] = None) -> None  # Clear one PDF or all
cache.summary() -> str                                # Human-readable summary
```

**Example:**

```python
from advanced.cache import PipelineCache

cache = PipelineCache(cache_dir=".r2r_cache")

pdf_path = "paper.pdf"

# Check and load from cache
if cache.has_analysis(pdf_path):
    analysis = cache.load_analysis(pdf_path)
else:
    analysis = analyzer.analyze(document, diagrams)
    cache.save_analysis(pdf_path, analysis)

# Clear all caches
cache.clear()
```

---

## 7. Return Type Reference

Quick reference table of all important return types and their key fields.

| Type | Module | Key Fields |
|---|---|---|
| `GenerationResult` | `providers.base` | `text`, `model`, `input_tokens`, `output_tokens`, `finish_reason` |
| `ModelInfo` | `providers.base` | `name`, `provider`, `max_context_tokens`, `max_output_tokens`, `capabilities`, `cost_per_1k_input`, `cost_per_1k_output` |
| `GenerationConfig` | `providers.base` | `temperature`, `top_p`, `max_output_tokens`, `stop_sequences`, `response_format` |
| `PaperAnalysis` | `core.analyzer` | `title`, `authors`, `abstract`, `sections`, `equations`, `hyperparameters`, `architecture_description`, `key_contributions`, `datasets_mentioned`, `loss_functions`, `full_text`, `diagrams_mermaid`, `raw_token_count` |
| `ParsedPaper` | `core.paper_parser` | `title`, `authors`, `abstract`, `sections`, `figures`, `tables`, `equations_raw`, `references`, `full_text`, `metadata` |
| `ArchitecturePlan` | `core.architect` | `repo_name`, `description`, `python_version`, `files`, `requirements`, `directory_tree`, `config_schema`, `training_entrypoint`, `inference_entrypoint`, `readme_outline` |
| `FileSpec` | `core.architect` | `path`, `description`, `dependencies`, `priority` |
| `PlanningResult` | `core.planner` | `overall_plan`, `architecture_design`, `logic_design`, `config_content`, `combined_plan` |
| `OverallPlan` | `core.planner` | `core_components`, `methods_to_implement`, `training_objectives`, `data_processing_steps`, `evaluation_protocols`, `summary` |
| `ArchitectureDesign` | `core.planner` | `file_list`, `class_diagram_mermaid`, `sequence_diagram_mermaid`, `module_relationships` |
| `LogicDesign` | `core.planner` | `execution_order`, `dependency_graph`, `file_specifications` |
| `FileAnalysis` | `core.file_analyzer` | `file_path`, `classes`, `functions`, `imports`, `dependencies`, `algorithms`, `input_output_spec`, `test_criteria` |
| `ValidationReport` | `core.validator` | `issues`, `score`, `equation_coverage`, `hyperparam_coverage`, `summary`, `passed`, `critical_count`, `warning_count` |
| `ValidationIssue` | `core.validator` | `severity`, `file_path`, `line_hint`, `description`, `suggestion`, `category` |
| `RefinementResult` | `core.refiner` | `original`, `refined`, `critique`, `improvements`, `iterations`, `improved` |
| `ExecutionResult` | `advanced.executor` | `success`, `stdout`, `stderr`, `exit_code`, `duration_seconds`, `error_type`, `modified_files` |
| `DebugReport` | `advanced.debugger` | `iteration`, `error_message`, `error_type`, `fixes`, `resolved` |
| `DebugFix` | `advanced.debugger` | `file_path`, `original_content`, `fixed_content`, `error_description`, `fix_description` |
| `EvaluationScore` | `advanced.evaluator` | `overall_score`, `component_scores`, `coverage`, `missing_components`, `extra_components`, `summary`, `severity_breakdown` |
