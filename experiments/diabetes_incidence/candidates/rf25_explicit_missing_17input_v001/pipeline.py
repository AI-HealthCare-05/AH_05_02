"""Train RF25 with explicit categorical missing tokens and evaluate 17 inputs."""

import json

import joblib
import numpy as np
import pandas as pd
from src.ml.evaluation.audit_service_release import metrics, select
from src.ml.modeling.model_family_expansion import CATEGORICAL_25_FEATURES, NUMERIC_25_FEATURES
from src.ml.modeling.rf_engineered_features import make_rf_pipeline

from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET

FEATURES = [*NUMERIC_25_FEATURES, *CATEGORICAL_25_FEATURES]
MISSING_AT_INFERENCE = {
    "current_drinker",
    "liver_disease_diagnosis",
    "psychiatric_disease_diagnosis",
    "cancer_diagnosis",
    "household_structure",
    "cerebrovascular_disease_diagnosis",
    "heart_disease_diagnosis",
    "chronic_lung_disease_diagnosis",
}
PARAMETERS = {
    "classifier__min_samples_leaf": 39,
    "classifier__max_samples": 0.7,
    "classifier__criterion": "log_loss",
    "classifier__ccp_alpha": 0.00001,
    "classifier__bootstrap": True,
    "classifier__n_jobs": 1,
}


def _mask(frame):
    result = frame[FEATURES].copy()
    for column in MISSING_AT_INFERENCE:
        result[column] = np.nan
    return result


def run_experiment(context):
    root, out = context["root"], context["run_dir"]
    cohort = pd.read_pickle(root / "data/processed/official_v1/klosa_diabetes_incidence_stage3_25features_v1.pkl")
    train, validation, test = split_grouped_cohort(cohort, random_state=42)
    pid_sets = [set(frame.pid) for frame in (train, validation, test)]
    assert not any(pid_sets[left] & pid_sets[right] for left, right in ((0, 1), (0, 2), (1, 2)))

    pipeline = make_rf_pipeline(
        list(NUMERIC_25_FEATURES),
        list(CATEGORICAL_25_FEATURES),
        preserve_categorical_missing=True,
        random_state=42,
    )
    pipeline.set_params(**PARAMETERS)
    pipeline.fit(train[FEATURES], train[TARGET])
    probabilities = {
        "observed": {
            "validation": pipeline.predict_proba(validation[FEATURES])[:, 1],
            "test": pipeline.predict_proba(test[FEATURES])[:, 1],
        },
        "missing_eight": {
            "validation": pipeline.predict_proba(_mask(validation))[:, 1],
            "test": pipeline.predict_proba(_mask(test))[:, 1],
        },
    }
    results = {}
    for condition, prediction in probabilities.items():
        threshold = select(validation[TARGET].to_numpy(int), prediction["validation"], 0.43)
        results[condition] = {
            "threshold": threshold,
            "validation": metrics(validation[TARGET].to_numpy(int), prediction["validation"], threshold),
            "test": metrics(test[TARGET].to_numpy(int), prediction["test"], threshold),
        }

    selected = results["missing_eight"]
    joblib.dump(
        {
            "pipeline": pipeline,
            "features": FEATURES,
            "missing_at_inference": sorted(MISSING_AT_INFERENCE),
            "threshold": selected["threshold"],
            "model_version": "rf25-explicit-missing-17input-v1",
            "feature_schema_version": "klosa_25features_explicit_missing_v1",
            "operational_model_activated": False,
        },
        out / "model.joblib",
        compress=3,
    )
    restored = joblib.load(out / "model.joblib")
    assert np.array_equal(
        restored["pipeline"].predict_proba(_mask(test).iloc[:3]),
        pipeline.predict_proba(_mask(test).iloc[:3]),
    )
    report = {
        "features": FEATURES,
        "missing_at_inference": sorted(MISSING_AT_INFERENCE),
        "categorical_missing_token": "__MISSING__",
        "parameters": pipeline.named_steps["classifier"].get_params(),
        "results": results,
    }
    (out / "comparison.json").write_text(json.dumps(report, indent=2))
    measured = selected["test"]
    return {
        "artifact": "model.joblib",
        "notes": "RF25 explicit categorical missing; 8 missing at inference; historical Test; research only",
        "metrics": {
            "recall": measured["recall"],
            "specificity": measured["specificity"],
            "auroc": measured["auroc"],
            "auprc": measured["auprc"],
            "brier_score": measured["brier"],
            "threshold": selected["threshold"],
            "f1": 2 * measured["tp"] / (2 * measured["tp"] + measured["fp"] + measured["fn"]),
            "confusion_matrix": {
                "true_positive": measured["tp"],
                "false_positive": measured["fp"],
                "true_negative": measured["tn"],
                "false_negative": measured["fn"],
            },
        },
    }
