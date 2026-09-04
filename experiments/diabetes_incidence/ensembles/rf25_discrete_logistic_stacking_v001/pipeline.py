"""Logistic stack of calibrated RF25 and pooled-logistic predictions."""

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
    SOURCE_RELATIVE_PATH,
    _calibration_summary,
    _oof_predictions,
    _raw_predictions,
    _runner_metrics,
    apply_platt,
    fit_platt,
    make_tuned_rf,
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
    SURVIVAL_EVENT,
    build_discrete_survival_cohort,
    horizon_evaluation_frame,
)

COHORT_FILENAME = "klosa_diabetes_incidence_stage3_25features_v1.pkl"
VALIDATION_SPECIFICITY_FLOOR = 0.43


def _logit(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped))


def stack_features(rf: np.ndarray, logistic: np.ndarray) -> np.ndarray:
    if len(rf) != len(logistic):
        raise ValueError("두 기준 모델의 예측 길이가 다릅니다.")
    return np.column_stack((_logit(rf), _logit(logistic)))


def run_experiment(context: dict[str, Any]) -> dict[str, Any]:
    """Fit the stacker on Train OOF scores and evaluate a fixed Test once."""

    dataset_path = Path(context["dataset_path"]) / COHORT_FILENAME
    source_dir = Path(context["root"]) / SOURCE_RELATIVE_PATH
    if not dataset_path.is_file() or not source_dir.is_dir():
        raise FileNotFoundError("공통 코호트 또는 Git 제외 KLoSA 원천자료가 없습니다.")
    base = pd.read_pickle(dataset_path)
    assert_no_leakage(FEATURES)
    assert_no_leakage(BASE_FEATURES)
    if set(FEATURES) != set(BASE_FEATURES):
        raise AssertionError("두 기준 모델의 RF25 특성이 다릅니다.")

    survival = build_discrete_survival_cohort(
        base,
        load_diabetes_status_by_wave(source_dir),
        feature_columns=BASE_FEATURES,
    )
    base_splits = split_grouped_cohort(base, random_state=RANDOM_STATE)
    names = ("train", "validation", "test")
    pid_sets = {name: set(frame["pid"]) for name, frame in zip(names, base_splits, strict=True)}
    survival_splits = {name: survival.loc[survival["pid"].isin(pid_set)].copy() for name, pid_set in pid_sets.items()}
    horizon_splits = {
        name: horizon_evaluation_frame(frame, horizon_years=2, feature_columns=BASE_FEATURES)
        for name, frame in survival_splits.items()
    }

    rf_oof_raw, logistic_oof_raw = _oof_predictions(horizon_splits["train"], survival_splits["train"])
    train_target = horizon_splits["train"]["target"]
    rf_calibrator = fit_platt(train_target, rf_oof_raw)
    logistic_calibrator = fit_platt(train_target, logistic_oof_raw)
    rf_oof = apply_platt(rf_calibrator, rf_oof_raw)
    logistic_oof = apply_platt(logistic_calibrator, logistic_oof_raw)

    meta_model = LogisticRegression(
        C=1.0,
        class_weight=None,
        max_iter=2000,
        random_state=RANDOM_STATE,
    )
    meta_model.fit(stack_features(rf_oof, logistic_oof), train_target)

    rf_model = make_tuned_rf(RANDOM_STATE)
    rf_model.fit(horizon_splits["train"][FEATURES], train_target)
    survival_model = make_pooled_logistic_hazard_model(random_state=RANDOM_STATE)
    survival_model.fit(
        survival_splits["train"][MODEL_FEATURES],
        survival_splits["train"][SURVIVAL_EVENT],
    )

    probabilities = {}
    components = {}
    for name in ("validation", "test"):
        rf_raw, logistic_raw = _raw_predictions(rf_model, survival_model, horizon_splits[name])
        rf = apply_platt(rf_calibrator, rf_raw)
        logistic = apply_platt(logistic_calibrator, logistic_raw)
        components[name] = {"rf": rf, "logistic": logistic}
        probabilities[name] = meta_model.predict_proba(stack_features(rf, logistic))[:, 1]

    validation_target = horizon_splits["validation"]["target"]
    threshold = choose_threshold_for_specificity(
        validation_target,
        probabilities["validation"],
        minimum_specificity=VALIDATION_SPECIFICITY_FLOOR,
    )
    validation_metrics = evaluate(validation_target, probabilities["validation"], threshold)
    test_target = horizon_splits["test"]["target"]
    test_metrics = evaluate(test_target, probabilities["test"], threshold)

    component_metrics = {}
    for model_name in ("rf", "logistic"):
        component_threshold = choose_threshold_for_specificity(
            validation_target,
            components["validation"][model_name],
            minimum_specificity=VALIDATION_SPECIFICITY_FLOOR,
        )
        component_metrics[model_name] = {
            "threshold": component_threshold,
            "validation": evaluate(validation_target, components["validation"][model_name], component_threshold),
            "test": evaluate(test_target, components["test"][model_name], component_threshold),
        }

    record = {
        "status": "research_logistic_stacking_not_operationally_approved",
        "cohort_policy": "one earliest eligible origin per PID with observed 2-year outcome",
        "split_policy": "RF25 master PID 70/15/15 random_state=42",
        "base_oof_policy": "Train PID-stratified 5-fold; Platt calibration fit on OOF scores",
        "meta_policy": "C=1.0 unweighted Logistic fit only on Train OOF calibrated logits",
        "threshold_policy": "Validation maximize recall subject to specificity >= 0.43",
        "test_policy": "fixed reporting only; historical holdout previously inspected",
        "samples": {
            name: {"pids": len(frame), "events": int(frame["target"].sum())} for name, frame in horizon_splits.items()
        },
        "meta_model": {
            "intercept": float(meta_model.intercept_[0]),
            "rf_logit_coefficient": float(meta_model.coef_[0, 0]),
            "logistic_logit_coefficient": float(meta_model.coef_[0, 1]),
        },
        "oof_calibration": {
            "rf": _calibration_summary(train_target, rf_oof),
            "logistic": _calibration_summary(train_target, logistic_oof),
            "stack": _calibration_summary(
                train_target,
                meta_model.predict_proba(stack_features(rf_oof, logistic_oof))[:, 1],
            ),
        },
        "components": component_metrics,
        "threshold": threshold,
        "validation": {
            "metrics": validation_metrics,
            "calibration": _calibration_summary(validation_target, probabilities["validation"]),
        },
        "test": {
            "metrics": test_metrics,
            "calibration": _calibration_summary(test_target, probabilities["test"]),
        },
    }
    run_dir = Path(context["run_dir"])
    result_name = "logistic_stacking_results.json"
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
            "meta_features": ["rf_calibrated_logit", "logistic_calibrated_logit"],
            "threshold": threshold,
            "features": FEATURES,
            "horizon_years": 2,
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
        "notes": f"details={result_name}; research use only",
    }
