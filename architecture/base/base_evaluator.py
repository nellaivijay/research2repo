"""Base evaluator class with distributed support."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

try:
    import torch
    import torch.distributed as dist
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class BaseEvaluator(ABC):
    """
    Abstract base class for code evaluators with distributed support.
    
    This class provides a consistent interface for code evaluation with
    built-in support for distributed training scenarios.
    
    Args:
        cache_dir: Directory for caching evaluation results
        accelerator: Accelerator for distributed training (optional)
    """

    def __init__(
        self,
        cache_dir: str = "./cache/evaluator",
        accelerator: Optional[Any] = None
    ):
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
    def evaluate(self, code: str, **kwargs) -> Dict[str, Any]:
        """
        Evaluate generated code.
        
        Args:
            code: Generated code to evaluate
            **kwargs: Additional evaluation parameters
            
        Returns:
            Dictionary containing evaluation results
        """
        pass

    def evaluate_batch(self, codes: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Evaluate multiple code snippets.
        
        Args:
            codes: List of code snippets to evaluate
            **kwargs: Additional evaluation parameters
            
        Returns:
            List of evaluation results
        """
        # Default implementation: sequential evaluation
        results = []
        for code in codes:
            result = self.evaluate(code, **kwargs)
            results.append(result)
        return results

    def aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate evaluation results from multiple processes.
        
        Args:
            results: List of evaluation results
            
        Returns:
            Aggregated results
        """
        # Default implementation: average numeric values
        aggregated = {}
        if not results:
            return aggregated
        
        for key in results[0].keys():
            if isinstance(results[0][key], (int, float)):
                values = [r[key] for r in results if key in r]
                if values:
                    aggregated[key] = sum(values) / len(values)
            else:
                aggregated[key] = results[0][key]
        
        return aggregated
