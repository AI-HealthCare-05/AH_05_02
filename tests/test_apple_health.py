"""Apple Health export.xml 정제 파이프라인 테스트.

`tests/fixtures/apple_health_sample_export.xml`은 실제 export.xml 스키마
(DOCTYPE 포함)를 그대로 따르는 합성 데이터다. 값은 전부 가짜이며, sourceName도
실제 개인 이름 패턴("OOO의 Apple Watch")을 재현하되 특정 실존 인물을 가리키지
않도록 "테스트유저"로 채워져 있다.
"""

from __future__ import annotations

import os
import tempfile
from datetime import date, datetime, timezone

import pytest

from src.wearables import apple_health as ah

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "apple_health_sample_export.xml")


def _records():
    return list(ah.iter_normalized_records(FIXTURE_PATH, user_pseudo_id="u_test_hash"))


def test_only_target_record_types_are_yielded():
    records = _records()
    seen_types = {r.record_type for r in records}
    # 픽스처에는 걸음/거리/칼로리/심박/안정시심박/수면 + workout:* + activity_summary만 있어야 함
    assert seen_types <= {
        "steps",
        "distance",
        "active_energy",
        "heart_rate",
        "resting_heart_rate",
        "sleep",
        "workout:walking",
        "workout:badminton",
        "activity_summary",
    }
    assert "steps" in seen_types
    assert "sleep" in seen_types


def test_source_name_never_leaks_into_output():
    records = _records()
    for r in records:
        as_text = " ".join(str(v) for v in r.as_dict().values())
        assert "테스트유저" not in as_text, "원본 sourceName(개인 식별 가능 문자열)이 출력에 남아있으면 안 됨"
        assert r.device_type in {"watch", "phone", "other"}


def test_watch_source_classified_correctly():
    records = _records()
    step_records = [r for r in records if r.record_type == "steps" and r.local_date == date(2026, 3, 1)]
    assert len(step_records) == 2
    assert all(r.device_type == "watch" and r.source_app == "apple_health" for r in step_records)


def test_third_party_sleep_app_classified_by_known_app_name():
    records = _records()
    pillow = [r for r in records if r.record_type == "sleep" and r.source_app == "pillow"]
    assert len(pillow) == 1
    assert pillow[0].device_type == "other"


def test_sleep_duration_computed_in_minutes():
    records = _records()
    day1_sleep = [r for r in records if r.record_type == "sleep" and r.local_date == date(2026, 3, 1)]
    assert len(day1_sleep) == 1
    # 00:30 ~ 06:45 = 6h15m = 375분
    assert day1_sleep[0].value == pytest.approx(375.0)
    assert day1_sleep[0].unit == "min"


def test_sleep_crossing_midnight_attributed_to_start_local_date():
    records = _records()
    overnight = [r for r in records if r.record_type == "sleep" and r.local_date == date(2026, 3, 3)]
    assert len(overnight) == 1
    # 2026-03-03 23:40 ~ 2026-03-04 06:55 -> local_date는 시작일인 3/3
    assert overnight[0].start_at_utc.tzinfo is not None


def test_zero_steps_flagged_as_possibly_unworn():
    records = _records()
    day3_steps = [r for r in records if r.record_type == "steps" and r.local_date == date(2026, 3, 3)]
    assert len(day3_steps) == 1
    assert day3_steps[0].quality_flag == "미착용 의심"


def test_implausible_heart_rate_flagged_as_missing():
    records = _records()
    hr = [r for r in records if r.record_type == "heart_rate" and r.local_date == date(2026, 3, 4)]
    assert len(hr) == 1
    assert hr[0].quality_flag == "결측"  # 410bpm은 생리학적으로 불가능


def test_workout_sessions_are_extracted():
    records = _records()
    workouts = [r for r in records if r.record_type.startswith("workout:")]
    assert {r.record_type for r in workouts} == {"workout:walking", "workout:badminton"}
    walking = next(r for r in workouts if r.record_type == "workout:walking")
    assert walking.value == pytest.approx(32.5)
    assert walking.recording_method == "능동"


def test_activity_summary_is_extracted_per_day():
    records = _records()
    summaries = [r for r in records if r.record_type == "activity_summary"]
    assert len(summaries) == 3
    day3 = next(r for r in summaries if r.local_date == date(2026, 3, 3))
    assert day3.quality_flag == "미착용 의심"


