"""Universal registry system for Research2Repo components."""

import inspect
from typing import Dict, Type, Any, Optional


class Registry:
    """
    Universal registry for registering and building components.
    
    Supports registration of algorithms, processors, providers, and other
    extensible components with configuration-driven instantiation.
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Type]] = {}

    def register(self, kind: str, name: str):
        """
        Decorator for registering a component class.
        
        Args:
            kind: Component type (e.g., 'processor', 'provider', 'selector')
            name: Unique name for the component
            
        Returns:
            Decorator function that registers the class
        """
        def deco(cls: Type):
            self._store.setdefault(kind, {})
            if name in self._store[kind]:
                raise ValueError(f"{kind}.{name} already registered")
            self._store[kind][name] = cls
            return cls
        return deco

    def get(self, kind: str, name: str) -> Type:
        """
        Get a registered component class.
        
        Args:
            kind: Component type
            name: Component name
            
        Returns:
            Registered component class
        """
        return self._store[kind][name]

    def build(self, kind: str, name: str, *, runtime: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None):
        """
        Build a component instance with merged configuration.
        
        Runtime configuration takes precedence over static configuration.
        Only parameters accepted by the component's __init__ are passed.
        
        Args:
            kind: Component type
            name: Component name
            runtime: Runtime configuration (overrides cfg)
            cfg: Static configuration from components.yaml
            
        Returns:
            Instantiated component
        """
        cls = self.get(kind, name)
        cfg = cfg or {}
        merged = {**cfg, **runtime}  # Runtime config takes precedence
        
        # Filter to only include parameters accepted by the constructor
        sig = inspect.signature(cls.__init__)
        accepted = {p.name for p in list(sig.parameters.values())[1:]}  # Skip self
        filtered = {k: v for k, v in merged.items() if k in accepted}
        
        return cls(**filtered)

    def list_kinds(self) -> Dict[str, list]:
        """
        List all registered component types and their names.
        
        Returns:
            Dictionary mapping kinds to lists of component names
        """
        return {kind: list(components.keys()) for kind, components in self._store.items()}

    def has(self, kind: str, name: str) -> bool:
        """
        Check if a component is registered.
        
        Args:
            kind: Component type
            name: Component name
            
        Returns:
            True if component is registered, False otherwise
        """
        return kind in self._store and name in self._store[kind]


# Global registry instance
REGISTRY = Registry()


# Convenience decorators for common component types
def register_processor(name: str):
    """Register a paper processor."""
    return REGISTRY.register("processor", name)


def register_provider(name: str):
    """Register an LLM provider."""
    return REGISTRY.register("provider", name)


def register_selector(name: str):
    """Register a data selector."""
    return REGISTRY.register("selector", name)


def register_generator(name: str):
    """Register a code generator."""
    return REGISTRY.register("generator", name)


def register_evaluator(name: str):
    """Register an evaluation metric."""
    return REGISTRY.register("evaluator", name)
