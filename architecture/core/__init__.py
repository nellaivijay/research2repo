"""Core infrastructure for Research2Repo."""

from architecture.core.registry import (
    Registry,
    REGISTRY,
    register_processor,
    register_provider,
    register_selector,
    register_generator,
    register_evaluator,
)

__all__ = [
    "Registry",
    "REGISTRY",
    "register_processor",
    "register_provider",
    "register_selector",
    "register_generator",
    "register_evaluator",
]
