"""Reusable template for KLoSA discrete-time diabetes incidence models.

The module expects a cleaned *long* KLoSA panel: one row per participant and
wave.  It converts adjacent observations into person-period rows, fits pooled
binary classifiers for the conditional interval hazard, and converts predicted
hazards into a cumulative risk-signal curve.

This is research/screening code.  Its output is not a diagnosis, prescription,
causal treatment effect, or an annual probability.  KLoSA intervals are roughly
two years, so horizons must be labelled as approximate two-year intervals.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.base import ClassifierMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

LEAKAGE_DENYLIST = frozenset(
    {
        "diabetes_dx_next",
        "future_diabetes_diagnosis",
        "future_wave_measurements",
        "glucose_lowering_medication_at_followup",
    }
)


@dataclass(frozen=True)
class PanelContract:
    """Column contract for a cleaned long-format KLoSA panel."""

    pid: str = "pid"
    time: str = "survey_year"
    diagnosis: str = "diabetes_dx"
    event: str = "event_next_interval"
    interval_index: str = "interval_index"


DEFAULT_PANEL_CONTRACT = PanelContract()


def _as_binary_diagnosis(series: pd.Series) -> pd.Series:
    """Accept only an already-normalised 0/1 diagnosis variable."""
    numeric = pd.to_numeric(series, errors="coerce")
    invalid = numeric.dropna().loc[~numeric.dropna().isin([0, 1])]
    if not invalid.empty:
        raise ValueError("diagnosis must be normalised to 0/1 before person-period creation")
    return numeric


def make_person_period(
    panel: pd.DataFrame,
    feature_columns: Iterable[str],
    contract: PanelContract = DEFAULT_PANEL_CONTRACT,
) -> pd.DataFrame:
    """Create adjacent-wave at-risk rows without using future measurements.

    Each output row uses features observed at the start of an interval.  The
    target is 1 only when the participant was undiagnosed at interval start and
    first reports diabetes at the immediately following observation.  Rows at
    and after the first observed diagnosis are excluded.
    """
    features = list(feature_columns)
    required = {contract.pid, contract.time, contract.diagnosis, *features}
    missing = sorted(required.difference(panel.columns))
    if missing:
        raise ValueError(f"missing panel columns: {missing}")
    leaked = sorted(set(features).intersection(LEAKAGE_DENYLIST | {contract.diagnosis}))
    if leaked:
        raise ValueError(f"target/leakage columns cannot be model features: {leaked}")

    frame = panel.loc[:, list(required)].copy()
    frame[contract.diagnosis] = _as_binary_diagnosis(frame[contract.diagnosis])
    if frame.duplicated([contract.pid, contract.time]).any():
        raise ValueError("panel contains duplicate pid-time rows")
    frame = frame.sort_values([contract.pid, contract.time], kind="stable")

    rows: list[dict[str, object]] = []
    for pid, participant in frame.groupby(contract.pid, sort=False, dropna=False):
        participant = participant.reset_index(drop=True)
        at_risk_index = 0
        for index in range(len(participant) - 1):
            current = participant.iloc[index]
            followup = participant.iloc[index + 1]
            current_dx = current[contract.diagnosis]
            followup_dx = followup[contract.diagnosis]

            if pd.isna(current_dx):
                continue
            if int(current_dx) == 1:
                break
            if pd.isna(followup_dx):
                continue

            at_risk_index += 1
            row = {name: current[name] for name in features}
            row.update(
                {
                    contract.pid: pid,
                    "interval_start": current[contract.time],
                    "interval_end": followup[contract.time],
                    contract.interval_index: at_risk_index,
                    contract.event: int(followup_dx == 1),
                }
            )
            rows.append(row)
            if int(followup_dx) == 1:
                break

    columns = [
        contract.pid,
        "interval_start",
        "interval_end",
        contract.interval_index,
        *features,
        contract.event,
    ]
    return pd.DataFrame(rows).reindex(columns=columns)


def build_preprocessor(numeric_features: Iterable[str], categorical_features: Iterable[str]) -> ColumnTransformer:
    """Return train-only fitted preprocessing shared by all candidates."""
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric, list(numeric_features)),
            ("categorical", categorical, list(categorical_features)),
        ]
    )


def candidate_models(
    numeric_features: Iterable[str],
    categorical_features: Iterable[str],
    seed: int = 20260901,
) -> Mapping[str, Pipeline]:
    """Build comparable pooled discrete-time hazard candidates."""
    numeric = list(numeric_features)
    categorical = list(categorical_features)

    def pipeline(model: ClassifierMixin) -> Pipeline:
        return Pipeline(
            [
                ("preprocessor", build_preprocessor(numeric, categorical)),
                ("model", model),
            ]
        )

    return {
        "discrete_logistic": pipeline(
            LogisticRegression(
                C=1.0,
                class_weight="balanced",
                max_iter=4000,
                random_state=seed,
            )
        ),
        "discrete_random_forest": pipeline(
            RandomForestClassifier(
                n_estimators=500,
                max_depth=12,
                min_samples_leaf=20,
                max_features="sqrt",
                class_weight="balanced_subsample",
                n_jobs=-1,
                random_state=seed,
            )
        ),
        "discrete_lightgbm": pipeline(
            LGBMClassifier(
                objective="binary",
                n_estimators=500,
                learning_rate=0.03,
                num_leaves=31,
                min_child_samples=40,
                class_weight="balanced",
                reg_lambda=2.0,
                verbosity=-1,
                n_jobs=-1,
                random_state=seed,
            )
        ),
    }


def hazards_to_curve(interval_hazards: Iterable[float], interval_years: float = 2.0) -> pd.DataFrame:
    """Convert conditional interval hazards to survival and cumulative risk."""
    hazards = np.asarray(list(interval_hazards), dtype=float)
    if hazards.ndim != 1 or len(hazards) == 0:
        raise ValueError("interval_hazards must be a non-empty one-dimensional sequence")
    if not np.isfinite(hazards).all() or ((hazards < 0) | (hazards > 1)).any():
        raise ValueError("every interval hazard must be a finite probability in [0, 1]")
    if interval_years <= 0:
        raise ValueError("interval_years must be positive")

    survival = np.cumprod(1.0 - hazards)
    return pd.DataFrame(
        {
            "interval_index": np.arange(1, len(hazards) + 1),
            "approx_horizon_years": np.arange(1, len(hazards) + 1) * interval_years,
            "interval_hazard": hazards,
            "survival_probability": survival,
            "cumulative_risk_signal": 1.0 - survival,
        }
    )


def predict_static_scenario_curve(
    model: Pipeline,
    baseline_features: Mapping[str, object],
    intervals: int,
    interval_years: float = 2.0,
) -> pd.DataFrame:
    """Predict a reference curve while holding baseline covariates constant.

    This is a model-based static-covariate scenario, not a causal lifestyle
    intervention effect.  Time-varying future health values are not fabricated.
    """
    if intervals < 1:
        raise ValueError("intervals must be at least 1")
    records = []
    for interval_index in range(1, intervals + 1):
        record = dict(baseline_features)
        record["interval_index"] = interval_index
        records.append(record)
    hazards = model.predict_proba(pd.DataFrame(records))[:, 1]
    return hazards_to_curve(hazards, interval_years=interval_years)
