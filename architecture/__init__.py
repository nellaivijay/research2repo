"""
Architecture package for Research2Repo
Contains core system architecture components
"""

from .agents import AgentOrchestrator
from .pipeline import PaperAnalyzer, SystemArchitect, CodeSynthesizer, CodeValidator
from .providers import ProviderRegistry, get_provider

__all__ = [
    'AgentOrchestrator',
    'PaperAnalyzer', 
    'SystemArchitect',
    'CodeSynthesizer',
    'CodeValidator',
    'ProviderRegistry',
    'get_provider'
]