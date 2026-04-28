# How to Add a Custom Processor

This guide explains how to add a custom paper processor to Research2Repo using the registry system.

## Overview

Research2Repo uses a registry system to manage extensible components. Custom processors can be registered and used without modifying the core codebase.

## Architecture Overview

### Registry System

The registry system (`architecture/core/registry.py`) provides:
- Decorator-based registration
- Configuration-driven instantiation
- Runtime parameter overrides
- Type-safe component lookup

### Base Processor Pattern

All processors should follow the base class pattern:
- Inherit from a base class (when available)
- Implement required abstract methods
- Accept configuration parameters in `__init__`
- Provide consistent interface

## Step-by-Step Guide

### Step 1: Create Processor Class

Create your processor class in an appropriate location:

```python
# architecture/processors/custom_processor.py
from architecture.core.registry import register_processor

@register_processor("custom")
class CustomProcessor:
    """
    Custom paper processor.
    
    Args:
        param1: Description of param1
        param2: Description of param2 (default: 10)
        cache_dir: Directory for caching results
    """
    
    def __init__(
        self,
        param1: str,
        param2: int = 10,
        cache_dir: str = "./cache/custom"
    ):
        self.param1 = param1
        self.param2 = param2
        self.cache_dir = cache_dir
    
    def process(self, paper_path: str) -> dict:
        """
        Process the paper and return structured content.
        
        Args:
            paper_path: Path to the paper PDF file
            
        Returns:
            Dictionary containing processed paper content
        """
        # Your processing logic here
        content = {
            "title": "Extracted Title",
            "abstract": "Extracted Abstract",
            "sections": [],
            "references": []
        }
        
        return content
```

### Step 2: Register Processor

Use the `@register_processor` decorator to register your processor:

```python
from architecture.core.registry import register_processor

@register_processor("custom")
class CustomProcessor:
    # ... implementation
```

The decorator takes a single argument:
- `name`: Unique identifier for your processor

### Step 3: Add to components.yaml

Add your processor configuration to `config/components.yaml`:

```yaml
processors:
  custom:
    name: custom
    params:
      param1: "value1"
      param2: 20
      cache_dir: ./cache/custom
```

### Step 4: Import to Register

Ensure your processor is imported so it gets registered:

```python
# architecture/processors/__init__.py
from .custom_processor import *  # This triggers registration
```

### Step 5: Use Your Processor

#### Using CLI

```bash
research2repo process paper.pdf --processor custom
```

#### Using Python API

```python
from architecture.core.registry import REGISTRY

# Build processor with configuration
processor = REGISTRY.build(
    kind="processor",
    name="custom",
    runtime={},  # Runtime overrides
    cfg={"param1": "value1", "param2": 20}  # From components.yaml
)

# Use processor
content = processor.process("paper.pdf")
```

## Advanced Features

### Base Class Inheritance

If a base processor class exists, inherit from it:

```python
from architecture.processors.base_processor import BaseProcessor
from architecture.core.registry import register_processor

@register_processor("custom")
class CustomProcessor(BaseProcessor):
    def __init__(self, param1: str, param2: int = 10, cache_dir: str = "./cache/custom"):
        super().__init__(cache_dir=cache_dir)
        self.param1 = param1
        self.param2 = param2
    
    def process(self, paper_path: str) -> dict:
        # Your implementation
        pass
```

### Configuration Merging

Runtime configuration overrides static configuration:

```python
processor = REGISTRY.build(
    kind="processor",
    name="custom",
    runtime={"param2": 30},  # Override param2
    cfg={"param1": "value1", "param2": 20}  # Base config
)
# Result: param1="value1", param2=30
```

### Parameter Filtering

Only parameters accepted by `__init__` are passed:

```python
class CustomProcessor:
    def __init__(self, param1: str, param2: int = 10):
        self.param1 = param1
        self.param2 = param2

# Even if config has extra params, they're filtered:
processor = REGISTRY.build(
    kind="processor",
    name="custom",
    cfg={"param1": "value1", "param2": 20, "extra_param": "ignored"}
)
# Result: param1="value1", param2=20 (extra_param ignored)
```

