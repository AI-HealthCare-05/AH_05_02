"""Compare KLoSA core and t0-comorbidity features under specificity constraints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyreadstat
from sklearn.base import BaseEstimator, clone

from src.ml.modeling.klosa_feature_expansion import (
    CORE_CATEGORICAL,
    CORE_NUMERIC,
    _assert_participant_split,
    build_incident_frame,
)
from src.ml.modeling.klosa_full_retrain import brier_reference_metrics
from src.ml.modeling.recall_ensemble import (
    _apply_calibrator,
    _cv_splits,
    _sha256_file,
    _sigmoid_calibrator,
    build_candidates,
    metric_row,
    oof_probabilities,
)

DISEASE_CODES = {
    "baseline_hypertension_history": "C006",
    "baseline_cancer_history": "C016",
    "baseline_chronic_lung_history": "C023",
    "baseline_liver_history": "C028",
    "baseline_heart_history": "C033",
    "baseline_cerebrovascular_history": "C038",
    "baseline_psychiatric_history": "C043",
    "baseline_arthritis_history": "C048",
}
COMORBIDITY_FEATURES = list(DISEASE_CODES)


def _normalize_id(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").round().astype("Int64").astype("string")


def extract_comorbidity_history(raw_dir: Path) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Create confirmed-diagnosis history through each wave without future leakage."""
    pieces: list[pd.DataFrame] = []
    sources: list[dict[str, Any]] = []
    for wave in range(1, 11):
        path = raw_dir / f"w{wave:02d}_20260413.sav"
        if not path.exists():
            raise FileNotFoundError(path)
        rename = {f"w{wave:02d}{code}": name for name, code in DISEASE_CODES.items()}
        usecols = ["pid", *rename]
        frame, _ = pyreadstat.read_sav(path, usecols=usecols)
        frame = frame.rename(columns={"pid": "participant_id", **rename})
        frame["participant_id"] = _normalize_id(frame["participant_id"])
        frame["survey_wave"] = wave
        pieces.append(frame)
        sources.append({"wave": wave, "file": path.name, "sha256": _sha256_file(path), "rows": len(frame)})

    events = pd.concat(pieces, ignore_index=True).sort_values(["participant_id", "survey_wave"])
    for feature in COMORBIDITY_FEATURES:
        raw = pd.to_numeric(events[feature], errors="coerce")
        # Confirmed diagnosis is code 1. Code 5 is observed negative. Refusal,
        # unknown and cerebrovascular code 3 are not promoted to a diagnosis.
        observed = raw.isin([1, 5])
        ever_yes = raw.eq(1).groupby(events["participant_id"], sort=False).cummax()
        ever_observed = observed.groupby(events["participant_id"], sort=False).cummax()
        events[feature] = np.where(ever_yes, 1.0, np.where(ever_observed, 0.0, np.nan))
    if events.duplicated(["participant_id", "survey_wave"]).any():
        raise ValueError("Duplicate participant-wave rows in raw KLoSA extraction")
    return events[["participant_id", "survey_wave", *COMORBIDITY_FEATURES]], sources


def build_model_frame(panel_path: Path, raw_dir: Path) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    incident = build_incident_frame(panel_path)
    incident["participant_id"] = _normalize_id(incident["participant_id"])
    # Rebuild hypertension with the same raw-code history rule used for the
    # other seven conditions, avoiding duplicate merge suffixes.
    incident = incident.drop(columns=["baseline_hypertension_history"])
    history, sources = extract_comorbidity_history(raw_dir)
    merged = incident.merge(history, on=["participant_id", "survey_wave"], how="left", validate="many_to_one")
    if len(merged) != len(incident):
        raise ValueError("Comorbidity merge changed eligible incident row count")
    _assert_participant_split(merged)
    return merged, sources


def feature_sets() -> dict[str, dict[str, list[str]]]:
    return {
        "core_8": {"numeric_features": CORE_NUMERIC, "categorical_features": CORE_CATEGORICAL},
        "core_8_plus_t0_comorbidity_8": {
            "numeric_features": CORE_NUMERIC,
            "categorical_features": CORE_CATEGORICAL + COMORBIDITY_FEATURES,
        },
    }


