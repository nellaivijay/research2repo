"""
Abstract base provider and capability definitions.
All model providers must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


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
        for m in self.available_models():
            if m.name == self.model_name:
                return capability in m.capabilities
        return False

    def upload_file(self, file_path: str) -> object:
        """
        Upload a file for use in prompts (if provider supports FILE_UPLOAD).
        Default: raises NotImplementedError.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support file upload."
        )

    def model_info(self) -> Optional[ModelInfo]:
        """Get info for the currently selected model."""
        for m in self.available_models():
            if m.name == self.model_name:
                return m
        return None