### Distributed Processing

For distributed processing support:

```python
import torch.distributed as dist

class CustomProcessor:
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self.rank = dist.get_rank() if dist.is_initialized() else 0
    
    def process(self, paper_path: str):
        # Only process on rank 0
        if self.rank == 0:
            # Processing logic
            pass
        
        # Synchronize if needed
        if dist.is_initialized():
            dist.barrier()
```

## Best Practices

### 1. Type Hints

Use type hints for better IDE support and documentation:

```python
from typing import Dict, List, Optional

class CustomProcessor:
    def __init__(
        self,
        param1: str,
        param2: int = 10,
        cache_dir: Optional[str] = None
    ):
        self.param1 = param1
        self.param2 = param2
        self.cache_dir = cache_dir or "./cache/custom"
    
    def process(self, paper_path: str) -> Dict[str, any]:
        # Implementation
        pass
```

### 2. Docstrings

Provide comprehensive docstrings:

```python
class CustomProcessor:
    """
    Custom paper processor for specific use case.
    
    This processor handles papers with special formatting or content.
    
    Args:
        param1: Description of what param1 does
        param2: Description of what param2 does (default: 10)
        cache_dir: Directory for caching processed results
        
    Attributes:
        param1: Stores param1 value
        param2: Stores param2 value
        cache_dir: Cache directory path
        
    Example:
        >>> processor = CustomProcessor(param1="value")
        >>> content = processor.process("paper.pdf")
    """
```

### 3. Error Handling

Handle errors gracefully:

```python
class CustomProcessor:
    def process(self, paper_path: str) -> dict:
        try:
            # Processing logic
            pass
        except FileNotFoundError:
            raise ValueError(f"Paper not found: {paper_path}")
        except Exception as e:
            raise RuntimeError(f"Processing failed: {str(e)}")
```

### 4. Caching

Implement caching for expensive operations:

```python
import os
import json
from pathlib import Path

class CustomProcessor:
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def process(self, paper_path: str) -> dict:
        cache_file = self.cache_dir / f"{Path(paper_path).stem}.json"
        
        # Check cache
        if cache_file.exists():
            with open(cache_file) as f:
                return json.load(f)
        
        # Process
        content = self._process_paper(paper_path)
        
        # Cache result
        with open(cache_file, 'w') as f:
            json.dump(content, f)
        
        return content
```

### 5. Testing

Add tests for your processor:

```python
# tests/unit/test_custom_processor.py
import pytest
from architecture.processors.custom_processor import CustomProcessor

def test_custom_processor():
    processor = CustomProcessor(param1="test", param2=5)
    assert processor.param1 == "test"
    assert processor.param2 == 5

def test_custom_processor_process():
    processor = CustomProcessor(param1="test")
    content = processor.process("test_paper.pdf")
    assert "title" in content
    assert "abstract" in content
```

## Examples

See the existing processors in `architecture/processors/` for reference:
- `grobid_processor.py` - GROBID-based processing
- `pdfminer_processor.py` - PDFMiner-based processing
- `pymupdf_processor.py` - PyMuPDF-based processing

## Troubleshooting

### Processor Not Found

If your processor isn't found:
1. Ensure it's imported in `__init__.py`
2. Check the decorator name matches components.yaml
3. Verify the module is in the Python path

### Configuration Not Applied

If configuration isn't applied:
1. Check parameter names match `__init__` parameters
2. Verify components.yaml syntax is correct
3. Check for runtime overrides

### Registration Conflicts

If you get "already registered" error:
1. Choose a unique name for your processor
2. Check if another processor uses the same name
3. Use `REGISTRY.has("processor", "name")` to check

## Next Steps

- See [how_to_add_provider.md](how_to_add_provider.md) to add custom providers
- See [how_to_use.md](how_to_use.md) for usage examples
- See [examples/](../examples/) for example configurations
