"""
Health Check Route
==================

Provides a basic health check endpoint for monitoring and readiness probes.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Return service health status."""
    return {"status": "ok"}
