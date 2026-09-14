"""Use RF25 only in the first interval of a discrete-time risk curve."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from experiments.diabetes_incidence.ensembles.rf25_discrete_logistic_calibrated_blend_v001.pipeline import (
    FEATURES,
    RANDOM_STATE,
    RF_WEIGHTS,
    SOURCE_RELATIVE_PATH,
    _calibration_summary,
    _oof_predictions,
    _raw_predictions,
    _runner_metrics,
    apply_platt,
    blend_probabilities,
    fit_platt,
    make_tuned_rf,
)
from experiments.diabetes_incidence.ensembles.rf25_discrete_logistic_stacking_v001.pipeline import (
    stack_features,
)
from src.ml.evaluation.compare_klosa_thresholds import choose_threshold_for_specificity
from src.ml.modeling.discrete_time_survival import (
    BASE_FEATURES,
    MODEL_FEATURES,
    make_pooled_logistic_hazard_model,
)
from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.modeling.train_klosa_diabetes_sample import assert_no_leakage, evaluate
from src.ml.preprocessing.build_klosa_diabetes_multihorizon_cohort import load_diabetes_status_by_wave
from src.ml.preprocessing.build_klosa_discrete_survival_cohort import (
    HORIZON_YEARS,
    SURVIVAL_EVENT,
    build_discrete_survival_cohort,
    horizon_evaluation_frame,
)

COHORT_FILENAME = "klosa_diabetes_incidence_stage3_25features_v1.pkl"
VALIDATION_SPECIFICITY_FLOOR = 0.43


def predict_first_interval_curve(
    survival_model: Any,
    origins: pd.DataFrame,
    first_interval_probability: np.ndarray,
    *,
    horizon_years: int,
) -> np.ndarray:
    """Combine a supplied first-interval risk with later logistic hazards."""

    if horizon_years not in HORIZON_YEARS:
        raise ValueError(f"지원하지 않는 예측기간입니다: {horizon_years}")
    first = np.asarray(first_interval_probability, dtype=float)
    if len(first) != len(origins) or ((first < 0) | (first > 1)).any():
        raise ValueError("첫 구간 위험은 행 수가 같고 0과 1 사이여야 합니다.")
    intervals = horizon_years // 2
    if intervals == 1:
        return first
    later = origins[BASE_FEATURES].loc[origins.index.repeat(intervals - 1)].copy()
    later["interval_index"] = np.tile(np.arange(2, intervals + 1), len(origins))
    hazards = survival_model.predict_proba(later[MODEL_FEATURES])[:, 1].reshape(len(origins), intervals - 1)
    return 1 - (1 - first) * np.prod(1 - hazards, axis=1)


def _select_weight(
    target: pd.Series,
    calibrated_rf: np.ndarray,
    calibrated_logistic: np.ndarray,
) -> dict[str, Any]:
    candidates = []
    for weight in RF_WEIGHTS:
        probabilities = blend_probabilities(calibrated_rf, calibrated_logistic, float(weight))
        threshold = choose_threshold_for_specificity(
            target, probabilities, minimum_specificity=VALIDATION_SPECIFICITY_FLOOR
        )
        candidates.append(
            {
                "rf_weight": float(weight),
                "logistic_weight": float(1 - weight),
                "threshold": threshold,
                "metrics": evaluate(target, probabilities, threshold),
            }
        )
    return max(
        candidates,
        key=lambda item: (
            item["metrics"]["recall"],
            item["metrics"]["specificity"],
            item["metrics"]["auprc"],
            -item["metrics"]["brier_score"],
        ),
    )


def _select_first_interval_method(
    target: pd.Series,
    weighted: np.ndarray,
    stacked: np.ndarray,
) -> tuple[str, dict[str, dict[str, Any]]]:
    results = {}
    for name, probabilities in (("weighted_blend", weighted), ("logistic_stack", stacked)):
        threshold = choose_threshold_for_specificity(
            target, probabilities, minimum_specificity=VALIDATION_SPECIFICITY_FLOOR
        )
        results[name] = {
            "threshold": threshold,
            "metrics": evaluate(target, probabilities, threshold),
        }
    selected = max(
        results,
        key=lambda name: (
            results[name]["metrics"]["recall"],
            results[name]["metrics"]["specificity"],
            results[name]["metrics"]["auprc"],
            -results[name]["metrics"]["brier_score"],
        ),
    )
    return selected, results


def run_experiment(context: dict[str, Any]) -> dict[str, Any]:
    """Select a first-interval ensemble and extend it with later hazards."""

    dataset_path = Path(context["dataset_path"]) / COHORT_FILENAME
    source_dir = Path(context["root"]) / SOURCE_RELATIVE_PATH
    if not dataset_path.is_file() or not source_dir.is_dir():
        raise FileNotFoundError("공통 코호트 또는 Git 제외 KLoSA 원천자료가 없습니다.")
    base = pd.read_pickle(dataset_path)
    assert_no_leakage(FEATURES)
    assert_no_leakage(BASE_FEATURES)
    survival = build_discrete_survival_cohort(
        base,
        load_diabetes_status_by_wave(source_dir),
        feature_columns=BASE_FEATURES,
    )
    base_splits = split_grouped_cohort(base, random_state=RANDOM_STATE)
    names = ("train", "validation", "test")
    pid_sets = {name: set(frame["pid"]) for name, frame in zip(names, base_splits, strict=True)}
    survival_splits = {name: survival.loc[survival["pid"].isin(pid_set)].copy() for name, pid_set in pid_sets.items()}
    two_year_splits = {
        name: horizon_evaluation_frame(frame, horizon_years=2, feature_columns=BASE_FEATURES)
        for name, frame in survival_splits.items()
    }

    train_target = two_year_splits["train"]["target"]
    rf_oof_raw, logistic_oof_raw = _oof_predictions(two_year_splits["train"], survival_splits["train"])
    rf_calibrator = fit_platt(train_target, rf_oof_raw)
    logistic_calibrator = fit_platt(train_target, logistic_oof_raw)
    rf_oof = apply_platt(rf_calibrator, rf_oof_raw)
    logistic_oof = apply_platt(logistic_calibrator, logistic_oof_raw)
    meta_model = LogisticRegression(C=1.0, max_iter=2000, random_state=RANDOM_STATE)
    meta_model.fit(stack_features(rf_oof, logistic_oof), train_target)

    rf_model = make_tuned_rf(RANDOM_STATE)
    rf_model.fit(two_year_splits["train"][FEATURES], train_target)
    survival_model = make_pooled_logistic_hazard_model(random_state=RANDOM_STATE)
    survival_model.fit(
        survival_splits["train"][MODEL_FEATURES],
        survival_splits["train"][SURVIVAL_EVENT],
    )

    first_interval = {}
    for name in ("validation", "test"):
        rf_raw, logistic_raw = _raw_predictions(rf_model, survival_model, two_year_splits[name])
        rf = apply_platt(rf_calibrator, rf_raw)
        logistic = apply_platt(logistic_calibrator, logistic_raw)
        first_interval[name] = {"rf": rf, "logistic": logistic}

    validation_target = two_year_splits["validation"]["target"]
    selected_weight = _select_weight(
        validation_target,
        first_interval["validation"]["rf"],
        first_interval["validation"]["logistic"],
    )
    first_candidates = {}
    for name in ("validation", "test"):
        weighted = blend_probabilities(
            first_interval[name]["rf"],
            first_interval[name]["logistic"],
            selected_weight["rf_weight"],
        )
        stacked = meta_model.predict_proba(
            stack_features(first_interval[name]["rf"], first_interval[name]["logistic"])
        )[:, 1]
        first_candidates[name] = {
            "weighted_blend": weighted,
            "logistic_stack": stacked,
        }
    selected_method, method_validation = _select_first_interval_method(
        validation_target,
        first_candidates["validation"]["weighted_blend"],
        first_candidates["validation"]["logistic_stack"],
    )

    metrics = {name: {} for name in ("survival_only", "weighted_blend", "logistic_stack")}
    thresholds = {name: {} for name in metrics}
    samples = {}
    for years in HORIZON_YEARS:
        validation = horizon_evaluation_frame(
            survival_splits["validation"], horizon_years=years, feature_columns=BASE_FEATURES
        )
        test = horizon_evaluation_frame(survival_splits["test"], horizon_years=years, feature_columns=BASE_FEATURES)
        samples[str(years)] = {
            "validation": {"pids": len(validation), "events": int(validation["target"].sum())},
            "test": {"pids": len(test), "events": int(test["target"].sum())},
        }
        for model_name in metrics:
            if model_name == "survival_only":
                validation_first = first_interval["validation"]["logistic"]
                test_first = first_interval["test"]["logistic"]
            else:
                validation_first = first_candidates["validation"][model_name]
                test_first = first_candidates["test"][model_name]
            validation_first = (
                pd.Series(validation_first, index=two_year_splits["validation"]["pid"])
                .loc[validation["pid"]]
                .to_numpy()
            )
            test_first = pd.Series(test_first, index=two_year_splits["test"]["pid"]).loc[test["pid"]].to_numpy()
            validation_probability = predict_first_interval_curve(
                survival_model,
                validation,
                validation_first,
                horizon_years=years,
            )
            test_probability = predict_first_interval_curve(
                survival_model,
                test,
                test_first,
                horizon_years=years,
            )
            threshold = choose_threshold_for_specificity(
                validation["target"],
                validation_probability,
                minimum_specificity=VALIDATION_SPECIFICITY_FLOOR,
            )
            thresholds[model_name][str(years)] = threshold
            metrics[model_name][str(years)] = {
                "validation": evaluate(validation["target"], validation_probability, threshold),
                "test": evaluate(test["target"], test_probability, threshold),
                "test_calibration": _calibration_summary(test["target"], test_probability),
            }

    all_test_origins = (
        survival_splits["test"].sort_values(["pid", "interval_index"]).drop_duplicates("pid", keep="first")
    )
    all_first = (
        pd.Series(
            first_candidates["test"][selected_method],
            index=two_year_splits["test"]["pid"],
        )
        .loc[all_test_origins["pid"]]
        .to_numpy()
    )
    all_curve = np.column_stack(
        [
            predict_first_interval_curve(survival_model, all_test_origins, all_first, horizon_years=years)
            for years in HORIZON_YEARS
        ]
    )
    if (np.diff(all_curve, axis=1) < -1e-12).any():
        raise AssertionError("개인별 누적 위험곡선은 감소할 수 없습니다.")

    selected_metrics = metrics[selected_method]
    record = {
        "status": "research_first_interval_ensemble_not_operationally_approved",
        "curve_formula": "1-(1-p_ensemble_2y)*product(1-h_logistic_k), k=2..K",
        "selection_policy": "first method fixed by 2-year Validation only",
        "selected_first_interval_method": selected_method,
        "selected_weighted_blend": selected_weight,
        "first_interval_method_validation": method_validation,
        "meta_model": {
            "intercept": float(meta_model.intercept_[0]),
            "rf_logit_coefficient": float(meta_model.coef_[0, 0]),
            "logistic_logit_coefficient": float(meta_model.coef_[0, 1]),
        },
        "samples": samples,
        "thresholds": thresholds,
        "metrics": metrics,
        "selected_metrics": selected_metrics,
        "monotonic_curve_check": {
            "passed": True,
            "test_pids": len(all_test_origins),
            "horizons": list(HORIZON_YEARS),
        },
        "test_holdout_warning": "historical Test has been inspected in prior experiments",
    }
    run_dir = Path(context["run_dir"])
    result_name = "first_interval_survival_ensemble_results.json"
    (run_dir / result_name).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    artifact_name = "model.joblib"
    manifest = context["manifest"]
    joblib.dump(
        {
            "rf_model": rf_model,
            "survival_model": survival_model,
            "rf_calibrator": rf_calibrator,
            "logistic_calibrator": logistic_calibrator,
            "meta_model": meta_model,
            "first_interval_method": selected_method,
            "rf_weight": selected_weight["rf_weight"],
            "thresholds": thresholds[selected_method],
            "horizon_years": list(HORIZON_YEARS),
            "features": FEATURES,
            "dataset_version": manifest["dataset_version"],
            "split_version": manifest["split_version"],
            "feature_schema_version": manifest["feature_schema_version"],
            "purpose": "risk_screening_and_health_education_research_only",
            "operational_model": None,
        },
        run_dir / artifact_name,
        compress=3,
    )
    constraint_horizon = min(
        HORIZON_YEARS,
        key=lambda years: selected_metrics[str(years)]["test"]["specificity"],
    )
    return {
        "metrics": _runner_metrics(selected_metrics[str(constraint_horizon)]["test"]),
        "artifact": artifact_name,
        "notes": (
            f"selected={selected_method}; constraint_horizon={constraint_horizon}; "
            f"details={result_name}; research use only"
        ),
    }
