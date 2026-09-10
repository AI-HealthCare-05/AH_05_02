"""현재 RF에서 결측 범주와 생활·질환 요약 파생변수를 비교한다."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from src.ml.modeling.model_family_expansion import (
    CATEGORICAL_25_FEATURES,
    NUMERIC_25_FEATURES,
)
from src.ml.modeling.rf_engineered_features import make_rf_pipeline
from src.ml.preprocessing.build_klosa_diabetes_engineered_features import (
    CARDIOVASCULAR_SUMMARY_FEATURE,
    COMORBIDITY_COUNT_FEATURE,
    WEEKLY_EXERCISE_FEATURE,
    add_engineered_features,
)

from src.ml.evaluation.compare_klosa_thresholds import choose_threshold_for_recall
from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.modeling.train_klosa_diabetes_sample import assert_no_leakage, evaluate
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET

RANDOM_STATE = 42
MINIMUM_VALIDATION_RECALL = 0.80
COHORT_FILENAME = "klosa_diabetes_incidence_stage3_25features_v1.pkl"
VARIANTS = {
    "current_25_mode_imputation": {
        "numeric": list(NUMERIC_25_FEATURES),
        "categorical": list(CATEGORICAL_25_FEATURES),
        "preserve_categorical_missing": False,
    },
    "missing_category_25": {
        "numeric": list(NUMERIC_25_FEATURES),
        "categorical": list(CATEGORICAL_25_FEATURES),
        "preserve_categorical_missing": True,
    },
    "missing_plus_weekly_exercise_26": {
        "numeric": [*NUMERIC_25_FEATURES, WEEKLY_EXERCISE_FEATURE],
        "categorical": list(CATEGORICAL_25_FEATURES),
        "preserve_categorical_missing": True,
    },
    "missing_plus_comorbidity_summaries_27": {
        "numeric": [*NUMERIC_25_FEATURES, COMORBIDITY_COUNT_FEATURE],
        "categorical": [*CATEGORICAL_25_FEATURES, CARDIOVASCULAR_SUMMARY_FEATURE],
        "preserve_categorical_missing": True,
    },
    "missing_plus_all_engineered_28": {
        "numeric": [
            *NUMERIC_25_FEATURES,
            WEEKLY_EXERCISE_FEATURE,
            COMORBIDITY_COUNT_FEATURE,
        ],
        "categorical": [*CATEGORICAL_25_FEATURES, CARDIOVASCULAR_SUMMARY_FEATURE],
        "preserve_categorical_missing": True,
    },
}


def variant_features(specification: dict[str, Any]) -> list[str]:
    return [*specification["numeric"], *specification["categorical"]]


def select_by_validation(results: list[dict[str, Any]]) -> str:
    eligible = [result for result in results if result["validation"]["recall"] >= MINIMUM_VALIDATION_RECALL]
    if not eligible:
        raise ValueError("Validation Recall 0.80을 충족한 변형이 없습니다.")
    selected = max(
        eligible,
        key=lambda result: (
            result["validation"]["specificity"],
            result["validation"]["auprc"],
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
    """동일 분할에서 Validation 선택 후 사전 지정 Test 결과만 보고한다."""

    dataset_path = Path(context["dataset_path"]) / COHORT_FILENAME
    if not dataset_path.is_file():
        raise FileNotFoundError(f"공통 RF 25변수 코호트가 없습니다: {dataset_path}")
    cohort = add_engineered_features(pd.read_pickle(dataset_path))
    train, validation, test = split_grouped_cohort(cohort, random_state=RANDOM_STATE)
    pid_sets = [set(frame["pid"]) for frame in (train, validation, test)]
    if any(pid_sets[left] & pid_sets[right] for left, right in ((0, 1), (0, 2), (1, 2))):
        raise AssertionError("동일 PID가 둘 이상의 분할에 포함됐습니다.")

    models: dict[str, Any] = {}
    results: list[dict[str, Any]] = []
    for variant, specification in VARIANTS.items():
        features = variant_features(specification)
        assert_no_leakage(features)
        model = make_rf_pipeline(
            specification["numeric"],
            specification["categorical"],
            preserve_categorical_missing=specification["preserve_categorical_missing"],
            random_state=RANDOM_STATE,
        )
        model.fit(train[features], train[TARGET])
        validation_probabilities = model.predict_proba(validation[features])[:, 1]
        threshold = choose_threshold_for_recall(
            validation[TARGET],
            validation_probabilities,
            minimum_recall=MINIMUM_VALIDATION_RECALL,
        )
        results.append(
            {
                "variant": variant,
                "feature_count": len(features),
                "features": features,
                "preserve_categorical_missing": specification["preserve_categorical_missing"],
                "threshold": threshold,
                "validation": evaluate(validation[TARGET], validation_probabilities, threshold),
            }
        )
        models[variant] = model

    selected_variant = select_by_validation(results)
    for result in results:
        features = result["features"]
        probabilities = models[result["variant"]].predict_proba(test[features])[:, 1]
        result["test"] = evaluate(test[TARGET], probabilities, result["threshold"])
        result["selected_on_validation"] = result["variant"] == selected_variant

    record = {
        "status": "research_feature_engineering_comparison_not_for_deployment",
        "split_policy": "same PID 70/15/15 split for all variants; random_state=42",
        "threshold_policy": "Validation only; maximize specificity with recall >= 0.80",
        "selection_policy": "Validation specificity, AUPRC, then fewer features; before Test",
        "selected_variant": selected_variant,
        "derived_feature_contract": {
            WEEKLY_EXERCISE_FEATURE: "exercise_days_per_week * exercise_minutes; minutes/week",
            COMORBIDITY_COUNT_FEATURE: "count of 8 explicit yes values; missing if any status missing",
            CARDIOVASCULAR_SUMMARY_FEATURE: (
                "yes if hypertension/heart/cerebrovascular has any yes; "
                "no only if all three explicit no; otherwise missing"
            ),
        },
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
        "results": results,
    }
    run_dir = Path(context["run_dir"])
    result_name = "feature_engineering_results.json"
    (run_dir / result_name).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    artifact_name = "model_variants.joblib"
    manifest = context["manifest"]
    joblib.dump(
        {
            "models": {
                result["variant"]: {
                    "pipeline": models[result["variant"]],
                    "threshold": result["threshold"],
                    "features": result["features"],
                }
                for result in results
            },
            "selected_variant": selected_variant,
            "dataset_version": manifest["dataset_version"],
            "split_version": manifest["split_version"],
            "feature_schema_version": manifest["feature_schema_version"],
            "purpose": "risk_screening_and_health_education_research_only",
            "operational_model": None,
        },
        run_dir / artifact_name,
        compress=3,
    )
    selected_test = next(result["test"] for result in results if result["variant"] == selected_variant)
    return {
        "metrics": _runner_metrics(selected_test),
        "artifact": artifact_name,
        "notes": (f"selected_on_validation={selected_variant}; details={result_name}; no operational model selected"),
    }