def test_overlapping_sleep_records_flagged_duplicate_watch_wins():
    records = _records()
    flagged = ah.flag_duplicates(records)
    day2_sleep = [r for r in flagged if r.record_type == "sleep" and r.local_date == date(2026, 3, 2)]
    assert len(day2_sleep) == 2
    by_source = {r.source_app: r for r in day2_sleep}
    assert by_source["apple_health"].quality_flag == "정상"
    assert by_source["pillow"].quality_flag == "중복"


def test_daily_summary_sums_multiple_step_records():
    records = _records()
    flagged = ah.flag_duplicates(records)
    summaries = {s.local_date: s for s in ah.build_daily_summaries(flagged)}
    assert summaries[date(2026, 3, 1)].steps == 812 + 1523


def test_daily_summary_excludes_duplicate_sleep_from_total():
    records = _records()
    flagged = ah.flag_duplicates(records)
    summaries = {s.local_date: s for s in ah.build_daily_summaries(flagged)}
    day2 = summaries[date(2026, 3, 2)]
    # Pillow(380분)이 아니라 Watch(395분)만 반영
    assert day2.sleep_minutes == pytest.approx(395.0)
    assert "중복_레코드_제외" in day2.quality_flags


def test_daily_summary_includes_workout_totals():
    records = _records()
    flagged = ah.flag_duplicates(records)
    summaries = {s.local_date: s for s in ah.build_daily_summaries(flagged)}
    assert summaries[date(2026, 3, 1)].workout_count == 1
    assert summaries[date(2026, 3, 1)].workout_minutes == pytest.approx(32.5)


def test_missing_day_has_no_fabricated_values():
    records = _records()
    flagged = ah.flag_duplicates(records)
    summaries = {s.local_date: s for s in ah.build_daily_summaries(flagged)}
    day4 = summaries[date(2026, 3, 4)]
    assert day4.steps is None
    assert day4.sleep_minutes is None
    assert "결측" in day4.quality_flags


def test_mile_distance_converted_to_km():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
 <ExportDate value="2026-03-05 00:00:00 +0000"/>
 <Me HKCharacteristicTypeIdentifierDateOfBirth="1990-01-01" HKCharacteristicTypeIdentifierBiologicalSex="HKBiologicalSexNotSet" HKCharacteristicTypeIdentifierBloodType="HKBloodTypeNotSet" HKCharacteristicTypeIdentifierFitzpatrickSkinType="HKFitzpatrickSkinTypeNotSet" HKCharacteristicTypeIdentifierCardioFitnessMedicationsUse="None"/>
 <Record type="HKQuantityTypeIdentifierDistanceWalkingRunning" sourceName="테스트유저의 iPhone" unit="mi" value="1.0" startDate="2026-03-05 08:00:00 +0000" endDate="2026-03-05 08:10:00 +0000"/>
</HealthData>
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as fh:
        fh.write(xml)
        path = fh.name
    try:
        records = list(ah.iter_normalized_records(path, user_pseudo_id="u2"))
    finally:
        os.unlink(path)
    assert len(records) == 1
    assert records[0].unit == "km"
    assert records[0].value == pytest.approx(1.60934, rel=1e-3)


def test_in_bed_sleep_value_is_not_counted_as_asleep():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="ko_KR">
 <ExportDate value="2026-03-06 00:00:00 +0900"/>
 <Me HKCharacteristicTypeIdentifierDateOfBirth="1990-01-01" HKCharacteristicTypeIdentifierBiologicalSex="HKBiologicalSexNotSet" HKCharacteristicTypeIdentifierBloodType="HKBloodTypeNotSet" HKCharacteristicTypeIdentifierFitzpatrickSkinType="HKFitzpatrickSkinTypeNotSet" HKCharacteristicTypeIdentifierCardioFitnessMedicationsUse="None"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="테스트유저의 Apple Watch" value="HKCategoryValueSleepAnalysisInBed" startDate="2026-03-06 23:00:00 +0900" endDate="2026-03-07 07:00:00 +0900"/>
</HealthData>
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as fh:
        fh.write(xml)
        path = fh.name
    try:
        records = list(ah.iter_normalized_records(path, user_pseudo_id="u3"))
    finally:
        os.unlink(path)
    assert records == []
