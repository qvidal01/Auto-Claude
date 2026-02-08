"""
Spec Creation Pipeline Orchestrator
====================================

Main orchestration logic for spec creation with dynamic complexity adaptation.

This module has been refactored into smaller components:
- pipeline/models.py: Data structures and utility functions
- pipeline/agent_runner.py: Agent execution logic
- pipeline/orchestrator.py: Main SpecOrchestrator class

Import from the pipeline subpackage for the main classes.
"""

# Re-export main classes and functions from the pipeline subpackage
from .pipeline.models import get_specs_dir
from .pipeline.orchestrator import SpecOrchestrator

__all__ = [
    "SpecOrchestrator",
    "get_specs_dir",
]
