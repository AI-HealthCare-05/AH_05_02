"""Full KNHANES baseline, ensemble and post-processing comparison."""

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
from sklearn.base import BaseEstimator, clone
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

from src.ml.modeling.klosa_full_retrain import (
    brier_reference_metrics,
    expected_calibration_error,
    reliability_bins,
    select_adaptive_threshold,
)
from src.ml.modeling.recall_ensemble import (
    SPECS,
    _apply_calibrator,
    _best_blend,
    _sha256_file,
    _sigmoid_calibrator,
    _threshold_version,
    _weighted_average,
    choose_family_models,
    load_dataset,
    metric_row,
)


def cross_fitted_stacker(
    base_oof: dict[str, np.ndarray],
    names: list[str],
    y: np.ndarray,
    folds: int,
    seed: int,
) -> tuple[np.ndarray, LogisticRegression]:
    matrix = np.column_stack([base_oof[name] for name in names])
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    oof = np.zeros(len(y), dtype=float)
    for train_index, holdout_index in splitter.split(matrix, y):
        model = LogisticRegression(class_weight="balanced", max_iter=3000, random_state=seed)
        model.fit(matrix[train_index], y[train_index])
        oof[holdout_index] = model.predict_proba(matrix[holdout_index])[:, 1]
    final = LogisticRegression(class_weight="balanced", max_iter=3000, random_state=seed)
    final.fit(matrix, y)
    return oof, final


