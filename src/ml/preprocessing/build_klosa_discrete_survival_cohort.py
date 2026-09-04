"""Build one-origin-per-PID discrete survival rows for 2-18 year risk."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

SURVIVAL_EVENT = "event_in_interval"
MAX_INTERVAL = 9
HORIZON_YEARS = tuple(range(2, 19, 2))


def select_earliest_eligible_origins(base_cohort: pd.DataFrame) -> pd.DataFrame:
    """Keep one earliest non-diabetic landmark row for each PID."""

    required = {"pid", "baseline_wave", "diabetes_status_t0"}
    if missing := sorted(required.difference(base_cohort.columns)):
        raise ValueError(f"생존 기준 코호트 필수 열이 없습니다: {missing}")
    eligible = base_cohort.loc[base_cohort["diabetes_status_t0"].eq(5)].copy()
    origins = (
        eligible.sort_values(["pid", "baseline_wave"])
        .drop_duplicates("pid", keep="first")
        .rename(columns={"baseline_wave": "origin_wave"})
    )
    if origins["pid"].duplicated().any():
        raise AssertionError("생존 코호트에 PID별 기준시점이 두 개 이상입니다.")
    return origins


def _normalize_statuses(
    status_by_wave: Mapping[int, pd.DataFrame],
) -> dict[int, pd.Series]:
    normalized = {}
    for wave, frame in status_by_wave.items():
        if not {"pid", "diabetes_status"}.issubset(frame.columns):
            raise ValueError(f"wave {wave} 당뇨 상태 열이 없습니다.")
        if frame["pid"].duplicated().any():
            raise ValueError(f"wave {wave}에 중복 PID가 있습니다.")
        normalized[wave] = frame.set_index("pid")["diabetes_status"]
    return normalized


def _expand_origin(
    origin: pd.Series,
    statuses: Mapping[int, pd.Series],
    feature_columns: Sequence[str],
) -> list[dict[str, object]]:
    rows = []
    origin_wave = int(origin["origin_wave"])
    feature_values = {name: origin[name] for name in feature_columns}
    for interval_index in range(1, min(MAX_INTERVAL, 10 - origin_wave) + 1):
        outcome_wave = origin_wave + interval_index
        wave_status = statuses.get(outcome_wave)
        status = np.nan if wave_status is None else wave_status.get(origin["pid"], np.nan)
        if status not in (1, 5):
            break
        rows.append(
            {
                "pid": origin["pid"],
                "origin_wave": origin_wave,
                "interval_index": interval_index,
                "elapsed_years": interval_index * 2,
                SURVIVAL_EVENT: int(status == 1),
                **feature_values,
            }
        )
        if status == 1:
            break
    return rows


def _validate_survival_rows(cohort: pd.DataFrame) -> None:
    if cohort.empty:
        raise ValueError("생존 코호트가 비어 있습니다.")
    if cohort.duplicated(["pid", "interval_index"]).any():
        raise AssertionError("PID-구간 중복 행이 있습니다.")
    if cohort.groupby("pid")[SURVIVAL_EVENT].sum().gt(1).any():
        raise AssertionError("동일 PID에 생존 사건이 두 번 이상 있습니다.")
    event_interval = cohort.loc[cohort[SURVIVAL_EVENT].eq(1)].set_index("pid")["interval_index"]
    if (cohort["interval_index"] > cohort["pid"].map(event_interval)).fillna(False).any():
        raise AssertionError("최초 사건 이후 행이 남아 있습니다.")


def build_discrete_survival_cohort(
    base_cohort: pd.DataFrame,
    status_by_wave: Mapping[int, pd.DataFrame],
    *,
    feature_columns: Sequence[str],
) -> pd.DataFrame:
    """Expand each origin until first diagnosis or right censoring."""

    origins = select_earliest_eligible_origins(base_cohort)
    if missing := sorted(set(feature_columns).difference(origins.columns)):
        raise ValueError(f"생존 입력 특성 열이 없습니다: {missing}")
    normalized_status = _normalize_statuses(status_by_wave)
    output_columns = ["pid", "origin_wave", "interval_index", "elapsed_years", SURVIVAL_EVENT]
    output_columns.extend(feature_columns)
    rows = [
        row for _, origin in origins.iterrows() for row in _expand_origin(origin, normalized_status, feature_columns)
    ]

    cohort = pd.DataFrame(rows, columns=output_columns)
    _validate_survival_rows(cohort)
    return cohort


def horizon_evaluation_frame(
    survival_cohort: pd.DataFrame,
    *,
    horizon_years: int,
    feature_columns: Sequence[str],
) -> pd.DataFrame:
    """Return origins with observed status through a horizon or an earlier event."""

    if horizon_years not in HORIZON_YEARS:
        raise ValueError(f"지원하지 않는 예측기간입니다: {horizon_years}")
    interval = horizon_years // 2
    grouped = survival_cohort.groupby("pid", sort=False)
    summary = grouped.agg(
        observed_intervals=("interval_index", "max"),
        event_interval=("interval_index", lambda values: np.nan),
    )
    events = survival_cohort.loc[survival_cohort[SURVIVAL_EVENT].eq(1)].set_index("pid")["interval_index"]
    summary["event_interval"] = events
    eligible = summary["observed_intervals"].ge(interval) | summary["event_interval"].le(interval)
    summary = summary.loc[eligible].copy()
    summary["target"] = summary["event_interval"].le(interval).fillna(False).astype("int8")

    origins = (
        survival_cohort.sort_values(["pid", "interval_index"]).drop_duplicates("pid", keep="first").set_index("pid")
    )
    columns = ["origin_wave", *feature_columns]
    result = origins.loc[summary.index, columns].join(summary[["target"]]).reset_index()
    if result["target"].nunique() < 2:
        raise ValueError(f"{horizon_years}년 평가 코호트에 두 라벨이 모두 필요합니다.")
    return result
