"""Compare cumulative verified KLoSA core candidates with the current RF25."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from src.ml.experiments.tune_klosa_stage3_group_cv import pid_stratified_folds
from src.ml.modeling.model_family_expansion import CATEGORICAL_25_FEATURES, NUMERIC_25_FEATURES
from src.ml.modeling.rf_engineered_features import make_rf_pipeline
from src.ml.preprocessing.build_klosa_diabetes_core_candidate_cohort import (
    EXERCISE_DURATION_FEATURE,
    MEAL_CATEGORICAL_FEATURES,
    MEAL_NUMERIC_FEATURES,
    RELATIVE_GRIP_FEATURE,
    SMOKING_ALCOHOL_CATEGORICAL_FEATURES,
    SMOKING_ALCOHOL_NUMERIC_FEATURES,
    WEIGHT_CHANGE_FEATURE,
    add_core_candidate_features,
)

from src.ml.evaluation.compare_klosa_thresholds import choose_threshold_for_recall
from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.modeling.train_klosa_diabetes_sample import assert_no_leakage, evaluate
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET

RANDOM_STATE = 42
N_SPLITS = 5
MINIMUM_RECALL = 0.80
COHORT_FILENAME = "klosa_diabetes_incidence_stage3_25features_v1.pkl"
SOURCE_DATASET_PATH = Path("data/interim/source_extract/klosa/20260413")

VARIANTS: dict[str, dict[str, list[str]]] = {
    "A_current_25": {"numeric": [], "categorical": []},
    "B_plus_weight_change_26": {"numeric": [], "categorical": [WEIGHT_CHANGE_FEATURE]},
    "C_plus_relative_grip_27": {
        "numeric": [RELATIVE_GRIP_FEATURE],
        "categorical": [WEIGHT_CHANGE_FEATURE],
    },
    "D_plus_exercise_duration_28": {
        "numeric": [RELATIVE_GRIP_FEATURE],
        "categorical": [WEIGHT_CHANGE_FEATURE, EXERCISE_DURATION_FEATURE],
    },
    "E_plus_meal_regularity_31": {
        "numeric": [RELATIVE_GRIP_FEATURE, *MEAL_NUMERIC_FEATURES],
        "categorical": [
            WEIGHT_CHANGE_FEATURE,
            EXERCISE_DURATION_FEATURE,
            *MEAL_CATEGORICAL_FEATURES,
        ],
    },
    "F_plus_smoking_alcohol_burden_34": {
        "numeric": [
            RELATIVE_GRIP_FEATURE,
            *MEAL_NUMERIC_FEATURES,
            *SMOKING_ALCOHOL_NUMERIC_FEATURES,
        ],
        "categorical": [
            WEIGHT_CHANGE_FEATURE,
            EXERCISE_DURATION_FEATURE,
            *MEAL_CATEGORICAL_FEATURES,
            *SMOKING_ALCOHOL_CATEGORICAL_FEATURES,
        ],
    },
}


def feature_types(specification: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    return (
        [*NUMERIC_25_FEATURES, *specification["numeric"]],
        [*CATEGORICAL_25_FEATURES, *specification["categorical"]],
    )


def _make_model(specification: dict[str, list[str]], random_state: int):
    numeric, categorical = feature_types(specification)
    return make_rf_pipeline(
        numeric,
        categorical,
        preserve_categorical_missing=False,
        random_state=random_state,
    )


def _oof_variant(
    train: pd.DataFrame,
    folds: list[tuple[np.ndarray, np.ndarray]],
    variant: str,
    specification: dict[str, list[str]],
) -> dict[str, Any]:
    numeric, categorical = feature_types(specification)
    features = [*numeric, *categorical]
    probabilities = np.full(len(train), np.nan, dtype=float)
    for fold_number, (fit_indices, oof_indices) in enumerate(folds):
        fold_fit = train.iloc[fit_indices]
        fold_oof = train.iloc[oof_indices]
        model = _make_model(specification, RANDOM_STATE + fold_number)
        model.fit(fold_fit[features], fold_fit[TARGET])
        probabilities[oof_indices] = model.predict_proba(fold_oof[features])[:, 1]
    if np.isnan(probabilities).any():
        raise AssertionError("Train의 모든 행에 PID OOF 예측이 있어야 합니다.")

    threshold = choose_threshold_for_recall(train[TARGET], probabilities, minimum_recall=MINIMUM_RECALL)
    fold_metrics = [
        evaluate(train.iloc[oof_indices][TARGET], probabilities[oof_indices], threshold) for _, oof_indices in folds
    ]
    return {
        "variant": variant,
        "feature_count": len(features),
        "added_numeric": specification["numeric"],
        "added_categorical": specification["categorical"],
        "features": features,
        "oof_threshold": threshold,
        "oof_metrics": evaluate(train[TARGET], probabilities, threshold),
        "worst_fold_recall": float(min(metrics["recall"] for metrics in fold_metrics)),
        "fold_recall_std": float(np.std([metrics["recall"] for metrics in fold_metrics])),
        "fold_specificity_std": float(np.std([metrics["specificity"] for metrics in fold_metrics])),
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
    """Select A-F on Train OOF, then evaluate only the OOF winner on Test."""

    root = Path(context["root"])
    dataset_path = Path(context["dataset_path"]) / COHORT_FILENAME
    source_dir = root / SOURCE_DATASET_PATH
    if not dataset_path.is_file():
        raise FileNotFoundError(f"공통 RF 25변수 코호트가 없습니다: {dataset_path}")
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Git 제외 KLoSA 원자료가 없습니다: {source_dir}")

    cohort = add_core_candidate_features(pd.read_pickle(dataset_path), source_dir)
    all_added = sorted(
        {
            feature
            for specification in VARIANTS.values()
            for feature_type in ("numeric", "categorical")
            for feature in specification[feature_type]
        }
    )
    for specification in VARIANTS.values():
        numeric, categorical = feature_types(specification)
        assert_no_leakage([*numeric, *categorical])

    train, validation, test = split_grouped_cohort(cohort, random_state=RANDOM_STATE)
    pid_sets = [set(frame["pid"]) for frame in (train, validation, test)]
    if any(pid_sets[left] & pid_sets[right] for left, right in ((0, 1), (0, 2), (1, 2))):
        raise AssertionError("공통 분할 간 PID 중복이 있습니다.")

    folds = list(pid_stratified_folds(train, N_SPLITS, RANDOM_STATE))
    oof_results = []
    for variant, specification in VARIANTS.items():
        print(f"[core-candidates] Train PID OOF: {variant}", flush=True)
        oof_results.append(_oof_variant(train, folds, variant, specification))
    selected_variant = select_by_oof(oof_results)

    validation_results = []
    selected_model = None
    selected_threshold = None
    selected_features = None
    for variant, specification in VARIANTS.items():
        print(f"[core-candidates] Validation report: {variant}", flush=True)
        numeric, categorical = feature_types(specification)
        features = [*numeric, *categorical]
        model = _make_model(specification, RANDOM_STATE)
        model.fit(train[features], train[TARGET])
        probabilities = model.predict_proba(validation[features])[:, 1]
        threshold = choose_threshold_for_recall(validation[TARGET], probabilities, minimum_recall=MINIMUM_RECALL)
        validation_results.append(
            {
                "variant": variant,
                "feature_count": len(features),
                "threshold": threshold,
                "metrics": evaluate(validation[TARGET], probabilities, threshold),
                "selection_use": "report_only_not_used_for_variant_selection",
            }
        )
        if variant == selected_variant:
            selected_model = model
            selected_threshold = threshold
            selected_features = features

    if selected_model is None or selected_threshold is None or selected_features is None:
        raise AssertionError("OOF 선택 변형을 Validation 단계에서 찾지 못했습니다.")

    print(f"[core-candidates] Final Test: {selected_variant}", flush=True)
    test_probabilities = selected_model.predict_proba(test[selected_features])[:, 1]
    test_metrics = evaluate(test[TARGET], test_probabilities, selected_threshold)

    record = {
        "status": "research_klosa_core_candidates_not_for_deployment",
        "sequence": list(VARIANTS),
        "selection_policy": (
            "Train PID 5-fold OOF recall >= 0.80, then specificity, AUPRC, AUROC, worst-fold recall, fewer features"
        ),
        "validation_policy": "all variants reported; not used for variant selection",
        "test_policy": "OOF-selected variant only after Validation threshold is fixed",
        "excluded_detection_opportunity_features": [
            "health_screening_history",
            "healthcare_utilization",
        ],
        "selected_variant": selected_variant,
        "selected_features": selected_features,
        "candidate_missing_rate": {feature: float(cohort[feature].isna().mean()) for feature in all_added},
        "splits": {
            name: {
                "rows": len(frame),
                "pids": int(frame["pid"].nunique()),
                "events": int(frame[TARGET].sum()),
            }
            for name, frame in (("train", train), ("validation", validation), ("test", test))
        },
        "oof_results": oof_results,
        "validation_results": validation_results,
        "test_selected_only": test_metrics,
    }
    run_dir = Path(context["run_dir"])
    result_name = "core_candidate_results.json"
    (run_dir / result_name).write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    artifact_name = "model.joblib"
    manifest = context["manifest"]
    joblib.dump(
        {
            "pipeline": selected_model,
            "threshold": selected_threshold,
            "features": selected_features,
            "selected_variant": selected_variant,
            "feature_builder": "add_core_candidate_features",
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
            f"selected_on_train_pid_oof={selected_variant}; details={result_name}; "
            "Test contains selected variant only; research use only"
        ),
    }
