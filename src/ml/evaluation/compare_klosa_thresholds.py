"""Compare KLoSA model operating points selected on validation only."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

_matplotlib_config_dir = Path(tempfile.gettempdir()) / "chronic-disease-matplotlib"
_matplotlib_config_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_matplotlib_config_dir))

import joblib  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import roc_curve  # noqa: E402

from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort  # noqa: E402
from src.ml.modeling.train_klosa_diabetes_sample import evaluate  # noqa: E402
from src.ml.preprocessing.build_klosa_diabetes_cohort import (  # noqa: E402
    TARGET,
    WEB_MODEL_FEATURES,
    build_cohort,
)

MODEL_SPECS = [
    {
        "model": "Logistic Regression",
        "weighting": "none",
        "path": Path("models/artifacts/baselines/klosa_diabetes_incidence_pooled/model.joblib"),
        "primary": True,
    },
    {
        "model": "Random Forest",
        "weighting": "none",
        "path": Path("models/artifacts/baselines/klosa_diabetes_incidence_random_forest_unweighted/model.joblib"),
        "primary": True,
    },
    {
        "model": "XGBoost",
        "weighting": "none",
        "path": Path("models/artifacts/baselines/klosa_diabetes_incidence_xgboost_unweighted/model.joblib"),
        "primary": True,
    },
    {
        "model": "Logistic Regression",
        "weighting": "balanced",
        "path": Path("models/artifacts/baselines/klosa_diabetes_incidence_logistic_balanced/model.joblib"),
        "primary": False,
    },
    {
        "model": "Random Forest",
        "weighting": "balanced_subsample",
        "path": Path("models/artifacts/baselines/klosa_diabetes_incidence_random_forest/model.joblib"),
        "primary": False,
    },
    {
        "model": "XGBoost",
        "weighting": "scale_pos_weight",
        "path": Path("models/artifacts/baselines/klosa_diabetes_incidence_xgboost/model.joblib"),
        "primary": False,
    },
]
TARGET_RECALLS = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]


def choose_threshold_for_recall(
    target: pd.Series,
    probabilities,
    minimum_recall: float,
) -> float:
    """Efficiently maximize specificity subject to validation recall."""

    false_positive_rate, recall, thresholds = roc_curve(
        target,
        probabilities,
        drop_intermediate=False,
    )
    eligible = np.flatnonzero(recall >= minimum_recall)
    if not len(eligible):
        raise ValueError(f"No threshold reaches recall {minimum_recall}")
    specificity = 1 - false_positive_rate
    best_specificity = specificity[eligible].max()
    tied = eligible[np.isclose(specificity[eligible], best_specificity)]
    best_index = tied[np.argmin(thresholds[tied])]
    return float(thresholds[best_index])


def evaluate_operating_points(
    validation_target: pd.Series,
    validation_probabilities,
    test_target: pd.Series,
    test_probabilities,
    target_recalls: list[float],
) -> list[dict[str, Any]]:
    """Select thresholds on validation and evaluate them unchanged on test."""

    rows = []
    for target_recall in target_recalls:
        threshold = choose_threshold_for_recall(
            validation_target,
            validation_probabilities,
            minimum_recall=target_recall,
        )
        validation_metrics = evaluate(
            validation_target,
            validation_probabilities,
            threshold,
        )
        test_metrics = evaluate(test_target, test_probabilities, threshold)
        rows.append(
            {
                "target_validation_recall": target_recall,
                "threshold": threshold,
                "validation_recall": validation_metrics["recall"],
                "validation_specificity": validation_metrics["specificity"],
                "test_recall": test_metrics["recall"],
                "test_specificity": test_metrics["specificity"],
                "test_false_positive_rate": 1 - test_metrics["specificity"],
                "test_true_positives": test_metrics["confusion_matrix"]["tp"],
                "test_false_negatives": test_metrics["confusion_matrix"]["fn"],
                "test_true_negatives": test_metrics["confusion_matrix"]["tn"],
                "test_false_positives": test_metrics["confusion_matrix"]["fp"],
                "test_f1": test_metrics["f1"],
            }
        )
    return rows


def run_comparison(
    data_dir: Path,
    output_dir: Path,
    random_state: int = 42,
) -> dict[str, Any]:
    """Run the fixed threshold comparison for every available model bundle."""

    cohort = build_cohort(data_dir)
    _, validation, test = split_grouped_cohort(cohort, random_state=random_state)
    rows = []
    versions = {}
    for spec in MODEL_SPECS:
        if not spec["path"].exists():
            raise FileNotFoundError(f"Missing model bundle: {spec['path']}")
        bundle = joblib.load(spec["path"])
        if bundle["metadata"].get("features") != WEB_MODEL_FEATURES:
            raise ValueError(f"Feature contract mismatch: {spec['path']}")
        pipeline = bundle["pipeline"]
        validation_probabilities = pipeline.predict_proba(validation[WEB_MODEL_FEATURES])[:, 1]
        test_probabilities = pipeline.predict_proba(test[WEB_MODEL_FEATURES])[:, 1]
        model_key = f"{spec['model']}__{spec['weighting']}"
        versions[model_key] = bundle["metadata"]["model_version"]
        for row in evaluate_operating_points(
            validation[TARGET],
            validation_probabilities,
            test[TARGET],
            test_probabilities,
            TARGET_RECALLS,
        ):
            rows.append(
                {
                    "model": spec["model"],
                    "weighting": spec["weighting"],
                    "primary_comparison": spec["primary"],
                    "model_version": bundle["metadata"]["model_version"],
                    **row,
                }
            )

    frame = pd.DataFrame(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_dir / "operating_points.csv", index=False)
    result = {
        "selection_dataset": "validation",
        "evaluation_dataset": "test",
        "threshold_status": "evaluation_only_not_operational",
        "target_validation_recalls": TARGET_RECALLS,
        "test_n": int(len(test)),
        "test_events": int(test[TARGET].sum()),
        "test_non_events": int(len(test) - test[TARGET].sum()),
        "model_versions": versions,
        "operating_points": rows,
    }
    (output_dir / "operating_points.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    plot_primary_tradeoff(frame, output_dir / "recall_specificity_tradeoff.png")
    return result


def plot_primary_tradeoff(frame: pd.DataFrame, output_path: Path) -> None:
    """Plot test recall and specificity for the three unweighted models."""

    primary = frame.loc[frame["primary_comparison"]].copy()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    for (model, weighting), group in primary.groupby(["model", "weighting"]):
        label = f"{model} ({weighting})"
        axes[0].plot(
            group["target_validation_recall"],
            group["test_recall"],
            marker="o",
            label=label,
        )
        axes[1].plot(
            group["target_validation_recall"],
            group["test_specificity"],
            marker="o",
            label=label,
        )
    axes[0].set_title("Test recall")
    axes[0].set_ylabel("Recall")
    axes[1].set_title("Test specificity")
    axes[1].set_ylabel("Specificity")
    for axis in axes:
        axis.set_xlabel("Target recall selected on validation")
        axis.set_ylim(0, 1)
        axis.grid(alpha=0.25)
        axis.legend(frameon=False)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/interim/source_extract/klosa/20260413"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/diabetes_incidence/candidates/klosa_diabetes_threshold_comparison"),
    )
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_comparison(args.data_dir, args.output_dir, args.random_state)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
