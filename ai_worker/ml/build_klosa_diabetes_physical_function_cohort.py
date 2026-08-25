"""Add stable t0 ADL, IADL, grip-strength, mobility, and fall features."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_worker.ml.build_klosa_diabetes_cohort import _numeric, load_transition
from ai_worker.ml.build_klosa_diabetes_extended_cohort import COMORBIDITY_SOURCES
from ai_worker.ml.build_klosa_diabetes_mental_rhythm_cohort import (
    MENTAL_RHYTHM_EXTENDED_FEATURES,
    MENTAL_RHYTHM_SOURCES,
    build_mental_rhythm_transition,
)
from ai_worker.ml.build_klosa_diabetes_socioeconomic_cohort import _code_category

PHYSICAL_FUNCTION_NUMERIC_FEATURES = [
    "adl_limitation_count",
    "iadl_limitation_count",
    "mean_grip_strength_kg",
]
PHYSICAL_FUNCTION_CATEGORICAL_FEATURES = [
    "recent_fall_history",
    "nearby_outing_assistance",
]
PHYSICAL_FUNCTION_FEATURES = [
    *PHYSICAL_FUNCTION_NUMERIC_FEATURES,
    *PHYSICAL_FUNCTION_CATEGORICAL_FEATURES,
]
PHYSICAL_FUNCTION_EXTENDED_FEATURES = [
    *MENTAL_RHYTHM_EXTENDED_FEATURES,
    *PHYSICAL_FUNCTION_FEATURES,
]


def _adl_source(baseline_wave: int) -> str:
    prefix = f"w{baseline_wave:02d}"
    return f"{prefix}Adl" if baseline_wave == 1 else f"{prefix}adl"


def build_physical_function_transition(
    t0: pd.DataFrame,
    t1: pd.DataFrame,
    baseline_wave: int,
) -> pd.DataFrame:
    cohort = build_mental_rhythm_transition(t0, t1, baseline_wave)
    prefix = f"w{baseline_wave:02d}"
    adl = _numeric(t0[_adl_source(baseline_wave)]).where(lambda values: values.between(0, 7))
    iadl = _numeric(t0[f"{prefix}iadl"]).where(lambda values: values.between(0, 10))
    grip = _numeric(t0[f"{prefix}mgrip"]).where(lambda values: values.between(1, 80))
    additions = pd.DataFrame(
        {
            "pid": t0["pid"],
            "adl_limitation_count": adl,
            "iadl_limitation_count": iadl,
            "mean_grip_strength_kg": grip,
            "recent_fall_history": _numeric(t0[f"{prefix}C056"]).map({1: True, 5: False}),
            "nearby_outing_assistance": _code_category(t0[f"{prefix}C212"]),
        }
    )
    return cohort.merge(additions, on="pid", how="left", validate="many_to_one")


def physical_function_extra_columns(baseline_wave: int) -> list[str]:
    prefix = f"w{baseline_wave:02d}"
    return [
        *(f"{prefix}{suffix}" for suffix in COMORBIDITY_SOURCES.values()),
        f"{prefix}edu",
        f"{prefix}marital",
        f"{prefix}hhsize",
        f"{prefix}hhinc",
        *(f"{prefix}{suffix}" for suffix in MENTAL_RHYTHM_SOURCES.values()),
        _adl_source(baseline_wave),
        f"{prefix}iadl",
        f"{prefix}mgrip",
        f"{prefix}C056",
        f"{prefix}C212",
    ]


def build_physical_function_cohort(data_dir: Path) -> pd.DataFrame:
    transitions = []
    for baseline_wave in range(1, 10):
        t0, t1 = load_transition(
            data_dir,
            baseline_wave,
            extra_t0_columns=physical_function_extra_columns(baseline_wave),
        )
        transitions.append(build_physical_function_transition(t0, t1, baseline_wave))
    return pd.concat(transitions, ignore_index=True)
