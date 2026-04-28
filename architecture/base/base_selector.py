"""Base selector class for data selection strategies."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

try:
    import torch
    import torch.distributed as dist
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class BaseSelector(ABC):
    """
    Abstract base class for data selectors with distributed support.
    
    This class provides a consistent interface for data selection with
    built-in support for distributed training scenarios, following the
    DataFlex pattern.
    
    Args:
        dataset: Dataset to select from
        accelerator: Accelerator for distributed training (optional)
        seed: Random seed for reproducibility
    """

    def __init__(
        self,
        dataset: Any,
        accelerator: Optional[Any] = None,
        seed: int = 42
    ):
        self.dataset = dataset
        self.accelerator = accelerator
        self.seed = seed
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

    def warmup(self, num_samples: int, replacement: bool = False) -> List[int]:
        """
        Warmup sampling with distributed support.
        
        Args:
            num_samples: Number of samples to warmup with
            replacement: Whether to sample with replacement
            
        Returns:
            List of sample indices
        """
        if self.is_main_process():
            dataset_size = len(self.dataset)
            if TORCH_AVAILABLE:
                generator = torch.Generator()
                generator.manual_seed(self.seed)
                
                if replacement:
                    indices = torch.randint(
                        0, dataset_size, (num_samples,), generator=generator
                    ).tolist()
                else:
                    if num_samples > dataset_size:
                        raise ValueError(
                            f"Cannot sample {num_samples} without replacement from {dataset_size} samples"
                        )
                    indices = torch.randperm(dataset_size, generator=generator)[:num_samples].tolist()
            else:
                # Fallback to random without torch
                import random
                random.seed(self.seed)
                if replacement:
                    indices = [random.randint(0, dataset_size - 1) for _ in range(num_samples)]
                else:
                    if num_samples > dataset_size:
                        raise ValueError(
                            f"Cannot sample {num_samples} without replacement from {dataset_size} samples"
                        )
                    indices = random.sample(range(dataset_size), num_samples)
        else:
            indices = None
        
        return self.broadcast_object(indices, src=0)

    @abstractmethod
    def select(self, model: Any, step_id: int, num_samples: int, **kwargs) -> List[int]:
        """
        Select samples from the dataset for the model in 'step_id'.
        
        Args:
            model: The model object used in the selection process
            step_id: The ID of the current training step or stage
            num_samples: The number of samples to select
            **kwargs: Additional keyword arguments for flexibility
            
        Returns:
            List of selected sample indices
        """
        pass

    def select_batch(self, model: Any, step_ids: List[int], num_samples_list: List[int], **kwargs) -> List[List[int]]:
        """
        Select samples for multiple steps.
        
        Args:
            model: The model object used in the selection process
            step_ids: List of step IDs
            num_samples_list: List of sample counts for each step
            **kwargs: Additional keyword arguments
            
        Returns:
            List of selected sample indices for each step
        """
        results = []
        for step_id, num_samples in zip(step_ids, num_samples_list):
            selected = self.select(model, step_id, num_samples, **kwargs)
            results.append(selected)
        return results
