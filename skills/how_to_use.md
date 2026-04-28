# How to Use Research2Repo

This guide covers the basic usage of Research2Repo for converting research papers to reproducible code repositories.

## Installation

### Basic Installation

```bash
pip install research2repo
```

### Installation with Optional Dependencies

```bash
# With all LLM providers
pip install research2repo[openai,anthropic,gemini]

# With web interface
pip install research2repo[web]

# With development tools
pip install research2repo[dev]

# With everything
pip install research2repo[all]
```

### Development Installation

```bash
git clone https://github.com/your-org/Research2Repo.git
cd Research2Repo
pip install -e ".[dev]"
```

## Quick Start

### Command Line Interface

Research2Repo provides a unified CLI with multiple subcommands:

```bash
# Check version
research2repo version
# or
r2r version

# Process a paper
research2repo process paper.pdf --output ./output

# Start web interface
research2repo web --port 7860

# Evaluate generated code
research2repo evaluate ./output
```

### Python API

```python
from architecture.pipeline.paper_parser import PaperParser
from architecture.agents.code_generator import CodeGenerator

# Parse paper
parser = PaperParser()
paper_content = parser.parse("paper.pdf")

# Generate code
generator = CodeGenerator(provider="openai")
code = generator.generate(paper_content)
```

## Configuration

### Environment Variables

Set your LLM provider API keys as environment variables:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export GEMINI_API_KEY="your-gemini-api-key"
```

### Component Configuration

Edit `config/components.yaml` to customize component behavior:

```yaml
providers:
  openai:
    name: openai
    params:
      model: gpt-4
      temperature: 0.7
      max_tokens: 2000
```

### Pipeline Configuration

Edit `config/pipeline_configs.yaml` to customize pipeline behavior:

```yaml
pipeline:
  stages:
    - paper_parsing
    - code_generation
    - evaluation
  output_dir: ./output
  cache_enabled: true
```

## Processing Papers

### Using CLI

```bash
# Basic processing
research2repo process paper.pdf

# With custom output directory
research2repo process paper.pdf --output ./my_output

# With specific provider
research2repo process paper.pdf --provider anthropic

# With custom processor
research2repo process paper.pdf --processor grobid
```

### Using Python API

```python
from architecture.pipeline.paper_parser import PaperParser
from architecture.agents.code_generator import CodeGenerator
from architecture.agents.evaluator import Evaluator

# Initialize components
parser = PaperParser()
generator = CodeGenerator(provider="openai")
evaluator = Evaluator()

# Process paper
paper = parser.parse("paper.pdf")
code = generator.generate(paper)
results = evaluator.evaluate(code)

print(f"Generated code saved to: {results['output_dir']}")
```

## Web Interface

### Starting the Web Interface

```bash
research2repo web
```

### Using the Web Interface

1. Open your browser to `http://localhost:7860`
2. Upload a PDF paper or enter an arXiv URL
3. Configure processing options
4. Click "Process" to generate code
5. View and download the generated repository

### Custom Web Interface

```bash
research2repo web --port 8080 --host 0.0.0.0
```

## Code Generation Strategies

Research2Repo supports multiple code generation strategies:

### Simple Generation

```bash
research2repo process paper.pdf --generator simple
```

### Iterative Generation

```bash
research2repo process paper.pdf --generator iterative
```

### Multi-Agent Generation

```bash
research2repo process paper.pdf --generator multi-agent
```

## Evaluation

### Evaluate Generated Code

```bash
research2repo evaluate ./output
```

### Custom Evaluation Metrics

```bash
research2repo evaluate ./output --evaluator syntax,semantic
```

## Advanced Usage

### Custom Components

You can register custom components using the registry system:

```python
from architecture.core.registry import register_processor

@register_processor("custom")
class CustomProcessor:
    def __init__(self, param1: str, param2: int = 10):
        self.param1 = param1
        self.param2 = param2
    
    def process(self, paper_path: str):
        # Your custom processing logic
        pass
```

### Configuration Merging

Runtime configuration overrides static configuration:

```python
from architecture.core.registry import REGISTRY

# Build component with runtime overrides
processor = REGISTRY.build(
    kind="processor",
    name="grobid",
    runtime={"timeout": 120},  # Override timeout
    cfg={"url": "http://localhost:8070"}  # Base config
)
```

### Batch Processing

Process multiple papers at once:

```bash
research2repo batch ./papers --output ./outputs
```

## Troubleshooting

### Common Issues

**Issue**: GROBID connection failed
- **Solution**: Ensure GROBID is running at `http://127.0.0.1:8070`
- Start GROBID: `docker run --rm -p 8070:8070 lfoppiano/grobid:0.7.2`

**Issue**: Ollama connection failed
- **Solution**: Ensure Ollama is running at `http://127.0.0.1:11434`
- Start Ollama: `ollama serve`

**Issue**: API key not found
- **Solution**: Set the appropriate environment variable for your provider

### Debug Mode

Enable debug mode for detailed logging:

```bash
research2repo process paper.pdf --debug
```

## Next Steps

- See [how_to_add_processor.md](how_to_add_processor.md) to add custom processors
- See [how_to_add_provider.md](how_to_add_provider.md) to add custom providers
- See [examples/](../examples/) for example configurations
- See the [wiki](https://github.com/your-org/Research2Repo/wiki) for more documentation
