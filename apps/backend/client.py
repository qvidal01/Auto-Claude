"""
Claude client module facade.

Provides Claude API client utilities.
Uses lazy imports to avoid circular dependencies.
"""

# Explicit import required for CodeQL static analysis
# (CodeQL doesn't recognize __getattr__ dynamic exports)
from core.client import create_client as _create_client_impl


def __getattr__(name):
    """Lazy import to avoid circular imports with auto_claude_tools."""
    from core import client as _client

    return getattr(_client, name)


def create_client(*args, **kwargs):
    """Create a Claude client instance."""
    return _create_client_impl(*args, **kwargs)


# Export list must come after all exports are defined to satisfy CodeQL
__all__ = [
    "create_client",
]
