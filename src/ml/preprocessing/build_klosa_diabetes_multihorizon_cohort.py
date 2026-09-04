"""Build nested 2-, 4-, and 8-year KLoSA diabetes-incidence cohorts."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET

HORIZON_YEARS = (2, 4, 8)
HORIZON_STEPS = {2: 1, 4: 2, 6: 3, 8: 4}
HORIZON_TARGETS = {years: f"target_diabetes_incident_within_{years}y" for years in HORIZON_STEPS}


def load_diabetes_status_by_wave(source_dir: Path) -> dict[int, pd.DataFrame]:
    """Load diagnosis status only; raw rows remain outside Git-managed outputs."""

    statuses = {}
    for wave in range(1, 11):
        source_column = f"w{wave:02d}chronic_b"
        frame = pd.read_stata(
            source_dir / f"str{wave:02d}_20260413.dta",
            columns=["pid", source_column],
            convert_categoricals=False,
        )
        if frame["pid"].duplicated().any():
            raise ValueError(f"wave {wave}에 중복 PID가 있습니다.")
        statuses[wave] = frame.rename(columns={source_column: "diabetes_status"})
    return statuses


def build_cumulative_horizon_cohort(
    base_cohort: pd.DataFrame,
    *,
    horizon_years: int,
    status_by_wave: Mapping[int, pd.DataFrame],
) -> pd.DataFrame:
    """Keep complete adjacent follow-up and label any diagnosis within horizon.

    The two-year base cohort already guarantees an explicitly observed first
    adjacent wave. Longer horizons additionally require every later adjacent
    status through the requested horizon to be explicit 1 (diagnosed) or 5
    (not diagnosed). This conservative complete-case contract avoids treating
    dropout as a negative outcome.
    """

    if horizon_years not in HORIZON_STEPS:
        raise ValueError(f"지원하지 않는 예측 구간입니다: {horizon_years}")
    required = {
        "pid",
        "baseline_wave",
        "diabetes_status_t0",
        "diabetes_status_t1",
        TARGET,
    }
    missing = sorted(required.difference(base_cohort.columns))
    if missing:
        raise ValueError(f"기준 코호트 필수 열이 없습니다: {missing}")

    steps = HORIZON_STEPS[horizon_years]
    target = HORIZON_TARGETS[horizon_years]
    parts = []
    for baseline_wave in range(1, 11 - steps):
        frame = base_cohort.loc[base_cohort["baseline_wave"].eq(baseline_wave)].copy()
        if frame.empty:
            continue
        future_columns = ["diabetes_status_t1"]
        for offset in range(2, steps + 1):
            outcome_wave = baseline_wave + offset
            status = status_by_wave[outcome_wave].rename(columns={"diabetes_status": f"diabetes_status_t{offset}"})
            frame = frame.merge(status, on="pid", how="inner", validate="one_to_one")
            future_columns.append(f"diabetes_status_t{offset}")

        valid = frame[future_columns].isin([1, 5]).all(axis=1)
        frame = frame.loc[valid].copy()
        frame[target] = frame[future_columns].eq(1).any(axis=1).astype("int8")
        frame["horizon_years"] = horizon_years
        frame["horizon_outcome_wave"] = baseline_wave + steps
        parts.append(frame)

    cohort = pd.concat(parts, ignore_index=True)
    if not cohort["diabetes_status_t0"].eq(5).all():
        raise AssertionError("기준 시점 기진단자가 다중 horizon 코호트에 포함됐습니다.")
    if not cohort[target].isin([0, 1]).all():
        raise AssertionError("다중 horizon 라벨은 0 또는 1이어야 합니다.")
    if cohort.duplicated(["pid", "baseline_wave"]).any():
        raise AssertionError("다중 horizon 코호트에 PID-baseline 중복이 있습니다.")
    return cohort


def build_multihorizon_cohorts(
    base_cohort: pd.DataFrame,
    source_dir: Path,
) -> dict[int, pd.DataFrame]:
    """Return all prespecified horizons under one cumulative-label contract."""

    statuses = load_diabetes_status_by_wave(source_dir)
    cohorts = {
        years: build_cumulative_horizon_cohort(
            base_cohort,
            horizon_years=years,
            status_by_wave=statuses,
        )
        for years in HORIZON_YEARS
    }
    return cohorts
