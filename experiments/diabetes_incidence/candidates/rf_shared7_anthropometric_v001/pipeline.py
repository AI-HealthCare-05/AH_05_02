"""Refit the tuned RF25 configuration with seven anthropometric features."""

from __future__ import annotations

import json
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from src.ml.evaluation.audit_service_release import metrics, select

from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET

FEATURES = [
    "age",
    "height_cm",
    "weight_kg",
    "bmi",
    "sex",
    "smoking_status",
    "education_level",
]
NUMERIC_FEATURES = ["age", "height_cm", "weight_kg", "bmi"]
CATEGORICAL_FEATURES = ["sex", "smoking_status", "education_level"]
VALID_RANGES = {
    "age": (40, 110),
    "height_cm": (120, 220),
    "weight_kg": (25, 250),
    "bmi": (10, 70),
}


def _sanitize(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame[FEATURES].copy()
    for column, (lower, upper) in VALID_RANGES.items():
        values = pd.to_numeric(result[column], errors="coerce")
        result[column] = values.where(values.between(lower, upper))
    return result


def _pipeline() -> Pipeline:
    preprocessing = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline([("imputer", SimpleImputer(strategy="median", add_indicator=True))]),
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    classifier = RandomForestClassifier(
        n_estimators=500,
        max_depth=8,
        min_samples_leaf=39,
        max_samples=0.7,
        bootstrap=True,
        criterion="log_loss",
        ccp_alpha=1e-5,
        max_features="sqrt",
        class_weight=None,
        random_state=42,
        n_jobs=1,
    )
    return Pipeline([("preprocessing", preprocessing), ("classifier", classifier)])


def run_experiment(context: dict[str, Any]) -> dict[str, Any]:
    root, out = context["root"], context["run_dir"]
    cohort = pd.read_pickle(root / "data/processed/official_v1/klosa_diabetes_incidence_stage3_25features_v1.pkl")
    train, validation, test = split_grouped_cohort(cohort, random_state=42)
    assert not (
        set(train.pid) & set(validation.pid) or set(train.pid) & set(test.pid) or set(validation.pid) & set(test.pid)
    )

    pipeline = _pipeline()
    pipeline.fit(_sanitize(train), train[TARGET])
    validation_probability = pipeline.predict_proba(_sanitize(validation))[:, 1]
    threshold = select(validation[TARGET].to_numpy(int), validation_probability, 0.43)
    test_probability = pipeline.predict_proba(_sanitize(test))[:, 1]
    result = {
        "features": FEATURES,
        "parameters": pipeline.named_steps["classifier"].get_params(),
        "validation": metrics(validation[TARGET].to_numpy(int), validation_probability, threshold),
        "test": metrics(test[TARGET].to_numpy(int), test_probability, threshold),
    }
    artifact = {
        "pipeline": pipeline,
        "features": FEATURES,
        "valid_ranges": VALID_RANGES,
        "threshold": threshold,
        "feature_schema_version": "klosa_shared7_anthropometric_v1",
        "model_version": "rf-shared7-anthropometric-v1",
        "operational_model_activated": False,
    }
    joblib.dump(artifact, out / "model.joblib", compress=3)
    restored = joblib.load(out / "model.joblib")
    assert (
        restored["pipeline"].predict_proba(_sanitize(test).iloc[:3]) == pipeline.predict_proba(_sanitize(test).iloc[:3])
    ).all()
    (out / "comparison.json").write_text(json.dumps(result, indent=2))

    measured = result["test"]
    return {
        "artifact": "model.joblib",
        "notes": "Research-only shared-seven anthropometric RF refit; not activated for service.",
        "metrics": {
            "recall": measured["recall"],
            "specificity": measured["specificity"],
            "auroc": measured["auroc"],
            "auprc": measured["auprc"],
            "brier_score": measured["brier"],
            "threshold": threshold,
            "f1": 2 * measured["tp"] / (2 * measured["tp"] + measured["fp"] + measured["fn"]),
            "confusion_matrix": {
                "true_positive": measured["tp"],
                "false_positive": measured["fp"],
                "true_negative": measured["tn"],
                "false_negative": measured["fn"],
            },
        },
    }
