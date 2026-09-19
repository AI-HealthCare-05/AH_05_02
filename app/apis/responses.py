from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def envelope(data: Any) -> dict[str, Any]:
    return {
        "data": data,
        "meta": {"request_id": f"req_{uuid4().hex[:16]}", "timestamp": datetime.now(UTC)},
    }


def error_detail(error_code: str, message: str, *, retryable: bool = False) -> dict[str, object]:
    """Return the shared API error payload stored under HTTPException.detail."""

    return {"error_code": error_code, "message": message, "retryable": retryable}
