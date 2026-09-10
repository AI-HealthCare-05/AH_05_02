"""RF 25변수에서 지정한 세 변수의 개별·조합 제거 효과를 재탐색한다."""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from src.ml.experiments.tune_klosa_stage3_group_cv import pid_stratified_folds
from src.ml.modeling.model_family_expansion import (
    CATEGORICAL_25_FEATURES,
    FEATURES,
    NUMERIC_25_FEATURES,
)
from src.ml.modeling.rf_engineered_features import make_rf_pipeline

from src.ml.evaluation.compare_klosa_thresholds import choose_threshold_for_recall
from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.modeling.train_klosa_diabetes_sample import assert_no_leakage, evaluate
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET

RANDOM_STATE = 42
OOF_SEEDS = (42, 1042)
N_SPLITS = 5
MINIMUM_RECALL = 0.80
MATERIAL_SPECIFICITY_GAIN = 0.01
COHORT_FILENAME = "klosa_diabetes_incidence_stage3_25features_v1.pkl"
REMOVAL_CANDIDATES = (
    "psychiatric_disease_diagnosis",
    "cerebrovascular_disease_diagnosis",
    "exercise_minutes",
)


def build_variants() -> dict[str, tuple[str, ...]]:
    """원본을 포함해 세 후보의 모든 제거 조합을 고정 순서로 만든다."""

    variants: dict[str, tuple[str, ...]] = {"keep_all_25": ()}
    for removal_count in range(1, len(REMOVAL_CANDIDATES) + 1):
        for removed in combinations(REMOVAL_CANDIDATES, removal_count):
            variants[f"drop__{'__'.join(removed)}"] = removed
    return variants


def features_after_removal(removed: tuple[str, ...]) -> list[str]:
    """학습 당시 25개 변수 순서를 유지하면서 지정 변수만 제외한다."""

    return [feature for feature in FEATURES if feature not in removed]


def make_model(features: list[str], random_state: int):
    """각 제거안의 수치형·범주형 목록을 반영한 동일 사양 RF를 만든다."""

    numeric = [feature for feature in features if feature in NUMERIC_25_FEATURES]
    categorical = [feature for feature in features if feature in CATEGORICAL_25_FEATURES]
    if set(features) != set(numeric) | set(categorical):
        raise ValueError("수치형·범주형으로 분류되지 않은 입력 변수가 있습니다.")
    return make_rf_pipeline(
        numeric,
        categorical,
        preserve_categorical_missing=False,
        random_state=random_state,
    )


def run_seed_oof(
    train: pd.DataFrame,
    variants: dict[str, tuple[str, ...]],
    seed: int,
) -> list[dict[str, Any]]:
    """하나의 PID fold 시드에서 모든 제거안의 pooled OOF 성능을 계산한다."""

    folds = list(pid_stratified_folds(train, N_SPLITS, seed))
    results = []
    for name, removed in variants.items():
        features = features_after_removal(removed)
        probabilities = np.full(len(train), np.nan, dtype=float)
        fold_indices = []
        for fold_number, (fit_indices, oof_indices) in enumerate(folds):
            fit = train.iloc[fit_indices]
            oof = train.iloc[oof_indices]
            model = make_model(
                features,
                random_state=seed + fold_number,
            )
            model.fit(fit[features], fit[TARGET])
            probabilities[oof_indices] = model.predict_proba(oof[features])[:, 1]
            fold_indices.append(oof_indices)
        if np.isnan(probabilities).any():
            raise AssertionError(f"{name} OOF 예측에 누락이 있습니다.")

        threshold = choose_threshold_for_recall(train[TARGET], probabilities, minimum_recall=MINIMUM_RECALL)
        fold_metrics = [
            evaluate(
                train.iloc[indices][TARGET],
                probabilities[indices],
                threshold,
            )
            for indices in fold_indices
        ]
        results.append(
            {
                "variant": name,
                "removed_features": list(removed),
                "features": features,
                "feature_count": len(features),
                "oof_threshold": threshold,
                "oof_metrics": evaluate(train[TARGET], probabilities, threshold),
                "fold_metrics_at_pooled_threshold": fold_metrics,
                "worst_fold_recall": float(min(metrics["recall"] for metrics in fold_metrics)),
                "fold_recall_std": float(np.std([metrics["recall"] for metrics in fold_metrics])),
                "fold_specificity_std": float(np.std([metrics["specificity"] for metrics in fold_metrics])),
            }
        )
    return results


