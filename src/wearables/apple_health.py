"""Apple Health `export.xml` 정제 파이프라인.

이 모듈은 iOS 건강 앱에서 내보낸 export.xml(수 GB에 달할 수 있음)을 스트리밍으로
읽어, 프로젝트 공통 웨어러블 스키마(레코드 단위)로 정규화한다. 이후
`build_daily_summaries`로 일 단위 생활습관 요약을 생성한다.

개인정보 처리 원칙
------------------
- Apple의 `sourceName` 속성에는 기기 소유자의 실제 이름이 그대로 들어있는 경우가
  많다 (예: "OOO의 Apple Watch"). 이 모듈은 원본 sourceName을 절대 그대로
  반환하지 않고, `device_type`(watch/phone/other)과 `source_app`(알려진
  서드파티 앱 이름 또는 "unknown")으로만 변환한다.
- 사용자 식별자는 호출자가 이미 가명화한 `user_pseudo_id`를 넘겨줘야 하며, 이
  모듈은 그 값을 그대로 통과시킬 뿐 원본 개인 식별자를 다루지 않는다.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Iterable, Iterator

# --------------------------------------------------------------------------
# 스키마
# --------------------------------------------------------------------------

RECORD_TYPE_MAP: dict[str, str] = {
    "HKQuantityTypeIdentifierStepCount": "steps",
    "HKQuantityTypeIdentifierDistanceWalkingRunning": "distance",
    "HKQuantityTypeIdentifierActiveEnergyBurned": "active_energy",
    "HKQuantityTypeIdentifierHeartRate": "heart_rate",
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_heart_rate",
    "HKCategoryTypeIdentifierSleepAnalysis": "sleep",
}
"""정제 대상 Record type. 그 외 타입(생리주기, 배변 등)은 무시한다."""

# 생리학적으로 불가능한 값 범위 -> 결측/오류로 간주할 상한/하한
PLAUSIBLE_RANGES: dict[str, tuple[float, float]] = {
    "steps": (0, 100_000),
    "distance": (0, 500),  # km, 하루 기준 상한을 넉넉히 잡음(레코드 단위는 보통 훨씬 작음)
    "active_energy": (0, 20_000),
    "heart_rate": (25, 250),
    "resting_heart_rate": (25, 150),
}

SLEEP_ASLEEP_VALUES = {
    "HKCategoryValueSleepAnalysisAsleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM",
    "HKCategoryValueSleepAnalysisAsleepUnspecified",
    "HKCategoryValueSleepAnalysisAsleep",  # 구버전 iOS
}
"""수면 '중'으로 집계할 값. InBed(침대에 누워있음)는 실제 수면이 아니므로 제외."""

KNOWN_THIRD_PARTY_APPS = {
    "Pillow": "pillow",
    "Zepp Life": "zepp_life",
    "Planfit": "planfit",
    "SenssunLife": "senssunlife",
}
"""알려진 서드파티 앱 sourceName -> source_app 코드. 개인 식별 정보가 아니므로
그대로 유지해도 된다."""

_WATCH_SUFFIX_RE = re.compile(r"Apple Watch$")
_IPHONE_SUFFIX_RE = re.compile(r"iPhone$")


@dataclass(frozen=True)
class NormalizedRecord:
    """공통 웨어러블 출력 스키마 한 행."""

    user_pseudo_id: str
    platform: str
    record_type: str
    start_at_utc: datetime
    end_at_utc: datetime
    local_date: date
    timezone_offset: str
    value: float
    unit: str
    source_app: str
    device_type: str
    recording_method: str
    source_record_id: str
    quality_flag: str = "정상"

    def as_dict(self) -> dict[str, object]:
        return {
            "user_pseudo_id": self.user_pseudo_id,
            "platform": self.platform,
            "record_type": self.record_type,
            "start_at_utc": self.start_at_utc.isoformat(),
            "end_at_utc": self.end_at_utc.isoformat(),
            "local_date": self.local_date.isoformat(),
            "timezone_offset": self.timezone_offset,
            "value": self.value,
            "unit": self.unit,
            "source_app": self.source_app,
            "device_type": self.device_type,
            "recording_method": self.recording_method,
            "source_record_id": self.source_record_id,
            "quality_flag": self.quality_flag,
        }


# --------------------------------------------------------------------------
# 파싱 유틸리티
# --------------------------------------------------------------------------


def _parse_apple_datetime(raw: str) -> datetime:
    """"2026-03-01 08:00:00 +0900" 형태의 Apple Health 타임스탬프를 파싱한다."""
    return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S %z")


def _timezone_offset_str(dt: datetime) -> str:
    offset = dt.utcoffset() or timedelta(0)
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    return f"{sign}{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def classify_source(source_name: str, device_attr: str | None) -> tuple[str, str]:
    """`sourceName`(개인 이름이 섞여있을 수 있음)을 (device_type, source_app)으로
    변환한다. 원본 문자열은 반환하지 않는다.
    """
    if _WATCH_SUFFIX_RE.search(source_name):
        return "watch", "apple_health"
    if _IPHONE_SUFFIX_RE.search(source_name):
        return "phone", "apple_health"
    for app_name, code in KNOWN_THIRD_PARTY_APPS.items():
        if source_name == app_name:
            return "other", code
    if device_attr and "Watch" in device_attr:
        return "watch", "apple_health"
    if device_attr and "iPhone" in device_attr:
        return "phone", "apple_health"
    return "other", "unknown"


def _source_record_id(record_type: str, source_name: str, start: datetime, end: datetime, value: str) -> str:
    """원본 개인정보(sourceName)를 노출하지 않는 안정적인 레코드 식별자.

    sourceName은 해시로만 반영해 기기 소유자 이름이 id에 그대로 남지 않게 한다.
    """
    source_hash = hashlib.sha256(source_name.encode("utf-8")).hexdigest()[:12]
    raw = f"{record_type}|{source_hash}|{start.isoformat()}|{end.isoformat()}|{value}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _recording_method(metadata: dict[str, str]) -> str:
    if metadata.get("HKWasUserEntered") == "1":
        return "수동"
    return "자동"


# --------------------------------------------------------------------------
# 스트리밍 파서
# --------------------------------------------------------------------------


def iter_normalized_records(xml_path: str, user_pseudo_id: str) -> Iterator[NormalizedRecord]:
    """export.xml을 스트리밍으로 읽어 정규화된 레코드를 하나씩 생성한다.

    수 GB 파일도 메모리에 전체를 올리지 않도록 `iterparse` + 즉시 clear를
    사용한다.
    """
    context = ET.iterparse(xml_path, events=("start", "end"))
    _, root = next(context)  # root element 확보 (clear를 위해)

    current_metadata: dict[str, str] = {}

    for event, elem in context:
        tag = elem.tag
        if event == "start":
            if tag == "Record":
                current_metadata = {}
            continue

        # event == "end"
        if tag == "MetadataEntry":
            key = elem.get("key")
            value = elem.get("value")
            if key is not None:
                current_metadata[key] = value or ""
            elem.clear()
            continue

        if tag == "Record":
            record_type_raw = elem.get("type", "")
            record_type = RECORD_TYPE_MAP.get(record_type_raw)
            if record_type is None:
                elem.clear()
                current_metadata = {}
                continue
            normalized = _normalize_record(elem, record_type, current_metadata, user_pseudo_id)
            current_metadata = {}
            elem.clear()
            root.clear()
            if normalized is not None:
                yield normalized
            continue

        if tag == "Workout":
            normalized = _normalize_workout(elem, user_pseudo_id)
            elem.clear()
            root.clear()
            if normalized is not None:
                yield normalized
            continue

        if tag == "ActivitySummary":
            normalized = _normalize_activity_summary(elem, user_pseudo_id)
            elem.clear()
            root.clear()
            if normalized is not None:
                yield normalized
            continue


def _normalize_record(
    elem: ET.Element,
    record_type: str,
    metadata: dict[str, str],
    user_pseudo_id: str,
) -> NormalizedRecord | None:
    source_name = elem.get("sourceName", "")
    device_attr = elem.get("device")
    device_type, source_app = classify_source(source_name, device_attr)

    try:
        start = _parse_apple_datetime(elem.get("startDate", ""))
        end = _parse_apple_datetime(elem.get("endDate", ""))
    except ValueError:
        return None

    raw_value = elem.get("value", "")
    unit = elem.get("unit", "") or ""

    if record_type == "sleep":
        # 카테고리 값 -> 분 단위 지속시간으로 변환. Asleep 계열만 취급, InBed는 제외.
        if raw_value not in SLEEP_ASLEEP_VALUES:
            return None
        duration_minutes = (end - start).total_seconds() / 60
        value = round(duration_minutes, 1)
        unit = "min"
        quality_flag = "정상" if value > 0 else "결측"
    else:
        try:
            value = float(raw_value)
        except ValueError:
            return None
        if record_type == "distance" and unit == "km":
            pass
        elif record_type == "distance" and unit in ("mi",):
            value = round(value * 1.60934, 4)
            unit = "km"
        low, high = PLAUSIBLE_RANGES.get(record_type, (float("-inf"), float("inf")))
        if not (low <= value <= high):
            quality_flag = "결측"
        elif record_type == "steps" and value == 0:
            quality_flag = "미착용 의심"
        else:
            quality_flag = "정상"

    local_date = start.date()
    return NormalizedRecord(
        user_pseudo_id=user_pseudo_id,
        platform="apple_health",
        record_type=record_type,
        start_at_utc=start.astimezone(tz=timezone_utc()),
        end_at_utc=end.astimezone(tz=timezone_utc()),
        local_date=local_date,
        timezone_offset=_timezone_offset_str(start),
        value=value,
        unit=unit,
        source_app=source_app,
        device_type=device_type,
        recording_method=_recording_method(metadata),
        source_record_id=_source_record_id(record_type, source_name, start, end, raw_value),
        quality_flag=quality_flag,
    )


def _normalize_workout(elem: ET.Element, user_pseudo_id: str) -> NormalizedRecord | None:
    source_name = elem.get("sourceName", "")
    device_attr = elem.get("device")
    device_type, source_app = classify_source(source_name, device_attr)
    try:
        start = _parse_apple_datetime(elem.get("startDate", ""))
        end = _parse_apple_datetime(elem.get("endDate", ""))
    except ValueError:
        return None

    activity_type = elem.get("workoutActivityType", "").replace("HKWorkoutActivityType", "")
    duration = elem.get("duration")
    try:
        duration_value = float(duration) if duration is not None else (end - start).total_seconds() / 60
    except ValueError:
        duration_value = (end - start).total_seconds() / 60

    return NormalizedRecord(
        user_pseudo_id=user_pseudo_id,
        platform="apple_health",
        record_type=f"workout:{activity_type.lower()}" if activity_type else "workout",
        start_at_utc=start.astimezone(tz=timezone_utc()),
        end_at_utc=end.astimezone(tz=timezone_utc()),
        local_date=start.date(),
        timezone_offset=_timezone_offset_str(start),
        value=round(duration_value, 1),
        unit="min",
        source_app=source_app,
        device_type=device_type,
        recording_method="능동",  # Workout은 사용자가 직접 시작/종료를 조작
        source_record_id=_source_record_id("workout", source_name, start, end, activity_type),
        quality_flag="정상" if duration_value > 0 else "결측",
    )


def _normalize_activity_summary(elem: ET.Element, user_pseudo_id: str) -> NormalizedRecord | None:
    date_str = elem.get("dateComponents")
    if not date_str:
        return None
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None
    active_energy = elem.get("activeEnergyBurned")
    try:
        value = float(active_energy) if active_energy is not None else 0.0
    except ValueError:
        value = 0.0

    # ActivitySummary는 시간대 정보가 없는 날짜 단위 요약이라, 00:00 로컬 기준
    # 자정으로 간주하고 UTC 변환은 생략(로컬 날짜만 의미가 있음).
    naive_start = datetime(day.year, day.month, day.day)
    return NormalizedRecord(
        user_pseudo_id=user_pseudo_id,
        platform="apple_health",
        record_type="activity_summary",
        start_at_utc=naive_start,
        end_at_utc=naive_start,
        local_date=day,
        timezone_offset="unknown",
        value=value,
        unit="kcal",
        source_app="apple_health",
        device_type="watch",
        recording_method="자동",
        source_record_id=_source_record_id("activity_summary", "activity_summary", naive_start, naive_start, date_str),
        quality_flag="정상" if value > 0 else "미착용 의심",
    )


def timezone_utc():
    from datetime import timezone

    return timezone.utc


# --------------------------------------------------------------------------
# 중복 처리
# --------------------------------------------------------------------------

SOURCE_PRIORITY = {
    ("watch", "apple_health"): 0,
    ("phone", "apple_health"): 1,
}
"""같은 시간대·같은 record_type이 여러 소스에서 겹칠 때 우선순위. 낮을수록 우선.
목록에 없는 (device_type, source_app) 조합은 가장 낮은 우선순위(가장 큰 값)로 취급."""


def flag_duplicates(records: list[NormalizedRecord]) -> list[NormalizedRecord]:
    """같은 record_type + 겹치는 시간구간을 가진 레코드를 찾아 quality_flag를
    '중복'으로 표시한다. 겹치는 레코드 군집(cluster)마다 우선순위가 가장 높은
    레코드 하나만 원래 플래그를 유지하고 나머지는 '중복'으로 강등한다.

    우선순위가 동률이면(예: 서드파티 앱끼리 겹침) 먼저 시작한 레코드를 유지한다.
    """
    by_type: dict[str, list[NormalizedRecord]] = defaultdict(list)
    for record in records:
        by_type[record.record_type].append(record)

    result: list[NormalizedRecord] = []
    for group in by_type.values():
        group = sorted(group, key=lambda r: r.start_at_utc)
        clusters: list[list[NormalizedRecord]] = []
        cluster_end: datetime | None = None
        for record in group:
            if clusters and cluster_end is not None and record.start_at_utc < cluster_end:
                clusters[-1].append(record)
                cluster_end = max(cluster_end, record.end_at_utc)
            else:
                clusters.append([record])
                cluster_end = record.end_at_utc

        for cluster in clusters:
            if len(cluster) == 1:
                result.append(cluster[0])
                continue
            ranked = sorted(
                cluster,
                key=lambda r: (SOURCE_PRIORITY.get((r.device_type, r.source_app), 99), r.start_at_utc),
            )
            winner = ranked[0]
            result.append(winner)
            for loser in ranked[1:]:
                result.append(
                    NormalizedRecord(**{**loser.__dict__, "quality_flag": "중복"})
                )
    return result


# --------------------------------------------------------------------------
# 일 단위 생활습관 요약
# --------------------------------------------------------------------------


@dataclass
class DailySummary:
    user_pseudo_id: str
    local_date: date
    steps: int | None = None
    distance_km: float | None = None
    active_energy_kcal: float | None = None
    resting_heart_rate: float | None = None
    sleep_minutes: float | None = None
    workout_minutes: float = 0.0
    workout_count: int = 0
    quality_flags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "user_pseudo_id": self.user_pseudo_id,
            "local_date": self.local_date.isoformat(),
            "steps": self.steps,
            "distance_km": self.distance_km,
            "active_energy_kcal": self.active_energy_kcal,
            "resting_heart_rate": self.resting_heart_rate,
            "sleep_minutes": self.sleep_minutes,
            "workout_minutes": self.workout_minutes,
            "workout_count": self.workout_count,
            "quality_flags": sorted(set(self.quality_flags)),
        }


def build_daily_summaries(records: Iterable[NormalizedRecord]) -> list[DailySummary]:
    """정규화된 레코드들을 사용자·로컬 날짜 단위로 집계한다.

    - steps/distance/active_energy: 하루 합계 (단, quality_flag == '중복'인 레코드는 제외)
    - resting_heart_rate: 하루 평균
    - sleep: 같은 날 밤 수면은 시작일(전날) 기준으로 집계(자정을 걸친 수면은
      시작 시각의 로컬 날짜에 귀속)
    - workout: 개수와 총 시간 합산
    """
    grouped: dict[tuple[str, date], DailySummary] = {}
    resting_hr_accumulator: dict[tuple[str, date], list[float]] = defaultdict(list)

    for record in records:
        key = (record.user_pseudo_id, record.local_date)
        summary = grouped.setdefault(key, DailySummary(user_pseudo_id=record.user_pseudo_id, local_date=record.local_date))

        if record.quality_flag == "중복":
            summary.quality_flags.append("중복_레코드_제외")
            continue

        if record.record_type == "steps":
            summary.steps = (summary.steps or 0) + int(record.value)
        elif record.record_type == "distance":
            summary.distance_km = round((summary.distance_km or 0.0) + record.value, 3)
        elif record.record_type == "active_energy":
            summary.active_energy_kcal = round((summary.active_energy_kcal or 0.0) + record.value, 1)
        elif record.record_type == "resting_heart_rate":
            resting_hr_accumulator[key].append(record.value)
        elif record.record_type == "sleep":
            summary.sleep_minutes = round((summary.sleep_minutes or 0.0) + record.value, 1)
        elif record.record_type.startswith("workout"):
            summary.workout_minutes = round(summary.workout_minutes + record.value, 1)
            summary.workout_count += 1

        if record.quality_flag not in ("정상", "중복"):
            summary.quality_flags.append(record.quality_flag)

    for key, values in resting_hr_accumulator.items():
        grouped[key].resting_heart_rate = round(sum(values) / len(values), 1)

    return sorted(grouped.values(), key=lambda s: s.local_date)
