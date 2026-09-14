from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.wearables.common import CanonicalDailySummary


def _minutes(start: str, end: str) -> int:
    return max(0, round((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 60))


def _add_record(bucket: dict[str, Any], record: dict[str, Any]) -> None:
    kind = record.get("recordType")
    start = record["startTime"]
    if kind == "StepsRecord":
        count = max(0, int(record.get("count") or 0))
        bucket["steps"] = (bucket["steps"] or 0) + count
        if count == 0 and record.get("wearStatus") == "UNKNOWN":
            bucket["quality"].append("possible_not_worn")
    elif kind in {"ExerciseSessionRecord", "ActiveMinutesRecord"}:
        duration = int(record.get("activeMinutes") or _minutes(start, record.get("endTime", start)))
        bucket["active_minutes"] = (bucket["active_minutes"] or 0) + duration
    elif kind == "SleepSessionRecord":
        bucket["sleep_minutes"] = (bucket["sleep_minutes"] or 0) + _minutes(start, record.get("endTime", start))
    elif kind == "RestingHeartRateRecord":
        value = record.get("beatsPerMinute")
        if value is not None and 25 <= float(value) <= 250:
            bucket["heart_rates"].append(float(value))


def parse_health_connect_payload(payload: dict[str, Any]) -> list[CanonicalDailySummary]:
    """Reduce a Health Connect JSON object to privacy-safe daily values."""
    grouped: dict[date, dict[str, Any]] = defaultdict(
        lambda: {"steps": None, "active_minutes": None, "sleep_minutes": None, "heart_rates": [], "quality": []}
    )
    seen_ids: set[str] = set()
    for record in payload.get("records", []):
        metadata = record.get("metadata") or {}
        record_id = str(metadata.get("id") or metadata.get("clientRecordId") or "")
        if record_id and record_id in seen_ids:
            continue
        if record_id:
            seen_ids.add(record_id)
        start = record.get("startTime")
        if not start:
            continue
        local_date = datetime.fromisoformat(start).date()
        bucket = grouped[local_date]
        _add_record(bucket, record)

    result: list[CanonicalDailySummary] = []
    for summary_date, bucket in sorted(grouped.items()):
        heart_rates = bucket.pop("heart_rates")
        quality_flags = bucket.pop("quality")
        result.append(
            CanonicalDailySummary(
                summary_date=summary_date,
                resting_heart_rate=round(sum(heart_rates) / len(heart_rates)) if heart_rates else None,
                source="android_health_connect",
                quality="needs_confirmation" if not quality_flags else "review_required",
                **bucket,
            )
        )
    return result


def parse_health_connect_export(path: str | Path) -> list[CanonicalDailySummary]:
    """Parse the synthetic/portable Health Connect JSON shape used by the MVP."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_health_connect_payload(payload)
