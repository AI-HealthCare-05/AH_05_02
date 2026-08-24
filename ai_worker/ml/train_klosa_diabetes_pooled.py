"""Train the pooled KLoSA diabetes-incidence Logistic Regression baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import calibration_curve
from sklearn.model_selection import train_test_split

from ai_worker.ml.build_klosa_diabetes_cohort import (
    TARGET,
    WEB_MODEL_FEATURES,
    build_cohort,
)
from ai_worker.ml.train_klosa_diabetes_sample import (
    assert_no_leakage,
    choose_threshold,
    evaluate,
    make_logistic_pipeline,
)
from ai_worker.ml.infer_klosa_diabetes import (
    CALIBRATION_VERSION,
    FEATURE_SET_VERSION,
    INPUT_SCHEMA_VERSION,
    MODEL_VERSION,
    PREPROCESSING_VERSION,
    SUPPORTED_AGE_MAXIMUM,
    SUPPORTED_AGE_MINIMUM,
    TARGET_DEFINITION_VERSION,
)


ID_COLUMN = "pid"
AGE_GROUPS = {
    "45_to_64": lambda frame: frame["age"].between(45, 64),
    "65_to_74": lambda frame: frame["age"].between(65, 74),
    "75_plus": lambda frame: frame["age"].ge(75),
    "65_plus": lambda frame: frame["age"].ge(65),
}


def logistic_experiment_identity(class_weight: str | None) -> tuple[str, str]:
    """Return distinct model and experiment versions for weighting policy."""

    if class_weight is None:
        return MODEL_VERSION, "klosa_diabetes_incidence_pooled_logistic_v1"
    if class_weight == "balanced":
        return (
            "klosa-diabetes-incidence-pooled-logistic-balanced-v1",
            "klosa_diabetes_incidence_pooled_logistic_balanced_v1",
        )
    raise ValueError("class_weight must be None or 'balanced'")


def split_grouped_cohort(
    cohort: pd.DataFrame, random_state: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split 70/15/15 by PID, stratified by whether a PID ever has an event."""

    pid_labels = (
        cohort.groupby(ID_COLUMN, as_index=False)[TARGET]
        .max()
        .rename(columns={TARGET: "pid_has_event"})
    )
    train_pids, remainder_pids = train_test_split(
        pid_labels,
        test_size=0.30,
        random_state=random_state,
        stratify=pid_labels["pid_has_event"],
    )
    validation_pids, test_pids = train_test_split(
        remainder_pids,
        test_size=0.50,
        random_state=random_state,
        stratify=remainder_pids["pid_has_event"],
    )

    def select(pid_frame: pd.DataFrame) -> pd.DataFrame:
        return cohort.loc[cohort[ID_COLUMN].isin(pid_frame[ID_COLUMN])].copy()

    train, validation, test = map(
        select,
        (train_pids, validation_pids, test_pids),
    )
    pid_sets = [set(frame[ID_COLUMN]) for frame in (train, validation, test)]
    if any(pid_sets[i] & pid_sets[j] for i, j in ((0, 1), (0, 2), (1, 2))):
        raise AssertionError("A PID appeared in more than one split.")
    if sum(len(pid_set) for pid_set in pid_sets) != cohort[ID_COLUMN].nunique():
        raise AssertionError("At least one PID was lost during splitting.")
    return train, validation, test


def describe_frame(frame: pd.DataFrame) -> dict[str, Any]:
    events = int(frame[TARGET].sum())
    return {
        "person_periods": int(len(frame)),
        "unique_people": int(frame[ID_COLUMN].nunique()),
        "events": events,
        "non_events": int(len(frame) - events),
        "event_rate": float(frame[TARGET].mean()),
    }


