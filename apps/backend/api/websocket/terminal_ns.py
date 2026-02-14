"""
Terminal WebSocket Namespace
============================

Socket.IO ``/terminal`` namespace handling real-time terminal I/O.

Events (client → server):
    terminal:create  — Create a new PTY session
    terminal:input   — Write data to a PTY
    terminal:resize  — Resize a PTY window
    terminal:close   — Kill a PTY session

Events (server → client):
    terminal:output  — PTY output data
    terminal:exit    — PTY process exited
    terminal:error   — Error notification
"""

from __future__ import annotations

import logging
from typing import Any

import socketio

from ..services.terminal_service import TerminalService

logger = logging.getLogger(__name__)

# Singleton terminal service shared across all connections
_terminal_service = TerminalService()


def get_terminal_service() -> TerminalService:
    """Return the global TerminalService instance."""
    return _terminal_service


class TerminalNamespace(socketio.AsyncNamespace):
    """Socket.IO namespace for /terminal."""

    def __init__(self) -> None:
        super().__init__("/terminal")
        self.service = _terminal_service

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def on_connect(self, sid: str, environ: dict[str, Any]) -> None:
        logger.info("[TerminalNS] Client connected: %s", sid)

    async def on_disconnect(self, sid: str) -> None:
        logger.info("[TerminalNS] Client disconnected: %s", sid)

    # ------------------------------------------------------------------
    # Terminal events
    # ------------------------------------------------------------------

    async def on_terminal_create(
        self, sid: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create a new PTY session.

        Expected *data*::

            {
                "sessionId": str,
                "cwd": str | None,
                "cols": int,   # default 80
                "rows": int,   # default 24
            }
        """
        session_id: str = data.get("sessionId", "")
        if not session_id:
            await self.emit(
                "terminal:error", {"error": "sessionId is required"}, to=sid
            )
            return {"ok": False, "error": "sessionId is required"}

        cwd = data.get("cwd")
        cols = int(data.get("cols", 80))
        rows = int(data.get("rows", 24))

        try:

            async def _on_output(sess_id: str, raw: bytes) -> None:
                if raw:
                    await self.emit(
                        "terminal:output",
                        {
                            "sessionId": sess_id,
                            "data": raw.decode("utf-8", errors="replace"),
                        },
                        to=sid,
                    )

            await self.service.spawn(session_id, cwd, cols, rows, on_output=_on_output)
            logger.info(
                "[TerminalNS] Created session %s for client %s", session_id, sid
            )
            return {"ok": True, "sessionId": session_id}
        except Exception as exc:
            logger.exception("[TerminalNS] Failed to create session %s", session_id)
            await self.emit(
                "terminal:error", {"sessionId": session_id, "error": str(exc)}, to=sid
            )
            return {"ok": False, "error": str(exc)}

    async def on_terminal_input(self, sid: str, data: dict[str, Any]) -> None:
        """
        Write input to a PTY session.

        Expected *data*::

            {"sessionId": str, "data": str}
        """
        session_id = data.get("sessionId", "")
        input_data = data.get("data", "")
        if not session_id:
            return

        try:
            await self.service.write(session_id, input_data)
        except KeyError:
            await self.emit(
                "terminal:error",
                {"sessionId": session_id, "error": "Session not found"},
                to=sid,
            )

    async def on_terminal_resize(self, sid: str, data: dict[str, Any]) -> None:
        """
        Resize a PTY session.

        Expected *data*::

            {"sessionId": str, "cols": int, "rows": int}
        """
        session_id = data.get("sessionId", "")
        if not session_id:
            return

        cols = int(data.get("cols", 80))
        rows = int(data.get("rows", 24))

        try:
            await self.service.resize(session_id, cols, rows)
        except KeyError:
            await self.emit(
                "terminal:error",
                {"sessionId": session_id, "error": "Session not found"},
                to=sid,
            )

    async def on_terminal_close(self, sid: str, data: dict[str, Any]) -> None:
        """
        Close (kill) a PTY session.

        Expected *data*::

            {"sessionId": str}
        """
        session_id = data.get("sessionId", "")
        if not session_id:
            return

        await self.service.kill(session_id)
        await self.emit("terminal:exit", {"sessionId": session_id}, to=sid)
        logger.info("[TerminalNS] Closed session %s for client %s", session_id, sid)


def register_terminal_namespace(sio_server: socketio.AsyncServer) -> None:
    """Register the /terminal namespace on the given Socket.IO server."""
    sio_server.register_namespace(TerminalNamespace())
    logger.info("[TerminalNS] Registered /terminal namespace")
