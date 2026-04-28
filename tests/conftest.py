"""
Pytest configuration and fixtures for Research2Repo
"""

import pytest
import os
import tempfile
import json
from pathlib import Path
from typing import Dict, Any

# Test data paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
PAPERS_DIR = FIXTURES_DIR / "papers"
CONFIGS_DIR = FIXTURES_DIR / "configs"


@pytest.fixture
def sample_paper_data():
    """Fixture providing sample paper data for testing."""
    return {
        "title": "Attention Is All You Need",
        "authors": ["Vaswani et al."],
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
        "sections": ["Introduction", "Background", "Model Architecture", "Training", "Results", "Conclusion"],
        "equations": [
            "Attention(Q,K,V) = softmax(QK^T / sqrt(d_k))V",
            "FFN(x) = max(0, xW_1 + b_1)W_2 + b_2"
        ],
        "hyperparameters": {
            "d_model": 512,
            "d_ff": 2048,
            "heads": 8,
            "layers": 6,
            "dropout": 0.1
        }
    }


@pytest.fixture
def sample_pipeline_config():
    """Fixture providing sample pipeline configuration."""
    return {
        "mode": "agent",
        "provider": "gemini",
        "model": "gemini-1.5-pro",
        "enable_refine": True,
        "enable_execution": False,
        "enable_tests": True,
        "enable_devops": True
    }


@pytest.fixture
def temp_output_dir():
    """Fixture providing temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_config_file():
    """Fixture providing temporary config file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("test: value\n")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def mock_gemini_provider():
    """Fixture providing mock Gemini provider."""
    from tests.mocks.mock_providers.mock_gemini import MockGeminiProvider
    provider = MockGeminiProvider()
    yield provider
    provider.reset()


@pytest.fixture
def mock_openai_provider():
    """Fixture providing mock OpenAI provider."""
    from tests.mocks.mock_providers.mock_openai import MockOpenAIProvider
    provider = MockOpenAIProvider()
    yield provider
    provider.reset()


@pytest.fixture
def mock_anthropic_provider():
    """Fixture providing mock Anthropic provider."""
    from tests.mocks.mock_providers.mock_anthropic import MockAnthropicProvider
    provider = MockAnthropicProvider()
    yield provider
    provider.reset()


@pytest.fixture
def sample_repository_structure():
    """Fixture providing sample repository structure."""
    return {
        "src": {
            "model.py": "class Model:\n    pass",
            "data.py": "def load_data():\n    pass",
            "train.py": "def train():\n    pass"
        },
        "tests": {
            "test_model.py": "def test_model():\n    pass"
        },
        "config.yaml": "param: value",
        "requirements.txt": "torch\nnumpy",
        "README.md": "# Test Repository"
    }


@pytest.fixture
def sample_validation_report():
    """Fixture providing sample validation report."""
    return {
        "score": 92,
        "equation_coverage": 95,
        "hyperparam_coverage": 88,
        "critical_issues": [],
        "warnings": [
            {
                "file": "src/model.py",
                "line": 10,
                "message": "Consider adding docstring"
            }
        ]
    }


@pytest.fixture
def synthetic_paper():
    """Fixture providing synthetic paper data."""
    from datasets.synthetic_data_generator import SyntheticPaperGenerator
    
    generator = SyntheticPaperGenerator()
    return generator.generate_paper(domain="ml", complexity="medium")


@pytest.fixture
def synthetic_repository():
    """Fixture providing synthetic repository structure."""
    from datasets.synthetic_data_generator import SyntheticCodeGenerator
    from datasets.synthetic_data_generator import SyntheticPaperGenerator
    
    paper_generator = SyntheticPaperGenerator()
    code_generator = SyntheticCodeGenerator()
    
    paper = paper_generator.generate_paper(domain="ml", complexity="medium")
    return code_generator.generate_repository_structure(paper)


@pytest.fixture
def config_manager():
    """Fixture providing configuration manager."""
    from config.config_manager import ConfigManager
    
    manager = ConfigManager()
    return manager


@pytest.fixture
def mock_pipeline_state():
    """Fixture providing mock pipeline state."""
    return {
        "status": "completed",
        "current_stage": "Reference Evaluation",
        "progress": 100,
        "mode": "agent",
        "provider": "gemini",
        "model": "gemini-1.5-pro",
        "files_generated": 12,
        "validation_score": 92,
        "elapsed_time": 245.5,
        "total_cost": 0.025,
        "completed_stages": [
            "Parse Paper",
            "Decomposed Planning",
            "Per-File Analysis",
            "Document Segmentation",
            "Self-Refine Loop",
            "CodeRAG Mining",
            "Context-Managed Coding",
            "Validation",
            "Execution Sandbox",
            "Auto-Debugging",
            "DevOps Generation",
            "Reference Evaluation"
        ],
        "stage_times": {
            "Parse Paper": 15.2,
            "Decomposed Planning": 25.5,
            "Per-File Analysis": 45.8,
            "Document Segmentation": 12.3,
            "Self-Refine Loop": 35.7,
            "CodeRAG Mining": 28.4,
            "Context-Managed Coding": 52.1,
            "Validation": 18.9,
            "Execution Sandbox": 22.3,
            "Auto-Debugging": 15.6,
            "DevOps Generation": 12.4,
            "Reference Evaluation": 8.2
        },
        "cost_breakdown": {
            "Paper Analysis": 0.005,
            "Architecture Design": 0.00375,
            "Code Generation": 0.01,
            "Validation": 0.00375,
            "Testing": 0.0025
        },
        "validation_scores": {
            "Equation Coverage": 95,
            "Hyperparam Coverage": 88,
            "Code Quality": 92,
            "Test Coverage": 85
        }
    }


# Skip tests that require API keys if not available
def pytest_configure(config):
    """Configure pytest with custom markers and skip conditions."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (deselect with '-m \"not unit\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "benchmark: marks tests as benchmark tests (deselect with '-m \"not benchmark\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "requires_api: marks tests that require API keys"
    )
    config.addinivalue_line(
        "markers", "mock: marks tests that use mock providers"
    )


# Create fixtures directories if they don't exist
@pytest.fixture(autouse=True)
def setup_test_directories():
    """Create test directories if they don't exist."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create sample paper file if it doesn't exist
    sample_paper = PAPERS_DIR / "sample_paper.json"
    if not sample_paper.exists():
        from datasets.synthetic_data_generator import SyntheticPaperGenerator
        generator = SyntheticPaperGenerator()
        paper = generator.generate_paper(domain="ml", complexity="medium")
        with open(sample_paper, 'w') as f:
            json.dump(paper, f, indent=2)