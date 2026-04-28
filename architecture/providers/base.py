"""
Abstract base provider and capability definitions.
All model providers must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import time as _time
import functools


def retry_on_error(max_retries: int = 2, backoff: float = 1.0):
    """Decorator that retries LLM API calls on transient failures."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError, OSError) as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        wait = backoff * (2 ** attempt)
                        print(f"  [Provider] Retry {attempt + 1}/{max_retries} "
                              f"after {type(exc).__name__}, waiting {wait:.1f}s...")
                        _time.sleep(wait)
                except Exception as exc:
                    # Non-transient errors: check for rate-limit indicators
                    msg = str(exc).lower()
                    if ("rate" in msg or "429" in msg or "quota" in msg) and attempt < max_retries:
                        last_exc = exc
                        wait = backoff * (2 ** attempt)
                        print(f"  [Provider] Rate limited, retry {attempt + 1}/{max_retries} "
                              f"in {wait:.1f}s...")
                        _time.sleep(wait)
                    else:
                        raise
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator


class ModelCapability(Enum):
    """Capabilities a model provider may support."""
    TEXT_GENERATION = auto()
    VISION = auto()                # Image/diagram understanding
    LONG_CONTEXT = auto()          # 100k+ token context windows
    STRUCTURED_OUTPUT = auto()     # JSON-mode / function calling
    CODE_GENERATION = auto()       # Optimized for code
    FILE_UPLOAD = auto()           # Native file upload API
    STREAMING = auto()             # Streaming responses


@dataclass
class ModelInfo:
    """Metadata about a specific model."""
    name: str
    provider: str
    max_context_tokens: int
    max_output_tokens: int
    capabilities: list[ModelCapability] = field(default_factory=list)
    cost_per_1k_input: float = 0.0   # USD
    cost_per_1k_output: float = 0.0  # USD


@dataclass
class GenerationConfig:
    """Common generation parameters across all providers."""
    temperature: float = 0.2
    top_p: float = 0.95
    max_output_tokens: int = 8192
    stop_sequences: list[str] = field(default_factory=list)
    response_format: Optional[str] = None  # "json" or None


@dataclass
class GenerationResult:
    """Standardized response from any provider."""
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = "stop"
    raw_response: Optional[object] = None


class BaseProvider(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key
        self.model_name = model_name or self.default_model()
        self._model_info_cache = None

    @abstractmethod
    def default_model(self) -> str:
        """Return the default model name for this provider."""
        ...

    @abstractmethod
    def available_models(self) -> list[ModelInfo]:
        """List all models available through this provider."""
        ...

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
        images: Optional[list[bytes]] = None,
    ) -> GenerationResult:
        """
        Generate text from a prompt.

        Args:
            prompt: The user prompt / input text.
            system_prompt: Optional system-level instruction.
            config: Generation parameters.
            images: Optional list of image bytes for vision models.

        Returns:
            GenerationResult with the model's response.
        """
        ...

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ) -> dict:
        """
        Generate structured JSON output conforming to a schema.

        Args:
            prompt: The user prompt.
            schema: JSON schema the output must conform to.
            system_prompt: Optional system instruction.
            config: Generation parameters.

        Returns:
            Parsed dict matching the schema.
        """
        ...

    def supports(self, capability: ModelCapability) -> bool:
        """Check if current model supports a given capability."""
        info = self.model_info()
        return info is not None and capability in info.capabilities

    def upload_file(self, file_path: str) -> object:
        """
        Upload a file for use in prompts (if provider supports FILE_UPLOAD).
        Default: raises NotImplementedError.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support file upload."
        )

    def model_info(self) -> Optional[ModelInfo]:
        """Get info for the currently selected model (cached)."""
        if self._model_info_cache is None:
            for m in self.available_models():
                if m.name == self.model_name:
                    self._model_info_cache = m
                    break
        return self._model_info_cache
