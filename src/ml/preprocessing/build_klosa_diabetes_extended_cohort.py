"""Add safe t0 comorbidity features to the pooled diabetes cohort."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ml.preprocessing.build_klosa_diabetes_cohort import (
    WEB_MODEL_FEATURES,
    _numeric,
    build_transition,
    load_transition,
)

COMORBIDITY_SOURCES = {
    "hypertension_diagnosis": "chronic_a",
    "cancer_diagnosis": "chronic_c",
    "chronic_lung_disease_diagnosis": "chronic_d",
    "liver_disease_diagnosis": "chronic_e",
    "heart_disease_diagnosis": "chronic_f",
    "cerebrovascular_disease_diagnosis": "chronic_g",
    "psychiatric_disease_diagnosis": "chronic_h",
    "arthritis_rheumatism_diagnosis": "chronic_i",
}
COMORBIDITY_FEATURES = list(COMORBIDITY_SOURCES)
EXTENDED_MODEL_FEATURES = [*WEB_MODEL_FEATURES, *COMORBIDITY_FEATURES]


def _diagnosis_category(series: pd.Series) -> pd.Series:
    """Map KLoSA current diagnosis status without treating unknown as no."""

    return _numeric(series).map({1: "yes", 5: "no"})


def build_extended_transition(
    t0: pd.DataFrame,
    t1: pd.DataFrame,
    baseline_wave: int,
) -> pd.DataFrame:
    base = build_transition(t0, t1, baseline_wave)
    prefix = f"w{baseline_wave:02d}"
    additions = pd.DataFrame({"pid": t0["pid"]})
    for feature, suffix in COMORBIDITY_SOURCES.items():
        additions[feature] = _diagnosis_category(t0[f"{prefix}{suffix}"])
    return base.merge(additions, on="pid", how="left", validate="many_to_one")


def build_extended_cohort(data_dir: Path) -> pd.DataFrame:
    transitions = []
    for baseline_wave in range(1, 10):
        prefix = f"w{baseline_wave:02d}"
        extra_columns = [f"{prefix}{suffix}" for suffix in COMORBIDITY_SOURCES.values()]
        t0, t1 = load_transition(
            data_dir,
            baseline_wave,
            extra_t0_columns=extra_columns,
        )
        transitions.append(build_extended_transition(t0, t1, baseline_wave))
    return pd.concat(transitions, ignore_index=True)
