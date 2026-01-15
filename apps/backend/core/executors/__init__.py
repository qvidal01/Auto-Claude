"""Executor implementations for methodology task execution.

This module provides executors that orchestrate the execution of methodology phases.

Available Executors:
- FullAutoExecutor: Executes all phases without user intervention

Available Types:
- TaskResult: Result dataclass for task execution outcome
- TaskState: Enum for task state lifecycle values

TaskState Lifecycle:
    CREATED -> PLANNING -> PLANNING_COMPLETE -> CODING -> CODING_COMPLETE
            -> VALIDATION -> VALIDATION_COMPLETE -> COMPLETED
    Any state can transition to FAILED or ESCALATED on error.

Story Reference: Epic 4 - Full Auto Execution Pipeline
Story Reference: Story 4.2 - Implement Planning Phase Execution
"""

from .full_auto import FullAutoExecutor, TaskResult, TaskState

__all__ = ["FullAutoExecutor", "TaskResult", "TaskState"]
