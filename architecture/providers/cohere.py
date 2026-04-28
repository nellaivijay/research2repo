"""Cohere provider implementation."""

from architecture.base.base_provider import BaseProvider
from architecture.core.registry import register_provider
from typing import Optional, Iterator
import os


@register_provider("cohere")
class CohereProvider(BaseProvider):
    """
    Cohere LLM provider.
    
    Args:
        api_key: Cohere API key (or use COHERE_API_KEY env var)
        model: Model identifier (default: "command")
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "command",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 120,
        **kwargs
    ):
        super().__init__(api_key, model, temperature, max_tokens, timeout, **kwargs)
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        if not self.api_key:
            raise ValueError("COHERE_API_KEY environment variable must be set")

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using Cohere API."""
        try:
            import cohere
            
            client = cohere.Client(self.api_key)
            response = client.generate(
                model=self.model,
                prompt=prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=self.timeout
            )
            
            return response.generations[0].text
            
        except ImportError:
            raise ImportError("Cohere package not installed. Install with: pip install cohere")

    def generate_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        """Generate text with streaming using Cohere API."""
        try:
            import cohere
            
            client = cohere.Client(self.api_key)
            stream = client.generate_stream(
                model=self.model,
                prompt=prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            for event in stream:
                if hasattr(event, 'text') and event.text:
                    yield event.text
                    
        except ImportError:
            raise ImportError("Cohere package not installed. Install with: pip install cohere")

    def generate_batch(self, prompts: list, **kwargs) -> list:
        """Generate text for multiple prompts using Cohere batch API."""
        try:
            import cohere
            
            client = cohere.Client(self.api_key)
            response = client.batch_generate(
                model=self.model,
                prompts=prompts,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=self.timeout
            )
            
            return [gen.text for gen in response.generations]
            
        except ImportError:
            raise ImportError("Cohere package not installed. Install with: pip install cohere")
