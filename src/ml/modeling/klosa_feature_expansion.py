"""KLoSA feature-bundle ablation using leakage-safe longitudinal history."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from src.ml.modeling.klosa_full_retrain import (
    brier_reference_metrics,
    expected_calibration_error,
    reliability_bins,
    select_adaptive_threshold,
)
from src.ml.modeling.recall_ensemble import (
    _apply_calibrator,
    _cv_splits,
    _preprocessor,
    _sha256_file,
    _sigmoid_calibrator,
    _threshold_version,
    metric_row,
    oof_probabilities,
)

CORE_NUMERIC = ["age", "bmi", "self_rated_health", "meal_count_yesterday"]
CORE_CATEGORICAL = ["sex", "regular_exercise", "current_smoker", "current_drinker"]
HISTORY_NUMERIC = [
    "prior_wave_gap",
    "prior_bmi",
    "bmi_change",
    "prior_self_rated_health",
    "self_rated_health_change",
    "prior_meal_count_yesterday",
    "meal_count_change",
]
HISTORY_CATEGORICAL = [
    "prior_observation_available",
    "prior_regular_exercise",
    "regular_exercise_changed",
    "prior_current_smoker",
    "current_smoker_changed",
    "prior_current_drinker",
    "current_drinker_changed",
]
COMORBIDITY_CATEGORICAL = ["baseline_hypertension_history"]
PRIOR_CONTEXT_NUMERIC = ["prior_wave_gap"]
PRIOR_CONTEXT_CATEGORICAL = ["prior_observation_available"]
BMI_HISTORY_NUMERIC = ["prior_bmi", "bmi_change"]
HEALTH_HISTORY_NUMERIC = ["prior_self_rated_health", "self_rated_health_change"]
MEAL_HISTORY_NUMERIC = ["prior_meal_count_yesterday", "meal_count_change"]
BEHAVIOR_HISTORY_CATEGORICAL = [
    "prior_regular_exercise",
    "regular_exercise_changed",
    "prior_current_smoker",
    "current_smoker_changed",
    "prior_current_drinker",
    "current_drinker_changed",
]


def feature_bundles() -> dict[str, dict[str, list[str]]]:
    return {
        "core_8": {
            "numeric_features": CORE_NUMERIC,
            "categorical_features": CORE_CATEGORICAL,
        },
        "core_8_plus_hypertension": {
            "numeric_features": CORE_NUMERIC,
            "categorical_features": CORE_CATEGORICAL + COMORBIDITY_CATEGORICAL,
        },
        "core_8_plus_bmi_history": {
            "numeric_features": CORE_NUMERIC + PRIOR_CONTEXT_NUMERIC + BMI_HISTORY_NUMERIC,
            "categorical_features": CORE_CATEGORICAL + PRIOR_CONTEXT_CATEGORICAL,
        },
        "core_8_plus_health_history": {
            "numeric_features": CORE_NUMERIC + PRIOR_CONTEXT_NUMERIC + HEALTH_HISTORY_NUMERIC,
            "categorical_features": CORE_CATEGORICAL + PRIOR_CONTEXT_CATEGORICAL,
        },
        "core_8_plus_meal_history": {
            "numeric_features": CORE_NUMERIC + PRIOR_CONTEXT_NUMERIC + MEAL_HISTORY_NUMERIC,
            "categorical_features": CORE_CATEGORICAL + PRIOR_CONTEXT_CATEGORICAL,
        },
        "core_8_plus_behavior_history": {
            "numeric_features": CORE_NUMERIC + PRIOR_CONTEXT_NUMERIC,
            "categorical_features": CORE_CATEGORICAL + PRIOR_CONTEXT_CATEGORICAL + BEHAVIOR_HISTORY_CATEGORICAL,
        },
        "core_8_plus_bmi_history_hypertension": {
            "numeric_features": CORE_NUMERIC + PRIOR_CONTEXT_NUMERIC + BMI_HISTORY_NUMERIC,
            "categorical_features": CORE_CATEGORICAL + PRIOR_CONTEXT_CATEGORICAL + COMORBIDITY_CATEGORICAL,
        },
        "core_8_plus_longitudinal": {
            "numeric_features": CORE_NUMERIC + HISTORY_NUMERIC,
            "categorical_features": CORE_CATEGORICAL + HISTORY_CATEGORICAL,
        },
        "core_8_plus_longitudinal_hypertension": {
            "numeric_features": CORE_NUMERIC + HISTORY_NUMERIC,
            "categorical_features": CORE_CATEGORICAL + HISTORY_CATEGORICAL + COMORBIDITY_CATEGORICAL,
        },
    }


def _as_boolean(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series
    normalized = series.astype("string").str.strip().str.lower()
    return normalized.map({"true": True, "false": False, "1": True, "0": False})


def build_incident_frame(panel_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(panel_path, dtype={"participant_id": "string"}, low_memory=False)
    required = {
        "participant_id",
        "survey_wave",
        "survey_year",
        "split",
        "eligible_diabetes_incident",
        "target_diabetes_incident_next_wave",
        "diagnosed_through_wave_hypertension",
        *CORE_NUMERIC,
        *CORE_CATEGORICAL,
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing KLoSA panel columns: {sorted(missing)}")
    frame = frame.sort_values(["participant_id", "survey_wave"]).reset_index(drop=True)
    grouped = frame.groupby("participant_id", sort=False)
    prior_wave = grouped["survey_wave"].shift(1)
    frame["prior_observation_available"] = prior_wave.notna().astype("Int64")
    frame["prior_wave_gap"] = frame["survey_wave"] - prior_wave

    numeric_history = {
        "bmi": ("prior_bmi", "bmi_change"),
        "self_rated_health": (
            "prior_self_rated_health",
            "self_rated_health_change",
        ),
        "meal_count_yesterday": (
            "prior_meal_count_yesterday",
            "meal_count_change",
        ),
    }
    for source, (prior_name, change_name) in numeric_history.items():
        prior = grouped[source].shift(1)
        frame[prior_name] = prior
        frame[change_name] = frame[source] - prior

    for source in ("regular_exercise", "current_smoker", "current_drinker"):
        prior_name = f"prior_{source}"
        change_name = f"{source}_changed"
        prior = grouped[source].shift(1)
        frame[prior_name] = prior
        changed = frame[source].ne(prior).astype("float")
        frame[change_name] = changed.where(prior.notna(), np.nan)

    frame["baseline_hypertension_history"] = _as_boolean(frame["diagnosed_through_wave_hypertension"]).astype("Int64")
    eligible = _as_boolean(frame["eligible_diabetes_incident"]).fillna(False)
    target_available = frame["target_diabetes_incident_next_wave"].notna()
    incident = frame.loc[eligible & target_available].copy().reset_index(drop=True)
    incident["_target"] = pd.to_numeric(incident["target_diabetes_incident_next_wave"], errors="raise").astype(int)
    if not set(incident["_target"].unique()).issubset({0, 1}):
        raise ValueError("KLoSA incident target must be binary")
    return incident


def _model(bundle: dict[str, list[str]], c_value: float, seed: int) -> Pipeline:
    return Pipeline(
        [
            ("preprocess", _preprocessor(bundle, scale_numeric=True)),
            (
                "model",
                LogisticRegression(
                    C=c_value,
                    class_weight="balanced",
                    max_iter=3000,
                    random_state=seed,
                ),
            ),
        ]
    )


def _metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    null_probability: float,
    bins: int,
    name: str,
) -> dict[str, Any]:
    curve = reliability_bins(y_true, probabilities, bins, name)
    return {
        **metric_row(y_true, probabilities, threshold),
        **brier_reference_metrics(y_true, probabilities, null_probability),
        "expected_calibration_error": expected_calibration_error(curve),
    }


def _assert_participant_split(frame: pd.DataFrame) -> None:
    split_counts = frame.groupby("participant_id")["split"].nunique()
    if int(split_counts.max()) != 1:
        raise ValueError("Participant leakage across KLoSA splits")


def _selection_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        bool(row["constraints_passed"]),
        float(row["recall"]),
        float(row["auprc"]),
        float(row["specificity"]),
        float(row["brier_skill_score"]),
    )


def threshold_sensitivity(
    y_validation: np.ndarray,
    validation_probabilities: np.ndarray,
    y_test: np.ndarray,
    test_probabilities: np.ndarray,
    null_probability: float,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for target in config["exploratory_specificity_targets"]:
        sensitivity_config = json.loads(json.dumps(config))
        sensitivity_config["selection_constraints"]["minimum_specificity"] = float(target)
        threshold, validation_metrics = select_adaptive_threshold(
            y_validation, validation_probabilities, sensitivity_config
        )
        test_metrics = _metrics(
            y_test,
            test_probabilities,
            threshold,
            null_probability,
            int(config["reliability_bins"]),
            f"specificity_{target}",
        )
        rows.append(
            {
                "validation_minimum_specificity_target": float(target),
                "threshold": threshold,
                "validation_recall": validation_metrics["recall"],
                "validation_specificity": validation_metrics["specificity"],
                "test_recall": test_metrics["recall"],
                "test_specificity": test_metrics["specificity"],
                "test_auprc": test_metrics["auprc"],
                "test_brier_skill_score": test_metrics["brier_skill_score"],
                "test_predicted_positive_rate": test_metrics["predicted_positive_rate"],
            }
        )
    return rows


def run(
    panel_path: Path,
    config_path: Path,
    output_dir: Path,
    model_dir: Path,
) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    frame = build_incident_frame(panel_path)
    _assert_participant_split(frame)
    splits = {
        name: frame.loc[frame["split"] == name].copy().reset_index(drop=True)
        for name in ("train", "validation", "test")
    }
    train, validation, test = (splits[name] for name in ("train", "validation", "test"))
    y_train = train["_target"].to_numpy()
    y_validation = validation["_target"].to_numpy()
    y_test = test["_target"].to_numpy()
    null_probability = float(y_train.mean())
    folds = _cv_splits(train, "klosa", int(config["cv_folds"]), int(config["seed"]))

    search_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    test_rows: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    for bundle_name, bundle in feature_bundles().items():
        features = bundle["numeric_features"] + bundle["categorical_features"]
        oof_by_c: dict[float, np.ndarray] = {}
        bundle_search: list[dict[str, Any]] = []
        for c_value in config["c_values"]:
            candidate = _model(bundle, float(c_value), int(config["seed"]))
            oof = oof_probabilities(candidate, train, folds)
            oof_by_c[float(c_value)] = oof
            threshold, metrics = select_adaptive_threshold(y_train, oof, config)
            row = {
                "bundle": bundle_name,
                "feature_count": len(features),
                "c_value": float(c_value),
                "threshold": threshold,
                **metrics,
                **brier_reference_metrics(y_train, oof, null_probability),
            }
            bundle_search.append(row)
            search_rows.append(row)
        selected_search = max(bundle_search, key=_selection_key)
        selected_c = float(selected_search["c_value"])
        fitted = clone(_model(bundle, selected_c, int(config["seed"]))).fit(train[features], y_train)
        calibrator = _sigmoid_calibrator(oof_by_c[selected_c], y_train, int(config["seed"]))
        validation_probabilities = _apply_calibrator(calibrator, fitted.predict_proba(validation[features])[:, 1])
        threshold, selection_metrics = select_adaptive_threshold(y_validation, validation_probabilities, config)
        validation_row = {
            "bundle": bundle_name,
            "feature_count": len(features),
            "selected_c": selected_c,
            "threshold_version": _threshold_version("klosa", bundle_name, threshold, config["experiment_id"]),
            **selection_metrics,
            **brier_reference_metrics(y_validation, validation_probabilities, null_probability),
            "expected_calibration_error": expected_calibration_error(
                reliability_bins(
                    y_validation,
                    validation_probabilities,
                    int(config["reliability_bins"]),
                    bundle_name,
                )
            ),
        }
        validation_rows.append(validation_row)
        test_probabilities = _apply_calibrator(calibrator, fitted.predict_proba(test[features])[:, 1])
        test_metrics = _metrics(
            y_test,
            test_probabilities,
            threshold,
            null_probability,
            int(config["reliability_bins"]),
            bundle_name,
        )
        constraints = config["selection_constraints"]
        test_metrics["constraints_passed"] = bool(
            test_metrics["specificity"] >= float(constraints["minimum_specificity"])
            and test_metrics["auprc_lift"] >= float(constraints["minimum_auprc_lift"])
        )
        test_rows.append(
            {
                "bundle": bundle_name,
                "feature_count": len(features),
                "threshold_source": "validation",
                **test_metrics,
            }
        )
        artifacts[bundle_name] = {
            "model": fitted,
            "calibrator": calibrator,
            "threshold": threshold,
            "features": bundle,
        }

    selected_validation = max(validation_rows, key=_selection_key)
    selected_bundle = selected_validation["bundle"]
    core_validation = next(row for row in validation_rows if row["bundle"] == "core_8")
    acceptance = config["acceptance"]
    selected_validation["recall_gain_vs_core"] = float(selected_validation["recall"] - core_validation["recall"])
    selected_validation["expansion_acceptance_passed"] = bool(
        selected_bundle != "core_8"
        and selected_validation["recall_gain_vs_core"] >= float(acceptance["minimum_validation_recall_gain"])
        and (
            not bool(acceptance["require_non_decreasing_validation_auprc"])
            or selected_validation["auprc"] >= core_validation["auprc"]
        )
        and (
            not bool(acceptance["require_non_decreasing_validation_bss"])
            or selected_validation["brier_skill_score"] >= core_validation["brier_skill_score"]
        )
    )
    selected_artifact = artifacts[selected_bundle]
    selected_features = selected_artifact["features"]
    selected_feature_columns = selected_features["numeric_features"] + selected_features["categorical_features"]
    selected_validation_probabilities = _apply_calibrator(
        selected_artifact["calibrator"],
        selected_artifact["model"].predict_proba(validation[selected_feature_columns])[:, 1],
    )
    selected_test_probabilities = _apply_calibrator(
        selected_artifact["calibrator"],
        selected_artifact["model"].predict_proba(test[selected_feature_columns])[:, 1],
    )
    sensitivity_rows = threshold_sensitivity(
        y_validation,
        selected_validation_probabilities,
        y_test,
        selected_test_probabilities,
        null_probability,
        config,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(search_rows).to_csv(
        output_dir / "klosa_feature_expansion_oof_search.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(validation_rows).to_csv(
        output_dir / "klosa_feature_expansion_validation.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(test_rows).to_csv(
        output_dir / "klosa_feature_expansion_test.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(sensitivity_rows).to_csv(
        output_dir / "klosa_selected_bundle_threshold_sensitivity.csv",
        index=False,
        encoding="utf-8-sig",
    )
    bundle_rows = [
        {
            "bundle": name,
            "feature_count": len(values["numeric_features"]) + len(values["categorical_features"]),
            "numeric_features": "|".join(values["numeric_features"]),
            "categorical_features": "|".join(values["categorical_features"]),
        }
        for name, values in feature_bundles().items()
    ]
    pd.DataFrame(bundle_rows).to_csv(
        output_dir / "klosa_feature_bundle_definitions.csv",
        index=False,
        encoding="utf-8-sig",
    )
    artifact = {
        **selected_artifact,
        "selected_bundle": selected_bundle,
        "model_version": config["model_version"],
        "feature_schema_version": config["feature_schema_version"],
        "promotion_status": "candidate_internal_not_for_personal_probability_display",
    }
    model_path = model_dir / f"{config['model_version']}.joblib"
    joblib.dump(artifact, model_path)
    manifest = {
        "experiment_id": config["experiment_id"],
        "source_file": panel_path.name,
        "source_sha256": _sha256_file(panel_path),
        "target_definition": "t0 미진단자의 다음 인접 조사 신규 당뇨 진단 여부",
        "split_summary": {
            name: {
                "n": len(split),
                "positive_n": int(split["_target"].sum()),
                "positive_rate": float(split["_target"].mean()),
            }
            for name, split in splits.items()
        },
        "feature_bundles": feature_bundles(),
        "selected_candidate_validation": selected_validation,
        "selected_candidate_test": next(row for row in test_rows if row["bundle"] == selected_bundle),
        "test_used_for_selection": False,
        "disease_specific_feature_rule": {
            "baseline_hypertension_history": "allowed_for_future_diabetes_only; forbidden_for_hypertension_target"
        },
        "local_model_path": str(model_path),
        "promotion_status": "candidate_internal_not_for_personal_probability_display",
    }
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/klosa_feature_expansion.json"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/klosa_feature_expansion"))
    parser.add_argument("--model-dir", type=Path, default=Path("models/candidate/klosa_feature_expansion"))
    args = parser.parse_args()
    run(args.panel, args.config, args.output_dir, args.model_dir)


if __name__ == "__main__":
    main()
