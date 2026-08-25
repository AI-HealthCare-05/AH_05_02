"""Compatibility entrypoint for the formal FastAPI application.

The Sprint 1 in-memory prototype no longer has an independent runtime. Older
commands that import ``src.backend.main:app`` now use the same application as
``app.main:app``.
"""

from app.main import app

__all__ = ["app"]
