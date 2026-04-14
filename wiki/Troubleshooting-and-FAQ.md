# Troubleshooting and FAQ

This document covers common errors, performance tuning, quality optimization, and frequently asked questions about Research2Repo v3.0.

---

## Table of Contents

- [1. Common Errors](#1-common-errors)
  - [Provider Errors](#provider-errors)
  - [PDF Errors](#pdf-errors)
  - [Code Generation Errors](#code-generation-errors)
  - [Execution Errors](#execution-errors)
  - [Cache Errors](#cache-errors)
- [2. Performance Tuning](#2-performance-tuning)
- [3. Quality Tuning](#3-quality-tuning)
- [4. FAQ](#4-faq)
- [5. Getting Help](#5-getting-help)

---

## 1. Common Errors

### Provider Errors

#### "No model providers available"

**Full message:**
```
RuntimeError: No model providers available. Set one of:
GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, or start Ollama locally.
```

**Cause:** No LLM provider API key is set in the environment, and Ollama is not running.

**Solution:** Set at least one API key environment variable:

```bash
# Option 1: Gemini (recommended, cheapest for long papers)
export GEMINI_API_KEY="your-api-key-here"

# Option 2: OpenAI
export OPENAI_API_KEY="sk-..."

# Option 3: Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Option 4: Ollama (no key needed)
ollama serve
# Then in another terminal:
ollama pull codellama:34b
```

Verify your setup with:

```bash
python main.py --list-providers
```

---

#### "GEMINI_API_KEY not set" (or OPENAI_API_KEY, ANTHROPIC_API_KEY)

**Cause:** You specified a provider explicitly (e.g., `--provider gemini`) but the corresponding API key is not set.

**Solution:**

```bash
# Set the key
export GEMINI_API_KEY="your-api-key-here"

# Or pass it programmatically
from providers import get_provider
provider = get_provider(provider_name="gemini", api_key="your-api-key-here")
```

**Tip:** On macOS/Linux, add the export to your `~/.bashrc` or `~/.zshrc` to persist it across sessions.

---

#### "Rate limit exceeded"

**Cause:** You have exceeded the API rate limit for your provider. This is common with free-tier Gemini accounts or OpenAI accounts with low rate limits.

**Solutions:**

1. **Wait and retry.** Most rate limits reset within 1-60 seconds.
2. **Switch to a different provider:**
   ```bash
   python main.py --pdf_url "..." --provider openai  # If Gemini is rate-limited
   ```
3. **Use caching** to avoid re-running stages. Caching is enabled by default; previous successful stages will not be re-executed.
4. **Upgrade your API plan** for higher rate limits.

### Automatic Retry & Rate Limit Handling

Research2Repo automatically retries failed API calls with exponential backoff:

- **Transient errors** (`ConnectionError`, `TimeoutError`, `OSError`): retried automatically
- **Rate limits** (HTTP 429 / quota errors): detected and retried after a delay
- **Default behavior**: 2 retries with exponential backoff (1s, 2s, 4s, ...)
- **Non-transient errors**: raised immediately without retry

The retry decorator (`retry_on_error`) is defined in `providers/base.py` and can be applied to any provider method. No user configuration is needed — retries happen transparently.

---

#### "Context too long" / "Token limit exceeded"

**Cause:** The paper text plus the accumulated context exceeds the model's maximum context window. This is more common with OpenAI (128K context) and especially Ollama (varies by model, often 4K-32K).

**Solutions:**

1. **Use Gemini.** Gemini 2.5 Pro supports up to 2 million tokens, making it ideal for long papers:
   ```bash
   python main.py --pdf_url "..." --provider gemini
   ```
2. **Switch to a larger context model:**
   ```bash
   python main.py --pdf_url "..." --provider openai --model gpt-4o  # 128K context
   python main.py --pdf_url "..." --provider anthropic --model claude-3.5-sonnet  # 200K context
   ```
3. **Use a shorter paper** or pre-process to extract only the relevant sections.

---

#### "Model not found" / "Unknown model"

**Cause:** The specified model name is misspelled or not available for the chosen provider.

**Solutions:**

1. Check available models:
   ```bash
   python main.py --list-providers
   ```
2. Verify the exact model name. Common names:
   - Gemini: `gemini-2.5-pro`, `gemini-2.0-flash`
   - OpenAI: `gpt-4o`, `gpt-4-turbo`, `o3-mini`
   - Anthropic: `claude-3.5-sonnet`, `claude-3-opus`
   - Ollama: `codellama:34b`, `deepseek-coder:33b`, `llama3:70b`
3. For Ollama, make sure you have pulled the model:
   ```bash
   ollama pull codellama:34b
   ```

---

#### "Unknown provider '<name>'"

**Full message:**
```
ValueError: Unknown provider 'xyz'. Available: ['gemini', 'openai', 'anthropic', 'ollama']
```

**Cause:** An invalid provider name was specified.

**Solution:** Use one of the four supported provider names: `gemini`, `openai`, `anthropic`, `ollama`. Provider names are case-sensitive and must be lowercase.

---

### PDF Errors

#### "PDF exceeds 100MB limit"

**Cause:** The downloaded PDF file exceeds the configured maximum size. This is a safety check to prevent downloading extremely large files.

**Solutions:**

1. **Use a smaller PDF.** Most research papers are under 10 MB.
2. **Increase the size limit:**
   ```bash
   python main.py --pdf_url "..." --max-size 200  # Set to 200 MB
   ```
3. **Download the PDF manually** and use a local path:
   ```bash
   python main.py --pdf_url "/path/to/local/paper.pdf" --output_dir ./output
   ```

---

#### "Content-Type is not PDF"

**Cause:** The URL does not point directly to a PDF file. This often happens with:
- ArXiv abstract pages (use `/pdf/` instead of `/abs/`)
- Conference landing pages instead of direct PDF links
- URLs behind authentication walls

**Solutions:**

1. **Use the direct PDF URL:**
   ```bash
   # Wrong (abstract page):
   python main.py --pdf_url "https://arxiv.org/abs/1706.03762"

   # Correct (direct PDF):
   python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf"
   ```
2. **Download manually** if the URL requires authentication or JavaScript rendering:
   ```bash
   wget -O paper.pdf "https://example.com/paper"
   python main.py --pdf_url "paper.pdf"
   ```

---

#### "Timeout downloading PDF"

**Cause:** The PDF server did not respond within the timeout period (default: 120 seconds).

**Solutions:**

1. **Increase the timeout:**
   ```bash
   python main.py --pdf_url "..." --timeout 300  # 5-minute timeout
   ```
2. **Check your network connection.** Try opening the URL in a browser.
3. **Download manually** and use a local file path.

---

### Code Generation Errors

#### "Validation score too low"

**Cause:** The generated code scored below 80/100 on the fidelity validation, meaning significant discrepancies exist between the code and the paper.

**Solutions:**

1. **Enable self-refinement** (biggest quality improvement):
   ```bash
   python main.py --pdf_url "..." --mode agent --refine
   ```
2. **Use agent mode** (better than classic mode):
   ```bash
   python main.py --pdf_url "..." --mode agent
   ```
3. **Use a larger/better model:**
   ```bash
   python main.py --pdf_url "..." --provider openai --model gpt-4o
   ```
4. **Increase fix iterations:**
   ```bash
   python main.py --pdf_url "..." --max-fix-iterations 5
   ```

---

#### "Critical issues remain after fix"

**Cause:** The auto-fix loop reached its maximum iterations but could not resolve all critical validation issues.

**Solutions:**

1. **Increase the maximum fix iterations:**
   ```bash
   python main.py --pdf_url "..." --max-fix-iterations 5
   ```
2. **Enable the execution sandbox** for more thorough debugging:
   ```bash
   python main.py --pdf_url "..." --mode agent --execute --max-debug-iterations 5
   ```
3. **Try a different provider.** Different models have different strengths:
   - Anthropic Claude excels at code generation.
   - Gemini handles long papers better.
   - GPT-4o is strong at structured output.
4. **Manually review** the validation report for insights into what is failing.

---

#### "Missing imports in generated code"

**Cause:** The generated code references modules or functions that are not properly imported. This is more common with smaller models (especially Ollama local models with limited context windows) that lose track of cross-file dependencies.

**Solutions:**

1. **Use a larger context model.** Models with larger context windows maintain better cross-file consistency:
   ```bash
   python main.py --pdf_url "..." --provider gemini  # 2M token context
   ```
2. **Enable agent mode** which includes per-file analysis that explicitly tracks imports:
   ```bash
   python main.py --pdf_url "..." --mode agent
   ```
3. **Enable execution + auto-debug** which automatically fixes import errors:
   ```bash
   python main.py --pdf_url "..." --mode agent --execute
   ```

---

### Execution Errors

#### "Docker not found"

**Cause:** The execution sandbox is configured to use Docker, but Docker is not installed or not on the PATH.

**Solutions:**

1. **Install Docker:**
   - [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS, Windows)
   - `sudo apt install docker.io` (Ubuntu/Debian)
   - `sudo yum install docker` (RHEL/CentOS)
2. **The sandbox will automatically fall back to local execution** if Docker is not available. No action needed unless you specifically require Docker isolation.
3. **Explicitly disable Docker** to suppress the warning:
   ```python
   from advanced.executor import ExecutionSandbox
   sandbox = ExecutionSandbox(use_docker=False)
   ```

---

#### "CudaOOMError" / "CUDA out of memory"

**Cause:** The generated training code is trying to use more GPU memory than is available. Common with large models, large batch sizes, or when multiple processes are using the GPU.

**Solutions:**

1. **Reduce batch size** in the generated `config.yaml`:
   ```yaml
   training:
     batch_size: 4  # Reduce from default (e.g., 32)
   ```
2. **Use CPU mode** by modifying the generated training script to use `device = "cpu"`.
3. **Use gradient accumulation** if the paper requires large effective batch sizes.
4. **Free GPU memory** by stopping other GPU processes: `nvidia-smi` to check usage.

---

#### "ModuleNotFoundError" during execution

**Cause:** The generated code imports a Python package that is not installed in the execution environment.

**Solutions:**

1. **The auto-debugger should fix this automatically.** Increase iterations if needed:
   ```bash
   python main.py --pdf_url "..." --mode agent --execute --max-debug-iterations 5
   ```
2. **Install the missing package** in the generated repo's `requirements.txt`:
   ```bash
   cd output/
   pip install -r requirements.txt
   ```
3. **Check that the Dockerfile includes all requirements** if running in Docker mode.

---

#### "TimeoutError" during execution

**Cause:** The generated code did not complete within the configured timeout (default: 300 seconds). This is expected for training scripts that are meant to run for hours.

**Solutions:**

1. **Increase the timeout** for legitimate long-running scripts:
   ```python
   sandbox = ExecutionSandbox(timeout=3600)  # 1 hour
   ```
2. **Modify the generated code** to run a quick smoke test (e.g., 1 epoch on a tiny subset) instead of full training.
3. **Note:** The execution sandbox is primarily for verifying that the code runs without errors, not for full training. A timeout with a clean partial execution can be considered a success.

---

### Cache Errors

#### "Stale cache" / unexpected results from cached data

**Cause:** The cache contains results from a previous run that may be outdated (e.g., you changed the provider, model, or Research2Repo version).

**Solutions:**

1. **Force a fresh run:**
   ```bash
   python main.py --pdf_url "..." --no-cache
   ```
2. **Clear the cache for a specific paper:**
   ```python
   from advanced.cache import PipelineCache
   cache = PipelineCache()
   cache.clear(pdf_path="paper.pdf")
   ```

---

#### "Cache corruption" / unpickling errors

**Cause:** The cached pickle files are corrupted, possibly from a crashed run or a Python version change.

**Solutions:**

1. **Clear all caches:**
   ```bash
   python main.py --clear-cache
   ```
2. **Or manually delete the cache directory:**
   ```bash
   rm -rf .r2r_cache
   ```
3. **Programmatically:**
   ```python
   from advanced.cache import PipelineCache
   cache = PipelineCache()
   cache.clear()  # Clears all cached data
   ```

---

## 2. Performance Tuning

### Caching (Enabled by Default)

Caching is the single most effective performance optimization. The `PipelineCache` stores results from expensive LLM calls so they are not repeated on re-runs.

- **Paper analysis** (1-3 LLM calls): Cached after first run.
- **Architecture plan** (1-4 LLM calls): Cached after first run.
- **Generated files** (10-30+ LLM calls): Cached after first run.

To disable caching for a fresh run:
```bash
python main.py --pdf_url "..." --no-cache
```

### Classic vs. Agent Mode

| Aspect | Classic Mode | Agent Mode |
|---|---|---|
| LLM calls | ~15-25 | ~30-60 |
| Wall-clock time | ~2-5 min | ~5-15 min |
| Quality | Good | Better |
| Features | Core pipeline only | Full pipeline with planning, file analysis, tests, DevOps |

**Recommendation:** Use classic mode for quick iterations and agent mode for production-quality output.

### Self-Refinement Cost

The `--refine` flag adds verify/refine loops to planning and file analysis stages:

- Each refinement iteration adds approximately 2 extra LLM calls per artefact.
- With `max_refine_iterations=2`, this can double the LLM calls for planning and analysis.
- Use refinement selectively when quality matters more than speed.

### Provider Selection for Performance

| Provider | Speed | Cost | Quality | Best For |
|---|---|---|---|---|
| Gemini 2.5 Pro | Fast | Cheapest ($0.05-0.50) | High | Long papers, budget-conscious |
| GPT-4o | Fast | Moderate ($0.50-5.00) | High | Structured output, code quality |
| Claude 3.5 Sonnet | Moderate | Higher ($1.00-10.00) | Highest code quality | Best possible code output |
| Ollama (local) | Slowest | Free | Lower (model-dependent) | Offline use, privacy |

### Reducing LLM Calls

To minimize the number of LLM calls (and cost):

1. **Use classic mode** instead of agent mode.
2. **Disable optional stages:**
   ```bash
   python main.py --pdf_url "..." --skip-tests --skip-validation
   ```
3. **Use caching** (enabled by default).
4. **Avoid refinement** unless quality is critical.
5. **Pre-compute analysis** and pass it to later runs:
   ```python
   # Run 1: analyze only
   analysis = analyzer.analyze(document, diagrams)
   cache.save_analysis(pdf_path, analysis)

   # Run 2: skip analysis, go straight to planning
   analysis = cache.load_analysis(pdf_path)
   plan = architect.design_system(analysis)
   ```

---

## 3. Quality Tuning

### Mode Selection

**Agent mode consistently produces higher quality output than classic mode.** The key improvements in agent mode are:

1. **Decomposed planning** (4-step vs. monolithic): Produces more thorough architecture designs.
2. **Per-file analysis**: Generates detailed specifications before code, improving cross-file consistency. Per the PaperCoder ablation study, this alone contributes approximately +0.23 to evaluation scores.
3. **Self-refinement loops**: Verify/refine cycles catch and fix issues before code generation.

```bash
# Highest quality configuration
python main.py --pdf_url "..." \
    --mode agent \
    --refine \
    --execute \
    --max-fix-iterations 5 \
    --max-debug-iterations 5 \
    --max-refine-iterations 3
```

### Model Selection for Quality

Larger models produce better results. Approximate quality ranking:

1. Claude 3.5 Sonnet / Claude 3 Opus (best code generation)
2. GPT-4o (strong structured output and code)
3. Gemini 2.5 Pro (best cost/quality ratio for long papers)
4. GPT-4 Turbo (slightly lower than GPT-4o)
5. Ollama local models (quality varies significantly by model size)

### Feature Impact on Quality

| Feature | Quality Impact | Cost Impact | Recommendation |
|---|---|---|---|
| Agent mode (vs. classic) | High | ~2x LLM calls | Always use for production |
| `--refine` | Highest | ~2x calls per refined stage | Use when quality matters |
| Per-file analysis | High (+0.23) | +1 call per file | Always on in agent mode |
| Execution + auto-debug | Moderate | +2-10 calls if errors found | Use for verified output |
| Validation auto-fix | Moderate | +2-4 calls per fix iteration | Always enabled |
| DevOps generation | N/A (different output) | +5 calls | Enable for production repos |

### Paper Characteristics That Affect Quality

Research2Repo works best with papers that have:

- **Clear architecture descriptions** with explicit layer configurations.
- **Well-defined equations** with standard notation.
- **Explicit hyperparameter tables** (learning rate, batch size, etc.).
- **Standard ML frameworks** (PyTorch-based architectures).
- **Reproducibility sections** with training details.

Quality may be lower for papers that:

- Use heavy mathematical notation without implementation details.
- Describe only theoretical contributions without algorithms.
- Rely on proprietary or non-standard frameworks.
- Lack hyperparameter specifications.

---

## 4. FAQ

### General

**Q: What papers work best with Research2Repo?**

A: ML papers with clear architecture descriptions, explicit equations, and well-defined training procedures produce the best results. Transformer papers, GAN papers, and standard supervised learning papers (image classification, object detection, NLP tasks) work particularly well. Papers with clear figures showing model architecture are a bonus, as the vision-based diagram extraction provides additional context.

---

**Q: Can it handle non-ML papers?**

A: Research2Repo is designed and optimized for ML papers, but it can generate code for any paper that describes algorithms and implementations. Results may vary for purely theoretical papers, mathematical proofs, or papers in unrelated domains (e.g., biology, physics). The pipeline will still attempt to extract structure and generate code, but the output quality depends on how explicitly the paper describes implementable algorithms.

---

**Q: Does it support non-Python languages?**

A: Currently, Research2Repo generates Python code only. The prompts, architecture patterns, and generated DevOps files (Dockerfile, Makefile, setup.py) are all Python-focused. The generated code follows PyTorch conventions. Support for other frameworks (TensorFlow, JAX) or languages is not currently available.

---

**Q: Can I run it offline?**

A: Yes, with Ollama. Install Ollama locally, pull a model (e.g., `ollama pull codellama:34b`), and run Research2Repo with `--provider ollama`. No internet connection is needed after the initial model download and PDF acquisition. Note that local models typically produce lower quality output compared to cloud providers, especially for complex papers.

---

### Cost and Pricing

**Q: How much does it cost per paper?**

A: Costs vary by provider, paper length, and enabled features. Approximate ranges for a full agent-mode run:

| Provider | Model | Approximate Cost |
|---|---|---|
| Gemini | gemini-2.5-pro | $0.05-$0.50 (free tier available) |
| OpenAI | gpt-4o | $0.50-$5.00 |
| Anthropic | claude-3.5-sonnet | $1.00-$10.00 |
| Ollama | Any local model | Free (hardware costs only) |

Classic mode uses roughly half the LLM calls of agent mode, so costs are proportionally lower. Caching prevents re-spending on repeated runs of the same paper.

---

**Q: Is there a free option?**

A: Yes, two options:

1. **Gemini free tier**: Google offers a free tier for the Gemini API that is sufficient for processing several papers per day.
2. **Ollama**: Completely free (runs locally on your machine). Quality depends on the model and your hardware.

---

### Customization

**Q: Can I use my own prompts?**

A: Yes. Research2Repo loads prompts from the `prompts/` directory at runtime. Each pipeline stage has a corresponding prompt file:

| File | Stage |
|---|---|
| `prompts/analyzer.txt` | Paper analysis |
| `prompts/diagram_extractor.txt` | Diagram-to-Mermaid extraction |
| `prompts/architect.txt` | Architecture design |
| `prompts/overall_plan.txt` | Overall plan (decomposed planner step 1) |
| `prompts/architecture_design.txt` | Architecture design (decomposed planner step 2) |
| `prompts/logic_design.txt` | Logic design (decomposed planner step 3) |
| `prompts/file_analysis.txt` | Per-file analysis |
| `prompts/coder.txt` | Code generation |
| `prompts/validator.txt` | Code validation |
| `prompts/self_refine_verify.txt` | Self-refine verification step |
| `prompts/self_refine_refine.txt` | Self-refine refinement step |
| `prompts/auto_debug.txt` | Auto-debugger error analysis |
| `prompts/evaluator.txt` | Reference-based evaluation |

Edit these files to customize behavior. Each file supports `{{placeholder}}` substitution for dynamic values. If a prompt file does not exist, a hardcoded default is used.

---

**Q: Can I add a custom LLM provider?**

A: Yes. Implement the `BaseProvider` interface and register it:

```python
from providers.registry import ProviderRegistry

# Register your custom provider
ProviderRegistry.register(
    name="my_provider",
    module_path="my_package.my_module",
    class_name="MyCustomProvider",
    env_key="MY_API_KEY",  # Optional: env var for auto-detection
)

# Use it
from providers import get_provider
provider = get_provider(provider_name="my_provider")
```

Your provider class must implement `generate()`, `generate_structured()`, `available_models()`, and `default_model()`. See `providers/base.py` for the full interface.

---

### Code Quality

**Q: How do I improve generated code quality?**

A: In order of impact:

1. **Use agent mode with `--refine`**: This is the single biggest quality improvement.
2. **Use a larger model**: GPT-4o or Claude 3.5 Sonnet produce better code than smaller models.
3. **Provide better papers**: Papers with clear descriptions, equations, and architecture diagrams produce better code.
4. **Enable execution + auto-debug**: `--mode agent --execute` catches and fixes runtime errors.
5. **Increase fix iterations**: `--max-fix-iterations 5 --max-debug-iterations 5`.
6. **Customize prompts**: Edit files in `prompts/` for domain-specific guidance.

---

**Q: What if the generated code does not run?**

A: Use the execution sandbox with auto-debugging:

```bash
python main.py --pdf_url "..." --mode agent --execute --max-debug-iterations 5
```

This will:
1. Write the generated code to disk.
2. Attempt to execute the training entrypoint.
3. If execution fails, analyze the error with the LLM.
4. Generate targeted fixes.
5. Re-execute and repeat up to `max-debug-iterations` times.

The auto-debugger handles common errors like missing imports, incorrect tensor shapes, wrong function signatures, and configuration issues.

---

**Q: The generated code has syntax errors. What should I do?**

A: Syntax errors are rare with large models but can happen with Ollama/smaller models. Solutions:

1. **Use a larger model**: Gemini, GPT-4o, or Claude rarely produce syntax errors.
2. **The validation auto-fix loop should catch these**: Syntax errors are classified as critical issues and the auto-fixer will attempt to resolve them.
3. **Enable execution**: The auto-debugger specifically handles `SyntaxError` and `IndentationError`.

---

### Comparison

**Q: How is this different from PaperCoder?**

A: Research2Repo v3.0 is inspired by PaperCoder but extends it significantly:

| Feature | PaperCoder | Research2Repo v3.0 |
|---|---|---|
| LLM Providers | GPT-4o only | 4 providers (Gemini, OpenAI, Anthropic, Ollama) |
| Provider auto-detection | No | Yes (auto-selects best available) |
| Decomposed planning | Yes | Yes (4-step pipeline) |
| Per-file analysis | Yes | Yes |
| Self-refinement | Yes | Yes (configurable iterations) |
| Vision/diagram extraction | No | Yes (Mermaid.js conversion) |
| Execution sandbox | No | Yes (Docker + local modes) |
| Auto-debugging | No | Yes (LLM-assisted fix-and-retry) |
| DevOps generation | No | Yes (Dockerfile, CI, Makefile, setup.py) |
| Caching | No | Yes (content-addressed file cache) |
| Reference evaluation | No | Yes (with-reference and reference-free) |
| Cost estimation | No | Yes (per-provider cost tracking) |
| Offline mode | No | Yes (via Ollama) |
| Paper parsing backends | Not specified | 4 backends (doc2json, GROBID, PyMuPDF, PyPDF2) |

PaperCoder originated the key ideas of decomposed planning, per-file analysis, and self-refinement, which Research2Repo v3.0 implements alongside the additional capabilities listed above.

---

### Miscellaneous

**Q: Can I process multiple papers in batch?**

A: Yes. Use a simple loop:

```bash
for url in \
    "https://arxiv.org/pdf/1706.03762.pdf" \
    "https://arxiv.org/pdf/2010.11929.pdf" \
    "https://arxiv.org/pdf/1406.2661.pdf"; do
    name=$(basename "$url" .pdf)
    python main.py --pdf_url "$url" --mode agent --output_dir "./output/$name"
done
```

Or programmatically with the Python API:

```python
from agents.orchestrator import AgentOrchestrator
from providers import get_provider

orchestrator = AgentOrchestrator(provider=get_provider())
for pdf in ["paper1.pdf", "paper2.pdf"]:
    orchestrator.run(pdf_path=pdf, output_dir=f"./output/{pdf.stem}")
```

---

**Q: What happens if my internet connection drops mid-run?**

A: The pipeline will fail at the next LLM API call. However:
- Any completed stages are cached (if caching is enabled) and will not need to be re-run.
- Simply re-run the same command after reconnecting; the pipeline will resume from the last uncached stage.
- For fully offline operation, use Ollama.

---

**Q: Can I pre-download the PDF and use a local file?**

A: Yes. Pass a local file path instead of a URL:

```bash
python main.py --pdf_url "/path/to/paper.pdf" --output_dir ./output
```

Despite the `--pdf_url` argument name, local file paths are supported.

---

**Q: How do I evaluate the quality of generated code against a reference implementation?**

A: Use the evaluation feature with a reference directory:

```bash
python main.py --pdf_url "..." \
    --mode agent \
    --evaluate \
    --reference-dir "/path/to/reference/repo"
```

Or programmatically:

```python
from advanced.evaluator import ReferenceEvaluator

evaluator = ReferenceEvaluator(provider=provider, num_samples=3)
score = evaluator.evaluate_with_reference(
    generated_files=files,
    reference_dir="/path/to/reference/repo",
    paper_text=analysis.full_text,
)
print(f"Overall score: {score.overall_score}/5")
print(f"Coverage: {score.coverage}%")
print(f"Missing: {score.missing_components}")
```

The evaluator scores on a 1-5 scale across dimensions: method, training, data, evaluation, utils, and reproducibility.

---

**Q: What is the `.r2r_metadata.json` file in my output?**

A: This file is automatically generated by the agent orchestrator and contains full metadata about the pipeline run:

- Provider and model used
- Timestamp and total elapsed time
- Per-stage timing breakdown
- Configuration settings
- Paper title and file count

It serves as an audit trail and can be used for monitoring and quality tracking across runs.

---

**Q: How do I configure the generated repository's hyperparameters?**

A: The generated repository includes a `config.yaml` file (or similar) containing all hyperparameters extracted from the paper. Edit this file to adjust values:

```yaml
model:
  d_model: 512
  num_heads: 8
  num_layers: 6
  dropout: 0.1

training:
  learning_rate: 0.0001
  batch_size: 32
  num_epochs: 100
  warmup_steps: 4000
```

The generated code reads from this config file rather than hardcoding values, so changes take effect without modifying any Python source.

---

## 5. Getting Help

### Debugging Steps

If you encounter an issue not covered above:

1. **Enable verbose output** to see detailed progress:
   ```bash
   python main.py --pdf_url "..." --verbose
   ```

2. **Check provider availability:**
   ```bash
   python main.py --list-providers
   ```

3. **Try a fresh run without cache:**
   ```bash
   python main.py --pdf_url "..." --no-cache
   ```

4. **Test with a known-good paper** to rule out paper-specific issues:
   ```bash
   python main.py --pdf_url "https://arxiv.org/pdf/1706.03762.pdf" --output_dir ./test
   ```

5. **Check the validation report** for specific issues:
   ```python
   report = result["validation_report"]
   for issue in report.issues:
       print(f"[{issue.severity}] {issue.file_path}: {issue.description}")
       print(f"  Suggestion: {issue.suggestion}")
   ```

### Reporting Issues

If you find a bug or have a feature request:

1. **GitHub Issues**: Open an issue at [github.com/nellaivijay/Research2Repo/issues](https://github.com/nellaivijay/Research2Repo/issues).
2. **Include:**
   - The full error message or traceback.
   - The command you ran (redact API keys).
   - The paper URL (if not proprietary).
   - Your Python version (`python --version`).
   - Your provider and model.
   - The `--verbose` output if available.

### Resources

- **GitHub Repository**: [github.com/nellaivijay/Research2Repo](https://github.com/nellaivijay/Research2Repo)
- **Wiki**: See the other wiki pages for architecture overview, usage guide, and API reference.
- **PaperCoder Paper**: The research paper describing the decomposed planning and self-refinement methodology that Research2Repo builds upon.
