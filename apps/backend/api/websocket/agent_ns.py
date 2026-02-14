"""
Agent WebSocket Namespace
=========================

Socket.IO ``/agent`` namespace for real-time agent execution control.

Events (client → server):
    agent:start  — Start an agent build for a task
    agent:stop   — Stop a running agent
    agent:join   — Join a task room for progress updates
    agent:leave  — Leave a task room

Events (server → client):
    agent:progress — Phase / subtask progress updates
    agent:log      — Execution log lines
    agent:complete — Task finished successfully
    agent:error    — Task failed
"""

from __future__ import annotations

import logging
from typing import Any

import socketio

from ..services.agent_runner import AgentRunner

logger = logging.getLogger(__name__)

# Singleton runner — initialised by register_agent_namespace()
_agent_runner: AgentRunner | None = None


def get_agent_runner() -> AgentRunner:
    """Return the global AgentRunner instance."""
    if _agent_runner is None:
        raise RuntimeError(
            "AgentRunner not initialised — call register_agent_namespace first"
        )
    return _agent_runner


class AgentNamespace(socketio.AsyncNamespace):
    """Socket.IO namespace for /agent."""

    def __init__(self, runner: AgentRunner) -> None:
        super().__init__("/agent")
        self.runner = runner

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def on_connect(self, sid: str, environ: dict[str, Any]) -> None:
        logger.info("[AgentNS] Client connected: %s", sid)

    async def on_disconnect(self, sid: str) -> None:
        logger.info("[AgentNS] Client disconnected: %s", sid)

    # ------------------------------------------------------------------
    # Room management
    # ------------------------------------------------------------------

    async def on_agent_join(self, sid: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Join a task room to receive progress updates.

        Expected *data*::

            {"taskId": str}
        """
        task_id: str = data.get("taskId", "")
        if not task_id:
            return {"ok": False, "error": "taskId is required"}

        self.enter_room(sid, task_id)
        logger.info("[AgentNS] Client %s joined room %s", sid, task_id)
        return {"ok": True, "taskId": task_id}

    async def on_agent_leave(self, sid: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Leave a task room.

        Expected *data*::

            {"taskId": str}
        """
        task_id: str = data.get("taskId", "")
        if not task_id:
            return {"ok": False, "error": "taskId is required"}

        self.leave_room(sid, task_id)
        logger.info("[AgentNS] Client %s left room %s", sid, task_id)
        return {"ok": True, "taskId": task_id}

    # ------------------------------------------------------------------
    # Agent control
    # ------------------------------------------------------------------

    async def on_agent_start(self, sid: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Start an agent build for a task.

        Expected *data*::

            {
                "taskId": str,
                "projectDir": str,
                "specDir": str,
                "model": str | None,
                "skipQa": bool | None,
            }
        """
        task_id: str = data.get("taskId", "")
        project_dir: str = data.get("projectDir", "")
        spec_dir: str = data.get("specDir", "")

        if not task_id or not project_dir or not spec_dir:
            error = "taskId, projectDir, and specDir are required"
            await self.emit("agent:error", {"taskId": task_id, "error": error}, to=sid)
            return {"ok": False, "error": error}

        if self.runner.is_running(task_id):
            return {"ok": False, "error": "Task is already running"}

        # Auto-join the room so the caller receives events
        self.enter_room(sid, task_id)

        await self.runner.start(
            task_id,
            project_dir,
            spec_dir,
            model=data.get("model", "sonnet"),
            skip_qa=bool(data.get("skipQa", False)),
        )

        logger.info("[AgentNS] Agent started for task %s by %s", task_id, sid)
        return {"ok": True, "taskId": task_id}

    async def on_agent_stop(self, sid: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Stop a running agent.

        Expected *data*::

            {"taskId": str}
        """
        task_id: str = data.get("taskId", "")
        if not task_id:
            return {"ok": False, "error": "taskId is required"}

        cancelled = await self.runner.stop(task_id)
        if cancelled:
            logger.info("[AgentNS] Agent stopped for task %s by %s", task_id, sid)
            return {"ok": True, "taskId": task_id}

        return {"ok": False, "error": "Task is not running"}


def register_agent_namespace(sio_server: socketio.AsyncServer) -> None:
    """Register the /agent namespace on the given Socket.IO server."""
    global _agent_runner
    _agent_runner = AgentRunner(sio_server)
    sio_server.register_namespace(AgentNamespace(_agent_runner))
    logger.info("[AgentNS] Registered /agent namespace")
