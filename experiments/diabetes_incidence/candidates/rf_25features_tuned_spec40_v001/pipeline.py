"""서버 연동용 PID OOF 튜닝 RF25 연구 후보를 재현한다."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from src.ml.evaluation.compare_klosa_thresholds import (
    choose_threshold_for_recall,
    choose_threshold_for_specificity,
)
from src.ml.modeling.train_klosa_diabetes_extended_features import make_extended_pipeline
from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.modeling.train_klosa_diabetes_sample import assert_no_leakage, evaluate
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET
from src.ml.preprocessing.build_klosa_diabetes_mental_rhythm_cohort import (
    MENTAL_RHYTHM_CATEGORICAL_FEATURES,
    MENTAL_RHYTHM_EXTENDED_FEATURES,
    MENTAL_RHYTHM_NUMERIC_FEATURES,
)
from src.ml.preprocessing.build_klosa_diabetes_socioeconomic_cohort import (
    SOCIOECONOMIC_CATEGORICAL_FEATURES,
    SOCIOECONOMIC_NUMERIC_FEATURES,
)

RANDOM_STATE = 42
COHORT_FILENAME = "klosa_diabetes_incidence_stage3_25features_v1.pkl"
FEATURES = list(MENTAL_RHYTHM_EXTENDED_FEATURES)
VALIDATION_SPECIFICITY_FLOOR = 0.43
CAUTION_TARGET_RECALL = 0.90
TUNED_PARAMETERS = {
    "classifier__min_samples_leaf": 39,
    "classifier__max_samples": 0.7,
    "classifier__criterion": "log_loss",
    "classifier__ccp_alpha": 0.00001,
    "classifier__bootstrap": True,
}


def make_model():
    model = make_extended_pipeline(
        "random_forest",
        random_state=RANDOM_STATE,
        additional_numeric_features=[
            *SOCIOECONOMIC_NUMERIC_FEATURES,
            *MENTAL_RHYTHM_NUMERIC_FEATURES,
        ],
        additional_categorical_features=[
            *SOCIOECONOMIC_CATEGORICAL_FEATURES,
            *MENTAL_RHYTHM_CATEGORICAL_FEATURES,
        ],
    )
    model.set_params(**TUNED_PARAMETERS)
    return model


def _runner_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    confusion = raw["confusion_matrix"]
    return {
        "recall": raw["recall"],
        "specificity": raw["specificity"],
        "auroc": raw["auroc"],
        "auprc": raw["auprc"],
        "f1": raw["f1"],
        "brier_score": raw["brier_score"],
        "threshold": raw["threshold"],
        "confusion_matrix": {
            "true_positive": confusion["tp"],
            "false_positive": confusion["fp"],
            "true_negative": confusion["tn"],
            "false_negative": confusion["fn"],
        },
    }


def run_experiment(context: dict[str, Any]) -> dict[str, Any]:
    """Train fit, Validation thresholds, final Test evaluation 순서를 지킨다."""

    dataset_path = Path(context["dataset_path"]) / COHORT_FILENAME
    if not dataset_path.is_file():
        raise FileNotFoundError(f"공통 RF25 코호트가 없습니다: {dataset_path}")
    cohort = pd.read_pickle(dataset_path)
    required = {"pid", TARGET, *FEATURES}
    missing = sorted(required.difference(cohort.columns))
    if missing:
        raise ValueError(f"공통 코호트에 필수 열이 없습니다: {missing}")
    assert_no_leakage(FEATURES)

    train, validation, test = split_grouped_cohort(cohort, random_state=RANDOM_STATE)
    pid_sets = [set(frame["pid"]) for frame in (train, validation, test)]
    if any(pid_sets[left] & pid_sets[right] for left, right in ((0, 1), (0, 2), (1, 2))):
        raise AssertionError("공통 분할 간 PID 중복이 있습니다.")

    model = make_model()
    model.fit(train[FEATURES], train[TARGET])
    validation_probabilities = model.predict_proba(validation[FEATURES])[:, 1]
    high_threshold = choose_threshold_for_specificity(
        validation[TARGET],
        validation_probabilities,
        minimum_specificity=VALIDATION_SPECIFICITY_FLOOR,
    )
    caution_threshold = choose_threshold_for_recall(
        validation[TARGET],
        validation_probabilities,
        minimum_recall=CAUTION_TARGET_RECALL,
    )
    if not caution_threshold < high_threshold:
        raise AssertionError("caution 임계값은 high 임계값보다 낮아야 합니다.")

    validation_high = evaluate(validation[TARGET], validation_probabilities, high_threshold)
    validation_caution = evaluate(validation[TARGET], validation_probabilities, caution_threshold)
    test_probabilities = model.predict_proba(test[FEATURES])[:, 1]
    test_high = evaluate(test[TARGET], test_probabilities, high_threshold)
    test_caution = evaluate(test[TARGET], test_probabilities, caution_threshold)

    record = {
        "status": "research_candidate_not_operationally_approved",
        "fixed_hyperparameters": TUNED_PARAMETERS,
        "threshold_policy": {
            "high": "Validation: maximize Recall subject to Specificity >= 0.43",
            "caution": "Validation: maximize Specificity subject to Recall >= 0.90",
            "test_use": "reporting only after both thresholds were fixed",
        },
        "thresholds": {"caution": caution_threshold, "high": high_threshold},
        "splits": {
            name: {
                "rows": len(frame),
                "pids": int(frame["pid"].nunique()),
                "events": int(frame[TARGET].sum()),
            }
            for name, frame in (
                ("train", train),
                ("validation", validation),
                ("test", test),
            )
        },
        "validation": {"caution": validation_caution, "high": validation_high},
        "test": {"caution": test_caution, "high": test_high},
    }
    run_dir = Path(context["run_dir"])
    result_name = "tuned_spec40_results.json"
    (run_dir / result_name).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    artifact_name = "model.joblib"
    manifest = context["manifest"]
    joblib.dump(
        {
            "pipeline": model,
            "threshold": high_threshold,
            "thresholds": {"caution": caution_threshold, "high": high_threshold},
            "features": FEATURES,
            "selected_parameters": TUNED_PARAMETERS,
            "dataset_version": manifest["dataset_version"],
            "split_version": manifest["split_version"],
            "feature_schema_version": manifest["feature_schema_version"],
            "model_version": manifest["model_version"],
            "threshold_version": manifest["threshold_version"],
            "purpose": "risk_screening_and_health_education_research_only",
            "operational_model": None,
        },
        run_dir / artifact_name,
        compress=3,
    )
    return {
        "metrics": _runner_metrics(test_high),
        "artifact": artifact_name,
        "notes": (
            f"thresholds=caution:{caution_threshold},high:{high_threshold}; details={result_name}; research use only"
        ),
    }
