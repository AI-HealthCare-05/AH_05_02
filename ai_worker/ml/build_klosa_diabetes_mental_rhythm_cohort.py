"""Add stable t0 mental-health, sleep, and wellbeing features."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_worker.ml.build_klosa_diabetes_cohort import _numeric, load_transition
from ai_worker.ml.build_klosa_diabetes_extended_cohort import COMORBIDITY_SOURCES
from ai_worker.ml.build_klosa_diabetes_socioeconomic_cohort import (
    SOCIOECONOMIC_EXTENDED_FEATURES,
    _code_category,
    build_socioeconomic_transition,
)

MENTAL_RHYTHM_NUMERIC_FEATURES = [
    "health_satisfaction_score",
    "economic_satisfaction_score",
    "overall_quality_of_life_score",
]
MENTAL_RHYTHM_CATEGORICAL_FEATURES = [
    "depressed_feeling_last_week",
    "sleep_difficulty_last_week",
]
MENTAL_RHYTHM_FEATURES = [
    *MENTAL_RHYTHM_NUMERIC_FEATURES,
    *MENTAL_RHYTHM_CATEGORICAL_FEATURES,
]
MENTAL_RHYTHM_EXTENDED_FEATURES = [
    *SOCIOECONOMIC_EXTENDED_FEATURES,
    *MENTAL_RHYTHM_FEATURES,
]

MENTAL_RHYTHM_SOURCES = {
    "depressed_feeling_last_week": "C144",
    "sleep_difficulty_last_week": "C148",
    "health_satisfaction_score": "G026",
    "economic_satisfaction_score": "G027",
    "overall_quality_of_life_score": "G030",
}


def build_mental_rhythm_transition(
    t0: pd.DataFrame,
    t1: pd.DataFrame,
    baseline_wave: int,
) -> pd.DataFrame:
    cohort = build_socioeconomic_transition(t0, t1, baseline_wave)
    prefix = f"w{baseline_wave:02d}"
    additions = pd.DataFrame(
        {
            "pid": t0["pid"],
            "depressed_feeling_last_week": _code_category(t0[f"{prefix}C144"]),
            "sleep_difficulty_last_week": _code_category(t0[f"{prefix}C148"]),
            "health_satisfaction_score": _numeric(t0[f"{prefix}G026"]),
            "economic_satisfaction_score": _numeric(t0[f"{prefix}G027"]),
            "overall_quality_of_life_score": _numeric(t0[f"{prefix}G030"]),
        }
    )
    for feature in MENTAL_RHYTHM_NUMERIC_FEATURES:
        additions[feature] = additions[feature].where(additions[feature].between(0, 100))
    return cohort.merge(additions, on="pid", how="left", validate="many_to_one")


def build_mental_rhythm_cohort(data_dir: Path) -> pd.DataFrame:
    transitions = []
    for baseline_wave in range(1, 10):
        prefix = f"w{baseline_wave:02d}"
        extra_columns = [
            *(f"{prefix}{suffix}" for suffix in COMORBIDITY_SOURCES.values()),
            f"{prefix}edu",
            f"{prefix}marital",
            f"{prefix}hhsize",
            f"{prefix}hhinc",
            *(f"{prefix}{suffix}" for suffix in MENTAL_RHYTHM_SOURCES.values()),
        ]
        t0, t1 = load_transition(
            data_dir,
            baseline_wave,
            extra_t0_columns=extra_columns,
        )
        transitions.append(build_mental_rhythm_transition(t0, t1, baseline_wave))
    return pd.concat(transitions, ignore_index=True)