def _models(spec: dict[str, list[str]], y: np.ndarray, seed: int) -> dict[str, BaseEstimator]:
    candidates = build_candidates(spec, y, seed)
    return {
        "logistic_regression": candidates["logistic_regression"][1],
        "random_forest": candidates["random_forest"][2],
        "xgboost": candidates["xgboost"][0],
    }


def _threshold_at_specificity(
    y: np.ndarray, prob: np.ndarray, target: float, grid: dict[str, Any]
) -> tuple[float, dict[str, Any]]:
    thresholds = np.linspace(float(grid["minimum"]), float(grid["maximum"]), int(grid["points"]))
    rows = [metric_row(y, prob, float(threshold)) for threshold in thresholds]
    feasible = [row for row in rows if row["specificity"] >= target]
    pool = feasible or rows
    best = max(pool, key=lambda row: (row["recall"], row["specificity"], row["threshold"]))
    return float(best["threshold"]), best


def _cluster_bootstrap(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    threshold: float,
    repetitions: int,
    seed: int,
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    groups = frame.groupby("participant_id", sort=False).indices
    ids = np.asarray(list(groups), dtype=object)
    y = frame["_target"].to_numpy()
    samples: dict[str, list[float]] = {"recall": [], "specificity": [], "auprc": []}
    for _ in range(repetitions):
        drawn = rng.choice(ids, size=len(ids), replace=True)
        indices = np.concatenate([groups[item] for item in drawn])
        metrics = metric_row(y[indices], probabilities[indices], threshold)
        for name in samples:
            samples[name].append(float(metrics[name]))
    rows = []
    for name, values in samples.items():
        rows.append(
            {
                "metric": name,
                "lower_95_two_sided": float(np.quantile(values, 0.025)),
                "upper_95_two_sided": float(np.quantile(values, 0.975)),
                "lower_95_one_sided": float(np.quantile(values, 0.05)),
                "bootstrap_repetitions": repetitions,
                "bootstrap_unit": "participant_id",
            }
        )
    return rows


def run(panel_path: Path, raw_dir: Path, config_path: Path, output_dir: Path) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    frame, sources = build_model_frame(panel_path, raw_dir)
    splits = {
        name: frame.loc[frame["split"] == name].reset_index(drop=True) for name in ("train", "validation", "test")
    }
    train, validation, test = (splits[name] for name in ("train", "validation", "test"))
    y_train, y_validation, y_test = (part["_target"].to_numpy() for part in (train, validation, test))
    folds = _cv_splits(train, "klosa", int(config["cv_folds"]), int(config["seed"]))
    null_probability = float(y_train.mean())
    validation_rows: list[dict[str, Any]] = []
    test_rows: list[dict[str, Any]] = []
    prediction_cache: dict[tuple[str, str], np.ndarray] = {}

    for feature_name, spec in feature_sets().items():
        columns = spec["numeric_features"] + spec["categorical_features"]
        validation_members: list[np.ndarray] = []
        test_members: list[np.ndarray] = []
        for model_name, model in _models(spec, y_train, int(config["seed"])).items():
            oof = oof_probabilities(model, train, folds)
            calibrator = _sigmoid_calibrator(oof, y_train, int(config["seed"]))
            fitted = clone(model).fit(train[columns], y_train)
            validation_probability = _apply_calibrator(calibrator, fitted.predict_proba(validation[columns])[:, 1])
            test_probability = _apply_calibrator(calibrator, fitted.predict_proba(test[columns])[:, 1])
            validation_members.append(validation_probability)
            test_members.append(test_probability)
            prediction_cache[(feature_name, model_name)] = test_probability
            for target in config["specificity_targets"]:
                threshold, validation_metrics = _threshold_at_specificity(
                    y_validation, validation_probability, float(target), config["threshold_grid"]
                )
                test_metrics = metric_row(y_test, test_probability, threshold)
                common = {
                    "feature_set": feature_name,
                    "feature_count": len(columns),
                    "model": model_name,
                    "minimum_specificity_policy": float(target),
                    "threshold": threshold,
                }
                validation_rows.append({**common, **validation_metrics})
                test_rows.append(
                    {
                        **common,
                        **test_metrics,
                        **brier_reference_metrics(y_test, test_probability, null_probability),
                        "false_alerts_per_1000_negatives": 1000 * (1 - float(test_metrics["specificity"])),
                        "test_constraint_passed": bool(test_metrics["specificity"] >= float(target)),
                    }
                )
        validation_probability = np.mean(validation_members, axis=0)
        test_probability = np.mean(test_members, axis=0)
        model_name = "equal_soft_voting"
        prediction_cache[(feature_name, model_name)] = test_probability
        for target in config["specificity_targets"]:
            threshold, validation_metrics = _threshold_at_specificity(
                y_validation, validation_probability, float(target), config["threshold_grid"]
            )
            test_metrics = metric_row(y_test, test_probability, threshold)
            common = {
                "feature_set": feature_name,
                "feature_count": len(columns),
                "model": model_name,
                "minimum_specificity_policy": float(target),
                "threshold": threshold,
            }
            validation_rows.append({**common, **validation_metrics})
            test_rows.append(
                {
                    **common,
                    **test_metrics,
                    **brier_reference_metrics(y_test, test_probability, null_probability),
                    "false_alerts_per_1000_negatives": 1000 * (1 - float(test_metrics["specificity"])),
                    "test_constraint_passed": bool(test_metrics["specificity"] >= float(target)),
                }
            )

    primary = float(config["primary_minimum_specificity"])
    validation_primary = [row for row in validation_rows if row["minimum_specificity_policy"] == primary]
    selected = max(validation_primary, key=lambda row: (row["recall"], row["auprc"], row["specificity"]))
    selected_test = next(
        row
        for row in test_rows
        if row["feature_set"] == selected["feature_set"]
        and row["model"] == selected["model"]
        and row["minimum_specificity_policy"] == primary
    )
    ci_rows: list[dict[str, Any]] = []
    for target in config["specificity_targets"]:
        policy = next(
            row
            for row in validation_rows
            if row["feature_set"] == selected["feature_set"]
            and row["model"] == selected["model"]
            and row["minimum_specificity_policy"] == float(target)
        )
        policy_ci = _cluster_bootstrap(
            test,
            prediction_cache[(selected["feature_set"], selected["model"])],
            float(policy["threshold"]),
            int(config["bootstrap_repetitions"]),
            int(config["seed"]) + round(float(target) * 100),
        )
        ci_rows.extend({"minimum_specificity_policy": float(target), **row} for row in policy_ci)
    specificity_ci = next(
        row for row in ci_rows if row["metric"] == "specificity" and row["minimum_specificity_policy"] == primary
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(validation_rows).to_csv(
        output_dir / "validation_threshold_comparison.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(test_rows).to_csv(output_dir / "test_threshold_comparison.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(ci_rows).to_csv(
        output_dir / "selected_test_cluster_bootstrap_ci.csv", index=False, encoding="utf-8-sig"
    )
    coverage = (
        frame[COMORBIDITY_FEATURES].notna().mean().rename("non_missing_rate").rename_axis("feature").reset_index()
    )
    coverage.to_csv(output_dir / "comorbidity_feature_coverage.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "experiment_id": config["experiment_id"],
        "target": "t0 미진단자의 다음 인접 조사 신규 당뇨 진단",
        "selection_split": "validation",
        "test_used_for_selection": False,
        "primary_policy": f"maximize recall subject to validation specificity >= {primary:.2f}",
        "selected_validation": selected,
        "selected_test": selected_test,
        "specificity_lower_95_one_sided": specificity_ci["lower_95_one_sided"],
        "specificity_0_40_supported_on_test_ci": bool(specificity_ci["lower_95_one_sided"] >= primary),
        "split_summary": {
            name: {"n": len(part), "positive_n": int(part["_target"].sum())} for name, part in splits.items()
        },
        "raw_sources": sources,
        "panel_sha256": _sha256_file(panel_path),
        "leakage_exclusions": [
            "diabetes diagnosis",
            "future-wave predictors",
            "treatment/medication",
            "diagnosis timing",
            "chronic disease count",
        ],
        "cerebrovascular_code_3_rule": "not counted as confirmed diagnosis; retained as missing unless code 1 or 5 observed",
        "promotion_status": "candidate_internal_not_for_personal_probability_display",
    }
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/klosa_comorbidity_threshold_experiment.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/klosa_comorbidity_threshold"))
    args = parser.parse_args()
    run(args.panel, args.raw_dir, args.config, args.output_dir)


if __name__ == "__main__":
    main()
