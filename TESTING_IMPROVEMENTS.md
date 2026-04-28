# Testing Infrastructure Improvements

Based on OmniShotCut's testing approach, here's a comprehensive plan for improving Research2Repo's testing infrastructure.

## Current Testing State

### Existing Tests
- Basic test structure in `tests/` directory
- Limited test coverage
- No integration tests
- No performance benchmarks
- No mock providers for testing

### Limitations
- Difficult to test full pipeline end-to-end
- No way to test without actual API calls
- Limited ability to test error conditions
- No performance regression testing
- Limited provider testing

## Proposed Testing Infrastructure

### 1. Test Directory Structure

```
tests/
├── __init__.py
├── conftest.py                 # pytest configuration and fixtures
├── fixtures/                   # Test fixtures and data
│   ├── papers/                # Sample papers for testing
│   │   ├── short_paper.pdf
│   │   ├── medium_paper.pdf
│   │   └── long_paper.pdf
│   ├── configs/               # Test configurations
│   │   ├── test_config.yaml
│   │   └── minimal_config.yaml
│   └── expected_outputs/      # Expected outputs for validation
│       ├── classic_mode/
│       └── agent_mode/
├── unit/                      # Unit tests
│   ├── test_providers/
│   │   ├── test_base_provider.py
│   │   ├── test_gemini_provider.py
│   │   ├── test_openai_provider.py
│   │   ├── test_anthropic_provider.py
│   │   └── test_ollama_provider.py
│   ├── test_pipeline/
│   │   ├── test_analyzer.py
│   │   ├── test_architect.py
│   │   ├── test_coder.py
│   │   ├── test_validator.py
│   │   ├── test_planner.py
│   │   ├── test_file_analyzer.py
│   │   ├── test_refiner.py
│   │   └── test_paper_parser.py
│   ├── test_advanced/
│   │   ├── test_cache.py
│   │   ├── test_code_rag.py
│   │   ├── test_context_manager.py
│   │   ├── test_debugger.py
│   │   ├── test_executor.py
│   │   └── test_document_segmenter.py
│   └── test_utils/
│       ├── test_visualization.py
│       ├── test_file_io.py
│       └── test_metrics.py
├── integration/               # Integration tests
│   ├── test_full_pipeline.py
│   ├── test_classic_pipeline.py
│   ├── test_agent_pipeline.py
│   ├── test_provider_integration.py
│   ├── test_sandbox_execution.py
│   └── test_end_to_end.py
├── benchmarks/                # Performance benchmarks
│   ├── test_pipeline_performance.py
│   ├── test_provider_performance.py
│   ├── test_cost_comparison.py
│   └── test_quality_metrics.py
└── mocks/                     # Mock implementations
    ├── mock_providers/
    │   ├── __init__.py
    │   ├── mock_gemini.py
    │   ├── mock_openai.py
    │   └── mock_anthropic.py
    └── mock_data/
        ├── mock_paper_analysis.py
        └── mock_code_generation.py
```

### 2. Mock Providers for Testing

Create mock providers that simulate real provider behavior without making actual API calls:

```python
# tests/mocks/mock_providers/mock_gemini.py
class MockGeminiProvider:
    """Mock Gemini provider for testing."""
    
    def __init__(self, model_name="gemini-1.5-pro"):
        self.model_name = model_name
        self.call_count = 0
        self.responses = []
    
    def generate(self, prompt, **kwargs):
        """Simulate generate call."""
        self.call_count += 1
        # Return predefined response based on prompt
        return self._get_mock_response(prompt)
    
    def _get_mock_response(self, prompt):
        """Get mock response based on prompt type."""
        if "analyze" in prompt.lower():
            return self._mock_analysis_response()
        elif "architecture" in prompt.lower():
            return self._mock_architecture_response()
        elif "code" in prompt.lower():
            return self._mock_code_response()
        else:
            return "Mock response"
    
    def _mock_analysis_response(self):
        """Mock paper analysis response."""
        return """
        {
            "title": "Mock Paper Title",
            "authors": ["Author 1", "Author 2"],
            "abstract": "This is a mock abstract",
            "sections": ["Introduction", "Method", "Results"],
            "equations": ["E = mc^2"],
            "hyperparameters": {"learning_rate": 0.001}
        }
        """
    
    # ... other mock methods
```

