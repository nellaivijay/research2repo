# Provider System and Configuration

This document provides an in-depth reference for the Research2Repo provider abstraction layer, the configuration system, and guidance on extending the framework with custom providers.

---

## Table of Contents

1. [Provider Architecture](#1-provider-architecture)
2. [Available Providers](#2-available-providers)
3. [Provider Selection Logic](#3-provider-selection-logic)
4. [Cost Estimation](#4-cost-estimation)
5. [Configuration System](#5-configuration-system)
6. [Adding a Custom Provider](#6-adding-a-custom-provider)
7. [Temperature and Token Tuning](#7-temperature-and-token-tuning)

---

## 1. Provider Architecture

Research2Repo uses a provider abstraction layer that lets the pipeline work with any LLM backend through a uniform interface. All providers live in the `providers/` directory.

```
providers/
  base.py              # Abstract interface, capability enum, data classes
  gemini.py            # Google Gemini provider
  openai_provider.py   # OpenAI GPT provider
  anthropic_provider.py # Anthropic Claude provider
  ollama.py            # Local Ollama provider
  registry.py          # Auto-detection, factory, cost estimation
  __init__.py          # Public API exports
```

### BaseProvider (Abstract Base Class)

Every provider must subclass `BaseProvider` from `providers/base.py`. It defines the contract that the pipeline relies on.

```python
class BaseProvider(ABC):
    def __init__(self, api_key=None, model_name=None):
        self.api_key = api_key
        self.model_name = model_name or self.default_model()

    @abstractmethod
    def default_model(self) -> str: ...

    @abstractmethod
    def available_models(self) -> list[ModelInfo]: ...

    @abstractmethod
    def generate(self, prompt, system_prompt=None, config=None, images=None) -> GenerationResult: ...

    @abstractmethod
    def generate_structured(self, prompt, schema, system_prompt=None, config=None) -> dict: ...

    def supports(self, capability: ModelCapability) -> bool: ...
    def upload_file(self, file_path: str) -> object: ...
    def model_info(self) -> ModelInfo | None: ...
```

**Abstract methods that every provider must implement:**

| Method | Purpose |
|--------|---------|
| `default_model()` | Returns the default model name string for this provider. |
| `available_models()` | Returns a list of `ModelInfo` objects describing all supported models. |
| `generate()` | Core text generation. Accepts a prompt, optional system prompt, generation config, and optional image bytes for vision. Returns a `GenerationResult`. |
| `generate_structured()` | Generates structured JSON output conforming to a given schema. Falls back to text generation with JSON parsing if the provider has no native JSON mode. |

**Optional methods (with default implementations):**

| Method | Purpose |
|--------|---------|
| `supports(capability)` | Checks if the current model supports a given `ModelCapability`. Looks up the model in `available_models()`. |
| `upload_file(file_path)` | Uploads a file for use in prompts (Gemini File API). Default raises `NotImplementedError`. |
| `model_info()` | Returns the `ModelInfo` for the currently selected model. |

### ModelCapability Enum

The `ModelCapability` enum defines 7 capability flags that describe what a model can do:

| Capability | Value | Description |
|------------|-------|-------------|
| `TEXT_GENERATION` | 1 | Basic text generation. All models have this. |
| `VISION` | 2 | Image and diagram understanding. Accepts image bytes in the `generate()` call. |
| `LONG_CONTEXT` | 3 | Context windows of 100K+ tokens. Enables single-pass paper analysis without chunking. |
| `STRUCTURED_OUTPUT` | 4 | Native JSON mode or function calling. Enables reliable structured data extraction. |
| `CODE_GENERATION` | 5 | Optimized for generating source code. Models with this flag are preferred for the code synthesis stage. |
| `FILE_UPLOAD` | 6 | Native file upload API. Currently only Gemini supports this, allowing PDFs to be sent directly without text extraction. |
| `STREAMING` | 7 | Streaming response support. Currently declared but not used by the pipeline. |

These capabilities are used by the registry to route tasks to the most suitable provider. For example, diagram extraction is routed to a provider with `VISION`, and PDF upload is routed to one with `FILE_UPLOAD`.

### ModelInfo Dataclass

Each model is described by a `ModelInfo` object:

```python
@dataclass
class ModelInfo:
    name: str                              # Model identifier (e.g., "gpt-4o")
    provider: str                          # Provider name (e.g., "openai")
    max_context_tokens: int                # Maximum input context window size
    max_output_tokens: int                 # Maximum output tokens per generation
    capabilities: list[ModelCapability]    # List of supported capabilities
    cost_per_1k_input: float = 0.0         # USD per 1,000 input tokens
    cost_per_1k_output: float = 0.0        # USD per 1,000 output tokens
```

### GenerationConfig Dataclass

Generation parameters are passed via `GenerationConfig`:

```python
@dataclass
class GenerationConfig:
    temperature: float = 0.2              # Sampling temperature (0.0 = deterministic)
    top_p: float = 0.95                   # Nucleus sampling threshold
    max_output_tokens: int = 8192         # Maximum tokens to generate
    stop_sequences: list[str] = []        # Sequences that stop generation
    response_format: str | None = None    # "json" for JSON mode, None for text
```

The pipeline uses different configs for different tasks:

- **Code generation:** temperature 0.15, max_output_tokens 16384.
- **Analysis/extraction:** temperature 0.1, max_output_tokens 8192.
- **Structured output:** response_format="json".

### GenerationResult Dataclass

Every `generate()` call returns a standardized `GenerationResult`:

```python
@dataclass
class GenerationResult:
    text: str                             # The generated text content
    model: str                            # Model that produced the response
    input_tokens: int = 0                 # Number of input tokens consumed
    output_tokens: int = 0                # Number of output tokens generated
    finish_reason: str = "stop"           # Why generation stopped ("stop", "length", etc.)
    raw_response: object | None = None    # Provider-specific raw response object
```

---

## 2. Available Providers

### Google Gemini (`providers/gemini.py`)

The recommended provider for Research2Repo. Gemini offers the largest context windows, native PDF upload via the File API, and vision capabilities -- all in a single model.

**Setup:**

```bash
export GEMINI_API_KEY="your_key_here"
pip install google-generativeai
```

**Models:**

| Model | Context | Max Output | Capabilities | Input Cost | Output Cost |
|-------|---------|------------|-------------|------------|-------------|
| `gemini-2.5-pro-preview-05-06` (default) | 1,048,576 | 65,536 | TEXT, VISION, LONG_CONTEXT, STRUCTURED, CODE, FILE_UPLOAD, STREAMING | $0.00125/1K | $0.01/1K |
| `gemini-2.0-flash` | 1,048,576 | 8,192 | TEXT, VISION, LONG_CONTEXT, CODE, FILE_UPLOAD, STREAMING | $0.0001/1K | $0.0004/1K |
| `gemini-1.5-pro` | 2,097,152 | 8,192 | TEXT, VISION, LONG_CONTEXT, STRUCTURED, CODE, FILE_UPLOAD, STREAMING | $0.00125/1K | $0.005/1K |

**Unique features:**

- **File Upload API:** PDFs can be uploaded directly via `genai.upload_file()` and referenced in prompts. This avoids text extraction entirely and preserves the full document layout, figures, and formatting. The pipeline uses this through `generate_with_file()`.
- **Native Vision:** Images and PDF pages are processed natively using PIL. Vision requests pass image bytes directly in the `generate()` call.
- **2M Token Context (1.5 Pro):** The largest context window available, allowing even the longest papers to be processed in a single pass.
- **JSON Mode:** Structured output uses `response_mime_type: "application/json"` in the generation config.

### OpenAI (`providers/openai_provider.py`)

Strong general-purpose provider with excellent code generation and structured output support.

**Setup:**

```bash
export OPENAI_API_KEY="your_key_here"
pip install openai
```

**Models:**

| Model | Context | Max Output | Capabilities | Input Cost | Output Cost |
|-------|---------|------------|-------------|------------|-------------|
| `gpt-4o` (default) | 128,000 | 16,384 | TEXT, VISION, LONG_CONTEXT, STRUCTURED, CODE, STREAMING | $0.0025/1K | $0.01/1K |
| `gpt-4-turbo` | 128,000 | 4,096 | TEXT, VISION, LONG_CONTEXT, STRUCTURED, CODE, STREAMING | $0.01/1K | $0.03/1K |
| `o3` | 200,000 | 100,000 | TEXT, VISION, LONG_CONTEXT, STRUCTURED, CODE, STREAMING | $0.01/1K | $0.04/1K |
| `o1` | 200,000 | 100,000 | TEXT, LONG_CONTEXT, CODE | $0.015/1K | $0.06/1K |

**Unique features:**

- **JSON Mode:** Uses `response_format: {"type": "json_object"}` in the API call for reliable structured output.
- **Vision via Base64:** Images are encoded as base64 data URIs and embedded in the message content array.
- **Reasoning Models (o3, o1):** Extended thinking models with very large output limits. Note that o1 does not support vision or structured output.

### Anthropic (`providers/anthropic_provider.py`)

Excellent code generation quality. Claude models are often the top performer for complex implementations.

**Setup:**

```bash
export ANTHROPIC_API_KEY="your_key_here"
pip install anthropic
```

**Models:**

| Model | Context | Max Output | Capabilities | Input Cost | Output Cost |
|-------|---------|------------|-------------|------------|-------------|
| `claude-sonnet-4-20250514` (default) | 200,000 | 64,000 | TEXT, VISION, LONG_CONTEXT, STRUCTURED, CODE, STREAMING | $0.003/1K | $0.015/1K |
| `claude-opus-4-20250514` | 200,000 | 32,000 | TEXT, VISION, LONG_CONTEXT, STRUCTURED, CODE, STREAMING | $0.015/1K | $0.075/1K |
| `claude-3-5-sonnet-20241022` | 200,000 | 8,192 | TEXT, VISION, LONG_CONTEXT, STRUCTURED, CODE, STREAMING | $0.003/1K | $0.015/1K |

**Unique features:**

- **Vision via Base64:** Images are sent as base64-encoded content blocks with `type: "image"` and `source.type: "base64"`.
- **System Prompt:** Uses the dedicated `system` parameter in the API call (not injected into the message list).
- **Structured Output Handling:** Instructs the model to respond only with valid JSON. Strips markdown code fences from responses before parsing, handling models that wrap JSON in triple backticks.
- **200K Context Across All Models:** All Claude models support 200K input tokens, making them excellent for long papers.

### Ollama (`providers/ollama.py`)

Local, free inference using self-hosted models. Requires the Ollama application to be installed and running.

**Setup:**

```bash
# Install Ollama from https://ollama.ai
# Pull one or more models:
ollama pull deepseek-coder-v2
ollama pull llama3.1:70b
ollama pull codellama:34b
ollama pull llava:13b
ollama pull mistral

# Optionally set a custom host:
export OLLAMA_HOST="http://localhost:11434"
```

**Known Models:**

| Model | Context | Max Output | Capabilities | Cost |
|-------|---------|------------|-------------|------|
| `deepseek-coder-v2:latest` (default) | 128,000 | 8,192 | TEXT, CODE, LONG_CONTEXT | Free |
| `llama3.1:70b` | 128,000 | 8,192 | TEXT, LONG_CONTEXT, CODE | Free |
| `codellama:34b` | 16,384 | 4,096 | TEXT, CODE | Free |
| `llava:13b` | 4,096 | 2,048 | TEXT, VISION | Free |
| `mistral:latest` | 32,768 | 4,096 | TEXT, CODE | Free |

**Unique features:**

- **Free and Local:** No API keys required. All inference runs on your hardware.
- **Dynamic Model Discovery:** The provider queries the Ollama `/api/tags` endpoint to discover locally available models. Any model not in the known list is registered with default capabilities (TEXT_GENERATION only).
- **Custom Host:** Set `OLLAMA_HOST` to point to a remote Ollama instance.
- **JSON Mode:** Uses `"format": "json"` in the API payload when structured output is requested.
- **Vision Support:** The `llava:13b` model supports vision. Images are sent as base64-encoded strings in the `images` field.

**Important considerations:**

- Output quality varies significantly by model size and type. Larger models (70b+) produce substantially better code.
- Context windows are often smaller than cloud providers, which may limit analysis quality for very long papers.
- Generation is slower than cloud APIs unless you have high-end GPU hardware.

---

## 3. Provider Selection Logic

### Auto-Detection

When no `--provider` flag is given, Research2Repo auto-detects available providers by checking:

1. **API key environment variables:** `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`.
2. **Ollama availability:** Sends a health check to the Ollama server (`GET /api/tags` with a 2-second timeout).

The first available provider wins, checked in this order: Gemini, OpenAI, Anthropic, Ollama.

```python
# Auto-detection priority order:
available = ProviderRegistry.detect_available()
# Returns e.g. ["gemini", "openai"] based on which keys are set
# Pipeline uses available[0]
```

### Capability-Based Routing

The `ProviderRegistry.best_for(capability)` method finds the best available provider for a specific task. Each capability has its own preference order:

| Capability | Preference Order |
|------------|-----------------|
| `LONG_CONTEXT` | Gemini > Anthropic > OpenAI > Ollama |
| `VISION` | Gemini > OpenAI > Anthropic > Ollama |
| `CODE_GENERATION` | Anthropic > OpenAI > Gemini > Ollama |
| `STRUCTURED_OUTPUT` | OpenAI > Gemini > Anthropic > Ollama |
| `FILE_UPLOAD` | Gemini (only provider with this capability) |

This routing is used internally. For example, when the pipeline needs to extract diagrams, it may use `best_for(VISION)` to pick Gemini even if the primary provider is OpenAI.

### Explicit Override

Use `--provider` and `--model` to override auto-detection entirely:

```bash
python main.py --pdf_url "..." --provider anthropic --model claude-opus-4-20250514
```

For vision tasks specifically, use `--vision-provider` and `--vision-model`:

```bash
python main.py --pdf_url "..." --provider openai --vision-provider gemini
```

### Fallback Chain for Structured Output

When `generate_structured()` is called, the pipeline follows this fallback chain:

1. **Native JSON mode** -- If the provider supports `STRUCTURED_OUTPUT`, use it (e.g., OpenAI's `response_format: json_object`, Gemini's `response_mime_type: application/json`).
2. **Prompt-based JSON** -- Prepend a schema instruction to the prompt asking the model to respond with valid JSON only.
3. **Parse with cleanup** -- Strip markdown code fences (` ```json ... ``` `) if the model wraps its JSON response.
4. **JSON parse** -- Parse the cleaned response with `json.loads()`.

If parsing fails, the error propagates up. The pipeline stages handle retries at their own level.

---

## 4. Cost Estimation

### Using the Cost Estimator

The `ProviderRegistry.estimate_cost()` method calculates the estimated USD cost for a given usage:

```python
from providers import ProviderRegistry

cost = ProviderRegistry.estimate_cost(
    provider_name="openai",
    model_name="gpt-4o",
    input_tokens=50000,
    output_tokens=20000,
)
print(f"${cost:.4f}")  # $0.3250
```

The formula is:

```
cost = (input_tokens / 1000) * cost_per_1k_input
     + (output_tokens / 1000) * cost_per_1k_output
```

### Typical Pipeline Costs (20-Page Paper)

These are rough estimates for a typical 20-page ML paper. Actual costs depend on paper length, number of files generated, and features enabled.

**Classic Mode (10 stages):**

| Provider | Model | Estimated Cost |
|----------|-------|---------------|
| Gemini | gemini-2.5-pro-preview-05-06 | $0.10 - $0.30 |
| Gemini | gemini-2.0-flash | $0.01 - $0.05 |
| OpenAI | gpt-4o | $0.30 - $0.80 |
| OpenAI | gpt-4-turbo | $0.80 - $2.00 |
| Anthropic | claude-sonnet-4-20250514 | $0.30 - $0.80 |
| Anthropic | claude-opus-4-20250514 | $1.50 - $4.00 |
| Ollama | any | $0.00 (free) |

**Agent Mode (with --refine --execute):**

Expect 2-3x the classic mode cost due to additional planning stages, per-file analysis, self-refine verification/refinement loops, and execution debugging iterations.

| Provider | Model | Estimated Cost |
|----------|-------|---------------|
| Gemini | gemini-2.5-pro-preview-05-06 | $0.25 - $0.75 |
| Gemini | gemini-2.0-flash | $0.03 - $0.12 |
| OpenAI | gpt-4o | $0.75 - $2.00 |
| Anthropic | claude-sonnet-4-20250514 | $0.75 - $2.00 |
| Ollama | any | $0.00 (free) |

**Cost-saving tips:**

- Use `gemini-2.0-flash` for experimentation -- it is 10-25x cheaper than other models.
- Skip validation and tests in early iterations: `--skip-validation --skip-tests`.
- Enable caching (on by default) to avoid re-running unchanged stages.
- Use `--no-cache` only when you need a completely fresh run.

---

## 5. Configuration System

### R2RConfig Dataclass

The global configuration is defined in `config.py` as the `R2RConfig` dataclass:

```python
@dataclass
class R2RConfig:
    # Provider defaults
    default_provider: str = "auto"        # auto, gemini, openai, anthropic, ollama
    default_model: str = ""               # Empty = use provider's default model

    # Pipeline toggles
    enable_validation: bool = True        # Run the validation stage
    enable_test_generation: bool = True   # Generate pytest suite
    enable_equation_extraction: bool = True  # Dedicated equation extraction pass
    enable_caching: bool = True           # Content-addressed pipeline cache
    max_fix_iterations: int = 2           # Auto-fix attempts for critical issues

    # Download settings
    pdf_timeout: int = 120                # HTTP timeout for PDF download (seconds)
    pdf_max_size_mb: int = 100            # Maximum PDF file size

    # Generation settings
    code_temperature: float = 0.15        # Temperature for code generation
    analysis_temperature: float = 0.1     # Temperature for analysis/extraction
    max_code_tokens: int = 16384          # Max output tokens for code generation
    max_analysis_tokens: int = 8192       # Max output tokens for analysis

    # Vision settings
    max_diagram_pages: int = 30           # Max pages to scan for diagrams
    diagram_dpi: int = 150                # DPI for PDF page rendering
    vision_batch_size: int = 4            # Pages per vision batch

    # Cache settings
    cache_dir: str = ".r2r_cache"         # Cache directory path

    # Output settings
    verbose: bool = False                 # Verbose output
```

### Environment Variable Mapping

`R2RConfig.from_env()` creates a config from environment variables:

```python
config = R2RConfig.from_env()
```

The mapping is:

| Environment Variable | Config Field | Behavior |
|---------------------|--------------|----------|
| `R2R_PROVIDER` | `default_provider` | Direct value mapping. Default: `"auto"`. |
| `R2R_MODEL` | `default_model` | Direct value mapping. Default: `""` (provider default). |
| `R2R_SKIP_VALIDATION` | `enable_validation` | Set to `"true"` to disable. Inverted logic. |
| `R2R_SKIP_TESTS` | `enable_test_generation` | Set to `"true"` to disable. Inverted logic. |
| `R2R_NO_CACHE` | `enable_caching` | Set to `"true"` to disable. Inverted logic. |
| `R2R_CACHE_DIR` | `cache_dir` | Direct value mapping. Default: `".r2r_cache"`. |
| `R2R_VERBOSE` | `verbose` | Set to `"true"` to enable. |

### Configuration Precedence

Settings are resolved in this order (highest priority first):

```
CLI arguments  >  Environment variables  >  R2RConfig defaults
```

For example:

```bash
# Environment sets provider to gemini:
export R2R_PROVIDER="gemini"

# CLI overrides to openai:
python main.py --pdf_url "..." --provider openai
# Result: openai is used
```

### Timeout Settings

| Config Field | Default | Description |
|-------------|---------|-------------|
| `llm_generation_timeout` | 600 | Max seconds per LLM call |
| `validation_timeout` | 300 | Max seconds for validation pass |
| `execution_timeout` | 900 | Max seconds for sandbox execution |

These values are defined in `R2RConfig` and can be overridden programmatically.

### Retry Behavior

All provider API calls are wrapped with `retry_on_error(max_retries=2, backoff=1.0)`:

- Transient errors (connection, timeout): automatic retry with exponential backoff
- Rate limits (429 / quota): detected and retried
- Backoff schedule: 1s, 2s, 4s (doubling each attempt)
- Non-recoverable errors are raised immediately

### Agent Mode Configuration

The `AgentOrchestrator` accepts a configuration dict with these keys and defaults:

```python
_DEFAULT_CONFIG = {
    "enable_refine": False,           # Self-refine loops at each stage
    "enable_execution": False,        # Execution sandbox + auto-debug
    "enable_tests": True,             # Test generation
    "enable_evaluation": False,       # Reference-based evaluation
    "enable_devops": True,            # Dockerfile, Makefile, CI generation
    "interactive": False,             # Pause after planning for review
    "max_debug_iterations": 3,        # Auto-debug retry limit
    "max_refine_iterations": 2,       # Self-refine retry limit per stage
    "max_fix_iterations": 2,          # Validation auto-fix retry limit
    "reference_dir": None,            # Path to reference implementation
    "verbose": False,                 # Verbose output
}
```

CLI flags map directly to these config keys. When using the `AgentOrchestrator` programmatically, pass a dict that overrides any subset of these defaults:

```python
from agents.orchestrator import AgentOrchestrator

config = {
    "enable_refine": True,
    "enable_execution": True,
    "max_debug_iterations": 5,
}

orchestrator = AgentOrchestrator(provider=provider, config=config)
# All other keys retain their defaults
```

---

## 6. Adding a Custom Provider

You can extend Research2Repo with your own LLM provider by following these steps.

### Step 1: Subclass BaseProvider

Create a new file in the `providers/` directory (e.g., `providers/my_provider.py`):

```python
"""
Custom provider for MyLLM service.
"""

import os
from typing import Optional

from providers.base import (
    BaseProvider,
    GenerationConfig,
    GenerationResult,
    ModelCapability,
    ModelInfo,
)


class MyProvider(BaseProvider):
    """Custom provider for MyLLM."""

    MODELS = [
        ModelInfo(
            name="my-model-large",
            provider="myllm",
            max_context_tokens=100_000,
            max_output_tokens=8_192,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
            ],
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.005,
        ),
    ]

    def __init__(self, api_key=None, model_name=None):
        key = api_key or os.environ.get("MYLLM_API_KEY")
        if not key:
            raise ValueError("MYLLM_API_KEY not set.")
        super().__init__(api_key=key, model_name=model_name)
        # Initialize your client here

    def default_model(self) -> str:
        return "my-model-large"

    def available_models(self) -> list[ModelInfo]:
        return self.MODELS
```

### Step 2: Implement Abstract Methods

Implement `generate()` and `generate_structured()`:

```python
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
        images: Optional[list[bytes]] = None,
    ) -> GenerationResult:
        cfg = config or GenerationConfig()

        # Call your LLM API here
        response = self._call_api(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=cfg.temperature,
            max_tokens=cfg.max_output_tokens,
        )

        return GenerationResult(
            text=response["text"],
            model=self.model_name,
            input_tokens=response.get("input_tokens", 0),
            output_tokens=response.get("output_tokens", 0),
            finish_reason=response.get("finish_reason", "stop"),
            raw_response=response,
        )

    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ) -> dict:
        import json
        cfg = config or GenerationConfig()
        cfg.response_format = "json"
        schema_instruction = (
            f"Respond with valid JSON conforming to this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```\n\n"
        )
        result = self.generate(
            schema_instruction + prompt,
            system_prompt=system_prompt,
            config=cfg,
        )
        return json.loads(result.text)
```

### Step 3: Register with ProviderRegistry

Register your provider so it can be discovered and used:

```python
from providers.registry import ProviderRegistry

ProviderRegistry.register(
    name="myllm",                              # Short name for --provider flag
    module_path="providers.my_provider",        # Python import path
    class_name="MyProvider",                    # Class name
    env_key="MYLLM_API_KEY",                    # Env var for auto-detection (or None)
)
```

You can place this registration call in your own script, or add it to `providers/__init__.py` for automatic registration.

### Step 4: Set Capability Flags

Make sure your `ModelInfo` objects have accurate capability flags. The pipeline uses these flags to decide:

- Whether to send images to your provider (requires `VISION`).
- Whether to use your provider for PDF upload (requires `FILE_UPLOAD`).
- Whether to prefer your provider for code generation tasks (benefits from `CODE_GENERATION`).
- Whether to use JSON mode (benefits from `STRUCTURED_OUTPUT`).

If you add `VISION` support, handle the `images` parameter in your `generate()` method. If you add `FILE_UPLOAD` support, override the `upload_file()` method.

### Step 5: Use Your Provider

```bash
export MYLLM_API_KEY="your_key"
python main.py --pdf_url "..." --provider myllm --model my-model-large
```

Or programmatically:

```python
from providers import get_provider

provider = get_provider(provider_name="myllm")
```

---

## 7. Temperature and Token Tuning

Research2Repo uses different generation parameters for different pipeline stages. These are defined in the `R2RConfig` dataclass and applied through `GenerationConfig` objects at each stage.

### Default Values

| Parameter | Default Value | Used For |
|-----------|---------------|----------|
| `code_temperature` | 0.15 | Code synthesis (Stage 6/4). Low temperature produces more deterministic, syntactically correct code. |
| `analysis_temperature` | 0.1 | Paper analysis, equation extraction, architecture design, validation. Very low temperature for reliable structured extraction. |
| `max_code_tokens` | 16,384 | Maximum output tokens for code generation. A single file generation call can produce up to 16K tokens of code. |
| `max_analysis_tokens` | 8,192 | Maximum output tokens for analysis and extraction stages. Analysis outputs are typically shorter than code. |

Additionally, the `GenerationConfig` defaults are:

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| `temperature` | 0.2 | Global default. Overridden by stage-specific values. |
| `top_p` | 0.95 | Nucleus sampling. Keeps the top 95% probability mass. |
| `max_output_tokens` | 8,192 | Global default. Overridden by stage-specific values. |
| `stop_sequences` | `[]` | No stop sequences by default. |
| `response_format` | `None` | Set to `"json"` for structured output stages. |

### When to Adjust Temperature

**Lower the temperature (0.0 - 0.1) when:**

- You are getting inconsistent code output across runs.
- Generated code has syntax errors or hallucinated API calls.
- Structured JSON output is malformed.
- You want reproducible results.

**Raise the temperature (0.2 - 0.5) when:**

- Generated code is too repetitive or template-like.
- The pipeline is failing to produce creative solutions for novel architectures.
- You want to generate multiple candidates and pick the best one.

**General guidance:**

- Never go above 0.5 for code generation. Higher values introduce too many errors.
- For structured extraction (JSON), keep temperature at or below 0.15.
- Analysis can tolerate slightly higher temperature (0.1-0.2) since the output is prose rather than code.

### When to Adjust Token Limits

**Increase `max_code_tokens` when:**

- Generated files are being truncated (check for `finish_reason: "length"` in verbose output).
- You are generating very large files (complex model implementations, long training scripts).
- The paper describes a system with many classes in a single module.

**Decrease `max_code_tokens` when:**

- You want to reduce costs (output tokens are typically more expensive than input tokens).
- The models are generating excessively verbose code with too many comments or unused functions.

**Increase `max_analysis_tokens` when:**

- Paper analysis is missing sections or equations (the output was truncated).
- The paper is exceptionally long (50+ pages).

**Model-specific limits to be aware of:**

| Model | Max Output Limit |
|-------|-----------------|
| gemini-2.5-pro-preview-05-06 | 65,536 |
| gemini-2.0-flash | 8,192 |
| gemini-1.5-pro | 8,192 |
| gpt-4o | 16,384 |
| gpt-4-turbo | 4,096 |
| o3 | 100,000 |
| o1 | 100,000 |
| claude-sonnet-4-20250514 | 64,000 |
| claude-opus-4-20250514 | 32,000 |
| claude-3-5-sonnet-20241022 | 8,192 |
| Ollama models | 2,048 - 8,192 (varies) |

Setting `max_output_tokens` higher than the model's limit will not cause an error -- the model will simply stop at its maximum. However, setting it too low will truncate output and degrade quality.

### Modifying Parameters

Currently, temperature and token limits are configured through the `R2RConfig` dataclass. To change them, either:

1. **Modify `config.py` directly** for permanent changes:

```python
@dataclass
class R2RConfig:
    code_temperature: float = 0.1       # Changed from 0.15
    max_code_tokens: int = 32768        # Changed from 16384
```

2. **Create a custom config in your script** for programmatic usage:

```python
from config import R2RConfig

config = R2RConfig(
    code_temperature=0.1,
    analysis_temperature=0.05,
    max_code_tokens=32768,
    max_analysis_tokens=16384,
)
```

3. **Pass a custom `GenerationConfig`** when calling provider methods directly:

```python
from providers.base import GenerationConfig

config = GenerationConfig(
    temperature=0.1,
    max_output_tokens=32768,
    top_p=0.9,
)

result = provider.generate(prompt="...", config=config)
```
