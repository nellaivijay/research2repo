# Research2Repo

**Educational agentic framework for converting research papers into implementation repositories**

Research2Repo is an open source educational tool designed to help students and researchers understand how to convert academic research papers into production-ready code repositories. It demonstrates advanced concepts in agentic AI systems, multi-model integration, and automated software development.

## Educational Purpose

This tool serves educational purposes by helping students and researchers:
- Learn about agentic AI architectures and multi-agent systems
- Understand multi-model LLM integration patterns
- Practice automated code generation and validation
- Study research-to-implementation workflows
- Explore self-refine loops and automated debugging
- Gain hands-on experience with software automation

## Key Features

- **Multi-Model Support**: Integration with Google Gemini, OpenAI GPT-4o, Anthropic Claude, and local models via Ollama
- **Agentic Architecture**: Multi-agent system with decomposed planning and specialized agents
- **Self-Refine Loops**: Verify and refine artifacts at each pipeline stage
- **Execution Sandbox**: Docker and local sandbox environments for running generated code
- **Auto-Debug**: Automated error analysis and fixing for common Python error types
- **Reference Mining**: GitHub CodeRAG for finding reference implementations
- **Long-Context Processing**: Single-pass architecture preserving context without chunking
- **Multi-Backend PDF Parsing**: Support for GROBID, doc2json, PyMuPDF, PyPDF2

## Advanced Features

### Decomposed Planning
Four-stage planning process: overall plan → architecture design (UML) → logic design → config generation

### Per-File Analysis
Deep specification generation for each file before code implementation

### Self-Refine Loops
Verify-then-refine cycles at every pipeline stage to catch errors early

### Execution Sandbox
Docker and local sandbox environments to actually run and validate generated code

### Auto-Debug
Iterative error analysis and automatic fixing for common Python errors

### Context Management
Clean-slate context with cumulative code summaries to prevent context overflow

### Document Segmentation
Content-aware chunking for papers exceeding token limits while preserving structure

### CodeRAG
Mine GitHub for reference implementations with confidence-scored mappings

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/nellaivijay/research2repo.git
cd Research2Repo

# Install dependencies
pip install -r requirements.txt
```

### Provider Setup

```bash
# Google Gemini (recommended)
export GEMINI_API_KEY="your_key_here"

# OpenAI GPT-4o
export OPENAI_API_KEY="your_key_here"
pip install openai

# Anthropic Claude
export ANTHROPIC_API_KEY="your_key_here"
pip install anthropic

# Ollama (local models)
# Install from https://ollama.ai, then:
ollama pull deepseek-coder-v2
```

### Basic Usage

```bash
# Classic mode with auto-detected provider
python main.py --pdf_url "https://arxiv.org/pdf/paper.pdf"

# Agent mode with decomposed planning
python main.py --pdf_url "https://arxiv.org/pdf/paper.pdf" --mode agent

# Agent mode with self-refine loops
python main.py --pdf_url "https://arxiv.org/pdf/paper.pdf" --mode agent --refine

# Agent mode with execution sandbox and auto-debug
python main.py --pdf_url "https://arxiv.org/pdf/paper.pdf" --mode agent --execute

# Full pipeline with all features
python main.py --pdf_url "https://arxiv.org/pdf/paper.pdf" --mode agent --refine --execute
```

## Architecture

### Classic Mode
```
PDF → [Analyzer] → [Equation Extractor] → [Architect] → [Coder] → [Validator] → Repository
```

### Agent Mode
```
PDF → [Paper Parser] → [Decomposed Planner] → [Per-File Analyzer] → [Doc Segmenter]
  → [Self-Refine] → [CodeRAG] → [Context-Managed Coder] → [Validator] → [Execution Sandbox]
  → [Auto-Debugger] → [DevOps Generator] → [Evaluator] → Repository
```

## Pipeline Stages

1. **PaperAnalyzer**: Long-context analysis with vision diagram extraction
2. **DecomposedPlanner**: 4-stage planning (overall → architecture → logic → config)
3. **FileAnalyzer**: Per-file deep analysis with accumulated context
4. **DocumentSegmenter**: Semantic segmentation for large papers
5. **CodeRAG**: Mine GitHub for reference implementations
6. **CodeSynthesizer**: File-by-file generation with context management
7. **TestGenerator**: Auto-generated pytest suite
8. **CodeValidator**: Self-review and iterative auto-fix
9. **ExecutionSandbox**: Run code in sandbox environment
10. **AutoDebugger**: Iterative error fixing
11. **DevOpsGenerator**: Generate Dockerfile, CI, Makefile
12. **ReferenceEvaluator**: Score against reference implementation

## Multi-Model Provider System

- **Base Provider**: Abstract interface with capabilities enum
- **Gemini Provider**: Google Gemini (2.5 Pro, 2.0 Flash, 1.5 Pro)
- **OpenAI Provider**: GPT-4o, GPT-4-turbo, o3, o1
- **Anthropic Provider**: Claude Sonnet 4, Opus 4, 3.5 Sonnet
- **Ollama Provider**: Local models (DeepSeek, Llama, CodeLlama, Mistral)
- **Registry**: Auto-detection, fallback chains, cost estimation

## Project Structure

```
Research2Repo/
├── main.py                    # CLI entry point
├── config.py                  # Global configuration
├── providers/                 # Multi-model abstraction
│   ├── base.py
│   ├── gemini.py
│   ├── openai_provider.py
│   ├── anthropic_provider.py
│   ├── ollama.py
│   └── registry.py
├── core/                      # Pipeline stages
│   ├── analyzer.py
│   ├── architect.py
│   ├── coder.py
│   ├── validator.py
│   ├── planner.py
│   ├── file_analyzer.py
│   ├── refiner.py
│   └── paper_parser.py
├── advanced/                  # Advanced capabilities
│   ├── equation_extractor.py
│   ├── config_generator.py
│   ├── test_generator.py
│   ├── cache.py
│   ├── executor.py
│   ├── debugger.py
│   ├── evaluator.py
│   ├── devops.py
│   ├── code_rag.py
│   ├── document_segmenter.py
│   └── context_manager.py
├── agents/                    # Multi-agent architecture
│   ├── base.py
│   └── orchestrator.py
├── prompts/                   # Prompt templates
├── tests/                     # Test suite
└── requirements.txt
```

## Development

### Adding New Providers

Implement the `BaseProvider` interface in `providers/` directory following existing patterns.

### Testing

Run the test suite:
```bash
pytest tests/
```

## License

Apache 2.0 License - See LICENSE file for details.

## Educational Use

This tool is provided for educational purposes to help students and researchers learn about:
- Agentic AI architectures and multi-agent systems
- Multi-model LLM integration and provider abstraction
- Automated code generation and validation techniques
- Research-to-implementation workflows
- Self-refine loops and automated debugging
- Software automation and DevOps generation