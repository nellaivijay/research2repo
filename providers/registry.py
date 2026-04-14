"""
Provider registry — factory for creating providers by name.
Supports automatic detection, fallback chains, and cost estimation.
"""

from typing import Optional

from providers.base import BaseProvider, ModelCapability, ModelInfo


# Provider name -> (module_path, class_name)
_PROVIDER_MAP = {
    "gemini": ("providers.gemini", "GeminiProvider"),
    "openai": ("providers.openai_provider", "OpenAIProvider"),
    "anthropic": ("providers.anthropic_provider", "AnthropicProvider"),
    "ollama": ("providers.ollama", "OllamaProvider"),
}

# Env var that signals availability
_PROVIDER_ENV_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "ollama": None,  # always available if Ollama is running
}

import time as _time
_AVAILABLE_CACHE: dict = {"timestamp": 0.0, "providers": None}
_CACHE_TTL = 30  # seconds


class ProviderRegistry:
    """Central registry for model providers."""

    @staticmethod
    def list_providers() -> list[str]:
        """Return names of all registered providers."""
        return list(_PROVIDER_MAP.keys())

    @staticmethod
    def create(
        provider_name: str,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs,
    ) -> BaseProvider:
        """
        Create a provider instance.

        Args:
            provider_name: One of 'gemini', 'openai', 'anthropic', 'ollama'.
            api_key: Override API key (otherwise read from env).
            model_name: Override default model.
            **kwargs: Extra args passed to the provider constructor.

        Returns:
            Initialized BaseProvider subclass.
        """
        if provider_name not in _PROVIDER_MAP:
            raise ValueError(
                f"Unknown provider '{provider_name}'. "
                f"Available: {list(_PROVIDER_MAP.keys())}"
            )

        module_path, class_name = _PROVIDER_MAP[provider_name]
        import importlib
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls(api_key=api_key, model_name=model_name, **kwargs)

    @staticmethod
    def detect_available() -> list[str]:
        """Detect which providers have credentials configured."""
        now = _time.monotonic()
        if _AVAILABLE_CACHE["providers"] is not None and (now - _AVAILABLE_CACHE["timestamp"]) < _CACHE_TTL:
            return _AVAILABLE_CACHE["providers"]

        import os
        available = []
        for name, env_key in _PROVIDER_ENV_KEYS.items():
            if env_key is None:
                # Ollama: check if the service is reachable
                try:
                    import requests
                    resp = requests.get("http://localhost:11434/api/tags", timeout=2)
                    if resp.status_code == 200:
                        available.append(name)
                except Exception:
                    pass
            elif os.environ.get(env_key):
                available.append(name)

        _AVAILABLE_CACHE["timestamp"] = now
        _AVAILABLE_CACHE["providers"] = available
        return available

    @staticmethod
    def best_for(capability: ModelCapability) -> Optional[str]:
        """
        Return the provider best suited for a given capability,
        based on what's currently available.
        """
        available = ProviderRegistry.detect_available()

        # Preference order by capability
        preference = {
            ModelCapability.LONG_CONTEXT: ["gemini", "anthropic", "openai", "ollama"],
            ModelCapability.VISION: ["gemini", "openai", "anthropic", "ollama"],
            ModelCapability.CODE_GENERATION: ["anthropic", "openai", "gemini", "ollama"],
            ModelCapability.STRUCTURED_OUTPUT: ["openai", "gemini", "anthropic", "ollama"],
            ModelCapability.FILE_UPLOAD: ["gemini"],
        }

        order = preference.get(capability, list(_PROVIDER_MAP.keys()))
        for name in order:
            if name in available:
                return name
        return available[0] if available else None

    @staticmethod
    def estimate_cost(
        provider_name: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost in USD for a given usage."""
        if provider_name not in _PROVIDER_MAP:
            return 0.0
        import importlib
        module_path, class_name = _PROVIDER_MAP[provider_name]
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        for model in cls.KNOWN_MODELS:
            if model.name == model_name:
                return (
                    (input_tokens / 1000) * model.cost_per_1k_input
                    + (output_tokens / 1000) * model.cost_per_1k_output
                )
        return 0.0

    @staticmethod
    def register(name: str, module_path: str, class_name: str, env_key: Optional[str] = None):
        """Register a custom provider."""
        _PROVIDER_MAP[name] = (module_path, class_name)
        _PROVIDER_ENV_KEYS[name] = env_key


def get_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    required_capability: Optional[ModelCapability] = None,
    **kwargs,
) -> BaseProvider:
    """
    Convenience function to get the best available provider.

    If provider_name is given, use it. Otherwise auto-detect based on
    available credentials and required capability.
    """
    if provider_name:
        return ProviderRegistry.create(provider_name, api_key=api_key, model_name=model_name, **kwargs)

    if required_capability:
        best = ProviderRegistry.best_for(required_capability)
        if best:
            return ProviderRegistry.create(best, api_key=api_key, model_name=model_name, **kwargs)

    # Fallback: try in preference order
    available = ProviderRegistry.detect_available()
    if not available:
        raise RuntimeError(
            "No model providers available. Set one of: "
            "GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, "
            "or start Ollama locally."
        )
    return ProviderRegistry.create(available[0], api_key=api_key, model_name=model_name, **kwargs)
