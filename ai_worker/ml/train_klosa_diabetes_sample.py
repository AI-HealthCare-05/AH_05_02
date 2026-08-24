"""Train a minimal KLoSA wave 9 -> 10 diabetes-incidence baseline.

This is an executable sample, not the final pooled-wave production cohort.
It uses only wave-9 inputs and predicts a newly reported diabetes diagnosis at
wave 10 among people reporting no diabetes diagnosis at wave 9.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET = "target_diabetes_incident_next_wave"
ID_COLUMN = "pid"

NUMERIC_FEATURES = [
    "age",
    "bmi",
    "exercise_days_per_week",
    "exercise_minutes",
]
CATEGORICAL_FEATURES = [
    "sex",
    "smoking_status",
    "current_drinker",
    "regular_exercise",
]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

FORBIDDEN_FEATURE_FRAGMENTS = (
    "chronic_b",
    "c011",
    "c012",
    "c014",
    "c015",
    "c343",
    "target",
    "pid",
    "hhid",
)

WAVE9_COLUMNS = [
    "pid",
    "w09A002_age",
    "w09gender1",
    "w09C105",
    "w09C107",
    "w09C108",
    "w09C111",
    "w09C112",
    "w09smoke",
    "w09alc",
    "w09chronic_b",
]
WAVE10_COLUMNS = ["pid", "w10chronic_b"]


def _replace_special_missing(series: pd.Series) -> pd.Series:
    """Convert KLoSA negative special codes to missing values."""

    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.mask(numeric < 0)


def assert_no_leakage(feature_names: list[str]) -> None:
    """Fail closed if a target, identifier, or diagnosis proxy is selected."""

    leaking = [
        feature
        for feature in feature_names
        if any(fragment in feature.lower() for fragment in FORBIDDEN_FEATURE_FRAGMENTS)
    ]
    if leaking:
        raise ValueError(f"Forbidden leakage or identifier features: {leaking}")


def build_wave_9_10_cohort(wave9: pd.DataFrame, wave10: pd.DataFrame) -> pd.DataFrame:
    """Create the eligible wave 9 -> 10 person-level modeling cohort."""

    if wave9[ID_COLUMN].duplicated().any() or wave10[ID_COLUMN].duplicated().any():
        raise ValueError("Each wave must contain at most one row per PID.")

    merged = wave9.merge(
        wave10[[ID_COLUMN, "w10chronic_b"]],
        on=ID_COLUMN,
        how="inner",
        validate="one_to_one",
    )

    # 1=yes, 5=no. Missing or unobserved t1 is never assigned to class 0.
    eligible = merged.loc[
        merged["w09chronic_b"].eq(5)
        & merged["w10chronic_b"].isin([1, 5])
    ].copy()
    eligible[TARGET] = eligible["w10chronic_b"].eq(1).astype("int8")

    height_cm = _replace_special_missing(eligible["w09C107"])
    weight_kg = _replace_special_missing(eligible["w09C105"])
    plausible_height = height_cm.where(height_cm.between(120, 220))
    plausible_weight = weight_kg.where(weight_kg.between(25, 250))

    eligible["age"] = _replace_special_missing(eligible["w09A002_age"])
    eligible["bmi"] = plausible_weight / (plausible_height / 100) ** 2
    eligible["sex"] = _replace_special_missing(eligible["w09gender1"]).astype("Int64")
    eligible["smoking_status"] = _replace_special_missing(
        eligible["w09smoke"]
    ).astype("Int64")
    eligible["current_drinker"] = _replace_special_missing(
        eligible["w09alc"]
    ).astype("Int64")
    eligible["regular_exercise"] = _replace_special_missing(
        eligible["w09C108"]
    ).astype("Int64")

    exercise_days = _replace_special_missing(eligible["w09C111"])
    exercise_minutes = _replace_special_missing(eligible["w09C112"])
    no_regular_exercise = eligible["regular_exercise"].eq(5)
    eligible["exercise_days_per_week"] = exercise_days.mask(
        no_regular_exercise, 0
    )
    eligible["exercise_minutes"] = exercise_minutes.mask(no_regular_exercise, 0)

    return eligible[[ID_COLUMN, *FEATURES, TARGET]].reset_index(drop=True)


def make_logistic_pipeline(class_weight: str | None = "balanced") -> Pipeline:
    """Build preprocessing and a class-weighted logistic baseline."""

    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("one_hot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessing = ColumnTransformer(
        transformers=[
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ]
    )
    classifier = LogisticRegression(
        class_weight=class_weight,
        max_iter=2_000,
        random_state=42,
    )
    return Pipeline(
        steps=[("preprocessing", preprocessing), ("classifier", classifier)]
    )


def split_cohort(
    cohort: pd.DataFrame, random_state: int
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create reproducible person-level 70/15/15 splits."""

    train, remainder = train_test_split(
        cohort,
        test_size=0.30,
        random_state=random_state,
        stratify=cohort[TARGET],
    )
    validation, test = train_test_split(
        remainder,
        test_size=0.50,
        random_state=random_state,
        stratify=remainder[TARGET],
    )

    pid_sets = [set(frame[ID_COLUMN]) for frame in (train, validation, test)]
    if any(pid_sets[i] & pid_sets[j] for i, j in ((0, 1), (0, 2), (1, 2))):
        raise AssertionError("A PID appeared in more than one split.")
    return train, validation, test


