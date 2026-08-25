"""Full-sample KLoSA logistic retraining with calibration diagnostics."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import joblib

os.environ.setdefault("MPLCONFIGDIR", str(Path("tmp/matplotlib").resolve()))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.pipeline import Pipeline

from src.ml.modeling.recall_ensemble import (
    SPECS,
    _apply_calibrator,
    _cv_splits,
    _preprocessor,
    _sha256_file,
    _sigmoid_calibrator,
    _threshold_version,
    load_dataset,
    metric_row,
    oof_probabilities,
)


def brier_reference_metrics(y_true: np.ndarray, probabilities: np.ndarray, null_probability: float) -> dict[str, float]:
    model_brier = float(brier_score_loss(y_true, probabilities))
    null_probabilities = np.full(len(y_true), null_probability, dtype=float)
    null_brier = float(brier_score_loss(y_true, null_probabilities))
    return {
        "null_probability_train_prevalence": float(null_probability),
        "null_model_brier": null_brier,
        "brier_skill_score": float(1 - model_brier / null_brier),
    }


def reliability_bins(y_true: np.ndarray, probabilities: np.ndarray, bins: int, model_name: str) -> pd.DataFrame:
    frame = pd.DataFrame({"target": y_true, "probability": probabilities})
    if frame["probability"].nunique() < 2:
        return pd.DataFrame(
            {
                "model": [model_name],
                "bin_number": [1],
                "n": [len(frame)],
                "positive_n": [int(frame["target"].sum())],
                "mean_predicted_probability": [float(frame["probability"].mean())],
                "observed_positive_rate": [float(frame["target"].mean())],
                "absolute_calibration_error": [float(abs(frame["probability"].mean() - frame["target"].mean()))],
            }
        )
    frame["bin"] = pd.qcut(frame["probability"], q=bins, duplicates="drop")
    grouped = (
        frame.groupby("bin", observed=True)
        .agg(
            n=("target", "size"),
            positive_n=("target", "sum"),
            mean_predicted_probability=("probability", "mean"),
            observed_positive_rate=("target", "mean"),
        )
        .reset_index(drop=True)
    )
    grouped.insert(0, "bin_number", np.arange(1, len(grouped) + 1))
    grouped.insert(0, "model", model_name)
    grouped["absolute_calibration_error"] = (
        grouped["mean_predicted_probability"] - grouped["observed_positive_rate"]
    ).abs()
    return grouped


def expected_calibration_error(curve: pd.DataFrame) -> float:
    return float(np.average(curve["absolute_calibration_error"], weights=curve["n"]))


def select_adaptive_threshold(
    y_true: np.ndarray, probabilities: np.ndarray, config: dict[str, Any]
) -> tuple[float, dict[str, Any]]:
    threshold_config = config["threshold_grid"]
    fixed = np.linspace(
        float(threshold_config["minimum"]),
        float(threshold_config["maximum"]),
        int(threshold_config["points"]),
    )
    quantile_thresholds = np.quantile(probabilities, np.linspace(0.005, 0.995, 199))
    thresholds = np.unique(np.clip(np.concatenate([fixed, quantile_thresholds]), 0, 1))
    constraints = config["selection_constraints"]
    candidates = []
    for threshold in thresholds:
        metrics = metric_row(y_true, probabilities, float(threshold))
        metrics["constraints_passed"] = bool(
            metrics["specificity"] >= float(constraints["minimum_specificity"])
            and metrics["auprc_lift"] >= float(constraints["minimum_auprc_lift"])
        )
        candidates.append(metrics)
    feasible = [item for item in candidates if item["constraints_passed"]]
    best = max(
        feasible or candidates,
        key=lambda item: (item["recall"], item["auprc"], item["specificity"], item["threshold"]),
    )
    return float(best["threshold"]), best


def save_reliability_diagram(curves: pd.DataFrame, path: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(14, 6))
    for axis, limit, title in (
        (axes[0], 1.0, "Full probability range"),
        (axes[1], 0.1, "Low-risk range (0–0.1)"),
    ):
        axis.plot([0, limit], [0, limit], linestyle="--", color="black", label="Perfect calibration")
        for model_name, curve in curves.groupby("model", sort=False):
            axis.plot(
                curve["mean_predicted_probability"],
                curve["observed_positive_rate"],
                marker="o",
                linewidth=2,
                label=model_name,
            )
        axis.set_xlim(0, limit)
        axis.set_ylim(0, limit)
        axis.set_xlabel("Mean predicted probability")
        axis.set_ylabel("Observed positive rate")
        axis.set_title(title)
        axis.grid(alpha=0.25)
    axes[0].legend()
    figure.suptitle("KLoSA Reliability Diagram (Test)")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _assert_disjoint_participants(splits: dict[str, pd.DataFrame]) -> None:
    participant_sets = {name: set(frame[SPECS["klosa"].entity_id].astype("string")) for name, frame in splits.items()}
    pairs = (("train", "validation"), ("train", "test"), ("validation", "test"))
    for left, right in pairs:
        if participant_sets[left] & participant_sets[right]:
            raise ValueError(f"Participant leakage between {left} and {right}")


def _model(dataset_config: dict[str, Any], c_value: float, seed: int) -> Pipeline:
    return Pipeline(
        [
            ("preprocess", _preprocessor(dataset_config, scale_numeric=True)),
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


def _metrics_with_brier_reference(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    null_probability: float,
) -> dict[str, Any]:
    return {
        **metric_row(y_true, probabilities, threshold),
        **brier_reference_metrics(y_true, probabilities, null_probability),
    }


def _age_group_metrics(
    test: pd.DataFrame,
    y_test: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    null_probability: float,
) -> list[dict[str, Any]]:
    groups = pd.cut(test["age"], bins=[18, 44, 64, np.inf], labels=["19-44", "45-64", "65+"])
    rows = []
    for group in ("19-44", "45-64", "65+"):
        mask = (groups == group).to_numpy()
        if not mask.any():
            continue
        rows.append(
            {
                "age_group": group,
                **_metrics_with_brier_reference(y_test[mask], probabilities[mask], threshold, null_probability),
            }
        )
    return rows


def run(
    data_path: Path,
    config_path: Path,
    output_dir: Path,
    model_dir: Path,
) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    dataset_config = config["dataset"]
    frame = load_dataset(data_path, "klosa", dataset_config)
    splits = {
        name: frame.loc[frame["split"] == name].copy().reset_index(drop=True)
        for name in ("train", "validation", "test")
    }
    _assert_disjoint_participants(splits)
    train, validation, test = (splits[name] for name in ("train", "validation", "test"))
    y_train = train["_target"].to_numpy()
    y_validation = validation["_target"].to_numpy()
    y_test = test["_target"].to_numpy()
    null_probability = float(y_train.mean())
    feature_columns = dataset_config["numeric_features"] + dataset_config["categorical_features"]
    folds = _cv_splits(train, "klosa", int(config["cv_folds"]), int(config["seed"]))

    search_rows = []
    oof_by_c = {}
    for c_value in config["c_values"]:
        candidate = _model(dataset_config, float(c_value), int(config["seed"]))
        oof = oof_probabilities(candidate, train, folds)
        oof_by_c[float(c_value)] = oof
        threshold, metrics = select_adaptive_threshold(y_train, oof, config)
        search_rows.append(
            {
                "c_value": float(c_value),
                "threshold": threshold,
                **metrics,
                **brier_reference_metrics(y_train, oof, null_probability),
            }
        )
    selected_search = max(
        search_rows,
        key=lambda row: (
            row["constraints_passed"],
            row["recall"],
            row["auprc"],
            row["specificity"],
            row["brier_skill_score"],
        ),
    )
    selected_c = float(selected_search["c_value"])
    fitted = clone(_model(dataset_config, selected_c, int(config["seed"]))).fit(train[feature_columns], y_train)
    validation_raw = fitted.predict_proba(validation[feature_columns])[:, 1]
    calibrator = _sigmoid_calibrator(oof_by_c[selected_c], y_train, int(config["seed"]))
    validation_calibrated = _apply_calibrator(calibrator, validation_raw)

    validation_rows = []
    validation_probabilities = {
        "logistic_raw": validation_raw,
        "logistic_sigmoid_calibrated": validation_calibrated,
    }
    thresholds = {}
    for name, probabilities in validation_probabilities.items():
        threshold, selection_metrics = select_adaptive_threshold(y_validation, probabilities, config)
        thresholds[name] = threshold
        validation_rows.append(
            {
                "model": name,
                "threshold_version": _threshold_version("klosa", name, threshold, config["experiment_id"]),
                **selection_metrics,
                **brier_reference_metrics(y_validation, probabilities, null_probability),
            }
        )
    final_validation = max(
        validation_rows,
        key=lambda row: (
            row["constraints_passed"],
            row["recall"],
            row["auprc"],
            row["specificity"],
            row["brier_skill_score"],
        ),
    )
    final_name = final_validation["model"]

    test_raw = fitted.predict_proba(test[feature_columns])[:, 1]
    test_calibrated = _apply_calibrator(calibrator, test_raw)
    test_probabilities = {
        "null_train_prevalence": np.full(len(test), null_probability),
        "logistic_raw": test_raw,
        "logistic_sigmoid_calibrated": test_calibrated,
    }
    test_rows = []
    for name, probabilities in test_probabilities.items():
        threshold = 0.5 if name == "null_train_prevalence" else thresholds[name]
        test_rows.append(
            {
                "model": name,
                "threshold_source": "fixed_null" if name == "null_train_prevalence" else "validation",
                **_metrics_with_brier_reference(y_test, probabilities, threshold, null_probability),
            }
        )

    curves = pd.concat(
        [
            reliability_bins(
                y_test,
                probabilities,
                int(config["reliability_bins"]),
                name,
            )
            for name, probabilities in test_probabilities.items()
        ],
        ignore_index=True,
    )
    ece = {name: expected_calibration_error(curve) for name, curve in curves.groupby("model", sort=False)}
    for row in test_rows:
        row["expected_calibration_error"] = ece[row["model"]]

    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(search_rows).to_csv(output_dir / "klosa_full_oof_search.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(validation_rows).to_csv(output_dir / "klosa_full_validation.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(test_rows).to_csv(output_dir / "klosa_full_test.csv", index=False, encoding="utf-8-sig")
    curves.to_csv(output_dir / "klosa_calibration_curve.csv", index=False, encoding="utf-8-sig")
    save_reliability_diagram(curves, output_dir / "klosa_reliability_diagram.png")
    final_probabilities = test_probabilities[final_name]
    pd.DataFrame(
        _age_group_metrics(
            test,
            y_test,
            final_probabilities,
            thresholds[final_name],
            null_probability,
        )
    ).to_csv(output_dir / "klosa_full_age_group_test.csv", index=False, encoding="utf-8-sig")

    artifact = {
        "model": fitted,
        "calibrator": calibrator,
        "selected_c": selected_c,
        "final_candidate": final_name,
        "threshold": thresholds[final_name],
        "threshold_version": final_validation["threshold_version"],
        "model_version": dataset_config["model_version"],
        "feature_schema_version": dataset_config["feature_schema_version"],
        "feature_columns": feature_columns,
        "promotion_status": "candidate_internal_not_for_personal_probability_display",
    }
    model_path = model_dir / f"{dataset_config['model_version']}.joblib"
    joblib.dump(artifact, model_path)

    manifest = {
        "experiment_id": config["experiment_id"],
        "source_file": data_path.name,
        "source_sha256": _sha256_file(data_path),
        "target_definition": SPECS["klosa"].target_definition,
        "split_summary": {
            name: {
                "n": len(split),
                "positive_n": int(split["_target"].sum()),
                "positive_rate": float(split["_target"].mean()),
            }
            for name, split in splits.items()
        },
        "null_model_definition": "constant probability equal to train positive prevalence",
        "selected_c": selected_c,
        "final_candidate_validation": final_validation,
        "final_candidate_test": next(row for row in test_rows if row["model"] == final_name),
        "model_version": dataset_config["model_version"],
        "feature_schema_version": dataset_config["feature_schema_version"],
        "local_model_path": str(model_path),
        "promotion_status": "candidate_internal_not_for_personal_probability_display",
    }
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/klosa_full_retrain.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/klosa_full_retrain"))
    parser.add_argument("--model-dir", type=Path, default=Path("models/candidate/klosa_full_retrain"))
    args = parser.parse_args()
    run(args.data, args.config, args.output_dir, args.model_dir)


if __name__ == "__main__":
    main()
