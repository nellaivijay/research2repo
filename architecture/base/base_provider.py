"""Base provider class with distributed support."""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Iterator, Any, List

try:
    import torch
    import torch.distributed as dist
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers with distributed support.
    
    This class provides a consistent interface for LLM providers with
    built-in support for distributed training scenarios.
    
    Args:
        api_key: API key for authentication (optional)
        model: Model identifier
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds
        accelerator: Accelerator for distributed training (optional)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 120,
        accelerator: Optional[Any] = None
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.accelerator = accelerator
        self.rank = self._get_rank()
        self.world_size = self._get_world_size()

    def _get_rank(self) -> int:
        """Get the rank of the current process."""
        if TORCH_AVAILABLE and dist.is_available() and dist.is_initialized():
            return dist.get_rank()
        return 0

    def _get_world_size(self) -> int:
        """Get the total number of processes."""
        if TORCH_AVAILABLE and dist.is_available() and dist.is_initialized():
            return dist.get_world_size()
        return 1

    def is_main_process(self) -> bool:
        """Check if this is the main process (rank 0)."""
        return self.rank == 0

    def barrier(self):
        """Synchronize all processes."""
        if TORCH_AVAILABLE and dist.is_available() and dist.is_initialized():
            dist.barrier()

    def broadcast_object(self, obj: Any, src: int = 0) -> Any:
        """
        Broadcast an object from source process to all processes.
        
        Args:
            obj: Object to broadcast (only used on source process)
            src: Source process rank (default: 0)
            
        Returns:
            Broadcasted object
        """
        if TORCH_AVAILABLE and dist.is_available() and dist.is_initialized():
            if self.rank == src:
                objects = [obj]
            else:
                objects = [None]
            dist.broadcast_object_list(objects, src=src)
            return objects[0]
        return obj

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
        """
        pass

    def generate_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        """
        Generate text with streaming.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Yields:
            Generated text chunks
        """
        # Default implementation: call generate and yield result
        yield self.generate(prompt, **kwargs)

    def generate_batch(self, prompts: List[str], **kwargs) -> List[str]:
        """
        Generate text for multiple prompts.
        
        Args:
            prompts: List of input prompts
            **kwargs: Additional generation parameters
            
        Returns:
            List of generated texts
        """
        # Default implementation: sequential generation
        results = []
        for prompt in prompts:
            result = self.generate(prompt, **kwargs)
            results.append(result)
        return results

    def warmup(self, num_samples: int = 5):
        """
        Warmup the provider with sample generations.
        
        Args:
            num_samples: Number of samples to warmup with
        """
        if self.is_main_process():
            for i in range(num_samples):
                self.generate(f"Warmup prompt {i}", max_tokens=10)
        self.barrier()
