"""Evaluate frozen RF25 when eight optional inputs are explicitly missing."""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from src.ml.evaluation.audit_service_release import metrics, select

from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET

MASKED_FEATURES = [
    "current_drinker",
    "liver_disease_diagnosis",
    "psychiatric_disease_diagnosis",
    "cancer_diagnosis",
    "household_structure",
    "cerebrovascular_disease_diagnosis",
    "heart_disease_diagnosis",
    "chronic_lung_disease_diagnosis",
]


def _masked(frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    values = frame[features].copy()
    values[MASKED_FEATURES] = np.nan
    return values


def run_experiment(context):
    root, run_dir = context["root"], context["run_dir"]
    source_path = root / "models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib"
    source = joblib.load(source_path)
    pipeline = source["pipeline"]
    pipeline.set_params(**{key: 1 for key in pipeline.get_params() if key.endswith("__n_jobs")})
    features = list(source["features"])
    assert set(MASKED_FEATURES) <= set(features)

    cohort = pd.read_pickle(root / "data/processed/official_v1/klosa_diabetes_incidence_stage3_25features_v1.pkl")
    train, validation, test = split_grouped_cohort(cohort, random_state=42)
    pid_sets = [set(frame.pid) for frame in (train, validation, test)]
    assert not any(pid_sets[a] & pid_sets[b] for a, b in ((0, 1), (0, 2), (1, 2)))

    validation_probability = pipeline.predict_proba(_masked(validation, features))[:, 1]
    threshold = select(validation[TARGET].to_numpy(int), validation_probability, 0.43)
    test_probability = pipeline.predict_proba(_masked(test, features))[:, 1]
    validation_metrics = metrics(validation[TARGET].to_numpy(int), validation_probability, threshold)
    test_metrics = metrics(test[TARGET].to_numpy(int), test_probability, threshold)

    artifact = {
        "pipeline": pipeline,
        "features": features,
        "provided_features": [feature for feature in features if feature not in MASKED_FEATURES],
        "masked_features": MASKED_FEATURES,
        "threshold": threshold,
        "source_model_version": source.get("model_version"),
        "model_version": "rf25-17input-imputed-research-v1",
        "feature_schema_version": "klosa_rf25_17provided_8imputed_v1",
        "operational_model_activated": False,
    }
    joblib.dump(artifact, run_dir / "model.joblib", compress=3)
    reloaded = joblib.load(run_dir / "model.joblib")
    expected = pipeline.predict_proba(_masked(test.iloc[:3], features))
    actual = reloaded["pipeline"].predict_proba(_masked(test.iloc[:3], features))
    assert np.array_equal(expected, actual)

    return {
        "artifact": "model.joblib",
        "notes": "Frozen RF25; 17 provided and 8 explicitly missing; research only",
        "metrics": {
            "recall": test_metrics["recall"],
            "specificity": test_metrics["specificity"],
            "auroc": test_metrics["auroc"],
            "auprc": test_metrics["auprc"],
            "brier_score": test_metrics["brier"],
            "threshold": threshold,
            "f1": 2 * test_metrics["tp"] / (2 * test_metrics["tp"] + test_metrics["fp"] + test_metrics["fn"]),
            "confusion_matrix": {
                "true_positive": test_metrics["tp"],
                "false_positive": test_metrics["fp"],
                "true_negative": test_metrics["tn"],
                "false_negative": test_metrics["fn"],
            },
        },
        "validation": validation_metrics,
    }
