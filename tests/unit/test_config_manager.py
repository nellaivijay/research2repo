"""
Unit tests for configuration management
"""

import pytest
import tempfile
import os
from pathlib import Path
from config.config_manager import ConfigManager


@pytest.mark.unit
class TestConfigManager:
    """Test ConfigManager functionality."""
    
    def test_initialization(self):
        """Test config manager initialization."""
        manager = ConfigManager()
        assert manager.config_dir.exists()
    
    def test_initialization_with_custom_dir(self):
        """Test config manager with custom directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)
            assert manager.config_dir == Path(tmpdir)
    
    def test_get_all_pipeline_modes(self):
        """Test getting all pipeline modes."""
        manager = ConfigManager()
        modes = manager.get_all_pipeline_modes()
        
        assert isinstance(modes, list)
        assert "classic" in modes
        assert "agent" in modes
        assert "minimal" in modes
    
    def test_get_all_providers(self):
        """Test getting all providers."""
        manager = ConfigManager()
        providers = manager.get_all_providers()
        
        assert isinstance(providers, list)
        assert "gemini" in providers
        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers
    
    def test_load_pipeline_config_classic(self):
        """Test loading classic pipeline config."""
        manager = ConfigManager()
        config = manager.load_pipeline_config("classic")
        
        assert config.name == "classic"
        assert config.default_provider == "gemini"
        assert len(config.stages) > 0
        assert config.feature_flags["enable_cache"] == True
        assert config.performance_settings["max_fix_iterations"] == 2
    
    def test_load_pipeline_config_agent(self):
        """Test loading agent pipeline config."""
        manager = ConfigManager()
        config = manager.load_pipeline_config("agent")
        
        assert config.name == "agent"
        assert config.feature_flags["enable_refine"] == True
        assert config.performance_settings["max_refine_iterations"] == 2
    
    def test_load_pipeline_config_minimal(self):
        """Test loading minimal pipeline config."""
        manager = ConfigManager()
        config = manager.load_pipeline_config("minimal")
        
        assert config.name == "minimal"
        assert config.default_model == "gemini-1.5-flash"
        assert config.feature_flags["enable_vision"] == False
        assert config.feature_flags["enable_test_generation"] == False
    
    def test_load_provider_config_gemini(self):
        """Test loading Gemini provider config."""
        manager = ConfigManager()
        config = manager.load_provider_config("gemini")
        
        assert config.name == "gemini"
        assert config.base_url == "https://generativelanguage.googleapis.com"
        assert config.timeout == 120
        assert len(config.models) > 0
    
    def test_load_provider_config_openai(self):
        """Test loading OpenAI provider config."""
        manager = ConfigManager()
        config = manager.load_provider_config("openai")
        
        assert config.name == "openai"
        assert config.base_url == "https://api.openai.com/v1"
        assert len(config.models) > 0
    
    def test_get_model_config(self):
        """Test getting specific model config."""
        manager = ConfigManager()
        model_config = manager.get_model_config("gemini", "gemini-1.5-pro")
        
        assert "capabilities" in model_config
        assert "max_tokens" in model_config
        assert "cost_per_1k_input" in model_config
        assert model_config["max_tokens"] == 2000000
    
    def test_get_model_config_invalid_model(self):
        """Test getting invalid model config raises error."""
        manager = ConfigManager()
        
        with pytest.raises(ValueError, match="not found"):
            manager.get_model_config("gemini", "invalid-model")
    
    def test_get_model_config_invalid_provider(self):
        """Test getting model config for invalid provider raises error."""
        manager = ConfigManager()
        
        with pytest.raises(ValueError, match="not found"):
            manager.get_model_config("invalid-provider", "any-model")
    
    def test_config_caching(self):
        """Test that configs are cached."""
        manager = ConfigManager()
        
        # Load config first time
        config1 = manager.load_pipeline_config("classic")
        
        # Load config second time (should be cached)
        config2 = manager.load_pipeline_config("classic")
        
        assert config1 is config2
    
    def test_validate_config(self):
        """Test configuration validation."""
        manager = ConfigManager()
        assert manager.validate_config() == True
    
    def test_get_api_key_gemini(self):
        """Test getting API key for Gemini."""
        manager = ConfigManager()
        
        # Set environment variable
        os.environ["GEMINI_API_KEY"] = "test_key"
        api_key = manager.get_api_key("gemini")
        
        assert api_key == "test_key"
        
        # Cleanup
        del os.environ["GEMINI_API_KEY"]
    
    def test_get_api_key_ollama(self):
        """Test getting API key for Ollama (should be None)."""
        manager = ConfigManager()
        api_key = manager.get_api_key("ollama")
        
        assert api_key is None
    
    def test_invalid_pipeline_mode(self):
        """Test loading invalid pipeline mode raises error."""
        manager = ConfigManager()
        
        with pytest.raises(ValueError, match="not found"):
            manager.load_pipeline_config("invalid-mode")
    
    def test_invalid_provider(self):
        """Test loading invalid provider raises error."""
        manager = ConfigManager()
        
        with pytest.raises(ValueError, match="not found"):
            manager.load_provider_config("invalid-provider")