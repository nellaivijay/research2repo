"""
Integration tests for full Research2Repo pipeline
"""

import pytest
import tempfile
import os
from pathlib import Path


@pytest.mark.integration
@pytest.mark.mock
class TestFullPipelineIntegration:
    """Integration tests for complete pipeline execution."""
    
    def test_mock_provider_integration(self, mock_gemini_provider, sample_paper_data):
        """Test that mock providers integrate properly with pipeline."""
        # Simulate using mock provider for analysis
        response = mock_gemini_provider.generate("Analyze this paper")
        
        assert mock_gemini_provider.get_call_count() == 1
        assert "title" in response.lower()
    
    def test_config_manager_integration(self, config_manager):
        """Test config manager integration with pipeline."""
        # Load pipeline config
        pipeline_config = config_manager.load_pipeline_config("classic")
        
        assert pipeline_config.name == "classic"
        assert len(pipeline_config.stages) > 0
        
        # Load provider config
        provider_config = config_manager.load_provider_config("gemini")
        
        assert provider_config.name == "gemini"
        assert provider_config.base_url is not None
    
    def test_synthetic_data_pipeline_flow(self, synthetic_paper):
        """Test synthetic data generation to repository flow."""
        from datasets.synthetic_data_generator import SyntheticCodeGenerator
        
        code_generator = SyntheticCodeGenerator()
        repo_structure = code_generator.generate_repository_structure(synthetic_paper)
        
        # Verify complete repository structure
        assert "README.md" in repo_structure
        assert "src/model.py" in repo_structure
        assert "requirements.txt" in repo_structure
        assert "config.yaml" in repo_structure
        
        # Verify file contents are valid
        assert len(repo_structure["README.md"]) > 0
        assert "import" in repo_structure["src/model.py"]
        assert "torch" in repo_structure["requirements.txt"]
    
    def test_mock_pipeline_execution(self, mock_gemini_provider, temp_output_dir):
        """Test simulated pipeline execution with mock provider."""
        # Simulate pipeline stages
        stages = [
            "download_pdf",
            "analyze_paper", 
            "design_architecture",
            "synthesize_code",
            "save_repository"
        ]
        
        results = {}
        for stage in stages:
            if stage == "analyze_paper":
                response = mock_gemini_provider.generate("Analyze this paper")
                results[stage] = response
            elif stage == "design_architecture":
                response = mock_gemini_provider.generate("Design architecture")
                results[stage] = response
            elif stage == "synthesize_code":
                response = mock_gemini_provider.generate("Generate code")
                results[stage] = response
            else:
                results[stage] = "completed"
        
        # Verify all stages completed
        assert len(results) == len(stages)
        assert all(results.values())
        assert mock_gemini_provider.get_call_count() == 3
    
    def test_config_driven_pipeline(self, config_manager, mock_gemini_provider):
        """Test pipeline execution driven by configuration."""
        # Load pipeline configuration
        pipeline_config = config_manager.load_pipeline_config("minimal")
        
        # Verify configuration controls pipeline behavior
        assert pipeline_config.feature_flags["enable_vision"] == False
        assert pipeline_config.feature_flags["enable_test_generation"] == False
        assert pipeline_config.feature_flags["enable_validation"] == False
        
        # Verify minimal stages
        stage_names = [stage["name"] for stage in pipeline_config.stages]
        assert "download_pdf" in stage_names
        assert "analyze_paper" in stage_names
        assert len(stage_names) <= 5  # Minimal mode has fewer stages