def describe_age_groups(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    return {
        name: describe_frame(frame.loc[selector(frame)])
        for name, selector in AGE_GROUPS.items()
    }


def evaluate_age_groups(
    frame: pd.DataFrame, probabilities, threshold: float
) -> dict[str, dict[str, Any]]:
    results = {}
    probability_series = pd.Series(probabilities, index=frame.index)
    for name, selector in AGE_GROUPS.items():
        mask = selector(frame)
        subgroup = frame.loc[mask]
        if subgroup.empty or subgroup[TARGET].nunique() < 2:
            results[name] = {
                **describe_frame(subgroup),
                "status": "not_evaluable_single_class_or_empty",
            }
            continue
        results[name] = evaluate(
            subgroup[TARGET],
            probability_series.loc[subgroup.index].to_numpy(),
            threshold,
        )
    return results


def summarize_calibration(
    y_true: pd.Series, probabilities, n_bins: int = 10
) -> dict[str, Any]:
    """Summarize a quantile-binned reliability curve and ECE on held-out data."""

    probability_array = np.asarray(probabilities, dtype=float)
    observed, predicted = calibration_curve(
        y_true,
        probability_array,
        n_bins=n_bins,
        strategy="quantile",
    )
    edges = np.percentile(
        probability_array,
        np.linspace(0, 100, n_bins + 1),
    )
    bin_ids = np.searchsorted(edges[1:-1], probability_array)
    counts = np.bincount(bin_ids, minlength=n_bins)
    non_empty_counts = counts[counts > 0]
    if len(non_empty_counts) != len(observed):
        raise AssertionError("Calibration bin counts do not match curve points.")
    absolute_gaps = np.abs(observed - predicted)
    expected_calibration_error = float(
        np.average(absolute_gaps, weights=non_empty_counts)
    )
    return {
        "dataset": "test",
        "strategy": "quantile",
        "requested_bins": n_bins,
        "actual_bins": int(len(observed)),
        "mean_predicted_probability": predicted.tolist(),
        "observed_fraction_positive": observed.tolist(),
        "bin_counts": non_empty_counts.astype(int).tolist(),
        "expected_calibration_error": expected_calibration_error,
        "selection_policy": "reporting_only_not_used_for_model_or_threshold_selection",
    }


def run_training(
    data_dir: Path,
    output_dir: Path,
    model_dir: Path | None = None,
    random_state: int = 42,
    minimum_validation_recall: float = 0.80,
    class_weight: str | None = None,
) -> dict[str, Any]:
    assert_no_leakage(WEB_MODEL_FEATURES)
    model_version, experiment_name = logistic_experiment_identity(class_weight)
    cohort = build_cohort(data_dir)
    train, validation, test = split_grouped_cohort(cohort, random_state)

    model = make_logistic_pipeline(class_weight=class_weight)
    model.fit(train[WEB_MODEL_FEATURES], train[TARGET])

    validation_probabilities = model.predict_proba(
        validation[WEB_MODEL_FEATURES]
    )[:, 1]
    threshold = choose_threshold(
        validation[TARGET],
        validation_probabilities,
        minimum_recall=minimum_validation_recall,
    )
    test_probabilities = model.predict_proba(test[WEB_MODEL_FEATURES])[:, 1]

    model_metadata = {
        "model_version": model_version,
        "target_definition_version": TARGET_DEFINITION_VERSION,
        "input_schema_version": INPUT_SCHEMA_VERSION,
        "feature_set_version": FEATURE_SET_VERSION,
        "preprocessing_version": PREPROCESSING_VERSION,
        "calibration_version": CALIBRATION_VERSION,
        "data_version": "klosa-structured-waves-1-10-20260413",
        "split_version": f"pid-group-70-15-15-random-state-{random_state}",
        "features": WEB_MODEL_FEATURES,
        "supported_age_range": [SUPPORTED_AGE_MINIMUM, SUPPORTED_AGE_MAXIMUM],
        "operational_threshold_status": "pending_mentoring",
    }

    metrics = {
        "experiment": experiment_name,
        "status": "research_baseline_not_for_deployment",
        "data_source": "KLoSA structured waves 1-10",
        "target": TARGET,
        "features": WEB_MODEL_FEATURES,
        "model": {
            "type": "LogisticRegression",
            "class_weight": class_weight,
            "class_weight_source": (
                "train_inverse_class_frequency"
                if class_weight == "balanced"
                else "not_applied"
            ),
            "preprocessing_fit": "train_only",
            "probability_calibration": "none",
        },
        "version_metadata": model_metadata,
        "cohort": describe_frame(cohort),
        "cohort_by_age": describe_age_groups(cohort),
        "splits": {
            "method": "PID group 70/15/15; stratify PID by any event",
            "train": describe_frame(train),
            "validation": describe_frame(validation),
            "test": describe_frame(test),
            "pid_overlap": 0,
        },
        "threshold_selection": {
            "source": "validation_only",
            "minimum_recall": minimum_validation_recall,
            "selected_threshold": threshold,
            "status": "evaluation_only_not_operational",
        },
        "validation": evaluate(
            validation[TARGET], validation_probabilities, threshold
        ),
        "test": evaluate(test[TARGET], test_probabilities, threshold),
        "test_by_age": evaluate_age_groups(test, test_probabilities, threshold),
        "test_calibration": summarize_calibration(
            test[TARGET], test_probabilities, n_bins=10
        ),
        "random_state": random_state,
        "versions": {
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "limitations": [
            "Self-reported newly diagnosed diabetes or hyperglycemia, not biological onset.",
            "Repeated person-periods require PID-grouped splitting.",
            "Risk-band thresholds and probability calibration are not operationally validated.",
        ],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    if model_dir is not None:
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "model.joblib"
        joblib.dump(
            {"pipeline": model, "metadata": model_metadata},
            model_path,
        )
        metrics["artifact"] = {
            "path": str(model_path),
            "sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
            "git_policy": "local_only_do_not_commit",
        }
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/raw/klosa/20260413/extracted"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=None,
    )
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--minimum-validation-recall", type=float, default=0.80)
    parser.add_argument(
        "--class-weight",
        choices=["none", "balanced"],
        default="none",
        help="Use sklearn inverse-frequency weighting fitted from train only.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    class_weight = None if args.class_weight == "none" else args.class_weight
    weighted = class_weight == "balanced"
    output_dir = args.output_dir or Path(
        "experiments/klosa_diabetes_logistic_balanced_pooled"
        if weighted
        else "experiments/klosa_diabetes_logistic_pooled"
    )
    model_dir = args.model_dir or Path(
        "models/baselines/klosa_diabetes_incidence_logistic_balanced"
        if weighted
        else "models/baselines/klosa_diabetes_incidence_pooled"
    )
    metrics = run_training(
        args.data_dir,
        output_dir,
        model_dir,
        args.random_state,
        args.minimum_validation_recall,
        class_weight,
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
