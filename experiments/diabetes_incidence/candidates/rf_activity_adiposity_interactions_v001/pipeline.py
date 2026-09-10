"""현재 RF에 운동·비만 상호작용을 추가해 PID OOF로 비교한다."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from src.ml.experiments.tune_klosa_stage3_group_cv import pid_stratified_folds
from src.ml.modeling.model_family_expansion import (
    CATEGORICAL_25_FEATURES,
    NUMERIC_25_FEATURES,
)
from src.ml.modeling.rf_engineered_features import make_rf_pipeline
from src.ml.preprocessing.build_klosa_diabetes_engineered_features import (
    AGE_INACTIVITY_INTERACTION,
    BMI_INACTIVITY_INTERACTION,
    BMI_LOG_WEEKLY_INTERACTION,
    LOG_WEEKLY_EXERCISE_FEATURE,
    WEEKLY_EXERCISE_FEATURE,
    add_activity_adiposity_features,
)

from src.ml.evaluation.compare_klosa_thresholds import choose_threshold_for_recall
from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.modeling.train_klosa_diabetes_sample import assert_no_leakage, evaluate
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET

RANDOM_STATE = 42
N_SPLITS = 5
MINIMUM_RECALL = 0.80
COHORT_FILENAME = "klosa_diabetes_incidence_stage3_25features_v1.pkl"
VARIANTS = {
    "current_25": [],
    "weekly_raw_26": [WEEKLY_EXERCISE_FEATURE],
    "weekly_log_26": [LOG_WEEKLY_EXERCISE_FEATURE],
    "inactivity_interactions_27": [
        BMI_INACTIVITY_INTERACTION,
        AGE_INACTIVITY_INTERACTION,
    ],
    "full_activity_adiposity_29": [
        LOG_WEEKLY_EXERCISE_FEATURE,
        BMI_INACTIVITY_INTERACTION,
        AGE_INACTIVITY_INTERACTION,
        BMI_LOG_WEEKLY_INTERACTION,
    ],
}


def variant_features(added_features: list[str]) -> list[str]:
    return [*NUMERIC_25_FEATURES, *added_features, *CATEGORICAL_25_FEATURES]


def _make_model(added_features: list[str], random_state: int):
    return make_rf_pipeline(
        [*NUMERIC_25_FEATURES, *added_features],
        list(CATEGORICAL_25_FEATURES),
        preserve_categorical_missing=False,
        random_state=random_state,
    )


def response_consistency_audit(frame: pd.DataFrame) -> dict[str, Any]:
    regular = frame["regular_exercise"]
    days = pd.to_numeric(frame["exercise_days_per_week"], errors="coerce")
    minutes = pd.to_numeric(frame["exercise_minutes"], errors="coerce")
    missing = regular.isna() | days.isna() | minutes.isna()
    inconsistent = (~missing) & (
        ((~regular.astype(bool)) & (days.gt(0) | minutes.gt(0))) | (regular.astype(bool) & (days.le(0) | minutes.le(0)))
    )
    return {
        "complete_rows": int((~missing).sum()),
        "inconsistent_rows": int(inconsistent.sum()),
        "missing_rows": int(missing.sum()),
        "decision": "exclude zero-variance inconsistency flag",
    }


def _oof_variant(
    train: pd.DataFrame,
    folds: list[tuple[np.ndarray, np.ndarray]],
    variant: str,
    added_features: list[str],
) -> dict[str, Any]:
    features = variant_features(added_features)
    probabilities = np.full(len(train), np.nan, dtype=float)
    for fold_number, (fit_indices, oof_indices) in enumerate(folds):
        fold_fit = train.iloc[fit_indices]
        fold_oof = train.iloc[oof_indices]
        model = _make_model(added_features, RANDOM_STATE + fold_number)
        model.fit(fold_fit[features], fold_fit[TARGET])
        probabilities[oof_indices] = model.predict_proba(fold_oof[features])[:, 1]
    if np.isnan(probabilities).any():
        raise AssertionError("Train의 모든 행에 PID OOF 예측이 있어야 합니다.")

    threshold = choose_threshold_for_recall(train[TARGET], probabilities, minimum_recall=MINIMUM_RECALL)
    fold_metrics = [
        evaluate(
            train.iloc[oof_indices][TARGET],
            probabilities[oof_indices],
            threshold,
        )
        for _, oof_indices in folds
    ]
    return {
        "variant": variant,
        "feature_count": len(features),
        "added_features": added_features,
        "features": features,
        "oof_threshold": threshold,
        "oof_metrics": evaluate(train[TARGET], probabilities, threshold),
        "worst_fold_recall": float(min(metrics["recall"] for metrics in fold_metrics)),
        "fold_recall_std": float(np.std([metrics["recall"] for metrics in fold_metrics])),
        "fold_metrics_at_oof_threshold": fold_metrics,
    }


def select_by_oof(results: list[dict[str, Any]]) -> str:
    eligible = [result for result in results if result["oof_metrics"]["recall"] >= MINIMUM_RECALL]
    if not eligible:
        raise ValueError("OOF Recall 0.80을 충족한 변형이 없습니다.")
    selected = max(
        eligible,
        key=lambda result: (
            result["oof_metrics"]["specificity"],
            result["oof_metrics"]["auprc"],
            result["oof_metrics"]["auroc"],
            result["worst_fold_recall"],
            -result["feature_count"],
        ),
    )
    return str(selected["variant"])


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
    """Select one interaction variant on Train OOF before final evaluation."""

    dataset_path = Path(context["dataset_path"]) / COHORT_FILENAME
    if not dataset_path.is_file():
        raise FileNotFoundError(f"공통 RF 25변수 코호트가 없습니다: {dataset_path}")
    cohort = add_activity_adiposity_features(pd.read_pickle(dataset_path))
    for features in VARIANTS.values():
        assert_no_leakage(variant_features(features))

    train, validation, test = split_grouped_cohort(cohort, random_state=RANDOM_STATE)
    pid_sets = [set(frame["pid"]) for frame in (train, validation, test)]
    if any(pid_sets[left] & pid_sets[right] for left, right in ((0, 1), (0, 2), (1, 2))):
        raise AssertionError("공통 분할 간 PID 중복이 있습니다.")

    folds = list(pid_stratified_folds(train, N_SPLITS, RANDOM_STATE))
    results = [_oof_variant(train, folds, variant, added_features) for variant, added_features in VARIANTS.items()]
    selected_variant = select_by_oof(results)
    selected_result = next(result for result in results if result["variant"] == selected_variant)
    added_features = selected_result["added_features"]
    features = selected_result["features"]

    model = _make_model(added_features, RANDOM_STATE)
    model.fit(train[features], train[TARGET])
    validation_probabilities = model.predict_proba(validation[features])[:, 1]
    threshold = choose_threshold_for_recall(
        validation[TARGET],
        validation_probabilities,
        minimum_recall=MINIMUM_RECALL,
    )
    validation_metrics = evaluate(validation[TARGET], validation_probabilities, threshold)
    test_probabilities = model.predict_proba(test[features])[:, 1]
    test_metrics = evaluate(test[TARGET], test_probabilities, threshold)

    record = {
        "status": "research_activity_adiposity_interactions_not_for_deployment",
        "selection_policy": (
            "Train PID 5-fold OOF recall >= 0.80, then specificity, AUPRC, AUROC, worst-fold recall, fewer features"
        ),
        "validation_policy": "selected variant numeric threshold on Validation only",
        "test_policy": "selected variant only; reporting after selection",
        "response_consistency_audit": response_consistency_audit(cohort),
        "selected_variant": selected_variant,
        "selected_added_features": added_features,
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
        "oof_results": results,
        "validation": validation_metrics,
        "test": test_metrics,
    }
    run_dir = Path(context["run_dir"])
    result_name = "activity_adiposity_results.json"
    (run_dir / result_name).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    artifact_name = "model.joblib"
    manifest = context["manifest"]
    joblib.dump(
        {
            "pipeline": model,
            "threshold": threshold,
            "features": features,
            "selected_variant": selected_variant,
            "selected_added_features": added_features,
            "feature_builder": "add_activity_adiposity_features",
            "dataset_version": manifest["dataset_version"],
            "split_version": manifest["split_version"],
            "feature_schema_version": manifest["feature_schema_version"],
            "purpose": "risk_screening_and_health_education_research_only",
            "operational_model": None,
        },
        run_dir / artifact_name,
        compress=3,
    )
    return {
        "metrics": _runner_metrics(test_metrics),
        "artifact": artifact_name,
        "notes": (
            f"selected_on_train_oof={selected_variant}; details={result_name}; "
            "numeric threshold selected on Validation only; research use only"
        ),
    }
