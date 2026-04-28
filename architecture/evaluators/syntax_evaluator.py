"""Syntax evaluator implementation."""

from architecture.base.base_evaluator import BaseEvaluator
from architecture.core.registry import register_evaluator
from typing import Dict, Any
import ast
import re


@register_evaluator("syntax")
class SyntaxEvaluator(BaseEvaluator):
    """
    Syntax evaluator for checking code syntax validity.
    
    Args:
        cache_dir: Directory for caching evaluation results
        check_imports: Whether to check import statements
        check_execution: Whether to attempt code execution
    """

    def __init__(
        self,
        cache_dir: str = "./cache/evaluator",
        check_imports: bool = True,
        check_execution: bool = False,
        **kwargs
    ):
        super().__init__(cache_dir, **kwargs)
        self.check_imports = check_imports
        self.check_execution = check_execution

    def evaluate(self, code: str, **kwargs) -> Dict[str, Any]:
        """Evaluate code syntax."""
        results = {
            "valid_syntax": False,
            "syntax_errors": [],
            "import_errors": [],
            "execution_errors": [],
            "score": 0.0
        }
        
        # Check syntax
        try:
            ast.parse(code)
            results["valid_syntax"] = True
            results["score"] += 0.5
        except SyntaxError as e:
            results["syntax_errors"].append({
                "line": e.lineno,
                "message": str(e),
                "offset": e.offset
            })
        
        # Check imports
        if self.check_imports and results["valid_syntax"]:
            import_errors = self._check_imports(code)
            if not import_errors:
                results["score"] += 0.3
            else:
                results["import_errors"] = import_errors
        
        # Check execution
        if self.check_execution and results["valid_syntax"]:
            execution_errors = self._check_execution(code)
            if not execution_errors:
                results["score"] += 0.2
            else:
                results["execution_errors"] = execution_errors
        
        return results

    def _check_imports(self, code: str) -> list:
        """Check if imports are valid."""
        errors = []
        
        # Extract import statements
        imports = re.findall(r'^import\s+.+$|^from\s+.+\s+import\s+.+$', code, re.MULTILINE)
        
        for imp in imports:
            try:
                # Try to execute just the import
                exec(imp, {})
            except ImportError as e:
                errors.append({
                    "import": imp,
                    "error": str(e)
                })
            except Exception as e:
                errors.append({
                    "import": imp,
                    "error": str(e)
                })
        
        return errors

    def _check_execution(self, code: str) -> list:
        """Check if code can be executed without errors."""
        errors = []
        
        try:
            # Create a safe execution environment
            safe_globals = {
                "__builtins__": {
                    "print": lambda *args: None,
                    "len": len,
                    "range": range,
                    "list": list,
                    "dict": dict,
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                }
            }
            
            # Try to execute the code
            exec(code, safe_globals)
            
        except Exception as e:
            errors.append({
                "type": type(e).__name__,
                "message": str(e)
            })
        
        return errors
