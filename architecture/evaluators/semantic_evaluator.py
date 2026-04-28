"""Semantic evaluator implementation."""

from architecture.base.base_evaluator import BaseEvaluator
from architecture.core.registry import register_evaluator
from typing import Dict, Any, List
import re


@register_evaluator("semantic")
class SemanticEvaluator(BaseEvaluator):
    """
    Semantic evaluator for checking code quality and meaningfulness.
    
    Args:
        cache_dir: Directory for caching evaluation results
        similarity_threshold: Threshold for semantic similarity
        check_docstrings: Whether to check for docstrings
        check_comments: Whether to check for comments
    """

    def __init__(
        self,
        cache_dir: str = "./cache/evaluator",
        similarity_threshold: float = 0.8,
        check_docstrings: bool = True,
        check_comments: bool = True,
        **kwargs
    ):
        super().__init__(cache_dir, **kwargs)
        self.similarity_threshold = similarity_threshold
        self.check_docstrings = check_docstrings
        self.check_comments = check_comments

    def evaluate(self, code: str, **kwargs) -> Dict[str, Any]:
        """Evaluate code semantics."""
        results = {
            "has_docstrings": False,
            "has_comments": False,
            "function_count": 0,
            "class_count": 0,
            "line_count": 0,
            "docstring_coverage": 0.0,
            "comment_coverage": 0.0,
            "score": 0.0
        }
        
        # Count lines
        lines = code.split('\n')
        results["line_count"] = len(lines)
        
        # Count functions and classes
        results["function_count"] = len(re.findall(r'def\s+\w+', code))
        results["class_count"] = len(re.findall(r'class\s+\w+', code))
        
        # Check for docstrings
        if self.check_docstrings:
            docstring_coverage = self._check_docstrings(code)
            results["docstring_coverage"] = docstring_coverage
            results["has_docstrings"] = docstring_coverage > 0
            results["score"] += docstring_coverage * 0.4
        
        # Check for comments
        if self.check_comments:
            comment_coverage = self._check_comments(code)
            results["comment_coverage"] = comment_coverage
            results["has_comments"] = comment_coverage > 0
            results["score"] += comment_coverage * 0.3
        
        # Score based on structure
        if results["function_count"] > 0:
            results["score"] += 0.2
        if results["class_count"] > 0:
            results["score"] += 0.1
        
        return results

    def _check_docstrings(self, code: str) -> float:
        """Check docstring coverage."""
        # Count functions with docstrings
        functions = re.findall(r'def\s+(\w+)\s*\([^)]*\)\s*:\s*"""([^"]*)"""', code, re.DOTALL)
        
        if not functions:
            return 0.0
        
        functions_with_docstrings = len(functions)
        total_functions = len(re.findall(r'def\s+\w+', code))
        
        if total_functions == 0:
            return 0.0
        
        return functions_with_docstrings / total_functions

    def _check_comments(self, code: str) -> float:
        """Check comment coverage."""
        # Count comment lines
        comment_lines = 0
        code_lines = 0
        
        for line in code.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                code_lines += 1
            elif line.startswith('#'):
                comment_lines += 1
        
        if code_lines == 0:
            return 0.0
        
        return min(comment_lines / code_lines, 1.0)

    def compare_with_reference(self, code: str, reference: str) -> float:
        """Compare code with reference implementation."""
        # Simple token-based similarity
        code_tokens = set(re.findall(r'\w+', code.lower()))
        ref_tokens = set(re.findall(r'\w+', reference.lower()))
        
        if not code_tokens or not ref_tokens:
            return 0.0
        
        intersection = code_tokens & ref_tokens
        union = code_tokens | ref_tokens
        
        return len(intersection) / len(union)
