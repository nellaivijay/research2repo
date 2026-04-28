"""
Architecture package for Research2Repo
Contains core system architecture components
"""

# Agents
from .agents import BaseAgent

# Pipeline stages
from .pipeline import (
    PaperAnalyzer,
    SystemArchitect,
    CodeSynthesizer,
    CodeValidator,
    DecomposedPlanner,
    FileAnalyzer,
    SelfRefiner,
    PaperParser
)

# Providers
from .providers import ProviderRegistry, get_provider, BaseProvider, ModelCapability

__all__ = [
    # Agents
    'BaseAgent',
    # Pipeline stages
    'PaperAnalyzer',
    'SystemArchitect',
    'CodeSynthesizer',
    'CodeValidator',
    'DecomposedPlanner',
    'FileAnalyzer',
    'SelfRefiner',
    'PaperParser',
    # Providers
    'ProviderRegistry',
    'get_provider',
    'BaseProvider',
    'ModelCapability'
]