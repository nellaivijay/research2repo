"""Base processor class with distributed support."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

try:
    import torch
    import torch.distributed as dist
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class BaseProcessor(ABC):
    """
    Abstract base class for paper processors with distributed support.
    
    This class provides a consistent interface for paper processing with
    built-in support for distributed training scenarios.
    
    Args:
        cache_dir: Directory for caching processed results
        seed: Random seed for reproducibility
        accelerator: Accelerator for distributed training (optional)
    """

    def __init__(
        self,
        cache_dir: str = "./cache/processor",
        seed: int = 42,
        accelerator: Optional[Any] = None
    ):
        self.cache_dir = cache_dir
        self.seed = seed
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
    def process(self, paper_path: str, **kwargs) -> Dict[str, Any]:
        """
        Process a paper and return structured content.
        
        Args:
            paper_path: Path to the paper PDF file
            **kwargs: Additional processing parameters
            
        Returns:
            Dictionary containing processed paper content
        """
        pass

    def warmup(self, num_samples: int = 10) -> List[int]:
        """
        Warmup the processor with sample processing.
        
        Args:
            num_samples: Number of samples to warmup with
            
        Returns:
            List of processed sample indices
        """
        if self.is_main_process():
            if TORCH_AVAILABLE:
                generator = torch.Generator()
                generator.manual_seed(self.seed)
                indices = torch.randint(0, 100, (num_samples,), generator=generator).tolist()
            else:
                # Fallback to random without torch
                import random
                random.seed(self.seed)
                indices = random.sample(range(100), min(num_samples, 100))
        else:
            indices = None
        
        return self.broadcast_object(indices, src=0)
