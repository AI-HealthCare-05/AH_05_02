from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.ocr.health_checkup_2025 import extract_health_checkup_fields
from src.wearables.android_health import parse_health_connect_export
from src.wearables.common import build_health_candidates, exercise_verification_candidate

FIXTURES = Path(__file__).parent / "fixtures" / "wearables"


@dataclass
class StoredDay:
    summary_date: date
    steps: int | None
    active_minutes: int | None
    sleep_minutes: int | None = None
    resting_heart_rate: int | None = None
    source: str = "apple_health_export"
    quality: str = "user_confirmed"


def test_android_health_connect_export_is_reduced_to_daily_values() -> None:
    items = parse_health_connect_export(FIXTURES / "android_health_connect_sample.json")
    first = items[0]
    assert first.summary_date == date(2026, 9, 1)
    assert first.steps == 8150
    assert first.sleep_minutes == 460
    assert first.source == "android_health_connect"
    assert "com.example" not in str(first)


def test_health_candidates_use_only_confirmed_days() -> None:
    days = [
        StoredDay(date(2026, 9, day), steps=5000, active_minutes=50) for day in range(1, 4)
    ] + [StoredDay(date(2026, 9, 4), steps=9000, active_minutes=90, quality="review_required")]
    result = build_health_candidates(days)
    assert result["period"]["observed_days"] == 3
    assert result["health_input_candidates"] == {
        "exercise_days_per_week": 3.0,
        "exercise_minutes": 50,
        "regular_exercise": True,
    }
    assert result["requires_user_confirmation"] is True


def test_exercise_candidate_explains_why_it_passed() -> None:
    result = exercise_verification_candidate(steps=1500, active_minutes=4)
    assert result["eligible"] is True
    assert result["reasons"] == ["steps>=1000"]
    assert result["requires_user_confirmation"] is True


def test_2025_health_checkup_text_extraction_omits_identity() -> None:
    text = (Path("docs/samples/health_checkup") / "2025_general_health_checkup_synthetic_ocr.txt").read_text(
        encoding="utf-8"
    )
    result = extract_health_checkup_fields(text + "\n성명: 홍길동\n주민등록번호: 000000-0000000")
    assert result["checkup_date"] == "2025-06-18"
    assert result["height_cm"] == 168.2
    assert result["systolic_bp"] == 132
    assert result["diastolic_bp"] == 84
    assert result["fasting_glucose_mg_dl"] == 108
    assert "name" not in result
    assert "resident_number" not in result
