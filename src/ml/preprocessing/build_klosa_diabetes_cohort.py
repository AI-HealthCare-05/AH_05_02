"""Build the pooled KLoSA t0/t1 diabetes-incidence person-period cohort."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

TARGET = "target_diabetes_incident_next_wave"

WEB_MODEL_FEATURES = [
    "age",
    "sex",
    "bmi",
    "smoking_status",
    "current_drinker",
    "regular_exercise",
    "exercise_days_per_week",
    "exercise_minutes",
]

FORBIDDEN_MODEL_COLUMNS = {
    "pid",
    "baseline_wave",
    "outcome_wave",
    "interview_date_t0",
    "interview_date_t1",
    "follow_up_days",
    "diabetes_status_t0",
    "diabetes_status_t1",
    "interval_diagnosis_t1",
    TARGET,
}


def _numeric(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.mask(values < 0)


def _interview_date(frame: pd.DataFrame, prefix: str) -> pd.Series:
    return pd.to_datetime(
        {
            "year": frame[f"{prefix}mniw_y"],
            "month": frame[f"{prefix}mniw_m"],
            "day": frame[f"{prefix}mniw_d"],
        },
        errors="coerce",
    )


def load_transition(
    data_dir: Path,
    baseline_wave: int,
    extra_t0_columns: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if baseline_wave not in range(1, 10):
        raise ValueError("baseline_wave must be between 1 and 9")

    outcome_wave = baseline_wave + 1
    t0_prefix = f"w{baseline_wave:02d}"
    t1_prefix = f"w{outcome_wave:02d}"
    alcohol_column = "w01Alc" if baseline_wave == 1 else f"{t0_prefix}alc"

    t0_columns = [
        "pid",
        f"{t0_prefix}A002_age",
        f"{t0_prefix}gender1",
        f"{t0_prefix}C105",
        f"{t0_prefix}C107",
        f"{t0_prefix}C108",
        f"{t0_prefix}C111",
        f"{t0_prefix}C112",
        f"{t0_prefix}smoke",
        alcohol_column,
        f"{t0_prefix}chronic_b",
        f"{t0_prefix}mniw_y",
        f"{t0_prefix}mniw_m",
        f"{t0_prefix}mniw_d",
    ]
    t0_columns.extend(extra_t0_columns or [])
    t1_columns = [
        "pid",
        f"{t1_prefix}chronic_b",
        f"{t1_prefix}C011",
        f"{t1_prefix}mniw_y",
        f"{t1_prefix}mniw_m",
        f"{t1_prefix}mniw_d",
    ]

    t0 = pd.read_stata(
        data_dir / f"str{baseline_wave:02d}_20260413.dta",
        columns=t0_columns,
        convert_categoricals=False,
    )
    t1 = pd.read_stata(
        data_dir / f"str{outcome_wave:02d}_20260413.dta",
        columns=t1_columns,
        convert_categoricals=False,
    )
    return t0, t1


def build_transition(t0: pd.DataFrame, t1: pd.DataFrame, baseline_wave: int) -> pd.DataFrame:
    outcome_wave = baseline_wave + 1
    t0_prefix = f"w{baseline_wave:02d}"
    t1_prefix = f"w{outcome_wave:02d}"
    alcohol_column = "w01Alc" if baseline_wave == 1 else f"{t0_prefix}alc"

    if t0["pid"].duplicated().any() or t1["pid"].duplicated().any():
        raise ValueError(f"Duplicate PID found in transition {baseline_wave}->{outcome_wave}")

    left = pd.DataFrame(
        {
            "pid": t0["pid"],
            "age": _numeric(t0[f"{t0_prefix}A002_age"]),
            "sex_code": _numeric(t0[f"{t0_prefix}gender1"]),
            "height_cm": _numeric(t0[f"{t0_prefix}C107"]),
            "weight_kg": _numeric(t0[f"{t0_prefix}C105"]),
            "smoking_code": _numeric(t0[f"{t0_prefix}smoke"]),
            "alcohol_code": _numeric(t0[alcohol_column]),
            "exercise_code": _numeric(t0[f"{t0_prefix}C108"]),
            "exercise_days_per_week": _numeric(t0[f"{t0_prefix}C111"]),
            "exercise_minutes": _numeric(t0[f"{t0_prefix}C112"]),
            "diabetes_status_t0": t0[f"{t0_prefix}chronic_b"],
            "interview_date_t0": _interview_date(t0, t0_prefix),
        }
    )
    right = pd.DataFrame(
        {
            "pid": t1["pid"],
            "diabetes_status_t1": t1[f"{t1_prefix}chronic_b"],
            "interval_diagnosis_t1": t1[f"{t1_prefix}C011"],
            "interview_date_t1": _interview_date(t1, t1_prefix),
        }
    )
    linked = left.merge(right, on="pid", how="inner", validate="one_to_one")
    cohort = linked.loc[linked["diabetes_status_t0"].eq(5) & linked["diabetes_status_t1"].isin([1, 5])].copy()

    cohort["baseline_wave"] = baseline_wave
    cohort["outcome_wave"] = outcome_wave
    cohort["follow_up_days"] = (cohort["interview_date_t1"] - cohort["interview_date_t0"]).dt.days
    cohort[TARGET] = cohort["diabetes_status_t1"].eq(1).astype("int8")

    cohort["sex"] = cohort["sex_code"].map({1: "male", 5: "female"})
    cohort["smoking_status"] = cohort["smoking_code"].map({0: "never", 1: "former", 2: "current"})
    cohort["current_drinker"] = cohort["alcohol_code"].map({1: True, 2: False, 3: False})
    cohort["regular_exercise"] = cohort["exercise_code"].map({1: True, 5: False})

    plausible_height = cohort["height_cm"].where(cohort["height_cm"].between(120, 220))
    plausible_weight = cohort["weight_kg"].where(cohort["weight_kg"].between(25, 250))
    cohort["bmi"] = plausible_weight / (plausible_height / 100) ** 2

    no_regular_exercise = cohort["regular_exercise"].eq(False)  # noqa: E712
    cohort.loc[no_regular_exercise, "exercise_days_per_week"] = 0
    cohort.loc[no_regular_exercise, "exercise_minutes"] = 0
    cohort.loc[
        ~cohort["exercise_days_per_week"].between(0, 7),
        "exercise_days_per_week",
    ] = pd.NA
    cohort.loc[~cohort["exercise_minutes"].between(0, 720), "exercise_minutes"] = pd.NA

    columns = [
        "pid",
        "baseline_wave",
        "outcome_wave",
        "interview_date_t0",
        "interview_date_t1",
        "follow_up_days",
        "diabetes_status_t0",
        "diabetes_status_t1",
        "interval_diagnosis_t1",
        "height_cm",
        "weight_kg",
        *WEB_MODEL_FEATURES,
        TARGET,
    ]
    return cohort[columns].reset_index(drop=True)


def assert_model_matrix_is_safe(feature_names: list[str]) -> None:
    forbidden = sorted(set(feature_names) & FORBIDDEN_MODEL_COLUMNS)
    unknown = sorted(set(feature_names) - set(WEB_MODEL_FEATURES))
    if forbidden or unknown:
        raise ValueError(f"Unsafe model matrix; forbidden={forbidden}, outside_allowlist={unknown}")


def build_cohort(data_dir: Path) -> pd.DataFrame:
    transitions = []
    for baseline_wave in range(1, 10):
        t0, t1 = load_transition(data_dir, baseline_wave)
        transitions.append(build_transition(t0, t1, baseline_wave))
    cohort = pd.concat(transitions, ignore_index=True)
    assert_model_matrix_is_safe(WEB_MODEL_FEATURES)
    return cohort


def summarize(cohort: pd.DataFrame) -> dict:
    def group_summary(frame: pd.DataFrame) -> dict:
        events = int(frame[TARGET].sum())
        return {
            "person_periods": int(len(frame)),
            "unique_people": int(frame["pid"].nunique()),
            "events": events,
            "non_events": int(len(frame) - events),
            "event_rate": float(frame[TARGET].mean()),
            "age_min": int(frame["age"].min()),
            "age_max": int(frame["age"].max()),
        }

    transitions = []
    for (baseline_wave, outcome_wave), frame in cohort.groupby(["baseline_wave", "outcome_wave"], sort=True):
        events = int(frame[TARGET].sum())
        transitions.append(
            {
                "transition": f"{baseline_wave}_to_{outcome_wave}",
                "person_periods": int(len(frame)),
                "events": events,
                "non_events": int(len(frame) - events),
                "event_rate": float(frame[TARGET].mean()),
            }
        )

    follow_up = cohort["follow_up_days"].quantile([0.05, 0.50, 0.95])
    return {
        "all_available": group_summary(cohort),
        "age_40_plus": group_summary(cohort.loc[cohort["age"].ge(40)]),
        "follow_up_days": {
            "p05": float(follow_up.loc[0.05]),
            "median": float(follow_up.loc[0.50]),
            "p95": float(follow_up.loc[0.95]),
            "missing": int(cohort["follow_up_days"].isna().sum()),
        },
        "transitions": transitions,
        "features": WEB_MODEL_FEATURES,
        "target": TARGET,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/interim/source_extract/klosa/20260413"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional local .parquet output; never commit person-level data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cohort = build_cohort(args.data_dir)
    if args.output:
        if args.output.suffix != ".parquet":
            raise ValueError("Output must use the .parquet extension")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        cohort.to_parquet(args.output, index=False)
    print(json.dumps(summarize(cohort), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
