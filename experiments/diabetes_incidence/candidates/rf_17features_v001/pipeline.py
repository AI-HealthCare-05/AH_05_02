"""Frozen RF25 hyperparameters, refitted using seventeen baseline features."""

import json

import joblib
import pandas as pd
from sklearn.base import clone
from src.ml.evaluation.audit_service_release import metrics, select

from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET

REMOVED = {
    "current_drinker",
    "liver_disease_diagnosis",
    "psychiatric_disease_diagnosis",
    "cancer_diagnosis",
    "household_structure",
    "cerebrovascular_disease_diagnosis",
    "heart_disease_diagnosis",
    "chronic_lung_disease_diagnosis",
}


def run_experiment(context):
    root, out = context["root"], context["run_dir"]
    old = joblib.load(root / "models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib")
    features = [c for c in old["features"] if c not in REMOVED]
    assert len(features) == 17
    pipeline = clone(old["pipeline"])
    transformer = pipeline.named_steps["preprocessing"]
    transformer.transformers = [
        (name, pipe, [c for c in cols if c in features]) for name, pipe, cols in transformer.transformers
    ]
    pipeline.set_params(classifier__n_jobs=1)
    train, val, test = split_grouped_cohort(
        pd.read_pickle(root / "data/processed/official_v1/klosa_diabetes_incidence_stage3_25features_v1.pkl"),
        random_state=42,
    )
    assert not (set(train.pid) & set(val.pid) or set(train.pid) & set(test.pid) or set(val.pid) & set(test.pid))
    pipeline.fit(train[features], train[TARGET])
    vp = pipeline.predict_proba(val[features])[:, 1]
    threshold = select(val[TARGET].to_numpy(int), vp, 0.43)
    tp = pipeline.predict_proba(test[features])[:, 1]
    result = {
        "features": features,
        "removed": sorted(REMOVED),
        "parameters": pipeline.named_steps["classifier"].get_params(),
        "validation": metrics(val[TARGET].to_numpy(int), vp, threshold),
        "test": metrics(test[TARGET].to_numpy(int), tp, threshold),
        "test_original_threshold": metrics(test[TARGET].to_numpy(int), tp, old["threshold"]),
        "splits": {
            name: {"rows": len(f), "pids": int(f.pid.nunique()), "events": int(f[TARGET].sum())}
            for name, f in [("train", train), ("validation", val), ("test", test)]
        },
    }
    joblib.dump(
        {
            "pipeline": pipeline,
            "features": features,
            "threshold": threshold,
            "model_version": "rf17-refit-v1",
            "feature_schema_version": "klosa_17features_v1",
            "operational_model_activated": False,
        },
        out / "model.joblib",
        compress=3,
    )
    assert (
        joblib.load(out / "model.joblib")["pipeline"].predict_proba(test[features].iloc[:3])
        == pipeline.predict_proba(test[features].iloc[:3])
    ).all()
    (out / "comparison.json").write_text(json.dumps(result, indent=2))
    m = result["test"]
    return {
        "artifact": "model.joblib",
        "notes": "RF17 refit; historical repeatedly inspected Test; research only",
        "metrics": {
            "recall": m["recall"],
            "specificity": m["specificity"],
            "auroc": m["auroc"],
            "auprc": m["auprc"],
            "brier_score": m["brier"],
            "threshold": threshold,
            "f1": 2 * m["tp"] / (2 * m["tp"] + m["fp"] + m["fn"]),
            "confusion_matrix": {
                "true_positive": m["tp"],
                "false_positive": m["fp"],
                "true_negative": m["tn"],
                "false_negative": m["fn"],
            },
        },
    }