def ensemble_predictions(
    base_oof: dict[str, np.ndarray],
    base_validation: dict[str, np.ndarray],
    base_test: dict[str, np.ndarray],
    y_train: np.ndarray,
    config: dict[str, Any],
) -> tuple[
    dict[str, np.ndarray],
    dict[str, np.ndarray],
    dict[str, np.ndarray],
    dict[str, Any],
]:
    names = list(base_oof)
    tree_names = [name for name in names if name in {"random_forest", "xgboost", "lightgbm"}]
    blend_weights, blend_oof = _best_blend(base_oof, names, y_train, config)
    tree_blend_weights, tree_blend_oof = _best_blend(base_oof, tree_names, y_train, config)
    stacking_oof, stacker = cross_fitted_stacker(
        base_oof, names, y_train, int(config["stacking_cv_folds"]), int(config["seed"])
    )
    tree_stacking_oof, tree_stacker = cross_fitted_stacker(
        base_oof, tree_names, y_train, int(config["stacking_cv_folds"]), int(config["seed"])
    )

    def build(base: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        matrix = np.column_stack([base[name] for name in names])
        tree_matrix = np.column_stack([base[name] for name in tree_names])
        return {
            "soft_voting_equal": matrix.mean(axis=1),
            "oof_blending": _weighted_average(base, blend_weights),
            "stacking": stacker.predict_proba(matrix)[:, 1],
            "tree_soft_voting_equal": tree_matrix.mean(axis=1),
            "tree_oof_blending": _weighted_average(base, tree_blend_weights),
            "tree_stacking": tree_stacker.predict_proba(tree_matrix)[:, 1],
        }

    oof = {
        "soft_voting_equal": np.column_stack([base_oof[name] for name in names]).mean(axis=1),
        "oof_blending": blend_oof,
        "stacking": stacking_oof,
        "tree_soft_voting_equal": np.column_stack([base_oof[name] for name in tree_names]).mean(axis=1),
        "tree_oof_blending": tree_blend_oof,
        "tree_stacking": tree_stacking_oof,
    }
    metadata = {
        "base_model_order": names,
        "tree_base_model_order": tree_names,
        "blend_weights": blend_weights,
        "tree_blend_weights": tree_blend_weights,
        "stacker": stacker,
        "tree_stacker": tree_stacker,
    }
    return oof, build(base_validation), build(base_test), metadata


def _apply_isotonic(calibrator: IsotonicRegression, probabilities: np.ndarray) -> np.ndarray:
    return np.asarray(calibrator.predict(probabilities), dtype=float)


def fit_postprocessors(oof: dict[str, np.ndarray], y_train: np.ndarray, seed: int) -> dict[str, dict[str, Any]]:
    processors = {}
    for name, probabilities in oof.items():
        sigmoid = _sigmoid_calibrator(probabilities, y_train, seed)
        isotonic = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        isotonic.fit(probabilities, y_train)
        processors[name] = {"sigmoid": sigmoid, "isotonic": isotonic}
    return processors


def transformed_probabilities(
    raw: dict[str, np.ndarray], processors: dict[str, dict[str, Any]]
) -> dict[str, dict[str, np.ndarray]]:
    result = {}
    for name, probabilities in raw.items():
        result[name] = {
            "raw": probabilities,
            "sigmoid": _apply_calibrator(processors[name]["sigmoid"], probabilities),
            "isotonic": _apply_isotonic(processors[name]["isotonic"], probabilities),
        }
    return result


def _with_calibration_metrics(
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


def validation_comparison(
    y_validation: np.ndarray,
    probabilities: dict[str, dict[str, np.ndarray]],
    null_probability: float,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    rows = []
    thresholds = {}
    for model_name, variants in probabilities.items():
        model_group = (
            "baseline" if model_name in {"logistic_regression", "random_forest", "xgboost", "lightgbm"} else "ensemble"
        )
        fixed_name = f"{model_name}__raw_fixed_0_5"
        rows.append(
            {
                "model": model_name,
                "model_group": model_group,
                "postprocessing": "raw_fixed_0.5",
                "candidate": fixed_name,
                "selection_eligible": False,
                **_with_calibration_metrics(
                    y_validation,
                    variants["raw"],
                    0.5,
                    null_probability,
                    int(config["reliability_bins"]),
                    fixed_name,
                ),
            }
        )
        for postprocessing in ("raw", "sigmoid", "isotonic"):
            candidate = f"{model_name}__{postprocessing}_threshold_tuned"
            threshold, selection_metrics = select_adaptive_threshold(y_validation, variants[postprocessing], config)
            thresholds[candidate] = threshold
            rows.append(
                {
                    "model": model_name,
                    "model_group": model_group,
                    "postprocessing": f"{postprocessing}_threshold_tuned",
                    "candidate": candidate,
                    "selection_eligible": True,
                    "threshold_version": _threshold_version("knhanes", candidate, threshold, config["experiment_id"]),
                    **selection_metrics,
                    **brier_reference_metrics(y_validation, variants[postprocessing], null_probability),
                    "expected_calibration_error": expected_calibration_error(
                        reliability_bins(
                            y_validation,
                            variants[postprocessing],
                            int(config["reliability_bins"]),
                            candidate,
                        )
                    ),
                }
            )
    return rows, thresholds


def select_validation_candidate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in rows if row["selection_eligible"] and row["constraints_passed"]]
    return max(
        eligible,
        key=lambda row: (
            row["recall"],
            row["auprc"],
            row["specificity"],
            row["brier_skill_score"],
        ),
    )


def per_model_summary(validation_rows: list[dict[str, Any]], test_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    test_by_candidate = {row["candidate"]: row for row in test_rows}
    models = sorted({row["model"] for row in validation_rows})
    summary = []
    for model in models:
        candidates = [row for row in validation_rows if row["model"] == model and bool(row["selection_eligible"])]
        feasible = [row for row in candidates if bool(row["constraints_passed"])]
        selected = max(
            feasible or candidates,
            key=lambda row: (
                float(row["recall"]),
                float(row["auprc"]),
                float(row["specificity"]),
                float(row["brier_skill_score"]),
            ),
        )
        test = test_by_candidate[selected["candidate"]]
        summary.append(
            {
                "model_group": selected["model_group"],
                "model": model,
                "validation_selected_postprocessing": selected["postprocessing"],
                "validation_recall": selected["recall"],
                "validation_specificity": selected["specificity"],
                "test_auroc": test["auroc"],
                "test_auprc": test["auprc"],
                "test_recall": test["recall"],
                "test_specificity": test["specificity"],
                "test_brier": test["brier"],
                "test_brier_skill_score": test["brier_skill_score"],
                "test_expected_calibration_error": test["expected_calibration_error"],
                "test_constraints_passed": test["constraints_passed"],
            }
        )
    return summary


def test_comparison(
    y_test: np.ndarray,
    probabilities: dict[str, dict[str, np.ndarray]],
    validation_rows: list[dict[str, Any]],
    thresholds: dict[str, float],
    null_probability: float,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = [
        {
            "model": "null_train_prevalence",
            "model_group": "null",
            "postprocessing": "constant_train_prevalence",
            "candidate": "null_train_prevalence",
            "threshold_source": "fixed_null",
            **_with_calibration_metrics(
                y_test,
                np.full(len(y_test), null_probability),
                0.5,
                null_probability,
                int(config["reliability_bins"]),
                "null_train_prevalence",
            ),
        }
    ]
    for validation_row in validation_rows:
        model_name = validation_row["model"]
        postprocessing = validation_row["postprocessing"]
        if postprocessing == "raw_fixed_0.5":
            probability_key = "raw"
            threshold = 0.5
            threshold_source = "fixed_0.5"
        else:
            probability_key = postprocessing.removesuffix("_threshold_tuned")
            threshold = thresholds[validation_row["candidate"]]
            threshold_source = "validation"
        metrics = _with_calibration_metrics(
            y_test,
            probabilities[model_name][probability_key],
            threshold,
            null_probability,
            int(config["reliability_bins"]),
            validation_row["candidate"],
        )
        constraints = config["selection_constraints"]
        metrics["constraints_passed"] = bool(
            metrics["specificity"] >= float(constraints["minimum_specificity"])
            and metrics["auprc_lift"] >= float(constraints["minimum_auprc_lift"])
        )
        rows.append(
            {
                "model": model_name,
                "model_group": validation_row["model_group"],
                "postprocessing": postprocessing,
                "candidate": validation_row["candidate"],
                "threshold_source": threshold_source,
                **metrics,
            }
        )
    return rows


def save_reliability_diagram(curves: pd.DataFrame, path: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(14, 6))
    for axis, limit, title in (
        (axes[0], 1.0, "Full probability range"),
        (axes[1], 0.15, "Low-risk range (0–0.15)"),
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
    axes[0].legend(fontsize=8)
    figure.suptitle("KNHANES Reliability Diagram (Test)")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _final_age_groups(
    test: pd.DataFrame,
    y_test: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    null_probability: float,
) -> list[dict[str, Any]]:
    age_groups = pd.cut(test["age"], bins=[18, 44, 64, np.inf], labels=["19-44", "45-64", "65+"])
    rows = []
    for age_group in ("19-44", "45-64", "65+"):
        mask = (age_groups == age_group).to_numpy()
        rows.append(
            {
                "age_group": age_group,
                **_with_calibration_metrics(
                    y_test[mask], probabilities[mask], threshold, null_probability, 10, age_group
                ),
            }
        )
    return rows


def run(data_path: Path, config_path: Path, output_dir: Path, model_dir: Path) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    dataset_config = config["dataset"]
    frame = load_dataset(data_path, "knhanes", dataset_config)
    splits = {
        name: frame.loc[frame["split"] == name].copy().reset_index(drop=True)
        for name in ("train", "validation", "test")
    }
    train, validation, test = (splits[name] for name in ("train", "validation", "test"))
    y_train = train["_target"].to_numpy()
    y_validation = validation["_target"].to_numpy()
    y_test = test["_target"].to_numpy()
    null_probability = float(y_train.mean())
    feature_columns = dataset_config["numeric_features"] + dataset_config["categorical_features"]

    selected_models, base_oof, search_rows = choose_family_models("knhanes", train, dataset_config, config)
    fitted_models: dict[str, BaseEstimator] = {}
    base_validation = {}
    base_test = {}
    for name, model in selected_models.items():
        fitted = clone(model).fit(train[feature_columns], y_train)
        fitted_models[name] = fitted
        base_validation[name] = fitted.predict_proba(validation[feature_columns])[:, 1]
        base_test[name] = fitted.predict_proba(test[feature_columns])[:, 1]

    ensemble_oof, ensemble_validation, ensemble_test, ensemble_metadata = ensemble_predictions(
        base_oof, base_validation, base_test, y_train, config
    )
    all_oof = {**base_oof, **ensemble_oof}
    all_validation = {**base_validation, **ensemble_validation}
    all_test = {**base_test, **ensemble_test}
    processors = fit_postprocessors(all_oof, y_train, int(config["seed"]))
    validation_variants = transformed_probabilities(all_validation, processors)
    test_variants = transformed_probabilities(all_test, processors)
    validation_rows, thresholds = validation_comparison(y_validation, validation_variants, null_probability, config)
    final_validation = select_validation_candidate(validation_rows)
    test_rows = test_comparison(
        y_test,
        test_variants,
        validation_rows,
        thresholds,
        null_probability,
        config,
    )
    final_test = next(row for row in test_rows if row["candidate"] == final_validation["candidate"])

    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(search_rows).to_csv(output_dir / "knhanes_full_oof_search.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(validation_rows).to_csv(
        output_dir / "knhanes_full_validation_comparison.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(test_rows).to_csv(output_dir / "knhanes_full_test_comparison.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(per_model_summary(validation_rows, test_rows)).to_csv(
        output_dir / "knhanes_model_summary.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame([row for row in test_rows if row["model"] == "stacking"]).to_csv(
        output_dir / "knhanes_stacking_postprocess_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    final_model = final_validation["model"]
    reliability_variant_names = ["raw", "sigmoid", "isotonic"]
    curves = [
        reliability_bins(
            y_test,
            np.full(len(y_test), null_probability),
            int(config["reliability_bins"]),
            "null_train_prevalence",
        )
    ]
    curves.extend(
        reliability_bins(
            y_test,
            test_variants[final_model][variant],
            int(config["reliability_bins"]),
            f"{final_model}_{variant}",
        )
        for variant in reliability_variant_names
    )
    calibration_curves = pd.concat(curves, ignore_index=True)
    calibration_curves.to_csv(output_dir / "knhanes_calibration_curve.csv", index=False, encoding="utf-8-sig")
    save_reliability_diagram(calibration_curves, output_dir / "knhanes_reliability_diagram.png")

    final_postprocessing = final_validation["postprocessing"].removesuffix("_threshold_tuned")
    final_probabilities = test_variants[final_model][final_postprocessing]
    pd.DataFrame(
        _final_age_groups(
            test,
            y_test,
            final_probabilities,
            thresholds[final_validation["candidate"]],
            null_probability,
        )
    ).to_csv(output_dir / "knhanes_final_age_group_test.csv", index=False, encoding="utf-8-sig")

    artifact = {
        "base_models": fitted_models,
        "ensemble": ensemble_metadata,
        "postprocessors": processors,
        "final_candidate": final_validation["candidate"],
        "final_model": final_model,
        "final_postprocessing": final_postprocessing,
        "threshold": thresholds[final_validation["candidate"]],
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
        "target_definition": SPECS["knhanes"].target_definition,
        "split_summary": {
            name: {
                "n": len(split),
                "positive_n": int(split["_target"].sum()),
                "positive_rate": float(split["_target"].mean()),
            }
            for name, split in splits.items()
        },
        "null_model_definition": "constant probability equal to train positive prevalence",
        "comparison_scope": {
            "baseline_models": list(base_oof),
            "ensemble_models": list(ensemble_oof),
            "postprocessing": [
                "raw_fixed_0.5",
                "raw_threshold_tuned",
                "sigmoid_threshold_tuned",
                "isotonic_threshold_tuned",
            ],
        },
        "final_candidate_validation": final_validation,
        "final_candidate_test": final_test,
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
    parser.add_argument("--config", type=Path, default=Path("configs/knhanes_full_comparison.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/knhanes_full_comparison"))
    parser.add_argument("--model-dir", type=Path, default=Path("models/candidate/knhanes_full_comparison"))
    args = parser.parse_args()
    run(args.data, args.config, args.output_dir, args.model_dir)


if __name__ == "__main__":
    main()
