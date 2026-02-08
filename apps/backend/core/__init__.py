"""
Core Framework Module
=====================

Core components for the Auto Claude autonomous coding framework.

Note: We use lazy imports here because the full agent module has many dependencies
that may not be needed for basic operations.
"""

from typing import Any

# Module-level placeholders (with _ prefix) for CodeQL static analysis.
# The actual exported names (without _ prefix) trigger __getattr__ for lazy loading.
_run_autonomous_agent: Any = None
_run_followup_planner: Any = None
_WorktreeManager: Any = None

__all__ = [
    "run_autonomous_agent",
    "run_followup_planner",
    "WorktreeManager",
]


def __getattr__(name: str) -> Any:
    """Lazy imports to avoid circular dependencies and heavy imports."""
    if name == "run_autonomous_agent":
        from .agent import run_autonomous_agent

        return run_autonomous_agent
    elif name == "run_followup_planner":
        from .agent import run_followup_planner

        return run_followup_planner
    elif name == "WorktreeManager":
        from .worktree import WorktreeManager

        return WorktreeManager
    elif name in ("create_claude_client", "ClaudeClient"):
        from . import client as _client

        return getattr(_client, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
