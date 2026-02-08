"""
GitHub Orchestrator Services
============================

Service layer for GitHub automation workflows.

NOTE: Uses lazy imports to avoid circular dependency with context_gatherer.py.
The circular import chain was: orchestrator -> context_gatherer -> services.io_utils
-> services/__init__ -> pr_review_engine -> context_gatherer (circular!)

Module-level placeholders (with _ prefix) are defined for CodeQL static
analysis. The actual exported names (without _ prefix) trigger __getattr__
for lazy loading.
"""

from __future__ import annotations

from typing import Any

# Module-level placeholders (with _ prefix) for CodeQL static analysis.
_AutoFixProcessor: Any = None
_BatchProcessor: Any = None
_PRReviewEngine: Any = None
_PromptManager: Any = None
_ResponseParser: Any = None
_TriageEngine: Any = None

__all__ = [
    "PromptManager",
    "ResponseParser",
    "PRReviewEngine",
    "TriageEngine",
    "AutoFixProcessor",
    "BatchProcessor",
]


def __getattr__(name: str) -> object:
    """Lazy import handler - loads classes on first access."""
    if name == "AutoFixProcessor":
        from .autofix_processor import AutoFixProcessor

        return AutoFixProcessor
    elif name == "BatchProcessor":
        from .batch_processor import BatchProcessor

        return BatchProcessor
    elif name == "PRReviewEngine":
        from .pr_review_engine import PRReviewEngine

        return PRReviewEngine
    elif name == "PromptManager":
        from .prompt_manager import PromptManager

        return PromptManager
    elif name == "ResponseParser":
        from .response_parsers import ResponseParser

        return ResponseParser
    elif name == "TriageEngine":
        from .triage_engine import TriageEngine

        return TriageEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
