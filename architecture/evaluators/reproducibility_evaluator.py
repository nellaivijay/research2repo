"""Reproducibility evaluator implementation."""

from architecture.base.base_evaluator import BaseEvaluator
from architecture.core.registry import register_evaluator
from typing import Dict, Any, List
import re


@register_evaluator("reproducibility")
class ReproducibilityEvaluator(BaseEvaluator):
    """
    Reproducibility evaluator for checking code reproducibility.
    
    Args:
        cache_dir: Directory for caching evaluation results
        check_dependencies: Whether to check for dependencies
        check_data_availability: Whether to check for data availability
        check_random_seeds: Whether to check for random seed setting
    """

    def __init__(
        self,
        cache_dir: str = "./cache/evaluator",
        check_dependencies: bool = True,
        check_data_availability: bool = True,
        check_random_seeds: bool = True,
        **kwargs
    ):
        super().__init__(cache_dir, **kwargs)
        self.check_dependencies = check_dependencies
        self.check_data_availability = check_data_availability
        self.check_random_seeds = check_random_seeds

    def evaluate(self, code: str, **kwargs) -> Dict[str, Any]:
        """Evaluate code reproducibility."""
        results = {
            "has_requirements": False,
            "has_data_loading": False,
            "has_random_seeds": False,
            "has_version_info": False,
            "has_config_files": False,
            "score": 0.0
        }
        
        # Check for requirements.txt or dependencies
        if self.check_dependencies:
            has_requirements = self._check_dependencies(code)
            results["has_requirements"] = has_requirements
            if has_requirements:
                results["score"] += 0.3
        
        # Check for data loading
        if self.check_data_availability:
            has_data_loading = self._check_data_loading(code)
            results["has_data_loading"] = has_data_loading
            if has_data_loading:
                results["score"] += 0.2
        
        # Check for random seeds
        if self.check_random_seeds:
            has_seeds = self._check_random_seeds(code)
            results["has_random_seeds"] = has_seeds
            if has_seeds:
                results["score"] += 0.2
        
        # Check for version info
        has_version = self._check_version_info(code)
        results["has_version_info"] = has_version
        if has_version:
            results["score"] += 0.2
        
        # Check for config files
        has_config = self._check_config_files(code)
        results["has_config_files"] = has_config
        if has_config:
            results["score"] += 0.1
        
        return results

    def _check_dependencies(self, code: str) -> bool:
        """Check if code specifies dependencies."""
        # Check for common dependency indicators
        patterns = [
            r'import\s+requirements',
            r'from\s+requirements',
            r'pip\s+install',
            r'conda\s+install',
            r'environment\.yml',
            r'setup\.py',
            r'pyproject\.toml'
        ]
        
        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return True
        
        return False

    def _check_data_loading(self, code: str) -> bool:
        """Check if code has data loading."""
        patterns = [
            r'\.load\(',
            r'\.read\(',
            r'pd\.read_',
            r'np\.load',
            r'torch\.load',
            r'tf\.load',
            r'open\(',
            r'with\s+open'
        ]
        
        for pattern in patterns:
            if re.search(pattern, code):
                return True
        
        return False

    def _check_random_seeds(self, code: str) -> bool:
        """Check if code sets random seeds."""
        patterns = [
            r'np\.random\.seed',
            r'torch\.manual_seed',
            r'random\.seed',
            r'tf\.random\.set_seed'
        ]
        
        for pattern in patterns:
            if re.search(pattern, code):
                return True
        
        return False

    def _check_version_info(self, code: str) -> bool:
        """Check if code includes version information."""
        patterns = [
            r'__version__',
            r'VERSION\s*=',
            r'version\s*=',
            r'print\(__version__\)',
            r'print\(version\)'
        ]
        
        for pattern in patterns:
            if re.search(pattern, code):
                return True
        
        return False

    def _check_config_files(self, code: str) -> bool:
        """Check if code uses configuration files."""
        patterns = [
            r'\.yaml',
            r'\.yml',
            r'\.json',
            r'\.toml',
            r'\.cfg',
            r'\.ini',
            r'config\.load',
            r'load_config'
        ]
        
        for pattern in patterns:
            if re.search(pattern, code):
                return True
        
        return False
