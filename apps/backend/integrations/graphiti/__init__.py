"""
Graphiti Integration
====================

Integration with Graphiti knowledge graph for semantic memory.

Module-level placeholders (with _ prefix) are defined for CodeQL static
analysis. The actual exported names (without _ prefix) trigger __getattr__
for lazy loading.
"""

from typing import Any

# Config imports don't require graphiti package
from .config import GraphitiConfig, validate_graphiti_config

# Module-level placeholders (with _ prefix) for CodeQL static analysis.
_GraphitiMemory: Any = None
_create_llm_client: Any = None
_create_embedder: Any = None

__all__ = [
    "GraphitiConfig",
    "validate_graphiti_config",
    "GraphitiMemory",
    "create_llm_client",
    "create_embedder",
]


def __getattr__(name: str) -> Any:
    """Lazy import to avoid requiring graphiti package for config-only imports."""
    if name == "GraphitiMemory":
        from .memory import GraphitiMemory

        return GraphitiMemory
    elif name == "create_llm_client":
        from .providers import create_llm_client

        return create_llm_client
    elif name == "create_embedder":
        from .providers import create_embedder

        return create_embedder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