def summarize_seed_results(
    seed_results: dict[int, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """제거안별 다중 시드 평균과 원본 대비 안정성을 요약한다."""

    summaries = []
    for variant in build_variants():
        per_seed = [next(result for result in seed_results[seed] if result["variant"] == variant) for seed in OOF_SEEDS]
        baseline_per_seed = [
            next(result for result in seed_results[seed] if result["variant"] == "keep_all_25") for seed in OOF_SEEDS
        ]
        specificity_gains = [
            result["oof_metrics"]["specificity"] - baseline["oof_metrics"]["specificity"]
            for result, baseline in zip(per_seed, baseline_per_seed, strict=True)
        ]
        summaries.append(
            {
                "variant": variant,
                "removed_features": per_seed[0]["removed_features"],
                "features": per_seed[0]["features"],
                "feature_count": per_seed[0]["feature_count"],
                "mean_recall": float(np.mean([result["oof_metrics"]["recall"] for result in per_seed])),
                "mean_specificity": float(np.mean([result["oof_metrics"]["specificity"] for result in per_seed])),
                "mean_auprc": float(np.mean([result["oof_metrics"]["auprc"] for result in per_seed])),
                "mean_auroc": float(np.mean([result["oof_metrics"]["auroc"] for result in per_seed])),
                "mean_worst_fold_recall": float(np.mean([result["worst_fold_recall"] for result in per_seed])),
                "specificity_gain_vs_baseline_by_seed": specificity_gains,
                "specificity_improved_every_seed": all(gain > 0 for gain in specificity_gains),
                "material_specificity_gain_every_seed": all(
                    gain >= MATERIAL_SPECIFICITY_GAIN for gain in specificity_gains
                ),
                "seed_results": per_seed,
            }
        )
    return summaries


def select_variant(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    """모든 시드에서 원본보다 Specificity가 개선될 때만 제거안을 채택한다."""

    eligible = [
        summary
        for summary in summaries
        if summary["variant"] != "keep_all_25"
        and summary["mean_recall"] >= MINIMUM_RECALL
        and summary["specificity_improved_every_seed"]
    ]
    if not eligible:
        return next(summary for summary in summaries if summary["variant"] == "keep_all_25")
    return max(
        eligible,
        key=lambda summary: (
            summary["mean_specificity"],
            summary["mean_auprc"],
            summary["mean_auroc"],
            summary["mean_worst_fold_recall"],
            -summary["feature_count"],
        ),
    )


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
    """Train PID OOF 제거안 선택, Validation 임계값, Test 최종 평가를 수행한다."""

    cohort_path = Path(context["dataset_path"]) / COHORT_FILENAME
    if not cohort_path.is_file():
        raise FileNotFoundError(f"공통 RF 25변수 코호트가 없습니다: {cohort_path}")
    cohort = pd.read_pickle(cohort_path)
    required = {"pid", TARGET, *FEATURES}
    missing = sorted(required.difference(cohort.columns))
    if missing:
        raise ValueError(f"공통 코호트에 필수 열이 없습니다: {missing}")
    assert_no_leakage(FEATURES)

    train, validation, test = split_grouped_cohort(cohort, random_state=RANDOM_STATE)
    pid_sets = [set(frame["pid"]) for frame in (train, validation, test)]
    if any(pid_sets[left] & pid_sets[right] for left, right in ((0, 1), (0, 2), (1, 2))):
        raise AssertionError("공통 분할 간 PID 중복이 있습니다.")

    variants = build_variants()
    seed_results = {}
    for seed in OOF_SEEDS:
        print(f"PID OOF seed={seed}: {len(variants)} variants")
        seed_results[seed] = run_seed_oof(train, variants, seed)
    summaries = summarize_seed_results(seed_results)
    selected = select_variant(summaries)
    baseline = next(summary for summary in summaries if summary["variant"] == "keep_all_25")

    final_features = selected["features"]
    model = make_model(final_features, RANDOM_STATE)
    model.fit(train[final_features], train[TARGET])
    validation_probabilities = model.predict_proba(validation[final_features])[:, 1]
    threshold = choose_threshold_for_recall(
        validation[TARGET],
        validation_probabilities,
        minimum_recall=MINIMUM_RECALL,
    )
    validation_metrics = evaluate(validation[TARGET], validation_probabilities, threshold)

    # Test는 제거안·모델·임계값을 모두 확정한 뒤 선택된 한 모델에만 사용한다.
    test_probabilities = model.predict_proba(test[final_features])[:, 1]
    test_metrics = evaluate(test[TARGET], test_probabilities, threshold)
    selected_material = (
        selected["variant"] != "keep_all_25"
        and selected["material_specificity_gain_every_seed"]
        and selected["mean_auprc"] >= baseline["mean_auprc"]
        and selected["mean_worst_fold_recall"] >= baseline["mean_worst_fold_recall"]
    )

    record = {
        "status": "research_targeted_feature_removal_not_for_deployment",
        "removal_candidates": list(REMOVAL_CANDIDATES),
        "variant_count": len(variants),
        "oof_seeds": list(OOF_SEEDS),
        "oof_splits": N_SPLITS,
        "selection_policy": (
            "Train PID 5-fold OOF at recall >= 0.80; removal must improve "
            "specificity versus 25-feature baseline in every seed"
        ),
        "material_adoption_rule": (
            "specificity gain >= 0.01 in every seed; mean AUPRC and mean worst-fold recall not below baseline"
        ),
        "summaries": summaries,
        "selected_variant": selected["variant"],
        "selected_features": final_features,
        "selected_removed_features": selected["removed_features"],
        "selected_meets_material_adoption_rule": selected_material,
        "validation_policy": "numeric threshold selected on Validation only",
        "validation": validation_metrics,
        "test_policy": "selected model only; reporting only; never used for selection",
        "test": test_metrics,
        "caveat": "historical test has already been inspected and is not a pristine final holdout",
    }
    run_dir = Path(context["run_dir"])
    result_name = "targeted_feature_removal_results.json"
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
            "removed_features": selected["removed_features"],
            "selection": "multi_seed_pid_oof_targeted_feature_removal_v1",
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
            f"selected={selected['variant']}; features={len(final_features)}; "
            f"material_adoption={selected_material}; details={result_name}"
        ),
    }
