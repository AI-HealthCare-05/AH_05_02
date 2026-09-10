"""Nested PID OOF permutation importance로 RF 특성을 축소한다."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from src.ml.experiments.tune_klosa_stage3_group_cv import pid_stratified_folds

from src.ml.evaluation.compare_klosa_thresholds import choose_threshold_for_recall
from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.modeling.train_klosa_diabetes_sample import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    assert_no_leakage,
    evaluate,
)
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET
from src.ml.preprocessing.build_klosa_diabetes_extended_cohort import COMORBIDITY_FEATURES
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
OUTER_SPLITS = 5
INNER_SPLITS = 3
MINIMUM_RECALL = 0.80
FEATURE_COUNTS = (25, 20, 15, 10)
COHORT_FILENAME = "klosa_diabetes_incidence_stage3_25features_v1.pkl"
FEATURES = list(MENTAL_RHYTHM_EXTENDED_FEATURES)
SATISFACTION_FEATURES = {
    "health_satisfaction_score",
    "economic_satisfaction_score",
    "overall_quality_of_life_score",
}
ALL_NUMERIC_FEATURES = {
    *NUMERIC_FEATURES,
    *SOCIOECONOMIC_NUMERIC_FEATURES,
    *MENTAL_RHYTHM_NUMERIC_FEATURES,
}
ALL_CATEGORICAL_FEATURES = {
    *CATEGORICAL_FEATURES,
    *COMORBIDITY_FEATURES,
    *SOCIOECONOMIC_CATEGORICAL_FEATURES,
    *MENTAL_RHYTHM_CATEGORICAL_FEATURES,
}


def make_model(features: list[str], random_state: int) -> Pipeline:
    """선택된 열만 사용하는 RF Pipeline을 만든다."""

    numeric_features = [feature for feature in features if feature in ALL_NUMERIC_FEATURES]
    categorical_features = [feature for feature in features if feature in ALL_CATEGORICAL_FEATURES]
    if set(features) != set(numeric_features) | set(categorical_features):
        raise ValueError("수치형·범주형으로 분류되지 않은 입력 변수가 있습니다.")
    preprocessing = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline([("imputer", SimpleImputer(strategy="median", add_indicator=True))]),
                numeric_features,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("one_hot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ]
    )
    classifier = RandomForestClassifier(
        n_estimators=500,
        max_depth=8,
        min_samples_leaf=20,
        max_features="sqrt",
        class_weight=None,
        n_jobs=-1,
        random_state=random_state,
    )
    return Pipeline([("preprocessing", preprocessing), ("classifier", classifier)])


def specificity_at_recall(y_true: pd.Series, probabilities: np.ndarray) -> float:
    threshold = choose_threshold_for_recall(
        y_true,
        probabilities,
        minimum_recall=MINIMUM_RECALL,
    )
    return float(evaluate(y_true, probabilities, threshold)["specificity"])


def summarize_importances(values: dict[str, list[float]]) -> dict[str, dict[str, Any]]:
    summary = {}
    for feature in FEATURES:
        samples = np.asarray(values[feature], dtype=float)
        mean = float(samples.mean())
        standard_deviation = float(samples.std(ddof=0))
        positive_fraction = float(np.mean(samples > 0))
        summary[feature] = {
            "mean_specificity_drop": mean,
            "standard_deviation": standard_deviation,
            "positive_fold_fraction": positive_fraction,
            "stability_adjusted_score": mean - standard_deviation,
            "fold_values": samples.tolist(),
        }
    return summary


def nested_permutation_importance(
    outer_train: pd.DataFrame,
    random_state: int,
) -> dict[str, dict[str, Any]]:
    """Outer validation을 보지 않고 inner PID folds에서 중요도를 계산한다."""

    values: defaultdict[str, list[float]] = defaultdict(list)
    inner_folds = list(pid_stratified_folds(outer_train, INNER_SPLITS, random_state))
    for fold_number, (fit_indices, importance_indices) in enumerate(inner_folds):
        fit = outer_train.iloc[fit_indices]
        importance = outer_train.iloc[importance_indices]
        model = make_model(FEATURES, random_state + fold_number)
        model.fit(fit[FEATURES], fit[TARGET])
        base_probabilities = model.predict_proba(importance[FEATURES])[:, 1]
        base_specificity = specificity_at_recall(importance[TARGET], base_probabilities)
        for feature_index, feature in enumerate(FEATURES):
            permuted = importance[FEATURES].copy()
            generator = np.random.default_rng(random_state * 10_000 + fold_number * 100 + feature_index)
            permuted[feature] = generator.permutation(permuted[feature].to_numpy())
            permuted_probabilities = model.predict_proba(permuted)[:, 1]
            values[feature].append(base_specificity - specificity_at_recall(importance[TARGET], permuted_probabilities))
    return summarize_importances(values)


def rank_features(importance: dict[str, dict[str, Any]]) -> list[str]:
    """양의 fold가 많은 안정적 변수를 우선하고 변동성을 감점한다."""

    return sorted(
        FEATURES,
        key=lambda feature: (
            importance[feature]["mean_specificity_drop"] > 0 and importance[feature]["positive_fold_fraction"] >= 2 / 3,
            importance[feature]["stability_adjusted_score"],
            importance[feature]["mean_specificity_drop"],
            -importance[feature]["standard_deviation"],
        ),
        reverse=True,
    )


def select_features(
    importance: dict[str, dict[str, Any]],
    feature_count: int,
) -> list[str]:
    """축소안에서는 상관된 만족도 3개 중 가장 안정적인 하나만 남긴다."""

    if feature_count == len(FEATURES):
        return FEATURES.copy()
    ranked = rank_features(importance)
    satisfaction_representative = next(feature for feature in ranked if feature in SATISFACTION_FEATURES)
    allowed = [
        feature for feature in ranked if feature not in SATISFACTION_FEATURES or feature == satisfaction_representative
    ]
    selected = allowed[:feature_count]
    if satisfaction_representative not in selected:
        selected[-1] = satisfaction_representative
    if len(selected) != feature_count:
        raise AssertionError("요청한 변수 수를 선택하지 못했습니다.")
    return selected


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
    """Nested Train OOF 선택 후 Validation 임계값과 Test 최종 평가를 수행한다."""

    cohort_path = Path(context["dataset_path"]) / COHORT_FILENAME
    if not cohort_path.is_file():
        raise FileNotFoundError(f"공통 official_v1 코호트가 없습니다: {cohort_path}")
    cohort = pd.read_pickle(cohort_path)
    assert_no_leakage(FEATURES)
    train, validation, test = split_grouped_cohort(cohort, random_state=RANDOM_STATE)
    pid_sets = [set(frame["pid"]) for frame in (train, validation, test)]
    if any(pid_sets[left] & pid_sets[right] for left, right in ((0, 1), (0, 2), (1, 2))):
        raise AssertionError("공통 분할 간 PID 중복이 있습니다.")

    outer_folds = list(pid_stratified_folds(train, OUTER_SPLITS, RANDOM_STATE))
    oof_probabilities = {feature_count: np.full(len(train), np.nan, dtype=float) for feature_count in FEATURE_COUNTS}
    outer_records = []
    combined_importance_values: defaultdict[str, list[float]] = defaultdict(list)
    for outer_fold, (outer_fit_indices, outer_oof_indices) in enumerate(outer_folds):
        outer_fit = train.iloc[outer_fit_indices]
        outer_oof = train.iloc[outer_oof_indices]
        importance = nested_permutation_importance(
            outer_fit,
            RANDOM_STATE + outer_fold * 100,
        )
        for feature in FEATURES:
            combined_importance_values[feature].extend(importance[feature]["fold_values"])

        selected_by_count = {}
        for feature_count in FEATURE_COUNTS:
            selected = select_features(importance, feature_count)
            selected_by_count[str(feature_count)] = selected
            model = make_model(selected, RANDOM_STATE + outer_fold)
            model.fit(outer_fit[selected], outer_fit[TARGET])
            oof_probabilities[feature_count][outer_oof_indices] = model.predict_proba(outer_oof[selected])[:, 1]
        outer_records.append(
            {
                "outer_fold": outer_fold,
                "fit_pids": int(outer_fit["pid"].nunique()),
                "oof_pids": int(outer_oof["pid"].nunique()),
                "selected_features": selected_by_count,
                "importance": importance,
            }
        )

    count_results = []
    for feature_count in FEATURE_COUNTS:
        probabilities = oof_probabilities[feature_count]
        if np.isnan(probabilities).any():
            raise AssertionError(f"{feature_count}개 변수 OOF 예측이 누락됐습니다.")
        threshold = choose_threshold_for_recall(train[TARGET], probabilities, minimum_recall=MINIMUM_RECALL)
        count_results.append(
            {
                "feature_count": feature_count,
                "oof_threshold": threshold,
                "oof_metrics": evaluate(train[TARGET], probabilities, threshold),
            }
        )
    eligible = [result for result in count_results if result["oof_metrics"]["recall"] >= MINIMUM_RECALL]
    selected_result = max(
        eligible,
        key=lambda result: (
            result["oof_metrics"]["specificity"],
            result["oof_metrics"]["auprc"],
            -result["feature_count"],
        ),
    )

    final_importance = summarize_importances(combined_importance_values)
    consensus_features_by_count = {
        str(feature_count): select_features(final_importance, feature_count) for feature_count in FEATURE_COUNTS
    }
    final_features = consensus_features_by_count[str(selected_result["feature_count"])]
    model = make_model(final_features, RANDOM_STATE)
    model.fit(train[final_features], train[TARGET])
    validation_probabilities = model.predict_proba(validation[final_features])[:, 1]
    threshold = choose_threshold_for_recall(validation[TARGET], validation_probabilities, minimum_recall=MINIMUM_RECALL)
    validation_metrics = evaluate(validation[TARGET], validation_probabilities, threshold)

    # Test는 변수 수·최종 변수·모델·임계값이 모두 확정된 뒤 한 번만 사용한다.
    test_probabilities = model.predict_proba(test[final_features])[:, 1]
    test_metrics = evaluate(test[TARGET], test_probabilities, threshold)

    satisfaction_correlations = train[sorted(SATISFACTION_FEATURES)].corr().to_dict()
    record = {
        "status": "research_nested_oof_feature_selection_not_for_deployment",
        "selection_policy": ("nested Train PID OOF; recall >= 0.80, then specificity, AUPRC, fewer features"),
        "outer_splits": OUTER_SPLITS,
        "inner_splits": INNER_SPLITS,
        "permutation_metric": "specificity at recall >= 0.80",
        "satisfaction_reduction": (
            "for 20/15/10 variants retain only the highest-ranked of three correlated satisfaction scores"
        ),
        "satisfaction_correlations_train_only": satisfaction_correlations,
        "count_results": count_results,
        "consensus_features_by_count": consensus_features_by_count,
        "selected_feature_count": selected_result["feature_count"],
        "final_features": final_features,
        "removed_features": [feature for feature in FEATURES if feature not in final_features],
        "final_importance": final_importance,
        "outer_fold_details": outer_records,
        "validation": validation_metrics,
        "test": test_metrics,
        "test_selection_policy": "final reporting only; never used for feature or threshold selection",
        "caveat": "historical test has already been inspected and is not a pristine final holdout",
    }
    run_dir = Path(context["run_dir"])
    result_name = "feature_selection_results.json"
    (run_dir / result_name).write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    artifact_name = "model.joblib"
    manifest = context["manifest"]
    joblib.dump(
        {
            "pipeline": model,
            "threshold": threshold,
            "features": final_features,
            "feature_selection": "nested_pid_oof_permutation_importance_v1",
            "dataset_version": manifest["dataset_version"],
            "split_version": manifest["split_version"],
            "feature_schema_version": manifest["feature_schema_version"],
            "purpose": "risk_screening_and_health_education_research_only",
        },
        run_dir / artifact_name,
    )
    return {
        "metrics": _runner_metrics(test_metrics),
        "artifact": artifact_name,
        "notes": (
            f"selected_feature_count={len(final_features)}; details={result_name}; "
            "nested PID OOF selection; test not used for selection"
        ),
    }