def choose_threshold(
    y_true: pd.Series, probabilities: np.ndarray, minimum_recall: float = 0.80
) -> float:
    """Choose the most specific validation threshold meeting target recall."""

    candidates = np.unique(np.r_[0.0, probabilities, 1.0])
    selected = 0.5
    selected_specificity = -1.0
    for threshold in candidates:
        predicted = (probabilities >= threshold).astype(int)
        recall = recall_score(y_true, predicted, zero_division=0)
        tn, fp, _, _ = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
        specificity = tn / (tn + fp) if (tn + fp) else 0.0
        if recall >= minimum_recall and specificity > selected_specificity:
            selected = float(threshold)
            selected_specificity = specificity
    return selected


def evaluate(
    y_true: pd.Series, probabilities: np.ndarray, threshold: float
) -> dict[str, Any]:
    predicted = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    sensitivity = float(recall_score(y_true, predicted, zero_division=0))
    return {
        "n": int(len(y_true)),
        "events": int(y_true.sum()),
        "event_rate": float(y_true.mean()),
        "auprc": float(average_precision_score(y_true, probabilities)),
        "auroc": float(roc_auc_score(y_true, probabilities)),
        "recall": sensitivity,
        "sensitivity": sensitivity,
        "specificity": float(tn / (tn + fp)) if (tn + fp) else None,
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "brier_score": float(brier_score_loss(y_true, probabilities)),
        "threshold": float(threshold),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def run_training(
    data_dir: Path, output_dir: Path, random_state: int = 42
) -> dict[str, Any]:
    assert_no_leakage(FEATURES)

    wave9_path = data_dir / "Lt09_20260413.dta"
    wave10_path = data_dir / "Lt10_20260413.dta"
    for path in (wave9_path, wave10_path):
        if not path.exists():
            raise FileNotFoundError(f"Required KLoSA file not found: {path}")

    wave9 = pd.read_stata(
        wave9_path, columns=WAVE9_COLUMNS, convert_categoricals=False
    )
    wave10 = pd.read_stata(
        wave10_path, columns=WAVE10_COLUMNS, convert_categoricals=False
    )
    cohort = build_wave_9_10_cohort(wave9, wave10)
    train, validation, test = split_cohort(cohort, random_state=random_state)

    x_train, y_train = train[FEATURES], train[TARGET]
    x_validation, y_validation = validation[FEATURES], validation[TARGET]
    x_test, y_test = test[FEATURES], test[TARGET]

    dummy = DummyClassifier(strategy="prior")
    dummy.fit(x_train, y_train)
    dummy_probabilities = dummy.predict_proba(x_test)[:, 1]

    calibrated_model = CalibratedClassifierCV(
        estimator=make_logistic_pipeline(),
        method="sigmoid",
        cv=3,
    )
    calibrated_model.fit(x_train, y_train)
    validation_probabilities = calibrated_model.predict_proba(x_validation)[:, 1]
    threshold = choose_threshold(y_validation, validation_probabilities)
    test_probabilities = calibrated_model.predict_proba(x_test)[:, 1]

    metrics = {
        "sample_notice": (
            "Wave 9->10 executable baseline only; final production training must "
            "apply the full entry-to-t0 observed-history rule across all waves."
        ),
        "target": "next_adjacent_wave_incident_diabetes_diagnosis",
        "features": FEATURES,
        "cohort": {
            "n": int(len(cohort)),
            "events": int(cohort[TARGET].sum()),
            "event_rate": float(cohort[TARGET].mean()),
        },
        "splits": {
            "train": int(len(train)),
            "validation": int(len(validation)),
            "test": int(len(test)),
        },
        "dummy_test": {
            "auprc": float(average_precision_score(y_test, dummy_probabilities)),
            "brier_score": float(brier_score_loss(y_test, dummy_probabilities)),
        },
        "logistic_test": evaluate(y_test, test_probabilities, threshold),
        "threshold_selection": {
            "source": "validation_only",
            "minimum_recall": 0.80,
        },
        "random_state": random_state,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    joblib.dump(calibrated_model, output_dir / "model.joblib")
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/raw/klosa/20260413/extracted"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("models/samples/klosa_diabetes_incidence_9_10"),
    )
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = run_training(args.data_dir, args.output_dir, args.random_state)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