### 3. pytest Configuration

```python
# tests/conftest.py
import pytest
import os
import tempfile
from pathlib import Path

# Test data paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
PAPERS_DIR = FIXTURES_DIR / "papers"
CONFIGS_DIR = FIXTURES_DIR / "configs"

@pytest.fixture
def sample_paper():
    """Fixture providing a sample paper path."""
    return str(PAPERS_DIR / "short_paper.pdf")

@pytest.fixture
def test_config():
    """Fixture providing test configuration."""
    return str(CONFIGS_DIR / "test_config.yaml")

@pytest.fixture
def temp_output_dir():
    """Fixture providing temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def mock_provider():
    """Fixture providing mock provider."""
    from tests.mocks.mock_providers.mock_gemini import MockGeminiProvider
    return MockGeminiProvider()

@pytest.fixture
def sample_paper_analysis():
    """Fixture providing sample paper analysis."""
    return {
        "title": "Attention Is All You Need",
        "authors": ["Vaswani et al."],
        "abstract": "The dominant sequence transduction models...",
        "sections": ["Introduction", "Background", "Model", "Experiments", "Conclusion"],
        "equations": ["Attention(Q,K,V) = softmax(QK^T / sqrt(d_k))V"],
        "hyperparameters": {
            "d_model": 512,
            "d_ff": 2048,
            "heads": 8,
            "layers": 6,
            "dropout": 0.1
        }
    }

# Pytest markers
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "benchmark: marks tests as benchmark tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
```

### 4. Unit Test Examples

```python
# tests/unit/test_pipeline/test_analyzer.py
import pytest
from architecture.pipeline.analyzer import PaperAnalyzer

@pytest.mark.unit
class TestPaperAnalyzer:
    """Test PaperAnalyzer component."""
    
    def test_initialization(self, mock_provider):
        """Test analyzer initialization."""
        analyzer = PaperAnalyzer(provider=mock_provider)
        assert analyzer.provider is not None
    
    def test_analyze_paper(self, mock_provider, sample_paper_analysis):
        """Test paper analysis."""
        analyzer = PaperAnalyzer(provider=mock_provider)
        # Mock the analysis method
        analyzer.analyze = lambda x: sample_paper_analysis
        
        result = analyzer.analyze("mock_document")
        
        assert result["title"] == "Attention Is All You Need"
        assert len(result["authors"]) > 0
        assert len(result["sections"]) > 0
    
    def test_extract_equations(self, mock_provider):
        """Test equation extraction."""
        analyzer = PaperAnalyzer(provider=mock_provider)
        text = "The attention mechanism is defined as Attention(Q,K,V) = softmax(QK^T / sqrt(d_k))V"
        
        equations = analyzer.extract_equations(text)
        
        assert len(equations) > 0
        assert "Attention" in equations[0]
```

### 5. Integration Test Examples

```python
# tests/integration/test_full_pipeline.py
import pytest
import tempfile
import os
from pathlib import Path

@pytest.mark.integration
@pytest.mark.slow
class TestFullPipeline:
    """Test full pipeline integration."""
    
    def test_classic_pipeline_full(self, mock_provider, sample_paper, temp_output_dir):
        """Test complete classic pipeline."""
        from main import run_classic
        
        # Run pipeline with mock provider
        result = run_classic(
            pdf_url=sample_paper,
            output_dir=temp_output_dir,
            provider_name="mock",
            model_name="mock-model",
            skip_validation=True,
            skip_tests=True,
            skip_equations=True
        )
        
        # Verify output directory was created
        assert os.path.exists(temp_output_dir)
        
        # Verify some files were generated
        generated_files = list(Path(temp_output_dir).rglob("*"))
        assert len(generated_files) > 0
    
    def test_agent_pipeline_full(self, mock_provider, sample_paper, temp_output_dir):
        """Test complete agent pipeline."""
        from main import run_agent
        
        # Run agent pipeline with mock provider
        result = run_agent(
            pdf_url=sample_paper,
            output_dir=temp_output_dir,
            provider_name="mock",
            model_name="mock-model",
            enable_refine=False,
            enable_execution=False,
            enable_tests=False,
            enable_devops=False
        )
        
        # Verify output
        assert os.path.exists(temp_output_dir)
```

