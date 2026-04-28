"""Importance selector implementation."""

from architecture.base.base_selector import BaseSelector
from architecture.core.registry import register_selector
from typing import List, Any, Dict

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

import numpy as np


@register_selector("importance")
class ImportanceSelector(BaseSelector):
    """
    Importance-based data selector following DataFlex pattern.
    
    Selects samples based on importance scores (e.g., gradient-based, loss-based).
    
    Args:
        dataset: Dataset to select from
        accelerator: Accelerator for distributed training (optional)
        seed: Random seed for reproducibility
        strategy: Strategy for computing importance (gradient, loss, entropy)
        cache_dir: Directory for caching importance scores
    """

    def __init__(
        self,
        dataset: Any,
        accelerator: Any = None,
        seed: int = 42,
        strategy: str = "gradient",
        cache_dir: str = "./cache/importance",
        **kwargs
    ):
        super().__init__(dataset, accelerator, seed)
        self.strategy = strategy
        self.cache_dir = cache_dir
        self.importance_cache = {}

    def select(self, model: Any, step_id: int, num_samples: int, **kwargs) -> List[int]:
        """
        Select samples based on importance scores.
        
        Args:
            model: The model object used for computing importance
            step_id: The ID of the current training step
            num_samples: The number of samples to select
            **kwargs: Additional keyword arguments
            
        Returns:
            List of selected sample indices
        """
        dataset_size = len(self.dataset)
        
        if self.is_main_process():
            # Compute importance scores
            importance_scores = self._compute_importance(model, step_id, dataset_size, **kwargs)
            
            # Select top-k samples
            if TORCH_AVAILABLE:
                top_k_indices = torch.topk(
                    torch.tensor(importance_scores),
                    min(num_samples, len(importance_scores))
                ).indices.tolist()
            else:
                # Fallback to numpy
                top_k_indices = np.argsort(importance_scores)[-min(num_samples, len(importance_scores)):][::-1].tolist()
            
            selected_indices = top_k_indices
        else:
            selected_indices = None
        
        return self.broadcast_object(selected_indices, src=0)

    def _compute_importance(self, model: Any, step_id: int, dataset_size: int, **kwargs) -> List[float]:
        """
        Compute importance scores for all samples.
        
        Args:
            model: The model object
            step_id: The current step ID
            dataset_size: Size of the dataset
            **kwargs: Additional parameters
            
        Returns:
            List of importance scores
        """
        # Check cache
        cache_key = f"{step_id}_{dataset_size}"
        if cache_key in self.importance_cache:
            return self.importance_cache[cache_key]
        
        # Compute importance based on strategy
        if self.strategy == "gradient":
            scores = self._gradient_importance(model, dataset_size, **kwargs)
        elif self.strategy == "loss":
            scores = self._loss_importance(model, dataset_size, **kwargs)
        elif self.strategy == "entropy":
            scores = self._entropy_importance(model, dataset_size, **kwargs)
        else:
            # Default: random scores
            scores = np.random.rand(dataset_size).tolist()
        
        # Cache results
        self.importance_cache[cache_key] = scores
        
        return scores

    def _gradient_importance(self, model: Any, dataset_size: int, **kwargs) -> List[float]:
        """Compute gradient-based importance."""
        # Placeholder: In a real implementation, this would compute
        # gradient norms for each sample
        return np.random.rand(dataset_size).tolist()

    def _loss_importance(self, model: Any, dataset_size: int, **kwargs) -> List[float]:
        """Compute loss-based importance."""
        # Placeholder: In a real implementation, this would compute
        # loss values for each sample
        return np.random.rand(dataset_size).tolist()

    def _entropy_importance(self, model: Any, dataset_size: int, **kwargs) -> List[float]:
        """Compute entropy-based importance."""
        # Placeholder: In a real implementation, this would compute
        # entropy of predictions for each sample
        return np.random.rand(dataset_size).tolist()
