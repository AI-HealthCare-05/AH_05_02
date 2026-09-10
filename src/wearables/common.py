from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from statistics import mean
from typing import Protocol


class DailyWearableLike(Protocol):
    summary_date: date
    steps: int | None
    active_minutes: int | None
    sleep_minutes: int | None
    resting_heart_rate: int | None
    source: str
    quality: str


class AppleDailyLike(Protocol):
    local_date: date
    steps: int | None
    workout_minutes: float
    sleep_minutes: float | None
    resting_heart_rate: float | None
    quality_flags: list[str]


@dataclass(frozen=True)
class CanonicalDailySummary:
    summary_date: date
    steps: int | None = None
    active_minutes: int | None = None
    sleep_minutes: int | None = None
    resting_heart_rate: int | None = None
    source: str = "file_import"
    quality: str = "needs_confirmation"

    def as_api_item(self) -> dict[str, object]:
        return {
            "summary_date": self.summary_date.isoformat(),
            "steps": self.steps,
            "active_minutes": self.active_minutes,
            "sleep_minutes": self.sleep_minutes,
            "resting_heart_rate": self.resting_heart_rate,
        }


def from_apple_daily_summary(item: AppleDailyLike) -> CanonicalDailySummary:
    """Map Apple Health's local daily aggregate to the shared API contract."""
    flags = set(item.quality_flags)
    return CanonicalDailySummary(
        summary_date=item.local_date,
        steps=item.steps,
        active_minutes=round(item.workout_minutes or 0),
        sleep_minutes=round(item.sleep_minutes) if item.sleep_minutes else None,
        resting_heart_rate=round(item.resting_heart_rate) if item.resting_heart_rate else None,
        source="apple_health_export",
        quality="review_required" if flags else "needs_confirmation",
    )


def exercise_verification_candidate(
    *, steps: int | None, active_minutes: int | None, minimum_steps: int = 1_000, minimum_active_minutes: int = 10
) -> dict[str, object]:
    """Return a transparent MVP decision, not a medical or exercise-quality judgment."""
    steps_met = steps is not None and steps >= minimum_steps
    minutes_met = active_minutes is not None and active_minutes >= minimum_active_minutes
    reasons: list[str] = []
    if steps_met:
        reasons.append(f"steps>={minimum_steps}")
    if minutes_met:
        reasons.append(f"active_minutes>={minimum_active_minutes}")
    return {
        "eligible": steps_met or minutes_met,
        "reasons": reasons,
        "thresholds": {"steps": minimum_steps, "active_minutes": minimum_active_minutes},
        "requires_user_confirmation": True,
    }


def build_health_candidates(items: Iterable[DailyWearableLike]) -> dict[str, object]:
    """Summarise confirmed daily records into editable health-input candidates.

    Values are deliberately returned as candidates. They must never overwrite a
    health checkup or trigger a diagnosis without the user's review.
    """
    accepted = [item for item in items if item.quality == "user_confirmed"]
    activity_days = [
        item for item in accepted if (item.active_minutes or 0) >= 10 or (item.steps or 0) >= 1_000
    ]
    active_values = [item.active_minutes for item in activity_days if item.active_minutes is not None]
    step_values = [item.steps for item in accepted if item.steps is not None]
    sleep_values = [item.sleep_minutes for item in accepted if item.sleep_minutes is not None]
    heart_values = [item.resting_heart_rate for item in accepted if item.resting_heart_rate is not None]
    total_active_minutes = sum(value for value in active_values)
    return {
        "period": {
            "start_date": min((item.summary_date for item in accepted), default=None),
            "end_date": max((item.summary_date for item in accepted), default=None),
            "observed_days": len(accepted),
        },
        "health_input_candidates": {
            "exercise_days_per_week": float(len(activity_days)),
            "exercise_minutes": round(mean(active_values), 1) if active_values else 0.0,
            "regular_exercise": len(activity_days) >= 3 and total_active_minutes >= 150,
        },
        "supporting_summary": {
            "total_active_minutes": total_active_minutes,
            "average_steps": round(mean(step_values)) if step_values else None,
            "average_sleep_minutes": round(mean(sleep_values)) if sleep_values else None,
            "average_resting_heart_rate": round(mean(heart_values)) if heart_values else None,
        },
        "requires_user_confirmation": True,
        "notice": "웨어러블 요약으로 만든 입력 후보입니다. 건강검진 값이나 진단으로 자동 확정하지 않습니다.",
    }
