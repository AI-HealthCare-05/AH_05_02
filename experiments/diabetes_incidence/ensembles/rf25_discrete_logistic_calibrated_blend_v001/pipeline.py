"""Blend calibrated RF25 and pooled-logistic two-year risk estimates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

from src.ml.evaluation.compare_klosa_thresholds import choose_threshold_for_specificity
from src.ml.modeling.discrete_time_survival import (
    BASE_FEATURES,
    MODEL_FEATURES,
    make_pooled_logistic_hazard_model,
    predict_cumulative_risk,
)
from src.ml.modeling.train_klosa_diabetes_extended_features import make_extended_pipeline
from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.modeling.train_klosa_diabetes_sample import assert_no_leakage, evaluate
from src.ml.preprocessing.build_klosa_diabetes_mental_rhythm_cohort import (
    MENTAL_RHYTHM_CATEGORICAL_FEATURES,
    MENTAL_RHYTHM_EXTENDED_FEATURES,
    MENTAL_RHYTHM_NUMERIC_FEATURES,
)
from src.ml.preprocessing.build_klosa_diabetes_multihorizon_cohort import load_diabetes_status_by_wave
from src.ml.preprocessing.build_klosa_diabetes_socioeconomic_cohort import (
    SOCIOECONOMIC_CATEGORICAL_FEATURES,
    SOCIOECONOMIC_NUMERIC_FEATURES,
)
from src.ml.preprocessing.build_klosa_discrete_survival_cohort import (
    SURVIVAL_EVENT,
    build_discrete_survival_cohort,
    horizon_evaluation_frame,
)

RANDOM_STATE = 42
OOF_SPLITS = 5
VALIDATION_SPECIFICITY_FLOOR = 0.43
COHORT_FILENAME = "klosa_diabetes_incidence_stage3_25features_v1.pkl"
SOURCE_RELATIVE_PATH = Path("data/interim/source_extract/klosa/20260413")
FEATURES = list(MENTAL_RHYTHM_EXTENDED_FEATURES)
RF_WEIGHTS = np.round(np.arange(0.05, 1.0, 0.05), 2)
TUNED_RF_PARAMETERS = {
    "classifier__min_samples_leaf": 39,
    "classifier__max_samples": 0.7,
    "classifier__criterion": "log_loss",
    "classifier__ccp_alpha": 0.00001,
    "classifier__bootstrap": True,
}


def make_tuned_rf(random_state: int):
    model = make_extended_pipeline(
        "random_forest",
        random_state=random_state,
        additional_numeric_features=[
            *SOCIOECONOMIC_NUMERIC_FEATURES,
            *MENTAL_RHYTHM_NUMERIC_FEATURES,
        ],
        additional_categorical_features=[
            *SOCIOECONOMIC_CATEGORICAL_FEATURES,
            *MENTAL_RHYTHM_CATEGORICAL_FEATURES,
        ],
    )
    return model.set_params(**TUNED_RF_PARAMETERS)


def _logit(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped)).reshape(-1, 1)


def fit_platt(target: pd.Series, raw_probabilities: np.ndarray) -> LogisticRegression:
    calibrator = LogisticRegression(C=1e6, max_iter=2000, random_state=RANDOM_STATE)
    calibrator.fit(_logit(raw_probabilities), target)
    return calibrator


def apply_platt(calibrator: LogisticRegression, raw_probabilities: np.ndarray) -> np.ndarray:
    return calibrator.predict_proba(_logit(raw_probabilities))[:, 1]


def blend_probabilities(rf: np.ndarray, logistic: np.ndarray, rf_weight: float) -> np.ndarray:
    if not 0 <= rf_weight <= 1:
        raise ValueError("RF 가중치는 0과 1 사이여야 합니다.")
    if len(rf) != len(logistic):
        raise ValueError("두 모델의 예측 길이가 다릅니다.")
    return rf_weight * np.asarray(rf) + (1 - rf_weight) * np.asarray(logistic)


def _folds(frame: pd.DataFrame):
    splitter = StratifiedKFold(n_splits=OOF_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    return list(splitter.split(frame["pid"], frame["target"]))


def _raw_predictions(rf_model, survival_model, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    rf = rf_model.predict_proba(frame[FEATURES])[:, 1]
    logistic = predict_cumulative_risk(survival_model, frame, horizon_years=2)
    return rf, logistic


def _oof_predictions(train_2y: pd.DataFrame, train_survival: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    rf_oof = np.full(len(train_2y), np.nan)
    logistic_oof = np.full(len(train_2y), np.nan)
    for fold_number, (fit_indices, oof_indices) in enumerate(_folds(train_2y)):
        fit = train_2y.iloc[fit_indices]
        oof = train_2y.iloc[oof_indices]
        fit_pids = set(fit["pid"])
        fold_survival = train_survival.loc[train_survival["pid"].isin(fit_pids)]

        rf_model = make_tuned_rf(RANDOM_STATE + fold_number)
        rf_model.fit(fit[FEATURES], fit["target"])
        survival_model = make_pooled_logistic_hazard_model(random_state=RANDOM_STATE + fold_number)
        survival_model.fit(fold_survival[MODEL_FEATURES], fold_survival[SURVIVAL_EVENT])
        rf_oof[oof_indices], logistic_oof[oof_indices] = _raw_predictions(rf_model, survival_model, oof)
    if np.isnan(rf_oof).any() or np.isnan(logistic_oof).any():
        raise AssertionError("모든 Train 행에 PID OOF 예측이 필요합니다.")
    return rf_oof, logistic_oof


def _calibration_summary(target: pd.Series, probabilities: np.ndarray) -> dict[str, float]:
    labels = np.asarray(target, dtype=float)
    probabilities = np.asarray(probabilities, dtype=float)
    return {
        "brier_score": float(np.mean((labels - probabilities) ** 2)),
        "mean_predicted_probability": float(probabilities.mean()),
        "observed_event_rate": float(labels.mean()),
        "calibration_in_the_large": float(probabilities.mean() - labels.mean()),
    }


def _evaluate_candidate(target: pd.Series, probabilities: np.ndarray) -> dict[str, Any]:
    threshold = choose_threshold_for_specificity(
        target, probabilities, minimum_specificity=VALIDATION_SPECIFICITY_FLOOR
    )
    return {
        "threshold": threshold,
        "metrics": evaluate(target, probabilities, threshold),
        "calibration": _calibration_summary(target, probabilities),
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
    """Fit OOF calibrators, select blend on Validation, and report Test."""

    dataset_path = Path(context["dataset_path"]) / COHORT_FILENAME
    source_dir = Path(context["root"]) / SOURCE_RELATIVE_PATH
    base = pd.read_pickle(dataset_path)
    assert_no_leakage(FEATURES)
    assert_no_leakage(BASE_FEATURES)
    if set(FEATURES) != set(BASE_FEATURES):
        raise AssertionError("RF와 이산시간 모델의 기준 특성이 다릅니다.")

    survival = build_discrete_survival_cohort(
        base,
        load_diabetes_status_by_wave(source_dir),
        feature_columns=BASE_FEATURES,
    )
    base_splits = split_grouped_cohort(base, random_state=RANDOM_STATE)
    names = ("train", "validation", "test")
    pids = {name: set(frame["pid"]) for name, frame in zip(names, base_splits, strict=True)}
    survival_splits = {name: survival.loc[survival["pid"].isin(pid_set)].copy() for name, pid_set in pids.items()}
    horizon_splits = {
        name: horizon_evaluation_frame(frame, horizon_years=2, feature_columns=BASE_FEATURES)
        for name, frame in survival_splits.items()
    }

    rf_oof, logistic_oof = _oof_predictions(horizon_splits["train"], survival_splits["train"])
    rf_calibrator = fit_platt(horizon_splits["train"]["target"], rf_oof)
    logistic_calibrator = fit_platt(horizon_splits["train"]["target"], logistic_oof)

    rf_model = make_tuned_rf(RANDOM_STATE)
    rf_model.fit(horizon_splits["train"][FEATURES], horizon_splits["train"]["target"])
    survival_model = make_pooled_logistic_hazard_model(random_state=RANDOM_STATE)
    survival_model.fit(survival_splits["train"][MODEL_FEATURES], survival_splits["train"][SURVIVAL_EVENT])

    predictions = {}
    for name in ("validation", "test"):
        rf_raw, logistic_raw = _raw_predictions(rf_model, survival_model, horizon_splits[name])
        predictions[name] = {
            "rf": apply_platt(rf_calibrator, rf_raw),
            "logistic": apply_platt(logistic_calibrator, logistic_raw),
        }

    validation_target = horizon_splits["validation"]["target"]
    component_validation = {
        model_name: _evaluate_candidate(validation_target, probabilities)
        for model_name, probabilities in predictions["validation"].items()
    }
    candidates = []
    for rf_weight in RF_WEIGHTS:
        blended = blend_probabilities(
            predictions["validation"]["rf"],
            predictions["validation"]["logistic"],
            float(rf_weight),
        )
        result = _evaluate_candidate(validation_target, blended)
        candidates.append({"rf_weight": float(rf_weight), "logistic_weight": float(1 - rf_weight), **result})
    selected = max(
        candidates,
        key=lambda item: (
            item["metrics"]["recall"],
            item["metrics"]["specificity"],
            item["metrics"]["auprc"],
            -item["calibration"]["brier_score"],
        ),
    )

    test_target = horizon_splits["test"]["target"]
    component_test = {
        name: evaluate(test_target, predictions["test"][name], result["threshold"])
        for name, result in component_validation.items()
    }
    selected_test_probabilities = blend_probabilities(
        predictions["test"]["rf"], predictions["test"]["logistic"], selected["rf_weight"]
    )
    selected_test = evaluate(test_target, selected_test_probabilities, selected["threshold"])

    record = {
        "status": "research_calibrated_blend_not_operationally_approved",
        "cohort_policy": "one earliest eligible origin per PID with observed 2-year outcome",
        "split_policy": "RF25 master PID 70/15/15 random_state=42",
        "oof_policy": "Train PID-stratified 5-fold base predictions; Platt fit on OOF only",
        "selection_policy": "Validation specificity >= 0.43; recall, specificity, AUPRC, Brier",
        "test_policy": "fixed reporting only; historical holdout previously inspected",
        "rf_parameters": TUNED_RF_PARAMETERS,
        "weight_grid": [float(value) for value in RF_WEIGHTS],
        "samples": {
            name: {
                "pids": len(frame),
                "events": int(frame["target"].sum()),
            }
            for name, frame in horizon_splits.items()
        },
        "oof_calibration": {
            "rf": _calibration_summary(horizon_splits["train"]["target"], apply_platt(rf_calibrator, rf_oof)),
            "logistic": _calibration_summary(
                horizon_splits["train"]["target"], apply_platt(logistic_calibrator, logistic_oof)
            ),
        },
        "component_validation": component_validation,
        "component_test": component_test,
        "candidates": candidates,
        "selected": {
            **selected,
            "test": selected_test,
            "test_calibration": _calibration_summary(test_target, selected_test_probabilities),
        },
    }
    run_dir = Path(context["run_dir"])
    result_name = "calibrated_blend_results.json"
    (run_dir / result_name).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    artifact_name = "model.joblib"
    manifest = context["manifest"]
    joblib.dump(
        {
            "rf_model": rf_model,
            "survival_model": survival_model,
            "rf_calibrator": rf_calibrator,
            "logistic_calibrator": logistic_calibrator,
            "rf_weight": selected["rf_weight"],
            "logistic_weight": selected["logistic_weight"],
            "threshold": selected["threshold"],
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
        "metrics": _runner_metrics(selected_test),
        "artifact": artifact_name,
        "notes": (
            f"rf_weight={selected['rf_weight']}; logistic_weight={selected['logistic_weight']}; "
            f"details={result_name}; research use only"
        ),
    }
