"""Base generator class with distributed support."""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any

try:
    import torch
    import torch.distributed as dist
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class BaseGenerator(ABC):
    """
    Abstract base class for code generators with distributed support.
    
    This class provides a consistent interface for code generation with
    built-in support for distributed training scenarios.
    
    Args:
        max_iterations: Maximum number of generation iterations
        temperature: Sampling temperature (0.0-1.0)
        cache_dir: Directory for caching generated code
        accelerator: Accelerator for distributed training (optional)
    """

    def __init__(
        self,
        max_iterations: int = 3,
        temperature: float = 0.7,
        cache_dir: str = "./cache/generator",
        accelerator: Optional[Any] = None
    ):
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.cache_dir = cache_dir
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
    def generate(self, paper_content: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Generate code from paper content.
        
        Args:
            paper_content: Processed paper content
            **kwargs: Additional generation parameters
            
        Returns:
            Dictionary containing generated code and metadata
        """
        pass

    def refine(self, code: str, feedback: str, **kwargs) -> str:
        """
        Refine generated code based on feedback.
        
        Args:
            code: Generated code to refine
            feedback: Feedback for refinement
            **kwargs: Additional refinement parameters
            
        Returns:
            Refined code
        """
        # Default implementation: return original code
        return code

    def warmup(self, num_samples: int = 5):
        """
        Warmup the generator with sample generations.
        
        Args:
            num_samples: Number of samples to warmup with
        """
        if self.is_main_process():
            sample_content = {
                "title": "Sample Paper",
                "abstract": "Sample abstract for warmup"
            }
            for i in range(num_samples):
                self.generate(sample_content)
        self.barrier()
