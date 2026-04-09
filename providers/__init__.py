"""
Multi-model provider abstraction layer.
Supports: Google Gemini, OpenAI GPT-4, Anthropic Claude, Ollama (local).
"""

from providers.registry import ProviderRegistry, get_provider
from providers.base import BaseProvider, ModelCapability

__all__ = ["ProviderRegistry", "get_provider", "BaseProvider", "ModelCapability"]
