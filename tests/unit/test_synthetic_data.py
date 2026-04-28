"""
Unit tests for synthetic data generation
"""

import pytest
from datasets.synthetic_data_generator import SyntheticPaperGenerator, SyntheticCodeGenerator


@pytest.mark.unit
class TestSyntheticPaperGenerator:
    """Test SyntheticPaperGenerator functionality."""
    
    def test_initialization(self):
        """Test generator initialization."""
        generator = SyntheticPaperGenerator()
        assert generator.paper_templates is not None
        assert "ml" in generator.paper_templates
        assert "nlp" in generator.paper_templates
        assert "cv" in generator.paper_templates
    
    def test_generate_paper_ml(self):
        """Test generating ML paper."""
        generator = SyntheticPaperGenerator()
        paper = generator.generate_paper(domain="ml")
        
        assert paper["title"] is not None
        assert paper["authors"] is not None
        assert paper["abstract"] is not None
        assert len(paper["sections"]) > 0
        assert len(paper["equations"]) > 0
        assert paper["hyperparameters"] is not None
        assert paper["domain"] == "ml"
    
    def test_generate_paper_nlp(self):
        """Test generating NLP paper."""
        generator = SyntheticPaperGenerator()
        paper = generator.generate_paper(domain="nlp")
        
        assert paper["domain"] == "nlp"
        assert paper["title"] is not None
    
    def test_generate_paper_cv(self):
        """Test generating CV paper."""
        generator = SyntheticPaperGenerator()
        paper = generator.generate_paper(domain="cv")
        
        assert paper["domain"] == "cv"
        assert paper["title"] is not None
    
    def test_generate_paper_simple_complexity(self):
        """Test generating paper with simple complexity."""
        generator = SyntheticPaperGenerator()
        paper = generator.generate_paper(domain="ml", complexity="simple")
        
        assert paper["complexity"] == "simple"
        assert len(paper["sections"]) <= 4
    
    def test_generate_paper_medium_complexity(self):
        """Test generating paper with medium complexity."""
        generator = SyntheticPaperGenerator()
        paper = generator.generate_paper(domain="ml", complexity="medium")
        
        assert paper["complexity"] == "medium"
        assert 4 < len(paper["sections"]) <= 6
    
    def test_generate_paper_complex_complexity(self):
        """Test generating paper with complex complexity."""
        generator = SyntheticPaperGenerator()
        paper = generator.generate_paper(domain="ml", complexity="complex")
        
        assert paper["complexity"] == "complex"
        assert len(paper["sections"]) > 6
    
    def test_generate_paper_invalid_domain(self):
        """Test generating paper with invalid domain raises error."""
        generator = SyntheticPaperGenerator()
        
        with pytest.raises(ValueError, match="Unknown domain"):
            generator.generate_paper(domain="invalid")
    
    def test_generate_batch(self):
        """Test generating batch of papers."""
        generator = SyntheticPaperGenerator()
        papers = generator.generate_batch(num_papers=5, domain="ml")
        
        assert len(papers) == 5
        for paper in papers:
            assert paper["domain"] == "ml"
            assert paper["title"] is not None
    
    def test_paper_structure(self):
        """Test that generated paper has required structure."""
        generator = SyntheticPaperGenerator()
        paper = generator.generate_paper(domain="ml")
        
        required_fields = [
            "title", "authors", "abstract", "sections", 
            "equations", "hyperparameters", "full_text", 
            "domain", "complexity", "generated_at"
        ]
        
        for field in required_fields:
            assert field in paper
    
    def test_hyperparameters_valid(self):
        """Test that generated hyperparameters are valid."""
        generator = SyntheticPaperGenerator()
        paper = generator.generate_paper(domain="ml")
        
        hyperparams = paper["hyperparameters"]
        assert isinstance(hyperparams, dict)
        assert len(hyperparams) > 0
        
        for key, value in hyperparams.items():
            assert isinstance(key, str)
            assert value is not None


@pytest.mark.unit
class TestSyntheticCodeGenerator:
    """Test SyntheticCodeGenerator functionality."""
    
    def test_initialization(self):
        """Test code generator initialization."""
        generator = SyntheticCodeGenerator()
        assert generator.code_templates is not None
        assert "model" in generator.code_templates
        assert "data" in generator.code_templates
        assert "train" in generator.code_templates
    
    def test_generate_code_model(self):
        """Test generating model code."""
        generator = SyntheticCodeGenerator()
        code = generator.generate_code("model", model_name="TestModel")
        
        assert "class TestModel" in code
        assert "import torch" in code
        assert "def __init__" in code
        assert "def forward" in code
    
    def test_generate_code_data(self):
        """Test generating data loading code."""
        generator = SyntheticCodeGenerator()
        code = generator.generate_code("data", dataset_name="TestDataset")
        
        assert "class TestDataset" in code
        assert "Dataset" in code
        assert "__len__" in code
        assert "__getitem__" in code
    
    def test_generate_code_train(self):
        """Test generating training code."""
        generator = SyntheticCodeGenerator()
        code = generator.generate_code("train", epochs=10, lr=0.001)
        
        assert "def train_model" in code
        assert "epochs=10" in code
        assert "lr=0.001" in code
        assert "optimizer" in code
    
    def test_generate_code_invalid_type(self):
        """Test generating invalid code type raises error."""
        generator = SyntheticCodeGenerator()
        
        with pytest.raises(ValueError, match="Unknown code type"):
            generator.generate_code("invalid_type")
    
    def test_generate_repository_structure(self, sample_paper_data):
        """Test generating complete repository structure."""
        generator = SyntheticCodeGenerator()
        repo = generator.generate_repository_structure(sample_paper_data)
        
        assert isinstance(repo, dict)
        assert "README.md" in repo
        assert "src/model.py" in repo
        assert "src/data.py" in repo
        assert "src/train.py" in repo
        assert "requirements.txt" in repo
        assert "config.yaml" in repo
    
    def test_generate_readme(self, sample_paper_data):
        """Test README generation."""
        generator = SyntheticCodeGenerator()
        readme = generator._generate_readme(sample_paper_data)
        
        assert sample_paper_data["title"] in readme
        assert "Installation" in readme
        assert "Usage" in readme
        assert "Hyperparameters" in readme
    
    def test_generate_requirements(self, sample_paper_data):
        """Test requirements.txt generation."""
        generator = SyntheticCodeGenerator()
        requirements = generator._generate_requirements(sample_paper_data)
        
        assert "torch" in requirements
        assert "numpy" in requirements
        assert "pandas" in requirements
    
    def test_generate_config(self, sample_paper_data):
        """Test config.yaml generation."""
        generator = SyntheticCodeGenerator()
        config = generator._generate_config(sample_paper_data)
        
        assert isinstance(config, str)
        for key, value in sample_paper_data["hyperparameters"].items():
            assert key in config
    
    def test_repository_files_content(self, sample_paper_data):
        """Test that repository files have appropriate content."""
        generator = SyntheticCodeGenerator()
        repo = generator.generate_repository_structure(sample_paper_data)
        
        # Check model.py
        assert "class" in repo["src/model.py"]
        assert "def forward" in repo["src/model.py"]
        
        # Check data.py
        assert "Dataset" in repo["src/data.py"]
        
        # Check train.py
        assert "def train" in repo["src/train.py"]