"""Deprecated compatibility import for the formal API router.

Domain behavior lives in ``app/``. This module intentionally contains no mock
prediction logic so there is only one executable service baseline.
"""

from app.apis.v1 import v1_routers as router

__all__ = ["router"]
