from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest
from tortoise import Tortoise

from app.core.db.databases import TORTOISE_APP_MODELS
from app.dtos.wellness import OcrHealthApplyRequest, WearableHealthCandidateApplyRequest
from app.models.health import Consent, HealthCheckup
from app.models.users import User
from app.models.wellness import OcrDraft
from app.services.wellness import WellnessService
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


def test_wearable_file_preview_returns_normalized_items_without_identity() -> None:
    raw = (FIXTURES / "android_health_connect_sample.json").read_bytes()
    result = WellnessService.preview_wearable_file("android_health_connect", raw)
    assert result["detected_days"] == 2
    assert result["requires_user_confirmation"] is True
    assert "metadata" not in str(result["items"])


def test_health_candidates_use_only_confirmed_days() -> None:
    days = [StoredDay(date(2026, 9, day), steps=5000, active_minutes=50) for day in range(1, 4)] + [
        StoredDay(date(2026, 9, 4), steps=9000, active_minutes=90, quality="review_required")
    ]
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


@pytest.mark.asyncio
async def test_confirmed_wearable_and_ocr_candidates_patch_only_expected_health_fields() -> None:
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
    try:
        user = await User.create(email="wearable@example.com", hashed_password="unused")
        await Consent.create(user_id=user.id, version="test-v1", is_agreed=True)
        checkup = await HealthCheckup.create(
            user_id=user.id,
            eligibility_check_id=1,
            checkup_date=date(2026, 9, 1),
            age=52,
            sex="male",
            height_cm=170,
            weight_kg=70,
            bmi=24.2,
            self_rated_health="good",
            meal_count_yesterday=3,
            regular_exercise=False,
            current_drinker=False,
            feature_schema_version="test-v1",
        )
        wearable = await WellnessService().apply_wearable_health_candidates(
            user,
            checkup.id,
            WearableHealthCandidateApplyRequest(
                exercise_days_per_week=3,
                exercise_minutes=45,
                regular_exercise=True,
            ),
        )
        assert wearable["message"] == "건강정보가 갱신되었습니다."

        draft = await OcrDraft.create(
            user_id=user.id,
            document_name="synthetic.txt",
            extracted_fields={"height_cm": 168.2, "weight_kg": 72.4, "systolic_bp": 132, "diastolic_bp": 84},
        )
        applied = await WellnessService().apply_ocr_to_health_checkup(
            user,
            draft.id,
            checkup.id,
            OcrHealthApplyRequest(height_cm=168.2, weight_kg=72.4, systolic_bp=132, diastolic_bp=84),
        )
        assert applied["message"] == "건강정보가 갱신되었습니다."
        await checkup.refresh_from_db()
        assert checkup.regular_exercise is True
        assert checkup.exercise_days_per_week == 3
        assert checkup.height_cm == 168.2
        assert checkup.bmi == 25.6
    finally:
        await Tortoise.close_connections()
