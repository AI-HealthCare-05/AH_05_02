"""Validation-only age-stratified threshold experiment for KNHANES and KLoSA."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.ml.modeling.klosa_full_retrain import select_adaptive_threshold
from src.ml.modeling.recall_ensemble import _apply_calibrator, _threshold_version, load_dataset

AGE_GROUP_ORDER = ("19-44", "45-64", "65+")


def age_groups(frame: pd.DataFrame) -> pd.Series:
    return pd.cut(
        frame["age"],
        bins=[18, 44, 64, np.inf],
        labels=list(AGE_GROUP_ORDER),
    ).astype("string")


def metrics_from_predictions(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    predictions: np.ndarray,
    null_probability: float,
) -> dict[str, Any]:
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    specificity = float(tn / (tn + fp)) if tn + fp else 0.0
    prevalence = float(np.mean(y_true))
    brier = float(brier_score_loss(y_true, probabilities))
    null_brier = float(brier_score_loss(y_true, np.full(len(y_true), null_probability)))
    return {
        "n": int(len(y_true)),
        "positive_n": int(np.sum(y_true)),
        "prevalence": prevalence,
        "auroc": float(roc_auc_score(y_true, probabilities)),
        "auprc": float(average_precision_score(y_true, probabilities)),
        "auprc_lift": float(average_precision_score(y_true, probabilities) / prevalence),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "specificity": specificity,
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "brier": brier,
        "null_model_brier": null_brier,
        "brier_skill_score": float(1 - brier / null_brier),
        "predicted_positive_rate": float(np.mean(predictions)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def select_age_thresholds(
    validation: pd.DataFrame,
    probabilities: np.ndarray,
    config: dict[str, Any],
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    groups = age_groups(validation)
    y_validation = validation["_target"].to_numpy(dtype=int)
    thresholds: dict[str, float] = {}
    rows: list[dict[str, Any]] = []
    for group in AGE_GROUP_ORDER:
        mask = (groups == group).to_numpy()
        if not mask.any():
            continue
        positive_n = int(y_validation[mask].sum())
        if positive_n < int(config["minimum_validation_positive_events"]):
            raise ValueError(f"Insufficient validation events for {group}: {positive_n}")
        minimum_specificity = float(config["knhanes"]["minimum_specificity_by_age"][group])
        selection_config = {
            "threshold_grid": config["knhanes"]["threshold_grid"],
            "selection_constraints": {
                "minimum_specificity": minimum_specificity,
                "minimum_auprc_lift": float(config["minimum_auprc_lift"]),
            },
        }
        threshold, metrics = select_adaptive_threshold(y_validation[mask], probabilities[mask], selection_config)
        thresholds[group] = threshold
        rows.append(
            {
                "age_group": group,
                "minimum_specificity_policy": minimum_specificity,
                "threshold": threshold,
                "threshold_version": _threshold_version("knhanes", f"age-{group}", threshold, config["experiment_id"]),
                **metrics,
            }
        )
    return thresholds, rows


def evaluate_threshold_policy(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    thresholds: dict[str, float],
    global_threshold: float,
    null_probability: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups = age_groups(frame)
    y_true = frame["_target"].to_numpy(dtype=int)
    per_group: list[dict[str, Any]] = []
    aggregate: list[dict[str, Any]] = []
    for policy in ("global", "age_stratified"):
        if policy == "global":
            row_thresholds = np.full(len(frame), global_threshold)
        else:
            row_thresholds = groups.map(thresholds).to_numpy(dtype=float)
        predictions = (probabilities >= row_thresholds).astype(int)
        aggregate.append(
            {
                "policy": policy,
                **metrics_from_predictions(y_true, probabilities, predictions, null_probability),
            }
        )
        for group in AGE_GROUP_ORDER:
            mask = (groups == group).to_numpy()
            if not mask.any():
                continue
            threshold = global_threshold if policy == "global" else thresholds[group]
            per_group.append(
                {
                    "policy": policy,
                    "age_group": group,
                    "threshold": threshold,
                    **metrics_from_predictions(y_true[mask], probabilities[mask], predictions[mask], null_probability),
                }
            )
    return aggregate, per_group


def exploratory_sensitivity_analysis(
    validation: pd.DataFrame,
    test: pd.DataFrame,
    validation_probabilities: np.ndarray,
    test_probabilities: np.ndarray,
    global_threshold: float,
    null_probability: float,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    threshold_rows: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, Any]] = []
    for target in config["exploratory_specificity_targets"]:
        sensitivity_config = json.loads(json.dumps(config))
        sensitivity_config["knhanes"]["minimum_specificity_by_age"] = {
            group: float(target) for group in AGE_GROUP_ORDER
        }
        thresholds, rows = select_age_thresholds(validation, validation_probabilities, sensitivity_config)
        for row in rows:
            threshold_rows.append({"specificity_policy_target": float(target), **row})
        validation_aggregate, _ = evaluate_threshold_policy(
            validation,
            validation_probabilities,
            thresholds,
            global_threshold,
            null_probability,
        )
        test_aggregate, _ = evaluate_threshold_policy(
            test,
            test_probabilities,
            thresholds,
            global_threshold,
            null_probability,
        )
        for split, rows_for_split in (
            ("validation", validation_aggregate),
            ("test", test_aggregate),
        ):
            selected = next(row for row in rows_for_split if row["policy"] == "age_stratified")
            aggregate_rows.append(
                {
                    "specificity_policy_target": float(target),
                    "split": split,
                    **selected,
                }
            )
    return threshold_rows, aggregate_rows


def select_risk_band_cutoffs(
    validation: pd.DataFrame,
    probabilities: np.ndarray,
    config: dict[str, Any],
) -> tuple[dict[str, dict[str, float]], list[dict[str, Any]]]:
    groups = age_groups(validation)
    y_true = validation["_target"].to_numpy(dtype=int)
    grid = config["knhanes"]["threshold_grid"]
    fixed = np.linspace(float(grid["minimum"]), float(grid["maximum"]), int(grid["points"]))
    policy = config["risk_band_policy"]
    cutoffs: dict[str, dict[str, float]] = {}
    rows: list[dict[str, Any]] = []
    for group in AGE_GROUP_ORDER:
        mask = (groups == group).to_numpy()
        group_y = y_true[mask]
        group_probabilities = probabilities[mask]
        candidates = np.unique(
            np.concatenate([fixed, np.quantile(group_probabilities, np.linspace(0.005, 0.995, 199))])
        )
        metrics = []
        for threshold in candidates:
            predictions = (group_probabilities >= threshold).astype(int)
            tn, fp, fn, tp = confusion_matrix(group_y, predictions, labels=[0, 1]).ravel()
            metrics.append(
                {
                    "threshold": float(threshold),
                    "recall": float(tp / (tp + fn)) if tp + fn else 0.0,
                    "specificity": float(tn / (tn + fp)) if tn + fp else 0.0,
                }
            )
        low_feasible = [row for row in metrics if row["recall"] >= float(policy["low_cutoff_minimum_recall"])]
        if not low_feasible:
            raise ValueError(f"No feasible risk-band cutoff for {group}")
        low = max(low_feasible, key=lambda row: (row["specificity"], row["threshold"]))
        high_feasible = [
            row
            for row in metrics
            if row["specificity"] >= float(policy["high_cutoff_minimum_specificity"])
            and row["threshold"] > low["threshold"]
        ]
        if not high_feasible:
            raise ValueError(f"No feasible high-risk cutoff for {group}")
        high = max(high_feasible, key=lambda row: (row["recall"], -row["threshold"]))
        cutoffs[group] = {
            "low_cutoff": low["threshold"],
            "high_cutoff": high["threshold"],
        }
        rows.append(
            {
                "age_group": group,
                "low_cutoff": low["threshold"],
                "low_cutoff_recall": low["recall"],
                "low_cutoff_specificity": low["specificity"],
                "high_cutoff": high["threshold"],
                "high_cutoff_recall": high["recall"],
                "high_cutoff_specificity": high["specificity"],
            }
        )
    return cutoffs, rows


def evaluate_risk_bands(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    cutoffs: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    groups = age_groups(frame)
    y_true = frame["_target"].to_numpy(dtype=int)
    rows: list[dict[str, Any]] = []
    for group in AGE_GROUP_ORDER:
        group_mask = (groups == group).to_numpy()
        if not group_mask.any():
            continue
        low_cutoff = cutoffs[group]["low_cutoff"]
        high_cutoff = cutoffs[group]["high_cutoff"]
        group_probabilities = probabilities[group_mask]
        group_y = y_true[group_mask]
        bands = np.where(
            group_probabilities < low_cutoff,
            "low",
            np.where(group_probabilities >= high_cutoff, "high", "caution"),
        )
        for band in ("low", "caution", "high"):
            band_mask = bands == band
            n = int(band_mask.sum())
            positive_n = int(group_y[band_mask].sum())
            rows.append(
                {
                    "age_group": group,
                    "risk_band": band,
                    "low_cutoff": low_cutoff,
                    "high_cutoff": high_cutoff,
                    "n": n,
                    "positive_n": positive_n,
                    "observed_positive_rate": float(positive_n / n) if n else 0.0,
                    "age_group_share": float(n / group_mask.sum()),
                }
            )
    return rows


def knhanes_probabilities(artifact: dict[str, Any], frame: pd.DataFrame) -> np.ndarray:
    features = frame[artifact["feature_columns"]]
    base = {name: model.predict_proba(features)[:, 1] for name, model in artifact["base_models"].items()}
    model_name = artifact["final_model"]
    if model_name in base:
        raw = base[model_name]
    elif model_name == "stacking":
        names = artifact["ensemble"]["base_model_order"]
        raw = artifact["ensemble"]["stacker"].predict_proba(np.column_stack([base[name] for name in names]))[:, 1]
    else:
        raise ValueError(f"Unsupported final KNHANES model: {model_name}")
    postprocessing = artifact["final_postprocessing"]
    if postprocessing == "sigmoid":
        return _apply_calibrator(artifact["postprocessors"][model_name]["sigmoid"], raw)
    if postprocessing == "isotonic":
        return np.asarray(artifact["postprocessors"][model_name]["isotonic"].predict(raw))
    return np.asarray(raw)


def klosa_probabilities(artifact: dict[str, Any], frame: pd.DataFrame) -> np.ndarray:
    raw = artifact["model"].predict_proba(frame[artifact["feature_columns"]])[:, 1]
    if artifact["final_candidate"] == "logistic_sigmoid_calibrated":
        return _apply_calibrator(artifact["calibrator"], raw)
    return np.asarray(raw)


def run(
    knhanes_data: Path,
    klosa_data: Path,
    config_path: Path,
    knhanes_config_path: Path,
    klosa_config_path: Path,
    knhanes_artifact_path: Path,
    klosa_artifact_path: Path,
    output_dir: Path,
) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    knhanes_config = json.loads(knhanes_config_path.read_text(encoding="utf-8"))["dataset"]
    klosa_config = json.loads(klosa_config_path.read_text(encoding="utf-8"))["dataset"]
    knhanes = load_dataset(knhanes_data, "knhanes", knhanes_config)
    klosa = load_dataset(klosa_data, "klosa", klosa_config)
    knhanes_artifact = joblib.load(knhanes_artifact_path)
    klosa_artifact = joblib.load(klosa_artifact_path)

    knhanes_validation = knhanes.loc[knhanes["split"] == "validation"].reset_index(drop=True)
    knhanes_test = knhanes.loc[knhanes["split"] == "test"].reset_index(drop=True)
    validation_probabilities = knhanes_probabilities(knhanes_artifact, knhanes_validation)
    test_probabilities = knhanes_probabilities(knhanes_artifact, knhanes_test)
    age_thresholds, validation_rows = select_age_thresholds(knhanes_validation, validation_probabilities, config)
    null_probability = float(knhanes.loc[knhanes["split"] == "train", "_target"].mean())
    aggregate, per_group = evaluate_threshold_policy(
        knhanes_test,
        test_probabilities,
        age_thresholds,
        float(knhanes_artifact["threshold"]),
        null_probability,
    )
    sensitivity_thresholds, sensitivity_aggregate = exploratory_sensitivity_analysis(
        knhanes_validation,
        knhanes_test,
        validation_probabilities,
        test_probabilities,
        float(knhanes_artifact["threshold"]),
        null_probability,
        config,
    )
    risk_band_cutoffs, risk_band_validation = select_risk_band_cutoffs(
        knhanes_validation, validation_probabilities, config
    )
    risk_band_test = evaluate_risk_bands(knhanes_test, test_probabilities, risk_band_cutoffs)

    klosa_test = klosa.loc[klosa["split"] == "test"].reset_index(drop=True)
    klosa_test_probabilities = klosa_probabilities(klosa_artifact, klosa_test)
    klosa_null = float(klosa.loc[klosa["split"] == "train", "_target"].mean())
    klosa_global_threshold = float(klosa_artifact["threshold"])
    _, klosa_age_audit = evaluate_threshold_policy(
        klosa_test,
        klosa_test_probabilities,
        {group: klosa_global_threshold for group in AGE_GROUP_ORDER},
        klosa_global_threshold,
        klosa_null,
    )
    klosa_age_audit = [row for row in klosa_age_audit if row["policy"] == "global"]

    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(validation_rows).to_csv(
        output_dir / "knhanes_age_threshold_validation.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(aggregate).to_csv(
        output_dir / "knhanes_age_threshold_test_aggregate.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(per_group).to_csv(
        output_dir / "knhanes_age_threshold_test_by_age.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(sensitivity_thresholds).to_csv(
        output_dir / "knhanes_age_threshold_sensitivity_validation.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(sensitivity_aggregate).to_csv(
        output_dir / "knhanes_age_threshold_sensitivity_aggregate.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(risk_band_validation).to_csv(
        output_dir / "knhanes_risk_band_cutoffs_validation.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(risk_band_test).to_csv(
        output_dir / "knhanes_risk_band_test_by_age.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(klosa_age_audit).to_csv(
        output_dir / "klosa_global_threshold_test_by_age.csv", index=False, encoding="utf-8-sig"
    )
    manifest = {
        "experiment_id": config["experiment_id"],
        "knhanes_policy": {
            "model": knhanes_artifact["final_candidate"],
            "global_threshold": knhanes_artifact["threshold"],
            "age_thresholds": age_thresholds,
            "risk_band_cutoffs": risk_band_cutoffs,
            "threshold_source": "validation_age_groups_only",
            "test_used_for_selection": False,
        },
        "klosa_policy": config["klosa"],
        "promotion_status": "experimental_internal_not_for_personal_probability_display",
    }
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knhanes-data", type=Path, required=True)
    parser.add_argument("--klosa-data", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/age_stratified_thresholds.json"))
    parser.add_argument("--knhanes-config", type=Path, default=Path("configs/knhanes_full_comparison.json"))
    parser.add_argument("--klosa-config", type=Path, default=Path("configs/klosa_full_retrain.json"))
    parser.add_argument(
        "--knhanes-artifact",
        type=Path,
        default=Path("models/candidate/knhanes_full_comparison/diabetes-knhanes-full-comparison-v0.4.0.joblib"),
    )
    parser.add_argument(
        "--klosa-artifact",
        type=Path,
        default=Path("models/candidate/klosa_full_retrain/diabetes-klosa-full-calibrated-v0.4.0.joblib"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/age_stratified_thresholds"))
    args = parser.parse_args()
    run(
        args.knhanes_data,
        args.klosa_data,
        args.config,
        args.knhanes_config,
        args.klosa_config,
        args.knhanes_artifact,
        args.klosa_artifact,
        args.output_dir,
    )


if __name__ == "__main__":
    main()
