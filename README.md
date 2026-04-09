# Research2Repo v2.0

**Multi-model agentic framework that converts ML research papers into production-ready GitHub repositories.**

Supports **Google Gemini**, **OpenAI GPT-4o/o3**, **Anthropic Claude**, and **Ollama** (local models). Uses long-context single-pass architecture — no RAG, no chunking, no lost context.

---

## Architecture

```
PDF Paper --> [Analyzer] --> [Equation Extractor] --> [Architect] --> [Coder] --> [Validator] --> Repository
                 |                    |                    |              |             |
            Long-Context         Vision/LaTeX         Structured     Rolling       Self-Review
            + Multimodal         Extraction           JSON Output    Context       + Auto-Fix
```

### 10-Stage Pipeline

| Stage | Module | What It Does |
|-------|--------|-------------|
| 1 | `download_pdf()` | Download with validation, size limits, content-type check |
| 2 | `PaperAnalyzer` | Long-context analysis + vision diagram extraction to Mermaid.js |
| 3 | `EquationExtractor` | Dedicated equation extraction (LaTeX + PyTorch pseudocode) |
| 4 | `SystemArchitect` | Repository structure design, dependency planning, file specs |
| 5 | `ConfigGenerator` | Structured YAML config from all paper hyperparameters |
| 6 | `CodeSynthesizer` | File-by-file code generation with rolling dependency context |
| 7 | `TestGenerator` | Auto-generated pytest suite (dimensions, equations, integration) |
| 8 | `CodeValidator` | Self-review: equation fidelity, dimensions, hyperparameter coverage |
| 9 | `fix_issues()` | Auto-fix critical validation failures |
| 10 | Save | Write all files + metadata to output directory |

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

### Basic (auto-detects provider)

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf"
```

### Choose a specific provider and model

```bash
# Gemini 2.5 Pro
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --provider gemini --model gemini-2.5-pro-preview-05-06

# OpenAI GPT-4o
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --provider openai --model gpt-4o

# Anthropic Claude Sonnet 4
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --provider anthropic --model claude-sonnet-4-20250514

# Local via Ollama
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --provider ollama --model deepseek-coder-v2:latest
```

### Mix providers (Gemini for analysis, Claude for coding)

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --provider gemini --vision-provider anthropic
```

### Fast run (skip validation and tests)

```bash
python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" \
  --skip-validation --skip-tests --skip-equations
```

### List available providers and models

```bash
python main.py --list-providers
```

### Cache management

```bash
# Re-runs use cached results automatically
python main.py --pdf_url "..." --no-cache    # Force fresh run
python main.py --clear-cache                  # Clear all cached data
```

---

## Project Structure

```
Research2Repo/
  main.py                          # 10-stage orchestrator (290 lines)
  config.py                        # Global configuration
  pyproject.toml                   # Package metadata + optional deps

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

  advanced/                        # Advanced capabilities
    __init__.py
    equation_extractor.py          # Dedicated equation extraction (LaTeX + PyTorch)
    config_generator.py            # YAML config from hyperparameters
    test_generator.py              # Auto pytest suite generation
    cache.py                       # Content-addressed pipeline cache

  prompts/                         # Externalized prompt templates
    analyzer.txt                   # Paper analysis prompt
    architect.txt                  # Repo design prompt
    coder.txt                      # Code generation prompt
    validator.txt                  # Validation prompt
    diagram_extractor.txt          # Vision diagram extraction prompt
    equation_extractor.txt         # Equation extraction prompt
    test_generator.txt             # Test generation prompt

  tests/                           # Project tests
    __init__.py

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

### 2. Multimodal Diagram Extraction

Architecture diagrams are extracted from PDF pages as images, sent to a vision-capable model, and converted to **Mermaid.js** diagrams. These feed into the Architect and Coder stages so the generated code matches the visual architecture.

### 3. Rolling Context Code Generation

Files are generated in dependency order (config -> utils -> model components -> training -> tests). Each file receives:
- Full paper analysis (equations, hyperparameters, architecture)
- Previously generated dependency files
- Architecture plan with file descriptions
- Mermaid diagrams

### 4. Self-Review Validation Loop

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

## Advanced Features

### Equation Extraction
Dedicated pipeline that extracts every equation from the paper with:
- LaTeX representation
- PyTorch pseudocode translation
- Variable documentation (names, shapes, types)
- Category classification (forward pass, loss, optimization)

### Config Generation
Automatically generates a structured `config.yaml` with:
- All hyperparameters organized by section (model, training, data, regularization)
- YAML comments referencing paper sections
- Type-appropriate values (int, float, string, list)

### Test Generation
Auto-generates a pytest test suite covering:
- Tensor dimension tests through forward pass
- Equation correctness with known inputs
- Config injection and default value verification
- Full integration tests (forward + backward pass)

### Pipeline Caching
Content-addressed cache (keyed on PDF hash) stores:
- Paper analysis results
- Architecture plans
- Generated files
- Validation reports

Re-runs skip cached stages automatically. Use `--no-cache` to force fresh generation.

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

## CLI Reference

```
python main.py [OPTIONS]

Required:
  --pdf_url URL              URL of the research paper PDF

Provider:
  --provider NAME            gemini | openai | anthropic | ollama
  --model NAME               Specific model name
  --vision-provider NAME     Separate provider for vision tasks
  --vision-model NAME        Specific vision model

Pipeline:
  --output_dir DIR           Output directory (default: ./generated_repo)
  --skip-validation          Skip validation pass
  --skip-tests               Skip test generation
  --skip-equations           Skip equation extraction
  --max-fix-iterations N     Max auto-fix attempts (default: 2)

Cache:
  --no-cache                 Disable caching
  --cache-dir DIR            Custom cache directory
  --clear-cache              Clear all cached data

Misc:
  --list-providers           Show available providers and models
  --verbose, -v              Verbose output
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
