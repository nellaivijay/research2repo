"""
Configuration management for Research2Repo
Handles loading and validation of YAML configuration files
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""
    name: str
    stages: list
    default_provider: str
    default_model: str
    fallback_providers: list
    feature_flags: Dict[str, bool]
    performance_settings: Dict[str, int]
    output_settings: Dict[str, Any]


@dataclass
class ProviderConfig:
    """Configuration for a specific provider."""
    name: str
    api_key_env: Optional[str]
    base_url: str
    timeout: int
    max_retries: int
    models: Dict[str, Dict[str, Any]]


class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files.
                       Defaults to ./config if not specified.
        """
        if config_dir is None:
            # Default to config directory relative to this file
            self.config_dir = Path(__file__).parent.parent / "config"
        else:
            self.config_dir = Path(config_dir)
        
        self._pipeline_configs: Dict[str, PipelineConfig] = {}
        self._provider_configs: Dict[str, ProviderConfig] = {}
        self._model_configs: Dict[str, Dict[str, Any]] = {}
    
    def load_pipeline_config(self, mode: str) -> PipelineConfig:
        """
        Load pipeline configuration for a specific mode.
        
        Args:
            mode: Pipeline mode (classic, agent, minimal)
            
        Returns:
            PipelineConfig object
        """
        if mode in self._pipeline_configs:
            return self._pipeline_configs[mode]
        
        config_file = self.config_dir / "pipeline_configs.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Pipeline config file not found: {config_file}")
        
        with open(config_file, 'r') as f:
            all_configs = yaml.safe_load(f)
        
        if mode not in all_configs:
            raise ValueError(f"Pipeline mode '{mode}' not found in configuration")
        
        mode_config = all_configs[mode]
        
        # Extract feature flags
        feature_flags = {
            'enable_cache': mode_config.get('enable_cache', True),
            'enable_vision': mode_config.get('enable_vision', True),
            'enable_equation_extraction': mode_config.get('enable_equation_extraction', True),
            'enable_test_generation': mode_config.get('enable_test_generation', True),
            'enable_validation': mode_config.get('enable_validation', True),
            'enable_auto_fix': mode_config.get('enable_auto_fix', True),
            'enable_refine': mode_config.get('enable_refine', False),
            'enable_execution': mode_config.get('enable_execution', False),
            'enable_devops': mode_config.get('enable_devops', True),
            'enable_code_rag': mode_config.get('enable_code_rag', False),
            'enable_segmentation': mode_config.get('enable_segmentation', True),
            'enable_evaluation': mode_config.get('enable_evaluation', False),
        }
        
        # Extract performance settings
        performance_settings = {
            'max_fix_iterations': mode_config.get('max_fix_iterations', 2),
            'max_refine_iterations': mode_config.get('max_refine_iterations', 0),
            'max_debug_iterations': mode_config.get('max_debug_iterations', 0),
            'context_window': mode_config.get('context_window', 100000),
            'context_summary_interval': mode_config.get('context_summary_interval', 5),
        }
        
        # Extract output settings
        output_settings = {
            'output_format': mode_config.get('output_format', 'repository'),
            'include_readme': mode_config.get('include_readme', True),
            'include_license': mode_config.get('include_license', True),
            'include_setup_py': mode_config.get('include_setup_py', True),
            'include_dockerfile': mode_config.get('include_dockerfile', False),
            'include_ci_config': mode_config.get('include_ci_config', False),
        }
        
        config = PipelineConfig(
            name=mode,
            stages=mode_config.get('stages', []),
            default_provider=mode_config.get('default_provider', 'gemini'),
            default_model=mode_config.get('default_model', 'gemini-1.5-pro'),
            fallback_providers=mode_config.get('fallback_providers', []),
            feature_flags=feature_flags,
            performance_settings=performance_settings,
            output_settings=output_settings
        )
        
        self._pipeline_configs[mode] = config
        return config
    
    def load_provider_config(self, provider_name: str) -> ProviderConfig:
        """
        Load configuration for a specific provider.
        
        Args:
            provider_name: Name of the provider (gemini, openai, anthropic, ollama)
            
        Returns:
            ProviderConfig object
        """
        if provider_name in self._provider_configs:
            return self._provider_configs[provider_name]
        
        config_file = self.config_dir / "provider_configs.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Provider config file not found: {config_file}")
        
        with open(config_file, 'r') as f:
            all_configs = yaml.safe_load(f)
        
        if provider_name not in all_configs:
            raise ValueError(f"Provider '{provider_name}' not found in configuration")
        
        provider_config = all_configs[provider_name]
        
        config = ProviderConfig(
            name=provider_name,
            api_key_env=provider_config.get('api_key_env'),
            base_url=provider_config.get('base_url'),
            timeout=provider_config.get('timeout', 120),
            max_retries=provider_config.get('max_retries', 3),
            models=provider_config.get('models', {})
        )
        
        self._provider_configs[provider_name] = config
        return config
    
    def get_model_config(self, provider_name: str, model_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific model.
        
        Args:
            provider_name: Name of the provider
            model_name: Name of the model
            
        Returns:
            Dictionary containing model configuration
        """
        provider_config = self.load_provider_config(provider_name)
        
        if model_name not in provider_config.models:
            raise ValueError(f"Model '{model_name}' not found for provider '{provider_name}'")
        
        return provider_config.models[model_name]
    
    def get_all_providers(self) -> list:
        """Get list of all configured providers."""
        config_file = self.config_dir / "provider_configs.yaml"
        
        if not config_file.exists():
            return []
        
        with open(config_file, 'r') as f:
            all_configs = yaml.safe_load(f)
        
        return list(all_configs.keys())
    
    def get_all_pipeline_modes(self) -> list:
        """Get list of all configured pipeline modes."""
        config_file = self.config_dir / "pipeline_configs.yaml"
        
        if not config_file.exists():
            return []
        
        with open(config_file, 'r') as f:
            all_configs = yaml.safe_load(f)
        
        return list(all_configs.keys())
    
    def validate_config(self) -> bool:
        """
        Validate all configuration files.
        
        Returns:
            True if all configurations are valid, False otherwise
        """
        try:
            # Validate pipeline configs
            pipeline_file = self.config_dir / "pipeline_configs.yaml"
            if pipeline_file.exists():
                with open(pipeline_file, 'r') as f:
                    yaml.safe_load(f)
            
            # Validate provider configs
            provider_file = self.config_dir / "provider_configs.yaml"
            if provider_file.exists():
                with open(provider_file, 'r') as f:
                    yaml.safe_load(f)
            
            return True
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False
    
    def get_api_key(self, provider_name: str) -> Optional[str]:
        """
        Get API key for a provider from environment variables.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            API key if found, None otherwise
        """
        provider_config = self.load_provider_config(provider_name)
        api_key_env = provider_config.api_key_env
        
        if api_key_env is None:
            return None
        
        return os.environ.get(api_key_env)


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_dir: Optional[str] = None) -> ConfigManager:
    """
    Get the global configuration manager instance.
    
    Args:
        config_dir: Optional config directory path
        
    Returns:
        ConfigManager instance
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
    
    return _config_manager


if __name__ == "__main__":
    # Test the configuration manager
    config_manager = ConfigManager()
    
    print("Validating configurations...")
    if config_manager.validate_config():
        print("✓ All configurations are valid")
    else:
        print("✗ Configuration validation failed")
    
    print("\nAvailable pipeline modes:")
    for mode in config_manager.get_all_pipeline_modes():
        print(f"  - {mode}")
    
    print("\nAvailable providers:")
    for provider in config_manager.get_all_providers():
        print(f"  - {provider}")
    
    print("\nLoading classic pipeline config...")
    classic_config = config_manager.load_pipeline_config("classic")
    print(f"  Default provider: {classic_config.default_provider}")
    print(f"  Default model: {classic_config.default_model}")
    print(f"  Stages: {len(classic_config.stages)}")
    
    print("\nLoading Gemini provider config...")
    gemini_config = config_manager.load_provider_config("gemini")
    print(f"  Base URL: {gemini_config.base_url}")
    print(f"  Models: {list(gemini_config.models.keys())}")
    
    print("\nGetting model config for gemini-1.5-pro...")
    model_config = config_manager.get_model_config("gemini", "gemini-1.5-pro")
    print(f"  Max tokens: {model_config['max_tokens']}")
    print(f"  Capabilities: {model_config['capabilities']}")