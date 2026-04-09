# Low-Level Design

This document provides a comprehensive low-level design specification for Research2Repo v3.0. It covers class hierarchies, detailed class specifications with full method signatures, key algorithms, the prompt loading mechanism, and the JSON parsing strategy used throughout the system.

---

## Table of Contents

1. [Class Hierarchy Diagrams](#1-class-hierarchy-diagrams)
2. [Detailed Class Specifications](#2-detailed-class-specifications)
   - [Provider Layer](#21-provider-layer)
   - [Core Layer](#22-core-layer)
   - [Advanced Layer](#23-advanced-layer)
   - [Agent Layer](#24-agent-layer)
3. [Key Algorithms](#3-key-algorithms)
4. [Prompt Loading Mechanism](#4-prompt-loading-mechanism)
5. [JSON Parsing Strategy](#5-json-parsing-strategy)

---

## 1. Class Hierarchy Diagrams

### Provider Hierarchy

```
BaseProvider (ABC)  [providers/base.py]
  |
  |-- __init__(api_key, model_name)
  |-- [abstract] default_model() -> str
  |-- [abstract] available_models() -> list[ModelInfo]
  |-- [abstract] generate(prompt, system_prompt, config, images) -> GenerationResult
  |-- [abstract] generate_structured(prompt, schema, system_prompt, config) -> dict
  |-- supports(capability) -> bool
  |-- upload_file(file_path) -> object   [raises NotImplementedError]
  |-- model_info() -> Optional[ModelInfo]
  |
  +-- GeminiProvider        [providers/gemini.py]
  |     Adds: upload_file(), generate_with_file(), _build_config()
  |     MODELS: gemini-2.5-pro-preview-05-06, gemini-2.0-flash, gemini-1.5-pro
  |
  +-- OpenAIProvider        [providers/openai_provider.py]
  |     MODELS: gpt-4o, gpt-4-turbo, o3, o1
  |
  +-- AnthropicProvider     [providers/anthropic_provider.py]
  |     MODELS: claude-sonnet-4-20250514, claude-opus-4-20250514, claude-3-5-sonnet-20241022
  |
  +-- OllamaProvider        [providers/ollama.py]
        Extra param: host
        KNOWN_MODELS: deepseek-coder-v2:latest, llama3.1:70b, codellama:34b,
                      llava:13b, mistral:latest
```

### Agent Hierarchy

```
BaseAgent (ABC)  [agents/base.py]
  |
  |-- __init__(name, provider)
  |-- [abstract] execute(**kwargs) -> Any
  |-- log(message) -> None
  |-- communicate(target_agent, message) -> AgentMessage
  |
  +-- (extensible -- no concrete subclasses yet)
      AgentOrchestrator uses pipeline modules directly,
      not via BaseAgent subclasses.
```

### Pipeline Module Dependency Graph

```
                  +-------------------+
                  |  AgentOrchestrator|
                  +--------+----------+
                           |
          +--------+-------+-------+--------+--------+
          |        |       |       |        |        |
          v        v       v       v        v        v
    PaperAnalyzer  Decomposed  FileAnalyzer  Code      Code       Test
                   Planner                   Synthesizer Validator  Generator
          |                |                     |
          v                v                     v
    PaperParser    SystemArchitect         SelfRefiner
                                                |
                   +-----------------------------+
                   |            |           |
                   v            v           v
             ExecutionSandbox  AutoDebugger DevOpsGenerator
                                           ReferenceEvaluator
                                           EquationExtractor
                                           ConfigGenerator
                                           PipelineCache
```

### Registry and Factory

```
ProviderRegistry (static)  [providers/registry.py]
  |
  +-- list_providers() -> list[str]
  +-- create(provider_name, api_key, model_name, **kwargs) -> BaseProvider
  +-- detect_available() -> list[str]
  +-- best_for(capability) -> Optional[str]
  +-- estimate_cost(provider_name, model_name, input_tokens, output_tokens) -> float
  +-- register(name, module_path, class_name, env_key) -> None

get_provider() function  [providers/registry.py]
  Auto-detect and instantiate the best available provider.
```

---

## 2. Detailed Class Specifications

### 2.1 Provider Layer

---

#### `BaseProvider` (ABC) -- `providers/base.py`

Abstract base class that all LLM providers must implement. Defines the contract for text generation, structured output, capability detection, and file upload.

| Attribute | Type | Description |
|-----------|------|-------------|
| `api_key` | `Optional[str]` | API key for the provider |
| `model_name` | `str` | Active model name (defaults via `default_model()`) |

**Constructor:**

```python
def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None) -> None
```

Sets `self.api_key = api_key` and `self.model_name = model_name or self.default_model()`.

**Abstract Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `default_model` | `() -> str` | `str` | Return the default model name for this provider |
| `available_models` | `() -> list[ModelInfo]` | `list[ModelInfo]` | List all models available through this provider |
| `generate` | `(prompt: str, system_prompt: Optional[str], config: Optional[GenerationConfig], images: Optional[list[bytes]]) -> GenerationResult` | `GenerationResult` | Generate text from a prompt with optional vision input |
| `generate_structured` | `(prompt: str, schema: dict, system_prompt: Optional[str], config: Optional[GenerationConfig]) -> dict` | `dict` | Generate JSON output conforming to a schema |

**Concrete Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `supports` | `(capability: ModelCapability) -> bool` | `bool` | Check if current model supports a given capability by scanning `available_models()` |
| `upload_file` | `(file_path: str) -> object` | `object` | Upload a file for prompt inclusion. Default raises `NotImplementedError` |
| `model_info` | `() -> Optional[ModelInfo]` | `Optional[ModelInfo]` | Get `ModelInfo` for the currently selected model |

---

#### `GeminiProvider` -- `providers/gemini.py`

Google Gemini provider with File API support and native vision.

**Class Constants:**

| Constant | Type | Description |
|----------|------|-------------|
| `MODELS` | `list[ModelInfo]` | 3 models: `gemini-2.5-pro-preview-05-06` (1M ctx, 65K out), `gemini-2.0-flash` (1M ctx, 8K out), `gemini-1.5-pro` (2M ctx, 8K out) |

**Constructor:**

```python
def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None) -> None
```

Resolves key from `api_key` param or `GEMINI_API_KEY` env var. Raises `ValueError` if neither set. Configures `google.generativeai` and instantiates `genai.GenerativeModel(self.model_name)`.

**Instance Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `_model` | `genai.GenerativeModel` | The Gemini model instance |

**Methods (beyond inherited):**

| Method | Signature | Return Type | Visibility | Description |
|--------|-----------|-------------|------------|-------------|
| `default_model` | `() -> str` | `str` | public | Returns `"gemini-2.5-pro-preview-05-06"` |
| `available_models` | `() -> list[ModelInfo]` | `list[ModelInfo]` | public | Returns `self.MODELS` |
| `generate` | `(prompt, system_prompt, config, images) -> GenerationResult` | `GenerationResult` | public | Builds parts list (system prefix, PIL images, prompt text), calls `_model.generate_content()` |
| `generate_structured` | `(prompt, schema, system_prompt, config) -> dict` | `dict` | public | Sets `response_format="json"`, prepends schema instruction, calls `generate()`, parses with `json.loads()` |
| `upload_file` | `(file_path: str) -> object` | `object` | public | Calls `genai.upload_file(file_path)`, returns uploaded file handle |
| `generate_with_file` | `(uploaded_file: object, prompt: str, system_prompt: Optional[str], config: Optional[GenerationConfig]) -> GenerationResult` | `GenerationResult` | public | Generates using an uploaded file as context (zero-RAG long-context) |
| `_build_config` | `(config: Optional[GenerationConfig]) -> dict` | `dict` | private | Converts `GenerationConfig` to Gemini-native config dict. Maps `response_format="json"` to `response_mime_type="application/json"` |

---

#### `OpenAIProvider` -- `providers/openai_provider.py`

OpenAI GPT provider with vision and JSON-mode support.

**Class Constants:**

| Constant | Type | Description |
|----------|------|-------------|
| `MODELS` | `list[ModelInfo]` | 4 models: `gpt-4o` (128K ctx, 16K out), `gpt-4-turbo` (128K ctx, 4K out), `o3` (200K ctx, 100K out), `o1` (200K ctx, 100K out, no VISION/STRUCTURED_OUTPUT) |

**Constructor:**

```python
def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None) -> None
```

Resolves key from param or `OPENAI_API_KEY`. Creates `OpenAI(api_key=self.api_key)` client.

**Instance Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `_client` | `openai.OpenAI` | The OpenAI client instance |

**Key Implementation Details:**

- `generate()`: Builds `messages` list with system + user roles. For vision, encodes images as base64 `data:image/png;base64,...` URLs in multipart content. Uses `chat.completions.create()`. Maps `response_format="json"` to `{"type": "json_object"}`.
- `generate_structured()`: Sets `response_format="json"`, prepends schema instruction, calls `generate()`, parses result with `json.loads()`.
- `default_model()`: Returns `"gpt-4o"`.

---

#### `AnthropicProvider` -- `providers/anthropic_provider.py`

Anthropic Claude provider with vision and extended thinking support.

**Class Constants:**

| Constant | Type | Description |
|----------|------|-------------|
| `MODELS` | `list[ModelInfo]` | 3 models: `claude-sonnet-4-20250514` (200K ctx, 64K out), `claude-opus-4-20250514` (200K ctx, 32K out), `claude-3-5-sonnet-20241022` (200K ctx, 8K out) |

**Constructor:**

```python
def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None) -> None
```

Resolves key from param or `ANTHROPIC_API_KEY`. Creates `anthropic.Anthropic(api_key=self.api_key)`.

**Instance Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `_client` | `anthropic.Anthropic` | The Anthropic client instance |

**Key Implementation Details:**

- `generate()`: Builds `content` list with base64 image blocks (`type: "image"`, `source.type: "base64"`) and text block. System prompt goes as top-level `system` kwarg (not in messages). Uses `_client.messages.create()`. Extracts text from `response.content` blocks.
- `generate_structured()`: Prepends schema instruction with "Respond ONLY with valid JSON" system prompt. Strips markdown fences from output before `json.loads()`.
- `default_model()`: Returns `"claude-sonnet-4-20250514"`.

---

#### `OllamaProvider` -- `providers/ollama.py`

Ollama local model provider using the REST API.

**Class Constants:**

| Constant | Type | Description |
|----------|------|-------------|
| `KNOWN_MODELS` | `list[ModelInfo]` | 5 models: `deepseek-coder-v2:latest` (128K ctx), `llama3.1:70b` (128K ctx), `codellama:34b` (16K ctx), `llava:13b` (4K ctx, VISION), `mistral:latest` (32K ctx). All cost `$0.0/$0.0` |

**Constructor:**

```python
def __init__(
    self,
    api_key: Optional[str] = None,  # unused, interface consistency
    model_name: Optional[str] = None,
    host: Optional[str] = None,
) -> None
```

`self.host` resolved from `host` param, `OLLAMA_HOST` env var, or default `http://localhost:11434`.

**Instance Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `host` | `str` | Ollama server base URL |

**Key Implementation Details:**

- `available_models()`: Merges `KNOWN_MODELS` with live models from `GET {host}/api/tags`. Dynamically discovered models get default 4K context.
- `generate()`: POSTs to `{host}/api/generate` with `stream: false`. Maps images to base64 list. Maps `response_format="json"` to `format: "json"`. 600s request timeout.
- `generate_structured()`: Sets `response_format="json"`, prepends schema instruction, strips markdown fences, parses JSON.
- `default_model()`: Returns `"deepseek-coder-v2:latest"`.

---

#### `ProviderRegistry` -- `providers/registry.py`

Static factory and registry for creating providers by name. Uses lazy imports via `importlib`.

**Module-Level Constants:**

```python
_PROVIDER_MAP = {
    "gemini":    ("providers.gemini",            "GeminiProvider"),
    "openai":    ("providers.openai_provider",   "OpenAIProvider"),
    "anthropic": ("providers.anthropic_provider", "AnthropicProvider"),
    "ollama":    ("providers.ollama",            "OllamaProvider"),
}

_PROVIDER_ENV_KEYS = {
    "gemini":    "GEMINI_API_KEY",
    "openai":    "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "ollama":    None,  # checked via HTTP health check
}
```

**Static Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `list_providers` | `() -> list[str]` | `list[str]` | Returns keys from `_PROVIDER_MAP` |
| `create` | `(provider_name: str, api_key: Optional[str], model_name: Optional[str], **kwargs) -> BaseProvider` | `BaseProvider` | Lazy-imports module, instantiates class. Raises `ValueError` for unknown provider |
| `detect_available` | `() -> list[str]` | `list[str]` | Checks env vars for cloud providers, HTTP GET to `localhost:11434/api/tags` for Ollama |
| `best_for` | `(capability: ModelCapability) -> Optional[str]` | `Optional[str]` | Returns first available provider from capability-specific preference order |
| `estimate_cost` | `(provider_name: str, model_name: str, input_tokens: int, output_tokens: int) -> float` | `float` | Calculates USD cost from `ModelInfo.cost_per_1k_input/output` |
| `register` | `(name: str, module_path: str, class_name: str, env_key: Optional[str]) -> None` | `None` | Registers a custom provider into `_PROVIDER_MAP` |

**Capability Preference Order:**

| Capability | Provider Order |
|------------|---------------|
| `LONG_CONTEXT` | gemini, anthropic, openai, ollama |
| `VISION` | gemini, openai, anthropic, ollama |
| `CODE_GENERATION` | anthropic, openai, gemini, ollama |
| `STRUCTURED_OUTPUT` | openai, gemini, anthropic, ollama |
| `FILE_UPLOAD` | gemini |

---

#### `get_provider()` Function -- `providers/registry.py`

```python
def get_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    required_capability: Optional[ModelCapability] = None,
    **kwargs,
) -> BaseProvider
```

Auto-detection logic:
1. If `provider_name` given -> `ProviderRegistry.create(provider_name, ...)`
2. If `required_capability` given -> `ProviderRegistry.best_for(capability)` -> create
3. Fallback -> `detect_available()` -> create first available
4. No providers -> raises `RuntimeError`

---

### 2.2 Core Layer

---

#### `PaperAnalyzer` -- `core/analyzer.py`

Ingests PDF, extracts text, identifies sections, extracts architecture diagrams via vision, and produces structured `PaperAnalysis`.

**Class Constants:**

| Constant | Type | Value |
|----------|------|-------|
| `ANALYSIS_PROMPT_FILE` | `str` | `<project_root>/prompts/analyzer.txt` |
| `DIAGRAM_PROMPT_FILE` | `str` | `<project_root>/prompts/diagram_extractor.txt` |

**Constructor:**

```python
def __init__(
    self,
    provider: Optional[BaseProvider] = None,
    vision_provider: Optional[BaseProvider] = None,
) -> None
```

- `provider`: Auto-detected with `LONG_CONTEXT` capability if None.
- `vision_provider`: Uses explicit param, falls back to `provider` if it has `VISION`, then auto-detects `VISION` provider, then `None`.
- Sets `self._uploaded_file = None`.

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `upload_document` | `(pdf_path: str) -> object` | `object` | If provider has `FILE_UPLOAD`: calls `provider.upload_file()`. Otherwise: extracts text via PyPDF2. Returns file handle or text string |
| `extract_diagrams_to_mermaid` | `(pdf_path: str) -> list[str]` | `list[str]` | Extracts page images via PyMuPDF, sends in batches of 4 to vision provider, parses mermaid code blocks from response |
| `analyze` | `(document: object, vision_context: list[str]) -> PaperAnalysis` | `PaperAnalysis` | Full structured analysis. Uses `generate_with_file()` for Gemini, `generate()` for others. Parses JSON response into `PaperAnalysis` dataclass |

**Private Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `_load_prompt` | `(path: str, **kwargs) -> str` | `str` | Loads template file, substitutes `{{key}}` placeholders |
| `_extract_text_pypdf` | `(pdf_path: str) -> str` | `str` | Text extraction via `PyPDF2.PdfReader` |
| `_extract_page_images` | `(pdf_path: str) -> list[bytes]` | `list[bytes]` | Converts up to 30 pages to 150 DPI PNG bytes via PyMuPDF |
| `_parse_json_response` | `(text: str) -> dict` | `dict` | Strips markdown fences, calls `json.loads()` |
| `_default_analysis_prompt` | `() -> str` | `str` | Inline 10-field extraction prompt as fallback |

---

#### `SystemArchitect` -- `core/architect.py`

Designs the software architecture (repo structure, file decomposition, dependencies) from a `PaperAnalysis`.

**Class Constants:**

| Constant | Type | Value |
|----------|------|-------|
| `PROMPT_FILE` | `str` | `<project_root>/prompts/architect.txt` |

**Constructor:**

```python
def __init__(self, provider: Optional[BaseProvider] = None) -> None
```

Auto-detects with `STRUCTURED_OUTPUT` capability.

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `design_system` | `(analysis: PaperAnalysis, document: Optional[object], vision_context: Optional[list[str]]) -> ArchitecturePlan` | `ArchitecturePlan` | Builds context from analysis, calls `generate_structured()` with a 12-field JSON schema, parses into `ArchitecturePlan`, ensures essential files exist |

**Private Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `_build_context` | `(analysis: PaperAnalysis, vision_context: Optional[list[str]]) -> str` | `str` | Builds a structured string from paper title, authors, abstract, architecture, equations (capped at 20), hyperparameters, loss functions, contributions, and Mermaid diagrams |
| `_parse_plan` | `(data: dict) -> ArchitecturePlan` | `ArchitecturePlan` | Converts raw JSON dict to `ArchitecturePlan` with `FileSpec` list sorted by priority |
| `_ensure_essentials` | `(plan: ArchitecturePlan, analysis: PaperAnalysis) -> ArchitecturePlan` | `ArchitecturePlan` | Ensures `config.yaml` (priority -2), `README.md` (priority 100), and `requirements.txt` (priority -1) exist |
| `_fallback_generate` | `(prompt: str) -> dict` | `dict` | Text generation fallback with JSON parsing |

---

#### `DecomposedPlanner` -- `core/planner.py`

4-step planning pipeline: overall plan -> architecture design -> logic design -> config generation.

**Constructor:**

```python
def __init__(self, provider: Optional[BaseProvider] = None) -> None
```

Auto-detects with `STRUCTURED_OUTPUT` capability.

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `plan` | `(analysis: PaperAnalysis, document: Optional[object], vision_context: Optional[list[str]]) -> PlanningResult` | `PlanningResult` | Orchestrates all 4 steps sequentially, converts to backward-compatible `ArchitecturePlan` |

**Private Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `_step1_overall_plan` | `(analysis: PaperAnalysis) -> OverallPlan` | `OverallPlan` | Extracts core components, methods, training objectives, data steps, evaluation protocols, summary |
| `_step2_architecture_design` | `(analysis: PaperAnalysis, overall_plan: OverallPlan) -> ArchitectureDesign` | `ArchitectureDesign` | Designs file list, Mermaid class/sequence diagrams, module relationships. Feeds step 1 output as context |
| `_step3_logic_design` | `(analysis: PaperAnalysis, overall_plan: OverallPlan, arch_design: ArchitectureDesign) -> LogicDesign` | `LogicDesign` | Determines topological execution order, dependency graph, per-file specifications with key functions |
| `_step4_config_generation` | `(analysis: PaperAnalysis, overall_plan: OverallPlan, arch_design: ArchitectureDesign, logic_design: LogicDesign) -> str` | `str` | Generates YAML config from hyperparameters. Uses plain `generate()` (not structured) |
| `_to_architecture_plan` | `(analysis, overall_plan, arch_design, logic_design, config_content) -> ArchitecturePlan` | `ArchitecturePlan` | Backward-compatibility converter. Merges architecture + logic designs into `FileSpec` list with priorities from `execution_order`. Builds directory tree, detects entrypoints, extracts requirements |
| `_load_prompt` | `(path: str, **kwargs) -> str` | `str` | Static method. Template loader |
| `_paper_context` | `(analysis: PaperAnalysis) -> str` | `str` | Static method. Compact paper summary builder |
| `_fallback_generate` | `(prompt: str) -> dict` | `dict` | Text generation fallback with JSON parsing |

---

#### `FileAnalyzer` -- `core/file_analyzer.py`

Per-file analysis phase. Produces detailed specifications for each file before code generation.

**Constructor:**

```python
def __init__(self, provider: Optional[BaseProvider] = None) -> None
```

Auto-detects with `STRUCTURED_OUTPUT` capability.

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `analyze_file` | `(file_spec: FileSpec, analysis: PaperAnalysis, plan: ArchitecturePlan, prior_analyses: dict[str, FileAnalysis]) -> FileAnalysis` | `FileAnalysis` | Analyzes a single file. Builds context from paper, plan, and all prior analyses. Uses structured generation with 7-field schema |
| `analyze_all` | `(plan: ArchitecturePlan, analysis: PaperAnalysis) -> dict[str, FileAnalysis]` | `dict[str, FileAnalysis]` | Iterates over `plan.files` in priority order. Each analysis feeds into subsequent files as `prior_analyses` context |

**Private Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `_build_paper_context` | `(analysis: PaperAnalysis) -> str` | `str` | Static. Compact paper summary with equations (capped at 30), hyperparameters, loss functions, contributions, diagrams |
| `_build_plan_context` | `(plan: ArchitecturePlan) -> str` | `str` | Static. Repository name, description, directory tree, file list with priorities and dependencies |
| `_build_prior_context` | `(prior_analyses: dict[str, FileAnalysis]) -> str` | `str` | Static. Summarizes previously analyzed files: classes (with base classes, methods), functions (with args, return types), imports (capped at 15) |
| `_load_prompt` | `(path: str, **kwargs) -> str` | `str` | Static. Template loader |
| `_fallback_generate` | `(prompt: str) -> dict` | `dict` | Text generation fallback with JSON parsing |

---

#### `CodeSynthesizer` -- `core/coder.py`

Generates each source file in dependency order with rolling context.

**Class Constants:**

| Constant | Type | Value |
|----------|------|-------|
| `PROMPT_FILE` | `str` | `<project_root>/prompts/coder.txt` |

**Constructor:**

```python
def __init__(self, provider: Optional[BaseProvider] = None) -> None
```

Auto-detects with `CODE_GENERATION` capability.

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `generate_codebase` | `(analysis: PaperAnalysis, plan: ArchitecturePlan, document: Optional[object]) -> dict[str, str]` | `dict[str, str]` | Generates all files in order. Returns `{file_path: content}` dict |

**Private Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `_generate_single_file` | `(file_spec: FileSpec, analysis: PaperAnalysis, plan: ArchitecturePlan, generated_so_far: dict[str, str], document: Optional[object]) -> str` | `str` | Builds full context (paper, equations, hyperparams, loss functions, repo structure, dependency files, Mermaid diagrams), generates code. Max tokens: 16384 for model/train files, 4096 for config/markdown, 8192 default |
| `_get_dependency_context` | `(file_spec: FileSpec, generated: dict[str, str]) -> str` | `str` | Includes direct dependency files (truncated at 3000 chars) and last 3 recently generated files (truncated at 1500 chars) |
| `_clean_output` | `(text: str, file_path: str) -> str` | `str` | Strips markdown fences. For `.py` files, removes leading non-code explanation lines |
| `_system_prompt` | `() -> str` | `str` | Returns expert ML engineer system prompt |

---

#### `CodeValidator` -- `core/validator.py`

Self-review pass that verifies generated code against the original paper.

**Class Constants:**

| Constant | Type | Value |
|----------|------|-------|
| `PROMPT_FILE` | `str` | `<project_root>/prompts/validator.txt` |

**Constructor:**

```python
def __init__(self, provider: Optional[BaseProvider] = None) -> None
```

Auto-detects with `CODE_GENERATION` capability.

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `validate` | `(generated_files: dict[str, str], analysis: PaperAnalysis, plan: ArchitecturePlan) -> ValidationReport` | `ValidationReport` | Full validation via structured generation. Checks equation fidelity, dimension consistency, hyperparameter completeness, loss function accuracy, code quality |
| `fix_issues` | `(generated_files: dict[str, str], report: ValidationReport, analysis: PaperAnalysis) -> dict[str, str]` | `dict[str, str]` | Auto-fixes critical issues. Groups by file, sends original content + issues + paper equations to LLM, replaces content with fixed version |

**Private Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `_build_validation_context` | `(generated_files: dict[str, str], analysis: PaperAnalysis) -> str` | `str` | Builds context with all equations, hyperparameters, loss functions, architecture description, and all generated files (truncated at 5000 chars each) |
| `_parse_report` | `(data: dict) -> ValidationReport` | `ValidationReport` | Converts JSON dict to `ValidationReport` with `ValidationIssue` list |
| `_fallback_validate` | `(prompt: str) -> dict` | `dict` | Text generation fallback |

---

#### `SelfRefiner` -- `core/refiner.py`

Verify-then-refine loop for any pipeline artifact.

**Class Constants:**

| Constant | Type | Description |
|----------|------|-------------|
| `_JSON_ARTIFACT_TYPES` | `frozenset` | `{"overall_plan", "architecture_design", "logic_design", "file_analysis"}` |
| `_TEXT_ARTIFACT_TYPES` | `frozenset` | `{"config", "code"}` |

**Constructor:**

```python
def __init__(
    self,
    provider: Optional[BaseProvider] = None,
    max_iterations: int = 2,
) -> None
```

Auto-detects with `STRUCTURED_OUTPUT` capability.

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `refine` | `(artifact: Any, artifact_type: str, context: str, schema: Optional[dict]) -> RefinementResult` | `RefinementResult` | Full verify-refine loop. Raises `ValueError` for unknown artifact types |
| `verify` | `(artifact: Any, artifact_type: str, context: str) -> tuple[str, list[str]]` | `tuple[str, list[str]]` | Critique an artifact. Returns `(critique_text, list_of_issues)` |
| `refine_artifact` | `(artifact: Any, critique: str, artifact_type: str, context: str, schema: Optional[dict]) -> Any` | `Any` | Produce a refined version. JSON types use `generate_structured()`, text types use `generate()` |

**Private Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `_serialize_artifact` | `(artifact: Any, artifact_type: str) -> str` | `str` | Static. JSON types: `json.dumps()` (handles dicts and dataclasses via `__dict__`). Text types: `str()` |
| `_fallback_json_generate` | `(prompt: str) -> dict` | `dict` | Text generation fallback with JSON parsing |
| `_load_prompt` | `(path: str, **kwargs) -> str` | `str` | Static. Template loader |

---

#### `PaperParser` -- `core/paper_parser.py`

Multi-backend paper parser with fallback chain.

**Constructor:**

```python
def __init__(self) -> None
```

Sets `self._parser_used = None`.

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `parse` | `(pdf_path: str) -> ParsedPaper` | `ParsedPaper` | Tries backends in priority order. Raises `FileNotFoundError` if PDF missing, `RuntimeError` if all backends fail |

**Private Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `_parse_with_doc2json` | `(pdf_path: str) -> ParsedPaper` | `ParsedPaper` | Highest quality. Requires `pip install s2orc-doc2json`. Extracts body text, bib entries |
| `_parse_with_grobid` | `(pdf_path: str) -> ParsedPaper` | `ParsedPaper` | Posts PDF to GROBID REST API at `GROBID_URL` env var or `http://localhost:8070/api/processFulltextDocument`. Parses TEI XML response |
| `_parse_tei_xml` | `(tei_xml: str) -> ParsedPaper` | `ParsedPaper` | Extracts title, authors, abstract, sections, references, figures, tables from TEI XML using `xml.etree.ElementTree` with `tei` namespace |
| `_parse_with_pymupdf` | `(pdf_path: str) -> ParsedPaper` | `ParsedPaper` | Font-size heuristic section detection. Computes median font size, detects headers at >1.15x median+bold or >1.3x median. Extracts title from largest font on page 0. Extracts embedded images |
| `_parse_with_pypdf2` | `(pdf_path: str) -> ParsedPaper` | `ParsedPaper` | Basic text extraction. Uses regex heuristics for section detection and abstract extraction |
| `_detect_sections` | `(text: str) -> list[dict]` | `list[dict]` | Regex-based section boundary detection. Recognizes `1. Introduction`, `## Method`, `A.1 Appendix`, `III. Experiments` patterns |
| `_extract_equations_from_text` | `(text: str) -> list[str]` | `list[str]` | Extracts LaTeX: `\begin{equation}...\end{equation}`, `\[...\]`, `$$...$$`, `$...$` (filtered). Deduplicates while preserving order |

---

### 2.3 Advanced Layer

---

#### `ExecutionSandbox` -- `advanced/executor.py`

Docker-based or local execution sandbox.

**Constructor:**

```python
def __init__(
    self,
    use_docker: bool = True,
    timeout: int = 300,
    gpu: bool = False,
) -> None
```

Falls back to local execution if Docker not on PATH.

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `execute` | `(repo_dir: str, entrypoint: str = "train.py", args: Optional[list[str]] = None) -> ExecutionResult` | `ExecutionResult` | Validates paths, delegates to Docker or local execution. Catches Docker failures and falls back to local |

**Private Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `_build_docker_image` | `(repo_dir: str) -> str` | `str` | Generates Dockerfile if missing, runs `docker build -t r2r-sandbox:{basename}`, 600s build timeout |
| `_generate_dockerfile` | `(repo_dir: str) -> str` | `str` | Creates `python:3.10-slim` based Dockerfile. Includes `pip install -r requirements.txt` if `requirements.txt` exists |
| `_run_in_docker` | `(image_tag: str, entrypoint: str, args: list[str], timeout: int) -> ExecutionResult` | `ExecutionResult` | `docker run --rm` with `--memory 8g --cpus 4`. Optional `--gpus all`. Classifies errors on failure |
| `_run_locally` | `(repo_dir: str, entrypoint: str, args: list[str], timeout: int) -> ExecutionResult` | `ExecutionResult` | `subprocess.run()` with `cwd=repo_dir`. Snapshots file mtimes before/after to detect modified files |
| `_classify_error` | `(stderr: str) -> str` | `str` | Regex matching against 19 ordered patterns (see [Error Classification Algorithm](#error-classification)) |
| `_snapshot_mtimes` | `(directory: str) -> dict[str, float]` | `dict[str, float]` | Static. Walks directory tree, records `os.path.getmtime()` for each file |

---

#### `AutoDebugger` -- `advanced/debugger.py`

LLM-assisted iterative auto-debugging.

**Class Constants:**

| Constant | Type | Value |
|----------|------|-------|
| `PROMPT_FILE` | `str` | `<project_root>/prompts/auto_debug.txt` |

**Constructor:**

```python
def __init__(
    self,
    provider: Optional[BaseProvider] = None,
    max_iterations: int = 5,
) -> None
```

Auto-detects with `CODE_GENERATION` capability. Creates internal `ExecutionSandbox(use_docker=False, timeout=120)`.

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `debug` | `(repo_dir: str, execution_result: ExecutionResult, generated_files: dict[str, str]) -> tuple[dict[str, str], list[DebugReport]]` | `tuple[dict[str, str], list[DebugReport]]` | Iterative fix loop: analyze error -> generate fixes -> apply -> write to disk -> re-execute -> repeat |

**Private Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `_analyze_error` | `(error_message: str, error_type: str, relevant_files: dict[str, str]) -> list[DebugFix]` | `list[DebugFix]` | Narrows files to traceback-referenced subset, builds debug prompt, calls structured generation with fix schema |
| `_find_relevant_files` | `(error_message: str, all_files: dict[str, str]) -> dict[str, str]` | `dict[str, str]` | Parses `File "..."` references and `\w[\w/]*\.py` patterns from traceback, matches against file basenames |
| `_apply_fixes` | `(files: dict[str, str], fixes: list[DebugFix]) -> dict[str, str]` | `dict[str, str]` | Overwrites file content from `DebugFix.fixed_content`. Can also create new files |
| `_build_debug_prompt` | `(error_message: str, error_type: str, files: dict[str, str]) -> str` | `str` | Loads template or builds default prompt. Files truncated at 8000 chars. Error message truncated at 4000 chars |
| `_parse_fixes` | `(data: dict, all_files: dict[str, str]) -> list[DebugFix]` | `list[DebugFix]` | Converts JSON `fixes` array to `DebugFix` objects. Records `original_content` from `all_files` |
| `_text_fallback` | `(prompt: str) -> dict` | `dict` | Returns `{"fixes": []}` on JSON decode failure |

---

#### `ReferenceEvaluator` -- `advanced/evaluator.py`

Reference-based and reference-free evaluation scoring.

**Constructor:**

```python
def __init__(
    self,
    provider: Optional[BaseProvider] = None,
    num_samples: int = 3,
) -> None
```

Auto-detects with `CODE_GENERATION` capability. `num_samples` minimum is 1.

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `evaluate_with_reference` | `(generated_files: dict[str, str], reference_dir: str, paper_text: str) -> EvaluationScore` | `EvaluationScore` | Loads `.py` files from `reference_dir`, runs `num_samples` evaluations, averages scores. Falls back to reference-free if no `.py` files found |
| `evaluate_without_reference` | `(generated_files: dict[str, str], paper_text: str) -> EvaluationScore` | `EvaluationScore` | Uses only paper text to check algorithmic component coverage |

**Private Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `_load_reference_files` | `(ref_dir: str) -> dict[str, str]` | `dict[str, str]` | Walks directory, reads all `.py` files |
| `_build_eval_prompt` | `(generated: dict, reference: dict, paper_text: str, mode: str) -> str` | `str` | Builds evaluation prompt. Paper text truncated at 30000 chars. Files truncated at 6000 chars each |
| `_run_evaluations` | `(prompt: str) -> list[dict]` | `list[dict]` | Runs `num_samples` calls with `temperature=0.3` for variance. Falls back to text generation on failure |
| `_aggregate_scores` | `(scores: list[dict]) -> EvaluationScore` | `EvaluationScore` | Averages `overall_score`, per-component scores, `coverage`. Severity breakdown averaged and rounded. Lists/strings from first sample |
| `_text_fallback` | `(prompt: str) -> dict` | `dict` | Returns `{}` on failure |

---

#### `DevOpsGenerator` -- `advanced/devops.py`

Produces Docker, CI/CD, build, and packaging files.

**Constructor:**

```python
def __init__(self, provider: Optional[BaseProvider] = None) -> None
```

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `generate_all` | `(plan: Any, analysis: Any, generated_files: dict[str, str]) -> dict[str, str]` | `dict[str, str]` | Generates 5 files: `Dockerfile`, `docker-compose.yml`, `Makefile`, `.github/workflows/ci.yml`, `setup.py` |

**Private Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `_generate_dockerfile` | `(plan, analysis) -> str` | `str` | Multi-stage: `python:{version}-slim` (CPU) + `nvidia/cuda:12.1.0-runtime-ubuntu22.04` (GPU if torch/tensorflow in deps). Detects OpenCV system deps |
| `_generate_docker_compose` | `(plan) -> str` | `str` | `train` and `inference` services with volume mounts for `data/`, `checkpoints/`, `logs/`. GPU deploy block if needed |
| `_generate_makefile` | `(plan) -> str` | `str` | Targets: `install`, `train`, `evaluate`, `test`, `lint`, `clean`, `docker-build`, `docker-run`, `help` |
| `_generate_ci_yml` | `(plan) -> str` | `str` | GitHub Actions: checkout, setup-python, install deps, ruff lint, mypy type-check, pytest |
| `_generate_setup_py` | `(plan, analysis) -> str` | `str` | `setuptools`-based with `find_packages()`, `_read_requirements()`, dev extras (pytest, ruff, mypy) |
| `_llm_generate` | `(prompt: str, system_prompt: str) -> Optional[str]` | `Optional[str]` | Optional LLM-enhanced generation hook. Returns `None` on failure (unused in default mode) |

---

#### `EquationExtractor` -- `advanced/equation_extractor.py`

Dedicated equation extraction from text and images.

**Class Constants:**

| Constant | Type | Value |
|----------|------|-------|
| `PROMPT_FILE` | `str` | `<project_root>/prompts/equation_extractor.txt` |

**Constructor:**

```python
def __init__(self, provider: Optional[BaseProvider] = None) -> None
```

Auto-detects with `VISION` capability.

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `extract` | `(paper_text: str, page_images: Optional[list[bytes]]) -> list[ExtractedEquation]` | `list[ExtractedEquation]` | Extracts from text and images, deduplicates by normalized LaTeX |
| `extract_from_text` | `(paper_text: str) -> list[ExtractedEquation]` | `list[ExtractedEquation]` | Text truncated at 80000 chars. JSON response format |
| `extract_from_images` | `(page_images: list[bytes]) -> list[ExtractedEquation]` | `list[ExtractedEquation]` | Processes in batches of 4. Skips if provider lacks VISION |
| `map_to_files` | `(equations: list[ExtractedEquation], generated_files: dict[str, str]) -> dict[str, list[ExtractedEquation]]` | `dict[str, list[ExtractedEquation]]` | Searches for equation LaTeX/description terms in generated file content (case-insensitive, first 20 chars of term) |

---

#### `TestGenerator` -- `advanced/test_generator.py`

Auto-generates pytest test suites.

**Constructor:**

```python
def __init__(self, provider: Optional[BaseProvider] = None) -> None
```

Auto-detects with `CODE_GENERATION` capability.

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `generate_tests` | `(generated_files: dict[str, str], analysis: PaperAnalysis, plan: ArchitecturePlan) -> dict[str, str]` | `dict[str, str]` | Generates 5 test files: `tests/test_model.py`, `tests/test_loss.py`, `tests/test_integration.py`, `tests/conftest.py`, `tests/__init__.py` |

**Private Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `_generate_test_file` | `(context, target_files, analysis, prompt, focus) -> str` | `str` | Generates a single test file with specified focus area |
| `_generate_integration_tests` | `(context, generated_files, analysis, plan) -> str` | `str` | Tests: model instantiation, forward pass shape, backward pass gradients, training step loss reduction, save/load, config defaults |
| `_generate_conftest` | `(analysis, plan) -> str` | `str` | Deterministic (no LLM). Generates fixtures: `device`, `paper_config` (from hyperparameters), `small_config` (reduced dims), `sample_batch` |
| `_build_context` | `(generated_files, analysis, plan) -> str` | `str` | Paper title, equations (capped at 15), hyperparameters, directory tree, requirements |
| `_clean_output` | `(text: str) -> str` | `str` | Strips markdown fences |

---

#### `ConfigGenerator` -- `advanced/config_generator.py`

Generates structured YAML config from paper hyperparameters.

**Constructor:**

```python
def __init__(self, provider: Optional[BaseProvider] = None) -> None
```

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `generate` | `(analysis: PaperAnalysis) -> str` | `str` | LLM-generated YAML. Validates with `yaml.safe_load()`. Falls back to `_fallback_config()` on invalid YAML |
| `generate_schema` | `(analysis: PaperAnalysis) -> dict` | `dict` | JSON schema with categorized hyperparameters: `model`, `training`, `data`, `regularization` sections. Uses keyword matching sets for categorization |

**Hyperparameter Category Keywords:**

| Category | Keywords |
|----------|----------|
| `model` | d_model, d_ff, d_k, d_v, num_heads, num_layers, vocab_size, max_seq_len, hidden_size, num_encoder_layers, num_decoder_layers, intermediate_size |
| `training` | learning_rate, lr, batch_size, epochs, warmup_steps, warmup_ratio, max_steps, gradient_clip, weight_decay, adam_beta1, adam_beta2, adam_epsilon |
| `regularization` | dropout, attention_dropout, label_smoothing, weight_decay, gradient_clip_norm |

---

#### `PipelineCache` -- `advanced/cache.py`

Content-addressed file-system cache keyed on PDF SHA-256 hash.

**Class Constants:**

| Constant | Type | Value |
|----------|------|-------|
| `DEFAULT_DIR` | `str` | `".r2r_cache"` |

**Constructor:**

```python
def __init__(self, cache_dir: Optional[str] = None) -> None
```

Creates `self.cache_dir` as `Path`, calls `mkdir(parents=True, exist_ok=True)`.

**Cache Structure:**

```
.r2r_cache/
  {pdf_hash_16chars}/
    analysis.json        # Human-readable summary
    analysis.pkl         # Pickled PaperAnalysis
    architecture.pkl     # Pickled ArchitecturePlan
    files/               # Generated code files (directory tree)
    files_manifest.json  # List of generated file paths
    validation.pkl       # Pickled ValidationReport
    metadata.json        # Run metadata (timestamps, models, etc.)
```

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `has_analysis` | `(pdf_path: str) -> bool` | `bool` | Checks `analysis.json` exists |
| `save_analysis` | `(pdf_path: str, analysis: object) -> None` | `None` | Pickles analysis + saves JSON summary (field values truncated at 500 chars) |
| `load_analysis` | `(pdf_path: str) -> Optional[object]` | `Optional[object]` | Unpickles `analysis.pkl` |
| `has_architecture` | `(pdf_path: str) -> bool` | `bool` | Checks `architecture.pkl` exists |
| `save_architecture` | `(pdf_path: str, plan: object) -> None` | `None` | Pickles plan |
| `load_architecture` | `(pdf_path: str) -> Optional[object]` | `Optional[object]` | Unpickles plan |
| `has_generated_files` | `(pdf_path: str) -> bool` | `bool` | Checks `files/` dir exists and is non-empty |
| `save_generated_files` | `(pdf_path: str, files: dict[str, str]) -> None` | `None` | Writes files to `files/` dir + `files_manifest.json` |
| `load_generated_files` | `(pdf_path: str) -> Optional[dict[str, str]]` | `Optional[dict[str, str]]` | Reads all files from `files/` dir via `rglob("*")` |
| `save_validation` | `(pdf_path: str, report: object) -> None` | `None` | Pickles validation report |
| `load_validation` | `(pdf_path: str) -> Optional[object]` | `Optional[object]` | Unpickles validation report |
| `save_metadata` | `(pdf_path: str, metadata: dict) -> None` | `None` | JSON dumps metadata |
| `load_metadata` | `(pdf_path: str) -> Optional[dict]` | `Optional[dict]` | JSON loads metadata |
| `clear` | `(pdf_path: Optional[str] = None) -> None` | `None` | Clears specific PDF cache or all caches via `shutil.rmtree()` |
| `summary` | `() -> str` | `str` | Returns human-readable summary of cached entries with metadata |

---

### 2.4 Agent Layer

---

#### `BaseAgent` (ABC) -- `agents/base.py`

Abstract base class for all pipeline agents.

**Constructor:**

```python
def __init__(
    self,
    name: str,
    provider: Optional[BaseProvider] = None,
) -> None
```

Sets `self._name = name` and `self._provider = provider or get_provider()`.

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Human-readable agent name |
| `provider` | `BaseProvider` | The underlying LLM provider |

**Abstract Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `execute` | `(**kwargs: Any) -> Any` | `Any` | Primary agent action. Subclasses implement stage-specific work |

**Concrete Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `log` | `(message: str) -> None` | `None` | Prints `[{agent_name}] {message}` |
| `communicate` | `(target_agent: BaseAgent, message: AgentMessage) -> AgentMessage` | `AgentMessage` | Synchronous in-process message passing. Logs send/receive, returns acknowledgement message |

---

#### `AgentOrchestrator` -- `agents/orchestrator.py`

Master controller for the 10-stage pipeline.

**Default Configuration:**

```python
_DEFAULT_CONFIG = {
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
```

**Constructor:**

```python
def __init__(
    self,
    provider: Optional[BaseProvider] = None,
    config: Optional[dict[str, Any]] = None,
) -> None
```

Merges user config over defaults.

**Public Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `run` | `(pdf_path: str, output_dir: str, paper_analysis: Any = None, document: Any = None, vision_context: Optional[list[str]] = None) -> dict[str, Any]` | `dict[str, Any]` | Executes all 10 stages. Returns result dict with keys: `files`, `plan`, `analysis`, `file_analyses`, `validation_report`, `execution_result`, `evaluation_score`, `metadata` |

**Static Stage Methods (all use lazy imports):**

| Stage | Method | Description |
|-------|--------|-------------|
| 1 | `_stage_parse_paper(pdf_path, paper_analysis, document, vision_context, provider)` | PaperAnalyzer: upload + diagram extraction + analyze |
| 2 | `_stage_plan(analysis, document, vision_context, provider)` | DecomposedPlanner (falls back to SystemArchitect) |
| 3 | `_stage_file_analysis(plan, analysis, provider)` | FileAnalyzer.analyze_all() |
| 4 | `_stage_code_generation(analysis, plan, document, provider)` | CodeSynthesizer.generate_codebase() |
| 5 | `_stage_test_generation(generated_files, analysis, plan, provider)` | TestGenerator.generate_tests() |
| 6 | `_stage_validation(generated_files, analysis, plan, provider, max_fix_iterations)` | CodeValidator.validate() + iterative fix_issues() |
| 7 | `_stage_execution(generated_files, output_dir, plan, analysis, provider, max_debug_iterations)` | ExecutionSandbox.execute() + AutoDebugger.debug() loop |
| 8 | `_stage_devops(plan, analysis, generated_files, provider)` | DevOpsGenerator.generate_all() |
| 9 | `_stage_evaluation(generated_files, reference_dir, provider)` | ReferenceEvaluator.evaluate_with_reference() or evaluate_without_reference() |
| 10 | `_stage_save(generated_files, output_dir)` | Writes all files to disk, returns count |

**Private Instance Methods:**

| Method | Signature | Return Type | Description |
|--------|-----------|-------------|-------------|
| `_run_interactive` | `(plan, analysis) -> None` | `None` | Displays plan summary, directory tree, file list. Waits for Enter or `q` to abort |
| `_refine_output` | `(artifact, artifact_label, provider, max_iterations) -> Any` | `Any` | Static. Passes artifact through SelfRefiner for N iterations |
| `_print_summary` | `(result, elapsed) -> None` | `None` | Static. Prints final pipeline summary with paper title, provider, file count, output dir, time, scores, stage timings |

---

## 3. Key Algorithms

### 3.1 Provider Auto-Detection

```
FUNCTION get_provider(provider_name, model_name, api_key, required_capability):
    IF provider_name is given:
        RETURN ProviderRegistry.create(provider_name, api_key, model_name)

    IF required_capability is given:
        best = ProviderRegistry.best_for(required_capability)
        // best_for logic:
        //   1. Call detect_available() to find providers with credentials
        //   2. Look up preference order for this capability:
        //      LONG_CONTEXT:      [gemini, anthropic, openai, ollama]
        //      VISION:            [gemini, openai, anthropic, ollama]
        //      CODE_GENERATION:   [anthropic, openai, gemini, ollama]
        //      STRUCTURED_OUTPUT: [openai, gemini, anthropic, ollama]
        //      FILE_UPLOAD:       [gemini]
        //   3. Return first available provider in preference order
        IF best:
            RETURN ProviderRegistry.create(best, api_key, model_name)

    // Fallback: try any available provider
    available = ProviderRegistry.detect_available()
    // detect_available logic:
    //   FOR each provider in [gemini, openai, anthropic, ollama]:
    //     IF provider has env key (GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY):
    //       IF os.environ.get(env_key) is truthy -> add to available list
    //     ELSE IF provider is ollama:
    //       TRY HTTP GET http://localhost:11434/api/tags (timeout=2s)
    //       IF status 200 -> add to available list

    IF not available:
        RAISE RuntimeError("No model providers available")
    RETURN ProviderRegistry.create(available[0], api_key, model_name)
```

### 3.2 Rolling Context Code Generation

```
FUNCTION generate_codebase(analysis, plan, document):
    generated = {}  // ordered dict: file_path -> content

    // plan.files is already sorted by FileSpec.priority (lower = first)
    // Typical order: config.yaml (-2), requirements.txt (-1), utils (0),
    //                model (1-5), data (3-5), training (6-8), eval (9), README (100)

    FOR EACH file_spec IN plan.files:
        context = build_context(analysis)  // paper, equations, hyperparams, losses

        // Rolling context window:
        dependency_context = ""
        FOR dep_path IN file_spec.dependencies:
            IF dep_path IN generated:
                content = generated[dep_path][:3000]  // truncate at 3000 chars
                dependency_context += format_as_code_block(dep_path, content)

        // Also include last 3 generated files not already in dependencies
        recent_paths = last_3_keys(generated) - file_spec.dependencies
        FOR path IN recent_paths:
            content = generated[path][:1500]  // truncate at 1500 chars
            dependency_context += format_as_code_block(path, content, label="recent")

        // Dynamic max_tokens based on file type:
        max_tokens = 8192  // default
        IF file_spec.path ends with (.yaml, .yml, .toml, .cfg, .txt, .md):
            max_tokens = 4096
        ELSE IF "model" or "train" in file_spec.path:
            max_tokens = 16384

        content = provider.generate(full_prompt, config=GenerationConfig(
            temperature=0.15, max_output_tokens=max_tokens))

        generated[file_spec.path] = clean_output(content)

    RETURN generated
```

### 3.3 Self-Refine Loop

```
FUNCTION refine(artifact, artifact_type, context, schema):
    VALIDATE artifact_type IN {"overall_plan", "architecture_design",
        "logic_design", "file_analysis", "config", "code"}

    current = artifact
    all_improvements = []
    last_critique = ""
    iterations_done = 0

    FOR iteration = 1 TO max_iterations:
        // --- VERIFY STEP ---
        artifact_str = serialize_artifact(current, artifact_type)
        //   JSON types -> json.dumps(artifact.__dict__)
        //   Text types -> str(artifact)

        prompt = paper_context + artifact_str + verify_prompt_template
        data = provider.generate_structured(prompt, VERIFY_SCHEMA)
        //   VERIFY_SCHEMA = {critique: str, issues: list[str],
        //                    severity: "none"|"minor"|"major"|"critical"}
        critique = data["critique"]
        issues = data["issues"]

        IF no issues:
            BREAK  // artifact is good, skip refinement

        // --- REFINE STEP ---
        refine_prompt = paper_context + critique + artifact_str + refine_prompt_template
        IF artifact_type in JSON_TYPES:
            refined = provider.generate_structured(refine_prompt, schema)
        ELSE:
            refined = provider.generate(refine_prompt)  // strip markdown fences

        all_improvements.extend(issues)
        current = refined
        iterations_done = iteration

    RETURN RefinementResult(
        original=artifact, refined=current, critique=last_critique,
        improvements=all_improvements, iterations=iterations_done,
        improved=(iterations_done > 0))
```

### 3.4 Auto-Debug Loop

```
FUNCTION debug(repo_dir, execution_result, generated_files):
    files = copy(generated_files)
    reports = []
    current_result = execution_result

    FOR iteration = 1 TO max_iterations:
        IF current_result.success:
            BREAK

        // 1. FIND RELEVANT FILES
        //    Parse traceback for 'File "..."' references
        //    Match basenames against generated_files keys
        //    Fallback: use all files if no matches
        focused_files = find_relevant_files(current_result.stderr, files)

        // 2. ANALYZE ERROR (LLM)
        prompt = build_debug_prompt(stderr, error_type, focused_files)
        //    Files truncated at 8000 chars, error at 4000 chars
        data = provider.generate_structured(prompt, FIX_SCHEMA)
        //    FIX_SCHEMA = {fixes: [{file_path, fixed_content,
        //                           error_description, fix_description}]}
        fixes = parse_fixes(data)

        IF no fixes:
            RECORD DebugReport(resolved=False)
            BREAK

        // 3. APPLY FIXES
        FOR fix IN fixes:
            files[fix.file_path] = fix.fixed_content  // full file replacement

        // 4. WRITE TO DISK
        FOR path, content IN files:
            write_file(repo_dir / path, content)

        // 5. RE-EXECUTE
        current_result = sandbox.execute(repo_dir)
        RECORD DebugReport(iteration, error_msg, error_type, fixes, resolved)

    RETURN (files, reports)
```

### 3.5 Decomposed Planning (4-Step)

```
FUNCTION plan(analysis):
    // STEP 1: OVERALL PLAN
    //   Input: paper context (title, abstract, equations, hyperparameters,
    //          contributions, datasets, diagrams)
    //   Output: OverallPlan with 6 fields
    //   Schema: {core_components, methods_to_implement, training_objectives,
    //            data_processing_steps, evaluation_protocols, summary}
    overall_plan = step1_overall_plan(analysis)

    // STEP 2: ARCHITECTURE DESIGN
    //   Input: paper context + overall_plan summary
    //   Output: ArchitectureDesign with file_list, Mermaid diagrams,
    //           module relationships
    arch_design = step2_architecture_design(analysis, overall_plan)

    // STEP 3: LOGIC DESIGN
    //   Input: paper context + overall_plan summary + architecture (file list,
    //          class diagram)
    //   Output: LogicDesign with execution_order (topologically sorted),
    //           dependency_graph, file_specifications
    logic_design = step3_logic_design(analysis, overall_plan, arch_design)

    // STEP 4: CONFIG GENERATION
    //   Input: paper title + hyperparameters + training objectives
    //   Output: YAML string (NOT structured -- plain generation)
    config_content = step4_config_generation(analysis, overall_plan,
                                             arch_design, logic_design)

    // COMBINE into backward-compatible ArchitecturePlan:
    //   - FileSpec list from arch_design.file_list + logic_design descriptions
    //   - Priority from logic_design.execution_order index
    //   - Dependencies from logic_design.dependency_graph
    //   - Build directory tree from file paths
    //   - Detect training/inference entrypoints by filename keywords
    //   - Extract requirements from overall_plan.core_components
    //   - Base requirements always include: torch>=2.0, pyyaml, numpy
    combined = to_architecture_plan(analysis, overall_plan, arch_design,
                                     logic_design, config_content)

    RETURN PlanningResult(overall_plan, arch_design, logic_design,
                          config_content, combined)
```

### 3.6 Paper Parsing Fallback Chain

```
FUNCTION parse(pdf_path):
    IF not file_exists(pdf_path):
        RAISE FileNotFoundError

    backends = [
        ("doc2json", _parse_with_doc2json),   // Highest quality
        ("GROBID",   _parse_with_grobid),      // High quality
        ("PyMuPDF",  _parse_with_pymupdf),     // Good quality
        ("PyPDF2",   _parse_with_pypdf2),      // Basic fallback
    ]

    FOR (name, method) IN backends:
        TRY:
            result = method(pdf_path)
            RETURN result
        CATCH ImportError:
            // Library not installed, try next
            CONTINUE
        CATCH ConnectionError:
            // GROBID server not reachable, try next
            CONTINUE
        CATCH Exception:
            // Any other failure, try next
            CONTINUE

    RAISE RuntimeError("All parsing backends failed")
```

**Backend Quality Comparison:**

| Backend | Sections | Figures | Tables | Equations | References | Dependencies |
|---------|----------|---------|--------|-----------|------------|--------------|
| doc2json | Body text sections | No | No | From text regex | Bib entries | `s2orc-doc2json` |
| GROBID | TEI XML divs | Yes (figDesc) | Yes (type=table) | From text regex | biblStruct titles | Running GROBID server |
| PyMuPDF | Font-size heuristic | Embedded images | No | From text regex | No | `PyMuPDF` |
| PyPDF2 | Regex heuristic | No | No | From text regex | No | `PyPDF2` |

### 3.7 Error Classification

```
FUNCTION classify_error(stderr: str) -> str:
    // Patterns checked in order (most specific first):
    PATTERNS = [
        (r"ModuleNotFoundError",  "ModuleNotFoundError"),
        (r"ImportError",          "ImportError"),
        (r"SyntaxError",          "SyntaxError"),
        (r"IndentationError",     "IndentationError"),
        (r"NameError",            "NameError"),
        (r"TypeError",            "TypeError"),
        (r"ValueError",           "ValueError"),
        (r"AttributeError",       "AttributeError"),
        (r"KeyError",             "KeyError"),
        (r"IndexError",           "IndexError"),
        (r"FileNotFoundError",    "FileNotFoundError"),
        (r"ZeroDivisionError",    "ZeroDivisionError"),
        (r"RuntimeError",         "RuntimeError"),
        (r"cuda.*out of memory",  "CudaOOMError"),
        (r"OOM",                  "CudaOOMError"),
        (r"AssertionError",       "AssertionError"),
        (r"NotImplementedError",  "NotImplementedError"),
        (r"PermissionError",      "PermissionError"),
        (r"OSError",              "OSError"),
        (r"Traceback",            "UnclassifiedError"),
    ]

    FOR (pattern, error_name) IN PATTERNS:
        IF re.search(pattern, stderr, IGNORECASE):
            RETURN error_name

    RETURN "UnknownError" IF stderr.strip() ELSE ""
```

---

## 4. Prompt Loading Mechanism

Every module in the pipeline uses a consistent prompt loading pattern. This enables external prompt customization while providing reliable inline fallbacks.

### Pattern

```python
# 1. Compute path at class level (relative to project root)
PROMPT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),  # <project_root>
    "prompts",
    "filename.txt"
)

# 2. Load with placeholder substitution
def _load_prompt(self, path: str, **kwargs) -> str:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            template = f.read()
        for key, value in kwargs.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        return template
    return ""  # signal: file not found

# 3. Fallback to inline default
prompt = self._load_prompt(self.PROMPT_FILE)
if not prompt:
    prompt = self._default_analysis_prompt()  # inline string
```

### Prompt File Inventory

| Module | Prompt File(s) | Fallback Method |
|--------|---------------|-----------------|
| `PaperAnalyzer` | `prompts/analyzer.txt`, `prompts/diagram_extractor.txt` | `_default_analysis_prompt()` |
| `SystemArchitect` | `prompts/architect.txt` | `_default_prompt()` |
| `DecomposedPlanner` | `prompts/overall_plan.txt`, `prompts/architecture_design.txt`, `prompts/logic_design.txt` | `_default_overall_plan_prompt()`, `_default_arch_design_prompt()`, `_default_logic_design_prompt()` (module-level functions) |
| `FileAnalyzer` | `prompts/file_analysis.txt` | `_default_prompt()` (module-level function) |
| `CodeSynthesizer` | `prompts/coder.txt` | `_default_prompt()` |
| `CodeValidator` | `prompts/validator.txt` | `_default_prompt()` |
| `SelfRefiner` | `prompts/self_refine_verify.txt`, `prompts/self_refine_refine.txt` | `_default_verify_prompt()`, `_default_refine_prompt()` (module-level functions) |
| `AutoDebugger` | `prompts/auto_debug.txt` | `_default_debug_prompt()` |
| `ReferenceEvaluator` | `prompts/evaluator.txt` | `_default_ref_prompt()`, `_default_noref_prompt()` |
| `EquationExtractor` | `prompts/equation_extractor.txt` | `_default_prompt()` |
| `TestGenerator` | `prompts/test_generator.txt` | `_default_prompt()` |

### Placeholder Syntax

Placeholders use double curly braces: `{{variable_name}}`. They are replaced via simple string substitution (not Jinja2). Examples:

- `{{error_type}}` -- replaced with the classified error type
- `{{error_message}}` -- replaced with stderr content
- `{{source_files}}` -- replaced with formatted file content
- `{{mode}}` -- replaced with `"with_reference"` or `"without_reference"`

---

## 5. JSON Parsing Strategy

All structured LLM outputs follow a consistent 4-tier fallback chain to maximize robustness against malformed model responses.

### Tier 1: Structured Generation

```python
try:
    data = self.provider.generate_structured(
        prompt=full_prompt,
        schema=json_schema,
        system_prompt="...",
        config=GenerationConfig(temperature=0.1, max_output_tokens=8192),
    )
    # data is already a parsed dict
except Exception as e:
    # Fall through to Tier 2
```

Each provider implements `generate_structured()` differently:
- **Gemini**: Sets `response_mime_type="application/json"`, prepends schema instruction, calls `generate()`, parses with `json.loads()`.
- **OpenAI**: Sets `response_format={"type": "json_object"}`, prepends schema instruction.
- **Anthropic**: Prepends "Respond ONLY with valid JSON" instruction + schema.
- **Ollama**: Sets `format: "json"` in request payload, prepends schema instruction.

### Tier 2: Text Generation with Fence Stripping

```python
result = self.provider.generate(
    prompt=prompt + "\n\nRespond with ONLY a JSON object.",
    system_prompt="... Respond only with valid JSON.",
    config=GenerationConfig(temperature=0.1),
)
text = result.text.strip()

# Strip markdown fences
if text.startswith("```"):
    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
if text.endswith("```"):
    text = text[:-3]

data = json.loads(text.strip())
```

### Tier 3: Regex Extraction

Used implicitly when the above fails. Some modules attempt to extract JSON from mixed text:

```python
# Extract first JSON object from response
import re
match = re.search(r'\{.*\}', text, re.DOTALL)
if match:
    data = json.loads(match.group())
```

### Tier 4: Sensible Defaults

When all parsing attempts fail, each module returns a reasonable default:

| Module | Default Return |
|--------|---------------|
| `PaperAnalyzer` | Empty `PaperAnalysis` with `data = {}` |
| `SystemArchitect` | Raises exception (no silent default) |
| `DecomposedPlanner` | Raises exception from `_fallback_generate` |
| `CodeValidator` | Raises exception from `_fallback_validate` |
| `AutoDebugger` | `{"fixes": []}` -- no fixes applied |
| `ReferenceEvaluator` | `{}` -- empty evaluation |
| `SelfRefiner` | Raises exception from `_fallback_json_generate` |
| `EquationExtractor` | `[]` -- empty equation list |

### Markdown Fence Stripping (Common Pattern)

This exact code appears in 10+ locations across the codebase:

```python
text = result.text.strip()
if text.startswith("```"):
    # Remove opening fence (may include language tag like ```json)
    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
if text.endswith("```"):
    text = text[:-3]
return json.loads(text.strip())
```

---

## Appendix: Module-to-File Mapping

| Module | File Path | Lines |
|--------|-----------|-------|
| `BaseProvider`, `ModelCapability`, `ModelInfo`, `GenerationConfig`, `GenerationResult` | `providers/base.py` | 138 |
| `GeminiProvider` | `providers/gemini.py` | 183 |
| `OpenAIProvider` | `providers/openai_provider.py` | 166 |
| `AnthropicProvider` | `providers/anthropic_provider.py` | 160 |
| `OllamaProvider` | `providers/ollama.py` | 187 |
| `ProviderRegistry`, `get_provider` | `providers/registry.py` | 162 |
| `PaperAnalyzer`, `PaperAnalysis` | `core/analyzer.py` | 303 |
| `SystemArchitect`, `FileSpec`, `ArchitecturePlan` | `core/architect.py` | 289 |
| `DecomposedPlanner`, `OverallPlan`, `ArchitectureDesign`, `LogicDesign`, `PlanningResult` | `core/planner.py` | 697 |
| `FileAnalyzer`, `FileAnalysis` | `core/file_analyzer.py` | 381 |
| `CodeSynthesizer` | `core/coder.py` | 249 |
| `CodeValidator`, `ValidationIssue`, `ValidationReport` | `core/validator.py` | 290 |
| `SelfRefiner`, `RefinementResult` | `core/refiner.py` | 432 |
| `PaperParser`, `ParsedPaper` | `core/paper_parser.py` | 546 |
| `ExecutionSandbox`, `ExecutionResult` | `advanced/executor.py` | 376 |
| `AutoDebugger`, `DebugFix`, `DebugReport` | `advanced/debugger.py` | 393 |
| `ReferenceEvaluator`, `EvaluationScore` | `advanced/evaluator.py` | 435 |
| `DevOpsGenerator` | `advanced/devops.py` | 432 |
| `EquationExtractor`, `ExtractedEquation` | `advanced/equation_extractor.py` | 182 |
| `TestGenerator` | `advanced/test_generator.py` | 257 |
| `ConfigGenerator` | `advanced/config_generator.py` | 204 |
| `PipelineCache` | `advanced/cache.py` | 185 |
| `BaseAgent`, `AgentMessage` | `agents/base.py` | 148 |
| `AgentOrchestrator` | `agents/orchestrator.py` | 701 |
| `main` (CLI entry point) | `main.py` | 634 |
