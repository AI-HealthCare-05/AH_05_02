from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def envelope(data: Any) -> dict[str, Any]:
    return {
        "data": data,
        "meta": {"request_id": f"req_{uuid4().hex[:16]}", "timestamp": datetime.now(UTC)},
    }
