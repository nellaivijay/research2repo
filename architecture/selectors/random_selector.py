"""Random selector implementation."""

from architecture.base.base_selector import BaseSelector
from architecture.core.registry import register_selector
from typing import List, Any

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@register_selector("random")
class RandomSelector(BaseSelector):
    """
    Random data selector following DataFlex pattern.
    
    Args:
        dataset: Dataset to select from
        accelerator: Accelerator for distributed training (optional)
        seed: Random seed for reproducibility
        replacement: Whether to sample with replacement
    """

    def __init__(
        self,
        dataset: Any,
        accelerator: Any = None,
        seed: int = 42,
        replacement: bool = False,
        **kwargs
    ):
        super().__init__(dataset, accelerator, seed)
        self.replacement = replacement

    def select(self, model: Any, step_id: int, num_samples: int, **kwargs) -> List[int]:
        """
        Randomly select samples from the dataset.
        
        Args:
            model: The model object (not used in random selection)
            step_id: The ID of the current training step
            num_samples: The number of samples to select
            **kwargs: Additional keyword arguments
            
        Returns:
            List of selected sample indices
        """
        if self.is_main_process():
            dataset_size = len(self.dataset)
            if TORCH_AVAILABLE:
                generator = torch.Generator()
                generator.manual_seed(self.seed + int(step_id))
                
                if self.replacement:
                    selected_indices = torch.randint(
                        0, dataset_size, (num_samples,), generator=generator
                    ).tolist()
                else:
                    if num_samples > dataset_size:
                        raise ValueError(
                            f"Cannot sample {num_samples} without replacement from {dataset_size} samples"
                        )
                    selected_indices = torch.randperm(dataset_size, generator=generator)[:num_samples].tolist()
            else:
                # Fallback to random without torch
                import random
                random.seed(self.seed + int(step_id))
                if self.replacement:
                    selected_indices = [random.randint(0, dataset_size - 1) for _ in range(num_samples)]
                else:
                    if num_samples > dataset_size:
                        raise ValueError(
                            f"Cannot sample {num_samples} without replacement from {dataset_size} samples"
                        )
                    selected_indices = random.sample(range(dataset_size), num_samples)
        else:
            selected_indices = None
        
        return self.broadcast_object(selected_indices, src=0)
