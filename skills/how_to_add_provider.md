# How to Add a Custom Provider

This guide explains how to add a custom LLM provider to Research2Repo using the registry system.

## Overview

Research2Repo supports multiple LLM providers (OpenAI, Anthropic, Gemini, Ollama) through a unified interface. You can add custom providers using the registry system.

## Architecture Overview

### Provider Registry

The provider registry (`architecture/core/registry.py`) manages LLM providers:
- Decorator-based registration: `@register_provider`
- Configuration-driven instantiation
- Runtime parameter overrides
- Type-safe provider lookup

### Provider Interface

All providers should:
- Implement a consistent interface
- Accept configuration parameters
- Handle API errors gracefully
- Support streaming when possible

## Step-by-Step Guide

### Step 1: Create Provider Class

Create your provider class:

```python
# architecture/providers/custom_provider.py
from architecture.core.registry import register_provider
from typing import Dict, Optional

@register_provider("custom")
class CustomProvider:
    """
    Custom LLM provider.
    
    Args:
        api_key: API key for the service
        model: Model name to use
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "custom-model",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 120
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # Validate API key
        if not self.api_key:
            raise ValueError("API key is required")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
        """
        # Your generation logic here
        response = self._call_api(prompt, **kwargs)
        return response
    
    def generate_stream(self, prompt: str, **kwargs):
        """
        Generate text with streaming.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Yields:
            Generated text chunks
        """
        # Your streaming logic here
        for chunk in self._call_api_stream(prompt, **kwargs):
            yield chunk
    
    def _call_api(self, prompt: str, **kwargs) -> str:
        """Internal method to call the API."""
        # Implement API call
        pass
    
    def _call_api_stream(self, prompt: str, **kwargs):
        """Internal method to call the API with streaming."""
        # Implement streaming API call
        pass
```

### Step 2: Register Provider

Use the `@register_provider` decorator:

```python
from architecture.core.registry import register_provider

@register_provider("custom")
class CustomProvider:
    # ... implementation
```

### Step 3: Add to components.yaml

Add your provider configuration to `config/components.yaml`:

```yaml
providers:
  custom:
    name: custom
    params:
      api_key: null  # Set via environment variable CUSTOM_API_KEY
      model: custom-model
      temperature: 0.7
      max_tokens: 2000
      timeout: 120
```

### Step 4: Import to Register

Ensure your provider is imported:

```python
# architecture/providers/__init__.py
from .custom_provider import *  # This triggers registration
```

### Step 5: Use Your Provider

#### Using CLI

```bash
export CUSTOM_API_KEY="your-api-key"
research2repo process paper.pdf --provider custom
```

#### Using Python API

```python
from architecture.core.registry import REGISTRY

# Build provider with configuration
provider = REGISTRY.build(
    kind="provider",
    name="custom",
    runtime={"api_key": "your-api-key"},  # Runtime override
    cfg={"model": "custom-model", "temperature": 0.7}  # From components.yaml
)

# Use provider
response = provider.generate("Generate code for this algorithm")
```

## Advanced Features

### Base Class Inheritance

If a base provider class exists, inherit from it:

```python
from architecture.providers.base_provider import BaseProvider
from architecture.core.registry import register_provider

@register_provider("custom")
class CustomProvider(BaseProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "custom-model",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 120
    ):
        super().__init__(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
    
    def _call_api(self, prompt: str, **kwargs) -> str:
        # Your implementation
        pass
```

### Environment Variable Support

Support environment variables for API keys:

```python
import os

class CustomProvider:
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key or os.getenv("CUSTOM_API_KEY")
        if not self.api_key:
            raise ValueError("CUSTOM_API_KEY environment variable must be set")
```

### Retry Logic

Implement retry logic for API calls:

```python
import time
from typing import Callable

class CustomProvider:
    def __init__(self, max_retries: int = 3, retry_delay: int = 5, **kwargs):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def _call_api_with_retry(self, prompt: str, **kwargs) -> str:
        for attempt in range(self.max_retries):
            try:
                return self._call_api(prompt, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay)
```

### Rate Limiting

Implement rate limiting:

