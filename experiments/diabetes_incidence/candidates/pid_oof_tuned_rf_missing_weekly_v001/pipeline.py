"""PID OOF 튜닝 RF25에 명시적 결측과 주간 운동량을 순차 추가한다."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve
from src.ml.experiments.tune_klosa_stage3_group_cv import pid_stratified_folds
from src.ml.modeling.model_family_expansion import CATEGORICAL_25_FEATURES, NUMERIC_25_FEATURES
from src.ml.modeling.rf_engineered_features import make_rf_pipeline
from src.ml.preprocessing.build_klosa_diabetes_engineered_features import (
    WEEKLY_EXERCISE_FEATURE,
    add_engineered_features,
)

from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.modeling.train_klosa_diabetes_sample import assert_no_leakage, evaluate
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET

RANDOM_STATE = 42
N_SPLITS = 5
COHORT_FILENAME = "klosa_diabetes_incidence_stage3_25features_v1.pkl"
OOF_SPECIFICITY_FLOOR = 0.40
VALIDATION_SPECIFICITY_FLOOR = 0.43
OPERATIONAL_SPECIFICITY_FLOOR = 0.40
TUNED_PARAMETERS = {
    "classifier__min_samples_leaf": 39,
    "classifier__max_samples": 0.7,
    "classifier__criterion": "log_loss",
    "classifier__ccp_alpha": 0.00001,
    "classifier__bootstrap": True,
}
VARIANTS = {
    "tuned_rf25_mode": {
        "numeric": list(NUMERIC_25_FEATURES),
        "categorical": list(CATEGORICAL_25_FEATURES),
        "preserve_categorical_missing": False,
    },
    "tuned_rf25_explicit_missing": {
        "numeric": list(NUMERIC_25_FEATURES),
        "categorical": list(CATEGORICAL_25_FEATURES),
        "preserve_categorical_missing": True,
    },
    "tuned_rf26_explicit_missing_weekly_exercise": {
        "numeric": [*NUMERIC_25_FEATURES, WEEKLY_EXERCISE_FEATURE],
        "categorical": list(CATEGORICAL_25_FEATURES),
        "preserve_categorical_missing": True,
    },
}


def choose_threshold_for_specificity(
    target: pd.Series,
    probabilities: np.ndarray,
    minimum_specificity: float,
) -> float:
    """특이도 제약 안에서 Recall을 최대화하고 동률이면 특이도를 높인다."""

    false_positive_rate, recall, thresholds = roc_curve(target, probabilities, drop_intermediate=False)
    specificity = 1 - false_positive_rate
    eligible = np.flatnonzero(specificity >= minimum_specificity)
    if not len(eligible):
        raise ValueError(f"Specificity {minimum_specificity:.2f}를 충족하는 임계값이 없습니다.")
    best_recall = recall[eligible].max()
    tied = eligible[np.isclose(recall[eligible], best_recall)]
    best_specificity = specificity[tied].max()
    tied = tied[np.isclose(specificity[tied], best_specificity)]
    return float(thresholds[tied[np.argmin(thresholds[tied])]])


def _features(specification: dict[str, Any]) -> list[str]:
    return [*specification["numeric"], *specification["categorical"]]


def _make_model(specification: dict[str, Any], random_state: int):
    model = make_rf_pipeline(
        specification["numeric"],
        specification["categorical"],
        preserve_categorical_missing=specification["preserve_categorical_missing"],
        random_state=random_state,
    )
    model.set_params(**TUNED_PARAMETERS)
    return model


def _oof_variant(
    train: pd.DataFrame,
    folds: list[tuple[np.ndarray, np.ndarray]],
    variant: str,
    specification: dict[str, Any],
) -> dict[str, Any]:
    features = _features(specification)
    probabilities = np.full(len(train), np.nan, dtype=float)
    for fold_number, (fit_indices, oof_indices) in enumerate(folds):
        fold_fit = train.iloc[fit_indices]
        fold_oof = train.iloc[oof_indices]
        model = _make_model(specification, RANDOM_STATE + fold_number)
        model.fit(fold_fit[features], fold_fit[TARGET])
        probabilities[oof_indices] = model.predict_proba(fold_oof[features])[:, 1]
    if np.isnan(probabilities).any():
        raise AssertionError("Train의 모든 행에 PID OOF 예측이 있어야 합니다.")
    threshold = choose_threshold_for_specificity(train[TARGET], probabilities, OOF_SPECIFICITY_FLOOR)
    fold_metrics = [
        evaluate(train.iloc[oof_indices][TARGET], probabilities[oof_indices], threshold) for _, oof_indices in folds
    ]
    return {
        "variant": variant,
        "feature_count": len(features),
        "features": features,
        "preserve_categorical_missing": specification["preserve_categorical_missing"],
        "oof_threshold": threshold,
        "oof_metrics": evaluate(train[TARGET], probabilities, threshold),
        "worst_fold_recall": float(min(metric["recall"] for metric in fold_metrics)),
        "fold_recall_std": float(np.std([metric["recall"] for metric in fold_metrics])),
        "fold_metrics_at_oof_threshold": fold_metrics,
    }


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
    """Train PID OOF 변형 선택 후 Validation 임계값과 Test 결과를 기록한다."""

    dataset_path = Path(context["dataset_path"]) / COHORT_FILENAME
    if not dataset_path.is_file():
        raise FileNotFoundError(f"공통 RF 25변수 코호트가 없습니다: {dataset_path}")
    cohort = add_engineered_features(pd.read_pickle(dataset_path))
    train, validation, test = split_grouped_cohort(cohort, random_state=RANDOM_STATE)
    pid_sets = [set(frame["pid"]) for frame in (train, validation, test)]
    if any(pid_sets[left] & pid_sets[right] for left, right in ((0, 1), (0, 2), (1, 2))):
        raise AssertionError("공통 분할 간 PID 중복이 있습니다.")

    for specification in VARIANTS.values():
        assert_no_leakage(_features(specification))
    folds = list(pid_stratified_folds(train, N_SPLITS, RANDOM_STATE))
    oof_results = []
    for variant, specification in VARIANTS.items():
        print(f"[tuned-missing-weekly] PID OOF: {variant}", flush=True)
        oof_results.append(_oof_variant(train, folds, variant, specification))
    selected_oof = max(
        oof_results,
        key=lambda result: (
            result["oof_metrics"]["recall"],
            result["oof_metrics"]["specificity"],
            result["worst_fold_recall"],
            result["oof_metrics"]["auprc"],
            -result["feature_count"],
        ),
    )
    selected_variant = str(selected_oof["variant"])

    models: dict[str, Any] = {}
    results: list[dict[str, Any]] = []
    for variant, specification in VARIANTS.items():
        features = _features(specification)
        model = _make_model(specification, RANDOM_STATE)
        model.fit(train[features], train[TARGET])
        validation_probabilities = model.predict_proba(validation[features])[:, 1]
        threshold = choose_threshold_for_specificity(
            validation[TARGET],
            validation_probabilities,
            VALIDATION_SPECIFICITY_FLOOR,
        )
        test_probabilities = model.predict_proba(test[features])[:, 1]
        test_metrics = evaluate(test[TARGET], test_probabilities, threshold)
        results.append(
            {
                "variant": variant,
                "feature_count": len(features),
                "features": features,
                "threshold": threshold,
                "validation": evaluate(validation[TARGET], validation_probabilities, threshold),
                "test": test_metrics,
                "selected_on_train_pid_oof": variant == selected_variant,
                "test_specificity_constraint_passed": (test_metrics["specificity"] >= OPERATIONAL_SPECIFICITY_FLOOR),
            }
        )
        models[variant] = model

    selected_result = next(result for result in results if result["variant"] == selected_variant)
    record = {
        "status": "research_tuned_rf_feature_ablation_not_for_deployment",
        "fixed_hyperparameters": TUNED_PARAMETERS,
        "selection_policy": (
            "Train PID 5-fold OOF: maximize recall subject to specificity >= 0.40; "
            "then specificity, worst-fold recall, AUPRC, fewer features"
        ),
        "threshold_policy": ("Validation only: maximize recall subject to specificity >= 0.43"),
        "test_policy": "three variants prespecified; Test report-only",
        "selected_variant": selected_variant,
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
        "oof_results": oof_results,
        "results": results,
    }
    run_dir = Path(context["run_dir"])
    result_name = "tuned_missing_weekly_results.json"
    (run_dir / result_name).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    artifact_name = "model.joblib"
    manifest = context["manifest"]
    joblib.dump(
        {
            "pipeline": models[selected_variant],
            "threshold": selected_result["threshold"],
            "features": selected_result["features"],
            "selected_variant": selected_variant,
            "fixed_hyperparameters": TUNED_PARAMETERS,
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
        "metrics": _runner_metrics(selected_result["test"]),
        "artifact": artifact_name,
        "notes": (f"selected_on_train_pid_oof={selected_variant}; details={result_name}; research use only"),
    }
