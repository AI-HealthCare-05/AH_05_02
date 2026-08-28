"""Add stable t0 socioeconomic features to the comorbidity-expanded cohort."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.ml.preprocessing.build_klosa_diabetes_cohort import _numeric, load_transition
from src.ml.preprocessing.build_klosa_diabetes_extended_cohort import (
    COMORBIDITY_SOURCES,
    EXTENDED_MODEL_FEATURES,
    build_extended_transition,
)

SOCIOECONOMIC_NUMERIC_FEATURES = ["log_household_income"]
SOCIOECONOMIC_CATEGORICAL_FEATURES = [
    "education_level",
    "marital_status",
    "household_structure",
]
SOCIOECONOMIC_FEATURES = [
    *SOCIOECONOMIC_NUMERIC_FEATURES,
    *SOCIOECONOMIC_CATEGORICAL_FEATURES,
]
SOCIOECONOMIC_EXTENDED_FEATURES = [
    *EXTENDED_MODEL_FEATURES,
    *SOCIOECONOMIC_FEATURES,
]


def _code_category(series: pd.Series) -> pd.Series:
    numeric = _numeric(series)
    return numeric.map(lambda value: f"code_{int(value)}" if pd.notna(value) else np.nan)


def build_socioeconomic_transition(
    t0: pd.DataFrame,
    t1: pd.DataFrame,
    baseline_wave: int,
) -> pd.DataFrame:
    cohort = build_extended_transition(t0, t1, baseline_wave)
    prefix = f"w{baseline_wave:02d}"
    household_size = _numeric(t0[f"{prefix}hhsize"])
    household_income = _numeric(t0[f"{prefix}hhinc"])
    additions = pd.DataFrame(
        {
            "pid": t0["pid"],
            "education_level": _code_category(t0[f"{prefix}edu"]),
            "marital_status": _code_category(t0[f"{prefix}marital"]),
            "household_structure": household_size.map(
                lambda value: (
                    "single_person" if value == 1 else "multi_person" if pd.notna(value) and value > 1 else np.nan
                )
            ),
            "log_household_income": np.log1p(household_income),
        }
    )
    return cohort.merge(additions, on="pid", how="left", validate="many_to_one")


def build_socioeconomic_cohort(data_dir: Path) -> pd.DataFrame:
    transitions = []
    for baseline_wave in range(1, 10):
        prefix = f"w{baseline_wave:02d}"
        extra_columns = [
            *(f"{prefix}{suffix}" for suffix in COMORBIDITY_SOURCES.values()),
            f"{prefix}edu",
            f"{prefix}marital",
            f"{prefix}hhsize",
            f"{prefix}hhinc",
        ]
        t0, t1 = load_transition(
            data_dir,
            baseline_wave,
            extra_t0_columns=extra_columns,
        )
        transitions.append(build_socioeconomic_transition(t0, t1, baseline_wave))
    return pd.concat(transitions, ignore_index=True)
