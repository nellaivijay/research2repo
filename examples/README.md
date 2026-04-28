# Research2Repo Example Configurations

This directory contains example YAML configurations for different use cases.

## Directory Structure

```
examples/
├── processors/       # Processor configurations
│   ├── grobid.yaml
│   ├── pdfminer.yaml
│   └── pymupdf.yaml
├── providers/        # Provider configurations
│   ├── openai.yaml
│   ├── anthropic.yaml
│   ├── gemini.yaml
│   └── ollama.yaml
└── generators/       # Generator configurations
    ├── simple.yaml
    ├── iterative.yaml
    └── multi_agent.yaml
```

## Usage

### Using Example Configurations

```bash
research2repo process paper.pdf --config examples/processors/grobid.yaml
```

### Combining Configurations

You can combine configurations from different directories:

```bash
# Use GROBID processor with OpenAI provider
research2repo process paper.pdf \
  --processor grobid \
  --provider openai \
  --generator iterative
```

### Customizing Examples

Copy an example configuration and modify it:

```bash
cp examples/processors/grobid.yaml my_config.yaml
# Edit my_config.yaml
research2repo process paper.pdf --config my_config.yaml
```

## Processor Examples

### GROBID Processor

```yaml
processor:
  name: grobid
  params:
    url: http://127.0.0.1:8070/api/processFulltextDocument
    timeout: 60
    cache_dir: ./cache/grobid
```

**Requirements**: GROBID service running at `http://127.0.0.1:8070`

**Start GROBID**:
```bash
docker run --rm -p 8070:8070 lfoppiano/grobid:0.7.2
```

### PDFMiner Processor

```yaml
processor:
  name: pdfminer
  params:
    cache_dir: ./cache/pdfminer
```

**Requirements**: None (pure Python)

### PyMuPDF Processor

```yaml
processor:
  name: pymupdf
  params:
    cache_dir: ./cache/pymupdf
```

**Requirements**: `pip install pymupdf`

## Provider Examples

### OpenAI Provider

```yaml
provider:
  name: openai
  params:
    api_key: null  # Set via OPENAI_API_KEY environment variable
    model: gpt-4
    temperature: 0.7
    max_tokens: 2000
    timeout: 120
```

**Requirements**: OpenAI API key

**Set API key**:
```bash
export OPENAI_API_KEY="your-api-key"
```

### Anthropic Provider

```yaml
provider:
  name: anthropic
  params:
    api_key: null  # Set via ANTHROPIC_API_KEY environment variable
    model: claude-3-opus-20240229
    temperature: 0.7
    max_tokens: 2000
    timeout: 120
```

**Requirements**: Anthropic API key

**Set API key**:
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

### Gemini Provider

```yaml
provider:
  name: gemini
  params:
    api_key: null  # Set via GEMINI_API_KEY environment variable
    model: gemini-pro
    temperature: 0.7
    max_tokens: 2000
    timeout: 120
```

**Requirements**: Gemini API key

**Set API key**:
```bash
export GEMINI_API_KEY="your-api-key"
```

### Ollama Provider

```yaml
provider:
  name: ollama
  params:
    host: http://127.0.0.1:11434
    model: llama2
    temperature: 0.7
    timeout: 120
```

**Requirements**: Ollama service running

**Start Ollama**:
```bash
ollama serve
```

**Pull model**:
```bash
ollama pull llama2
```

## Generator Examples

### Simple Generator

```yaml
generator:
  name: simple
  params:
    max_iterations: 3
    temperature: 0.7
```

**Description**: Single-pass code generation with basic iteration

### Iterative Generator

```yaml
generator:
  name: iterative
  params:
    max_iterations: 5
    temperature: 0.7
    refinement_steps: 2
```

**Description**: Multi-pass generation with refinement loops

### Multi-Agent Generator

```yaml
generator:
  name: multi_agent
  params:
    max_iterations: 5
    temperature: 0.7
    num_agents: 3
```

**Description**: Multi-agent collaborative code generation

## Complete Examples

### Minimal Example

```yaml
processor:
  name: pdfminer

provider:
  name: openai

generator:
  name: simple

output:
  dir: ./output
```

### Full Example

```yaml
processor:
  name: grobid
  params:
    url: http://127.0.0.1:8070/api/processFulltextDocument
    cache_dir: ./cache/grobid

provider:
  name: openai
  params:
    model: gpt-4
    temperature: 0.7
    max_tokens: 2000

generator:
  name: iterative
  params:
    max_iterations: 5
    refinement_steps: 2

output:
  dir: ./output
  format: repository
  include_readme: true
  include_requirements: true
  include_tests: true

evaluation:
  enabled: true
  metrics:
    - syntax
    - semantic
```

## Configuration Reference

### Processor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| name | string | required | Processor name |
| url | string | - | API URL (for GROBID) |
| timeout | int | 60 | Request timeout (seconds) |
| cache_dir | string | ./cache | Cache directory |

### Provider Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| name | string | required | Provider name |
| api_key | string | null | API key (or use env var) |
| model | string | varies | Model identifier |
| temperature | float | 0.7 | Sampling temperature (0.0-1.0) |
| max_tokens | int | 2000 | Maximum tokens to generate |
| timeout | int | 120 | Request timeout (seconds) |

### Generator Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| name | string | required | Generator name |
| max_iterations | int | 3 | Maximum generation iterations |
| temperature | float | 0.7 | Sampling temperature |
| refinement_steps | int | 0 | Number of refinement steps |
| num_agents | int | 1 | Number of agents (for multi-agent) |

### Output Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| dir | string | ./output | Output directory |
| format | string | repository | Output format |
| include_readme | bool | true | Include README.md |
| include_requirements | bool | true | Include requirements.txt |
| include_tests | bool | false | Include test files |

## Tips

1. **Start Simple**: Begin with the minimal example, then add complexity
2. **Use Caching**: Enable caching for faster repeated processing
3. **Choose Right Provider**: Select provider based on cost and quality needs
4. **Adjust Temperature**: Lower temperature for more deterministic output
5. **Monitor Costs**: Be aware of API costs for paid providers

## Troubleshooting

### Configuration Not Found

Ensure the configuration file path is correct:
```bash
research2repo process paper.pdf --config examples/processors/grobid.yaml
```

### API Key Not Found

Set the appropriate environment variable:
```bash
export OPENAI_API_KEY="your-api-key"
```

### Service Not Available

Ensure required services are running:
- GROBID: `docker run --rm -p 8070:8070 lfoppiano/grobid:0.7.2`
- Ollama: `ollama serve`

### Permission Errors

Ensure output directory is writable:
```bash
mkdir -p ./output
chmod 755 ./output
```

## Next Steps

- See [how_to_use.md](../skills/how_to_use.md) for usage guide
- See [how_to_add_processor.md](../skills/how_to_add_processor.md) to add custom processors
- See [how_to_add_provider.md](../skills/how_to_add_provider.md) to add custom providers
