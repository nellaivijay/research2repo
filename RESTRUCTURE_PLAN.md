# Repository Restructuring Plan

Based on OmniShotCut's excellent repository structure, here's a recommended restructuring for the Research2Repo repository to achieve better modularity, scalability, and maintainability.

## Current Structure Issues
- Mixed concerns in top-level directories
- Limited separation between architecture, datasets, and utilities
- No dedicated testing infrastructure directory
- Configuration management could be more structured
- Limited scalability for future additions

## Recommended New Structure

```
Research2Repo/
├── architecture/              # Core architecture components
│   ├── __init__.py
│   ├── agents/                # Multi-agent architecture (current agents/)
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── orchestrator.py
│   ├── pipeline/              # Pipeline stages (current core/)
│   │   ├── __init__.py
│   │   ├── analyzer.py
│   │   ├── architect.py
│   │   ├── coder.py
│   │   ├── validator.py
│   │   ├── planner.py
│   │   ├── file_analyzer.py
│   │   ├── refiner.py
│   │   └── paper_parser.py
│   └── providers/             # Provider system (current providers/)
│       ├── __init__.py
│       ├── base.py
│       ├── gemini.py
│       ├── openai_provider.py
│       ├── anthropic_provider.py
│       ├── ollama.py
│       └── registry.py
│
├── datasets/                   # Dataset management
│   ├── __init__.py
│   ├── papers/                # Sample papers for testing
│   │   ├── classic/
│   │   ├── ml/
│   │   └── nlp/
│   ├── references/            # Reference implementations
│   │   ├── attention/
│   │   ├── transformer/
│   │   └── resnet/
│   └── benchmarks/           # Benchmark datasets
│       ├── small/
│       ├── medium/
│       └── large/
│
├── config/                     # Configuration management
│   ├── __init__.py
│   ├── pipeline_configs.yaml  # Pipeline configurations
│   │   ├── classic.yaml
│   │   ├── agent.yaml
│   │   └── minimal.yaml
│   ├── provider_configs.yaml  # Provider configurations
│   │   ├── gemini.yaml
│   │   ├── openai.yaml
│   │   ├── anthropic.yaml
│   │   └── ollama.yaml
│   └── model_configs.yaml     # Model-specific configurations
│       ├── gemini_models.yaml
│       ├── openai_models.yaml
│       ├── anthropic_models.yaml
│       └── ollama_models.yaml
│
├── test_code/                  # Testing and inference
│   ├── __init__.py
│   ├── inference.py           # CLI inference script
│   ├── batch_processor.py     # Batch processing tools
│   ├── evaluation.py          # Evaluation scripts
│   ├── integration/           # Integration tests
│   │   ├── test_full_pipeline.py
│   │   ├── test_provider_integration.py
│   │   └── test_sandbox_execution.py
│   └── unit/                  # Unit tests
│       ├── test_analyzer.py
│       ├── test_architect.py
│       ├── test_coder.py
│       └── test_validator.py
│
├── util/                      # Utility functions
│   ├── __init__.py
│   ├── visualization.py       # Visualization utilities
│   ├── file_io.py             # File I/O utilities
│   ├── data_processing.py     # Data processing utilities
│   ├── logging.py             # Logging utilities
│   └── metrics.py             # Metrics and monitoring
│
├── web/                       # Web interface
│   ├── __init__.py
│   ├── app.py                 # Gradio web interface
│   ├── assets/                # Static assets
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── templates/             # HTML templates
│       └── dashboard.html
│
├── advanced/                  # Advanced capabilities (current advanced/)
│   ├── __init__.py
│   ├── cache.py
│   ├── code_rag.py
│   ├── config_generator.py
│   ├── context_manager.py
│   ├── debugger.py
│   ├── devops.py
│   ├── document_segmenter.py
│   ├── equation_extractor.py
│   ├── evaluator.py
│   ├── executor.py
│   └── test_generator.py
│
├── prompts/                   # Prompt templates (current prompts/)
│   ├── analyzer.txt
│   ├── architect.txt
│   ├── architecture_design.txt
│   ├── auto_debug.txt
│   ├── coder.txt
│   ├── devops.txt
│   ├── diagram_extractor.txt
│   ├── equation_extractor.txt
│   ├── file_analysis.txt
│   ├── logic_design.txt
│   ├── overall_plan.txt
│   ├── reference_eval.txt
│   ├── self_refine_refine.txt
│   ├── self_refine_verify.txt
│   ├── test_generator.txt
│   └── validator.txt
│
├── main.py                    # CLI entry point (current main.py)
├── config.py                  # Global configuration (current config.py)
├── setup.py                   # Setup script (current setup.py)
├── pyproject.toml             # Python project configuration
├── requirements.txt           # Dependencies
├── requirements-dev.txt       # Development dependencies
├── README.md                  # Main documentation
├── LICENSE                    # Apache 2.0 license
├── CONTRIBUTING.md            # Contributing guidelines
├── OMNISHOTCUT_ANALYSIS.md    # OmniShotCut analysis
├── RESTRUCTURE_PLAN.md        # This file
│
└── tests/                     # Test suite (current tests/)
    ├── __init__.py
    ├── conftest.py           # pytest configuration
    └── fixtures/             # Test fixtures
```

