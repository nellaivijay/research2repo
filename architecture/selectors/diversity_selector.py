"""Diversity selector implementation."""

from architecture.base.base_selector import BaseSelector
from architecture.core.registry import register_selector
from typing import List, Any
import numpy as np

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@register_selector("diversity")
class DiversitySelector(BaseSelector):
    """
    Diversity-based data selector following DataFlex pattern.
    
    Selects diverse samples using clustering or other diversity metrics.
    
    Args:
        dataset: Dataset to select from
        accelerator: Accelerator for distributed training (optional)
        seed: Random seed for reproducibility
        strategy: Strategy for diversity (clustering, coverage, kmeans)
        n_clusters: Number of clusters for clustering-based selection
    """

    def __init__(
        self,
        dataset: Any,
        accelerator: Any = None,
        seed: int = 42,
        strategy: str = "clustering",
        n_clusters: int = 5,
        **kwargs
    ):
        super().__init__(dataset, accelerator, seed)
        self.strategy = strategy
        self.n_clusters = n_clusters

    def select(self, model: Any, step_id: int, num_samples: int, **kwargs) -> List[int]:
        """
        Select diverse samples from the dataset.
        
        Args:
            model: The model object (used for embeddings if available)
            step_id: The ID of the current training step
            num_samples: The number of samples to select
            **kwargs: Additional keyword arguments
            
        Returns:
            List of selected sample indices
        """
        dataset_size = len(self.dataset)
        
        if self.is_main_process():
            # Compute diversity-based selection
            if self.strategy == "clustering":
                selected_indices = self._clustering_selection(model, step_id, num_samples, dataset_size, **kwargs)
            elif self.strategy == "coverage":
                selected_indices = self._coverage_selection(model, step_id, num_samples, dataset_size, **kwargs)
            elif self.strategy == "kmeans":
                selected_indices = self._kmeans_selection(model, step_id, num_samples, dataset_size, **kwargs)
            else:
                # Default: random selection
                if TORCH_AVAILABLE:
                    generator = torch.Generator()
                    generator.manual_seed(self.seed + int(step_id))
                    selected_indices = torch.randperm(dataset_size, generator=generator)[:num_samples].tolist()
                else:
                    # Fallback to random without torch
                    import random
                    random.seed(self.seed + int(step_id))
                    selected_indices = random.sample(range(dataset_size), num_samples)
        else:
            selected_indices = None
        
        return self.broadcast_object(selected_indices, src=0)

    def _clustering_selection(self, model: Any, step_id: int, num_samples: int, dataset_size: int, **kwargs) -> List[int]:
        """Select samples using clustering."""
        # Placeholder: In a real implementation, this would:
        # 1. Extract embeddings for all samples
        # 2. Cluster the embeddings
        # 3. Select samples from each cluster
        
        # For now, return random selection
        if TORCH_AVAILABLE:
            generator = torch.Generator()
            generator.manual_seed(self.seed + int(step_id))
            return torch.randperm(dataset_size, generator=generator)[:num_samples].tolist()
        else:
            # Fallback to random without torch
            import random
            random.seed(self.seed + int(step_id))
            return random.sample(range(dataset_size), num_samples)

    def _coverage_selection(self, model: Any, step_id: int, num_samples: int, dataset_size: int, **kwargs) -> List[int]:
        """Select samples for maximum coverage."""
        # Placeholder: In a real implementation, this would select
        # samples that maximize coverage of the feature space
        
        # For now, return random selection
        if TORCH_AVAILABLE:
            generator = torch.Generator()
            generator.manual_seed(self.seed + int(step_id))
            return torch.randperm(dataset_size, generator=generator)[:num_samples].tolist()
        else:
            # Fallback to random without torch
            import random
            random.seed(self.seed + int(step_id))
            return random.sample(range(dataset_size), num_samples)

    def _kmeans_selection(self, model: Any, step_id: int, num_samples: int, dataset_size: int, **kwargs) -> List[int]:
        """Select samples using K-means clustering."""
        # Placeholder: In a real implementation, this would:
        # 1. Extract embeddings
        # 2. Run K-means clustering
        # 3. Select samples closest to cluster centers
        
        # For now, return random selection
        if TORCH_AVAILABLE:
            generator = torch.Generator()
            generator.manual_seed(self.seed + int(step_id))
            return torch.randperm(dataset_size, generator=generator)[:num_samples].tolist()
        else:
            # Fallback to random without torch
            import random
            random.seed(self.seed + int(step_id))
            return random.sample(range(dataset_size), num_samples)