```python
import time
from threading import Lock

class CustomProvider:
    def __init__(self, rate_limit: float = 1.0, **kwargs):
        self.rate_limit = rate_limit  # seconds between calls
        self.last_call_time = 0
        self.lock = Lock()
    
    def _call_api(self, prompt: str, **kwargs) -> str:
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_call_time
            if time_since_last < self.rate_limit:
                time.sleep(self.rate_limit - time_since_last)
            self.last_call_time = time.time()
        
        return self._make_api_call(prompt, **kwargs)
```

### Streaming Support

Implement streaming for better UX:

```python
class CustomProvider:
    def generate_stream(self, prompt: str, **kwargs):
        """
        Generate text with streaming.
        
        Yields:
            Text chunks as they arrive
        """
        response = self._call_api_stream(prompt, **kwargs)
        for chunk in response:
            yield chunk
```

## Best Practices

### 1. Error Handling

Handle API errors gracefully:

```python
class CustomProvider:
    def _call_api(self, prompt: str, **kwargs) -> str:
        try:
            response = self._make_api_call(prompt, **kwargs)
            return response
        except ConnectionError as e:
            raise RuntimeError(f"Failed to connect to API: {e}")
        except TimeoutError:
            raise RuntimeError(f"Request timed out after {self.timeout}s")
        except Exception as e:
            raise RuntimeError(f"API call failed: {e}")
```

### 2. Input Validation

Validate inputs:

```python
class CustomProvider:
    def __init__(self, temperature: float = 0.7, **kwargs):
        if not 0.0 <= temperature <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        self.temperature = temperature
    
    def generate(self, prompt: str, **kwargs) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        # ... rest of implementation
```

### 3. Type Hints

Use type hints:

```python
from typing import Dict, Optional, Iterator

class CustomProvider:
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        pass
    
    def generate_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        """Generate text with streaming."""
        pass
```

### 4. Docstrings

Provide comprehensive docstrings:

```python
class CustomProvider:
    """
    Custom LLM provider for specific service.
    
    This provider integrates with the Custom API service for text generation.
    
    Args:
        api_key: API key for authentication (required)
        model: Model identifier (default: "custom-model")
        temperature: Sampling temperature 0.0-1.0 (default: 0.7)
        max_tokens: Maximum tokens to generate (default: 2000)
        timeout: Request timeout in seconds (default: 120)
        
    Attributes:
        api_key: Stored API key
        model: Model identifier
        temperature: Sampling temperature
        max_tokens: Maximum tokens
        timeout: Request timeout
        
    Example:
        >>> provider = CustomProvider(api_key="key123")
        >>> response = provider.generate("Hello, world!")
    """
```

### 5. Testing

Add tests for your provider:

```python
# tests/unit/test_custom_provider.py
import pytest
from architecture.providers.custom_provider import CustomProvider

def test_custom_provider_init():
    provider = CustomProvider(api_key="test-key")
    assert provider.api_key == "test-key"
    assert provider.model == "custom-model"

def test_custom_provider_no_api_key():
    with pytest.raises(ValueError):
        CustomProvider()

def test_custom_provider_generate():
    provider = CustomProvider(api_key="test-key")
    # Mock API call for testing
    response = provider.generate("test prompt")
    assert isinstance(response, str)
```

## Examples

See existing providers for reference:
- `architecture/providers/openai.py` - OpenAI provider
- `architecture/providers/anthropic.py` - Anthropic provider
- `architecture/providers/gemini.py` - Gemini provider
- `architecture/providers/ollama.py` - Ollama provider

## Troubleshooting

### Provider Not Found

If your provider isn't found:
1. Ensure it's imported in `__init__.py`
2. Check the decorator name matches components.yaml
3. Verify the module is in the Python path

### API Key Issues

If API key issues occur:
1. Set environment variable for the provider
2. Pass api_key explicitly in configuration
3. Check for typos in environment variable name

### Connection Errors

If connection errors occur:
1. Verify API service is accessible
2. Check firewall/network settings
3. Increase timeout if needed
4. Check API key validity

### Rate Limiting

If rate limiting occurs:
1. Implement retry logic with exponential backoff
2. Add rate limiting to your provider
3. Use streaming for longer generations
4. Consider batch processing

## Next Steps

- See [how_to_add_processor.md](how_to_add_processor.md) to add custom processors
- See [how_to_use.md](how_to_use.md) for usage examples
- See [examples/](../examples/) for example configurations