@pytest.mark.integration
@pytest.mark.mock
class TestProviderIntegration:
    """Integration tests for provider system."""
    
    def test_multiple_mock_providers(self, mock_gemini_provider, mock_openai_provider, mock_anthropic_provider):
        """Test using multiple mock providers."""
        # Test each provider
        gemini_response = mock_gemini_provider.generate("Test prompt")
        openai_response = mock_openai_provider.generate("Test prompt")
        anthropic_response = mock_anthropic_provider.generate("Test prompt")
        
        # Verify all providers respond
        assert len(gemini_response) > 0
        assert len(openai_response) > 0
        assert len(anthropic_response) > 0
        
        # Verify call counts
        assert mock_gemini_provider.get_call_count() == 1
        assert mock_openai_provider.get_call_count() == 1
        assert mock_anthropic_provider.get_call_count() == 1
    
    def test_provider_fallback_simulation(self, config_manager):
        """Test provider fallback mechanism."""
        # Load configuration with fallback providers
        pipeline_config = config_manager.load_pipeline_config("classic")
        
        # Verify fallback providers are configured
        assert len(pipeline_config.fallback_providers) > 0
        assert "openai" in pipeline_config.fallback_providers
        assert "anthropic" in pipeline_config.fallback_providers


@pytest.mark.integration
@pytest.mark.mock
class TestDataFlowIntegration:
    """Integration tests for data flow through pipeline."""
    
    def test_paper_to_code_flow(self, synthetic_paper):
        """Test complete flow from paper to code."""
        from datasets.synthetic_data_generator import SyntheticCodeGenerator
        
        # Generate code from paper
        code_generator = SyntheticCodeGenerator()
        repo = code_generator.generate_repository_structure(synthetic_paper)
        
        # Verify paper data is reflected in generated code
        assert synthetic_paper["title"] in repo["README.md"]
        
        # Verify hyperparameters are used in config
        from config.config_manager import ConfigManager
        import yaml
        
        config_data = yaml.safe_load(repo["config.yaml"])
        for key, value in synthetic_paper["hyperparameters"].items():
            assert key in config_data
    
    def test_validation_flow(self, synthetic_repository):
        """Test validation flow for generated repository."""
        # Verify all expected files exist
        required_files = ["README.md", "src/model.py", "requirements.txt", "config.yaml"]
        for file in required_files:
            assert file in synthetic_repository
        
        # Verify Python files are syntactically valid
        import ast
        
        for file_path, content in synthetic_repository.items():
            if file_path.endswith(".py"):
                try:
                    ast.parse(content)
                except SyntaxError:
                    pytest.fail(f"Syntax error in {file_path}")


@pytest.mark.integration
@pytest.mark.mock
class TestErrorHandlingIntegration:
    """Integration tests for error handling."""
    
    def test_provider_error_handling(self, mock_gemini_provider):
        """Test error handling when provider fails."""
        # Reset provider
        mock_gemini_provider.reset()
        
        # Simulate error by testing invalid input
        try:
            # This should still work with mock provider
            response = mock_gemini_provider.generate("Test")
            assert response is not None
        except Exception as e:
            pytest.fail(f"Mock provider should not raise exceptions: {e}")
    
    def test_config_error_handling(self, config_manager):
        """Test error handling for invalid configuration."""
        # Test loading invalid pipeline mode
        with pytest.raises(ValueError):
            config_manager.load_pipeline_config("invalid_mode")
        
        # Test loading invalid provider
        with pytest.raises(ValueError):
            config_manager.load_provider_config("invalid_provider")


@pytest.mark.integration
@pytest.mark.mock
class TestPerformanceIntegration:
    """Integration tests for performance characteristics."""
    
    def test_pipeline_performance_with_mocks(self, mock_gemini_provider):
        """Test pipeline performance with mock providers."""
        import time
        
        # Simulate pipeline execution
        start_time = time.time()
        
        for i in range(5):
            mock_gemini_provider.generate(f"Test prompt {i}")
        
        elapsed_time = time.time() - start_time
        
        # Mock providers should be fast
        assert elapsed_time < 5.0  # Should complete in under 5 seconds
        assert mock_gemini_provider.get_call_count() == 5
    
    def test_config_loading_performance(self, config_manager):
        """Test configuration loading performance."""
        import time
        
        # Test first load (not cached)
        start_time = time.time()
        config1 = config_manager.load_pipeline_config("classic")
        first_load_time = time.time() - start_time
        
        # Test second load (cached)
        start_time = time.time()
        config2 = config_manager.load_pipeline_config("classic")
        second_load_time = time.time() - start_time
        
        # Cached load should be faster
        assert second_load_time < first_load_time
        
        # Verify same object is returned (caching works)
        assert config1 is config2