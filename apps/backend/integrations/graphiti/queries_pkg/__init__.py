"""
Graphiti Memory System - Modular Architecture

This package provides a clean separation of concerns for Graphiti memory:
- graphiti.py: Main facade and coordination
- client.py: Database connection management
- queries.py: Episode storage operations
- search.py: Semantic search and retrieval
- schema.py: Data structures and constants

Public API exports maintain backward compatibility with the original
graphiti_memory.py module.
"""

from .graphiti import GraphitiMemory
from .schema import (
    EPISODE_TYPE_CODEBASE_DISCOVERY,
    EPISODE_TYPE_GOTCHA,
    EPISODE_TYPE_HISTORICAL_CONTEXT,
    EPISODE_TYPE_PATTERN,
    EPISODE_TYPE_QA_RESULT,
    EPISODE_TYPE_SESSION_INSIGHT,
    EPISODE_TYPE_TASK_OUTCOME,
    MAX_CONTEXT_RESULTS,
    GroupIdMode,
)

# Import kuzu_driver_patched for test mocking support
# This module is used internally but needs to be accessible for patching
try:
    from . import kuzu_driver_patched  # noqa: F401
except ImportError:
    # kuzu_driver_patched may not be available if real_ladybug is not installed
    kuzu_driver_patched = None  # type: ignore

# Re-export for convenience
__all__ = [
    "GraphitiMemory",
    "GroupIdMode",
    "MAX_CONTEXT_RESULTS",
    "EPISODE_TYPE_SESSION_INSIGHT",
    "EPISODE_TYPE_CODEBASE_DISCOVERY",
    "EPISODE_TYPE_PATTERN",
    "EPISODE_TYPE_GOTCHA",
    "EPISODE_TYPE_TASK_OUTCOME",
    "EPISODE_TYPE_QA_RESULT",
    "EPISODE_TYPE_HISTORICAL_CONTEXT",
]