### 6. Benchmark Tests

```python
# tests/benchmarks/test_pipeline_performance.py
import pytest
import time
from tests.benchmarks.benchmark_utils import measure_time, measure_memory

@pytest.mark.benchmark
class TestPipelinePerformance:
    """Test pipeline performance."""
    
    @measure_time
    def test_analysis_stage_performance(self, mock_provider):
        """Benchmark paper analysis stage."""
        from architecture.pipeline.analyzer import PaperAnalyzer
        
        analyzer = PaperAnalyzer(provider=mock_provider)
        start_time = time.time()
        
        # Run analysis
        result = analyzer.analyze("mock_document")
        
        elapsed = time.time() - start_time
        assert elapsed < 10.0  # Should complete in under 10 seconds
    
    @measure_time
    def test_full_pipeline_performance(self, mock_provider, sample_paper, temp_output_dir):
        """Benchmark full pipeline execution."""
        from main import run_classic
        
        start_time = time.time()
        
        run_classic(
            pdf_url=sample_paper,
            output_dir=temp_output_dir,
            provider_name="mock",
            model_name="mock-model",
            skip_validation=True,
            skip_tests=True,
            skip_equations=True
        )
        
        elapsed = time.time() - start_time
        assert elapsed < 60.0  # Should complete in under 60 seconds
```

### 7. Test Utilities

```python
# tests/utils/test_helpers.py
class TestHelpers:
    """Test helper utilities."""
    
    @staticmethod
    def create_mock_paper(content: str, path: str):
        """Create a mock paper file."""
        with open(path, 'w') as f:
            f.write(content)
    
    @staticmethod
    def compare_output(actual: dict, expected: dict, tolerance: float = 0.1):
        """Compare actual output with expected output."""
        # Implement comparison logic
        pass
    
    @staticmethod
    def validate_generated_code(code: str):
        """Validate generated Python code."""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False
```

### 8. Continuous Integration Configuration

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run unit tests
        run: pytest tests/unit/ -v -m "unit"
  
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run integration tests
        run: pytest tests/integration/ -v -m "integration"
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  
  benchmarks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run benchmarks
        run: pytest tests/benchmarks/ -v -m "benchmark"
```

### 9. Test Coverage Goals

- **Unit Tests**: 80%+ coverage for core components
- **Integration Tests**: Cover all major pipeline flows
- **Benchmark Tests**: Performance regression detection
- **Provider Tests**: All providers tested with mocks

### 10. Test Data Management

### Sample Papers
- Short paper (< 5 pages): For quick tests
- Medium paper (5-15 pages): For standard tests
- Long paper (> 15 pages): For performance tests

### Expected Outputs
- Pre-generated outputs for validation
- Different outputs for different pipeline modes
- Reference implementations for comparison

## Implementation Timeline

### Week 1: Infrastructure Setup
- Create test directory structure
- Set up pytest configuration
- Create mock providers
- Add test fixtures

### Week 2: Unit Tests
- Write unit tests for all pipeline components
- Write unit tests for providers
- Write unit tests for utilities
- Achieve 80%+ coverage

### Week 3: Integration Tests
- Write integration tests for classic pipeline
- Write integration tests for agent pipeline
- Write provider integration tests
- Write end-to-end tests

### Week 4: Benchmarks and CI
- Write performance benchmarks
- Set up CI/CD pipeline
- Add coverage reporting
- Document testing procedures

## Benefits

### 1. Reliability
- Catch bugs early
- Prevent regressions
- Ensure code quality

### 2. Development Speed
- Faster debugging with isolated tests
- Confidence in refactoring
- Clear specification of expected behavior

### 3. Documentation
- Tests serve as documentation
- Clear examples of usage
- Specification of edge cases

### 4. Collaboration
- Easier for contributors to understand code
- Clear test requirements for PRs
- Automated quality checks

### 5. Performance
- Performance regression detection
- Cost optimization insights
- Provider comparison data

## Conclusion

This comprehensive testing infrastructure will significantly improve Research2Repo's reliability, maintainability, and development speed, following industry best practices demonstrated by successful research repositories like OmniShotCut.