## Migration Strategy

### Phase 1: Create New Directory Structure
1. Create new directories: `architecture/`, `datasets/`, `config/`, `test_code/`, `util/`, `web/`
2. Create subdirectories within each new directory
3. Add `__init__.py` files to all Python package directories

### Phase 2: Move Existing Components
1. Move `agents/` to `architecture/agents/`
2. Move `core/` to `architecture/pipeline/`
3. Move `providers/` to `architecture/providers/`
4. Keep `advanced/` as is (already well-organized)
5. Keep `prompts/` as is (already well-organized)
6. Keep `tests/` as is, but expand with new structure

### Phase 3: Create New Components
1. Create `datasets/` with sample papers and references
2. Create `config/` with YAML configuration files
3. Create `test_code/` with inference and evaluation scripts
4. Create `util/` with utility functions
5. Create `web/` with Gradio interface (already created)

### Phase 4: Update Imports and References
1. Update all import statements to use new paths
2. Update `main.py` to use new structure
3. Update configuration files
4. Update documentation

### Phase 5: Testing and Validation
1. Run existing tests to ensure no breakage
2. Add new tests for new components
3. Validate that CLI still works
4. Validate that web interface still works

## Benefits of This Structure

### 1. Clear Separation of Concerns
- **Architecture**: Core system architecture (agents, pipeline, providers)
- **Datasets**: Data management (papers, references, benchmarks)
- **Config**: Configuration management (pipeline, provider, model configs)
- **Test Code**: Testing and inference tools
- **Util**: General utilities (visualization, file I/O, logging)
- **Web**: Web interface and related assets

### 2. Scalability
- Easy to add new providers to `architecture/providers/`
- Easy to add new pipeline stages to `architecture/pipeline/`
- Easy to add new datasets to `datasets/`
- Easy to add new configurations to `config/`
- Easy to add new utilities to `util/`

### 3. Professionalism
- Follows industry best practices for repository organization
- Similar to successful research repositories like OmniShotCut
- Clear and predictable structure for contributors
- Easy navigation for users and developers

### 4. Maintainability
- Clear organization makes it easier to find and modify code
- Separation of concerns reduces coupling
- Easier to test individual components
- Easier to document and understand

### 5. Deployment
- Clear structure makes deployment easier
- Configuration files separated from code
- Web assets organized in dedicated directory
- Test infrastructure clearly separated

## Configuration Management

### Pipeline Configurations
```yaml
# config/pipeline_configs.yaml
classic:
  stages:
    - download_pdf
    - analyze_paper
    - extract_equations
    - design_architecture
    - generate_config
    - synthesize_code
    - generate_tests
    - validate_code
    - auto_fix_issues
    - save_repository
  default_provider: gemini
  default_model: gemini-1.5-pro

agent:
  stages:
    - parse_paper
    - decomposed_planning
    - per_file_analysis
    - document_segmentation
    - self_refine_loop
    - code_rag_mining
    - context_managed_coding
    - validation
    - execution_sandbox
    - auto_debugging
    - devops_generation
    - reference_evaluation
  default_provider: gemini
  default_model: gemini-1.5-pro
  enable_refine: true
  enable_execution: false
```

### Provider Configurations
```yaml
# config/provider_configs.yaml
gemini:
  api_key_env: GEMINI_API_KEY
  base_url: https://generativelanguage.googleapis.com
  timeout: 120
  max_retries: 3

openai:
  api_key_env: OPENAI_API_KEY
  base_url: https://api.openai.com/v1
  timeout: 120
  max_retries: 3

anthropic:
  api_key_env: ANTHROPIC_API_KEY
  base_url: https://api.anthropic.com
  timeout: 120
  max_retries: 3
```

## Testing Infrastructure

### Integration Tests
- Full pipeline execution with sample papers
- Provider integration tests
- Sandbox execution tests
- End-to-end workflow tests

### Unit Tests
- Individual component tests
- Provider tests
- Pipeline stage tests
- Utility function tests

### Benchmark Tests
- Performance benchmarks
- Cost comparison benchmarks
- Quality evaluation benchmarks

## Implementation Timeline

### Week 1: Structure Creation
- Create new directory structure
- Add `__init__.py` files
- Create configuration file templates

### Week 2: Component Migration
- Move existing components to new structure
- Update import statements
- Update configuration files

### Week 3: New Components
- Create `datasets/` with sample papers
- Create `config/` with YAML configurations
- Create `util/` with utilities
- Expand `test_code/` with tests

### Week 4: Testing and Documentation
- Update and run tests
- Update documentation
- Validate CLI and web interface
- Create migration guide

## Risks and Mitigation

### Risk: Breaking Changes
**Mitigation**: 
- Maintain backward compatibility during transition
- Provide migration scripts
- Clear documentation of changes

### Risk: Import Errors
**Mitigation**:
- Systematic update of all imports
- Comprehensive testing after migration
- Clear error messages for missing imports

### Risk: Configuration Complexity
**Mitigation**:
- Provide sensible defaults
- Clear documentation of configuration options
- Configuration validation

## Conclusion

This restructuring will make Research2Repo more professional, scalable, and maintainable while following industry best practices demonstrated by successful research repositories like OmniShotCut. The clear separation of concerns and modular structure will benefit both users and contributors.