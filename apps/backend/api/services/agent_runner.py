"""
Agent Runner Service
====================

Wraps the existing CLI build pipeline to run agents as background asyncio
tasks, emitting progress events via Socket.IO.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import socketio

logger = logging.getLogger(__name__)


class AgentRunner:
    """Manages background agent executions and emits Socket.IO events."""

    def __init__(self, sio: socketio.AsyncServer) -> None:
        self.sio = sio
        self._tasks: dict[str, asyncio.Task[None]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(
        self,
        task_id: str,
        project_dir: str,
        spec_dir: str,
        *,
        model: str = "sonnet",
        skip_qa: bool = False,
        auto_continue: bool = True,
    ) -> None:
        """Start an agent build for *task_id* in the background."""
        if task_id in self._tasks and not self._tasks[task_id].done():
            logger.warning("[AgentRunner] Task %s is already running", task_id)
            return

        self._tasks[task_id] = asyncio.create_task(
            self._run(
                task_id,
                project_dir,
                spec_dir,
                model=model,
                skip_qa=skip_qa,
                auto_continue=auto_continue,
            )
        )
        logger.info("[AgentRunner] Started background task %s", task_id)

    async def stop(self, task_id: str) -> bool:
        """Cancel a running agent task. Returns *True* if cancelled."""
        task = self._tasks.get(task_id)
        if task is None or task.done():
            return False

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        self._tasks.pop(task_id, None)
        logger.info("[AgentRunner] Stopped task %s", task_id)
        return True

    def is_running(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        return task is not None and not task.done()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _emit(self, event: str, task_id: str, data: dict[str, Any]) -> None:
        """Emit a Socket.IO event to the task room."""
        payload = {"taskId": task_id, **data}
        await self.sio.emit(event, payload, namespace="/agent", room=task_id)

    async def _run(
        self,
        task_id: str,
        project_dir: str,
        spec_dir: str,
        *,
        model: str,
        skip_qa: bool,
        auto_continue: bool,
    ) -> None:
        """Execute the build pipeline, streaming progress via Socket.IO."""
        try:
            await self._emit(
                "agent:progress",
                task_id,
                {
                    "phase": "planning",
                    "message": "Starting agent build…",
                },
            )

            project_path = Path(project_dir)
            spec_path = Path(spec_dir)

            # Run the synchronous build command in a thread so we don't
            # block the event loop.  We import lazily to keep module
            # loading lightweight and avoid circular imports.
            from cli.build_commands import handle_build_command

            await self._emit(
                "agent:log",
                task_id,
                {
                    "line": f"Running build for spec {spec_path.name}",
                },
            )

            await asyncio.to_thread(
                handle_build_command,
                project_dir=project_path,
                spec_dir=spec_path,
                model=model,
                max_iterations=None,
                verbose=False,
                force_isolated=True,
                force_direct=False,
                auto_continue=auto_continue,
                skip_qa=skip_qa,
                force_bypass_approval=True,
            )

            await self._emit(
                "agent:progress",
                task_id,
                {
                    "phase": "complete",
                    "message": "Build completed successfully",
                },
            )
            await self._emit(
                "agent:complete",
                task_id,
                {
                    "message": "Build completed successfully",
                },
            )

        except asyncio.CancelledError:
            await self._emit(
                "agent:error",
                task_id,
                {
                    "error": "Agent was cancelled",
                },
            )
            raise

        except Exception as exc:
            logger.exception("[AgentRunner] Task %s failed", task_id)
            await self._emit(
                "agent:error",
                task_id,
                {
                    "error": str(exc),
                },
            )

        finally:
            self._tasks.pop(task_id, None)
