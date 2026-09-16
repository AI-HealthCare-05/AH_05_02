"""Train a recall-first KNHANES current diabetes screening model.

This task identifies a current clinical diabetes signal among adults without a
reported diagnosis. It is not a future-onset model and must not be presented as
a diagnosis. KLoSA remains the separate future-incidence model.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.base import BaseEstimator, clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    mean_absolute_error,
    r2_score,
    roc_auc_score,
    root_mean_squared_error,
)
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.ml.modeling.transformers import AnthropometricWaistEstimator

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "configs" / "knhanes_current_screening_recall.json"
DEFAULT_INPUT = ROOT / "data" / "processed" / "official_v1" / "knhanes_cleaned_2016_2024.csv"
DEFAULT_OUTPUT = ROOT / "experiments" / "diabetes_current_screening" / "champion_v050"
DEFAULT_MODEL_OUTPUT = ROOT / "outputs" / "ml" / "knhanes_current_screening_recall_v050"


@dataclass(frozen=True)
class Candidate:
    name: str
    family: str
    estimator: BaseEstimator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model-output-dir", type=Path, default=DEFAULT_MODEL_OUTPUT)
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_contract(config: dict[str, Any]) -> None:
    waist_predictors = config.get("waist_estimator", {}).get("predictors", [])
    features = set(
        config["numeric_features"]
        + config.get("derived_numeric_features", [])
        + config["categorical_features"]
        + waist_predictors
    )
    leaked = features.intersection(config["leakage_denylist"])
    if leaked:
        raise ValueError(f"Label leakage features are prohibited: {sorted(leaked)}")
    split_years = config["split_contract"]
    year_sets = [set(split_years[name]) for name in ("train", "validation", "test")]
    if any(left.intersection(right) for left, right in itertools.combinations(year_sets, 2)):
        raise ValueError("Train, validation, and test years must be disjoint")


def load_cohort(path: Path, config: dict[str, Any]) -> pd.DataFrame:
    needed = [
        "record_key",
        "survey_year",
        "split",
        "survey_weight",
        "target_diabetes_clinical",
        "eligible_diabetes_undiagnosed",
        "cohort_19_plus",
        *config["numeric_features"],
        *config["categorical_features"],
    ]
    data = pd.read_csv(path, usecols=list(dict.fromkeys(needed)))
    data = data.loc[
        data["eligible_diabetes_undiagnosed"] & data["cohort_19_plus"] & data["target_diabetes_clinical"].notna()
    ].copy()
    data["target_diabetes_clinical"] = data["target_diabetes_clinical"].astype(int)
    expected = config["split_contract"]
    for split_name, years in expected.items():
        actual_years = sorted(data.loc[data["split"].eq(split_name), "survey_year"].unique().tolist())
        if actual_years != years:
            raise ValueError(f"Unexpected {split_name} years: {actual_years}; expected {years}")
    if data["record_key"].duplicated().any():
        raise ValueError("record_key must be unique")
    return data


def make_preprocessor(config: dict[str, Any]) -> ColumnTransformer:
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric, config["numeric_features"] + config.get("derived_numeric_features", [])),
            ("categorical", categorical, config["categorical_features"]),
        ]
    )


def candidate_grid(seed: int) -> list[Candidate]:
    candidates: list[Candidate] = []
    for c_value in (0.1, 1.0, 10.0):
        candidates.append(
            Candidate(
                name=f"logistic_c{c_value:g}",
                family="logistic",
                estimator=LogisticRegression(
                    C=c_value,
                    class_weight="balanced",
                    max_iter=4000,
                    random_state=seed,
                ),
            )
        )
    for depth, leaf in ((8, 20), (12, 20), (None, 40)):
        candidates.append(
            Candidate(
                name=f"random_forest_depth{depth}_leaf{leaf}",
                family="random_forest",
                estimator=RandomForestClassifier(
                    n_estimators=400,
                    max_depth=depth,
                    min_samples_leaf=leaf,
                    max_features="sqrt",
                    class_weight="balanced_subsample",
                    n_jobs=-1,
                    random_state=seed,
                ),
            )
        )
    for depth, leaf in ((10, 10), (None, 20)):
        candidates.append(
            Candidate(
                name=f"extra_trees_depth{depth}_leaf{leaf}",
                family="extra_trees",
                estimator=ExtraTreesClassifier(
                    n_estimators=400,
                    max_depth=depth,
                    min_samples_leaf=leaf,
                    max_features="sqrt",
                    class_weight="balanced",
                    n_jobs=-1,
                    random_state=seed,
                ),
            )
        )
    for leaves, child_samples in ((15, 40), (31, 40), (31, 80), (63, 80)):
        candidates.append(
            Candidate(
                name=f"lightgbm_leaves{leaves}_child{child_samples}",
                family="lightgbm",
                estimator=LGBMClassifier(
                    objective="binary",
                    n_estimators=450,
                    learning_rate=0.03,
                    num_leaves=leaves,
                    min_child_samples=child_samples,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    reg_lambda=2.0,
                    class_weight="balanced",
                    verbosity=-1,
                    n_jobs=-1,
                    random_state=seed,
                ),
            )
        )
    return candidates


def normalized_weights(values: pd.Series | np.ndarray) -> np.ndarray:
    weights = np.asarray(values, dtype=float)
    mean = float(np.mean(weights))
    if not np.isfinite(mean) or mean <= 0:
        raise ValueError("survey_weight must have a positive finite mean")
    return weights / mean


def build_pipeline(config: dict[str, Any], estimator: BaseEstimator) -> Pipeline:
    waist_config = config.get("waist_estimator", {})
    if not waist_config.get("enabled", False):
        return Pipeline([("preprocessor", make_preprocessor(config)), ("model", clone(estimator))])
    waist = AnthropometricWaistEstimator(
        enabled=True,
        predictors=tuple(waist_config.get("predictors", ["height_cm", "weight_kg", "age", "sex"])),
        seed=int(config["seed"]),
    )
    return Pipeline(
        [
            ("anthropometrics", waist),
            ("preprocessor", make_preprocessor(config)),
            ("model", clone(estimator)),
        ]
    )


def fit_pipeline(
    pipeline: Pipeline,
    x: pd.DataFrame,
    y: np.ndarray,
    weights: np.ndarray,
) -> Pipeline:
    pipeline.fit(x, y, model__sample_weight=weights)
    return pipeline


def oof_predictions(
    candidate: Candidate,
    train: pd.DataFrame,
    config: dict[str, Any],
) -> np.ndarray:
    features = config["numeric_features"] + config["categorical_features"]
    y = train[config["target"]].to_numpy(dtype=int)
    groups = train["survey_year"].to_numpy()
    predictions = np.zeros(len(train), dtype=float)
    splitter = GroupKFold(n_splits=len(np.unique(groups)))
    for fit_index, holdout_index in splitter.split(train, y, groups):
        pipeline = build_pipeline(config, candidate.estimator)
        fit_pipeline(
            pipeline,
            train.iloc[fit_index][features],
            y[fit_index],
            normalized_weights(train.iloc[fit_index]["survey_weight"]),
        )
        predictions[holdout_index] = pipeline.predict_proba(train.iloc[holdout_index][features])[:, 1]
    return predictions


def fit_platt(probabilities: np.ndarray, y: np.ndarray, weights: np.ndarray) -> LogisticRegression:
    clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)
    logits = np.log(clipped / (1 - clipped)).reshape(-1, 1)
    calibrator = LogisticRegression(C=1e6, max_iter=3000)
    calibrator.fit(logits, y, sample_weight=weights)
    return calibrator


def apply_platt(calibrator: LogisticRegression, probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)
    logits = np.log(clipped / (1 - clipped)).reshape(-1, 1)
    return calibrator.predict_proba(logits)[:, 1]


def threshold_metrics(
    y: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    sample_weight: np.ndarray | None = None,
) -> dict[str, float]:
    predicted = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1], sample_weight=sample_weight).ravel()

    def ratio(numerator: float, denominator: float) -> float:
        return float(numerator / denominator) if denominator else float("nan")

    return {
        "recall": ratio(tp, tp + fn),
        "specificity": ratio(tn, tn + fp),
        "precision": ratio(tp, tp + fp),
        "f1": ratio(2 * tp, 2 * tp + fp + fn),
        "tn": float(tn),
        "fp": float(fp),
        "fn": float(fn),
        "tp": float(tp),
    }


def select_threshold(
    y: np.ndarray,
    probabilities: np.ndarray,
    minimum_specificity: float,
    sample_weight: np.ndarray | None = None,
) -> tuple[float, dict[str, float]]:
    weights = np.ones(len(y), dtype=float) if sample_weight is None else np.asarray(sample_weight, dtype=float)
    order = np.argsort(-probabilities, kind="stable")
    sorted_probabilities = probabilities[order]
    sorted_y = y[order]
    sorted_weights = weights[order]
    positive_weights = sorted_weights * sorted_y
    negative_weights = sorted_weights * (1 - sorted_y)
    cumulative_tp = np.cumsum(positive_weights)
    cumulative_fp = np.cumsum(negative_weights)
    group_ends = np.r_[np.flatnonzero(np.diff(sorted_probabilities) != 0), len(y) - 1]
    total_positive = float(positive_weights.sum())
    total_negative = float(negative_weights.sum())
    recalls = cumulative_tp[group_ends] / total_positive
    specificities = (total_negative - cumulative_fp[group_ends]) / total_negative
    eligible = np.flatnonzero(specificities + 1e-12 >= minimum_specificity)
    if not len(eligible):
        raise RuntimeError("No threshold satisfies the specificity constraint")
    ranked = sorted(
        eligible,
        key=lambda index: (
            recalls[index],
            specificities[index],
            sorted_probabilities[group_ends[index]],
        ),
        reverse=True,
    )
    threshold = float(sorted_probabilities[group_ends[ranked[0]]])
    return threshold, threshold_metrics(y, probabilities, threshold, sample_weight)


def probability_metrics(
    y: np.ndarray,
    probabilities: np.ndarray,
    sample_weight: np.ndarray | None = None,
) -> dict[str, float]:
    prevalence = float(np.average(y, weights=sample_weight)) if sample_weight is not None else float(np.mean(y))
    brier = float(brier_score_loss(y, probabilities, sample_weight=sample_weight))
    null_brier = prevalence * (1 - prevalence)
    return {
        "prevalence": prevalence,
        "auroc": float(roc_auc_score(y, probabilities, sample_weight=sample_weight)),
        "auprc": float(average_precision_score(y, probabilities, sample_weight=sample_weight)),
        "auprc_lift": float(average_precision_score(y, probabilities, sample_weight=sample_weight) / prevalence),
        "brier": brier,
        "brier_skill_score": float(1 - brier / null_brier),
    }


def waist_estimator_oof_report(train: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Measure waist-estimation error using survey-year holdouts only."""
    observed = train.loc[train["waist_cm"].notna()].reset_index(drop=True)
    predictions = np.full(len(observed), np.nan, dtype=float)
    median_predictions = np.full(len(observed), np.nan, dtype=float)
    groups = observed["survey_year"].to_numpy()
    splitter = GroupKFold(n_splits=len(np.unique(groups)))
    waist_config = config.get("waist_estimator", {})
    predictors = tuple(waist_config.get("predictors", ["height_cm", "weight_kg", "age", "sex"]))
    for fit_index, holdout_index in splitter.split(observed, groups=groups):
        fit_frame = observed.iloc[fit_index]
        holdout = observed.iloc[holdout_index].copy()
        transformer = AnthropometricWaistEstimator(
            enabled=True,
            predictors=predictors,
            seed=int(config["seed"]),
        ).fit(fit_frame)
        median_predictions[holdout_index] = float(fit_frame["waist_cm"].median())
        holdout["waist_cm"] = np.nan
        predictions[holdout_index] = transformer.transform(holdout)["waist_cm"].to_numpy()

    actual = observed["waist_cm"].to_numpy(dtype=float)
    rows: list[dict[str, Any]] = []
    masks = {
        "all": np.ones(len(observed), dtype=bool),
        "19-44": observed["age"].between(19, 44).to_numpy(),
        "45-64": observed["age"].between(45, 64).to_numpy(),
        "65+": observed["age"].ge(65).to_numpy(),
    }
    for method, values in (("training_fold_median", median_predictions), ("anthropometric_hgb", predictions)):
        for group_name, mask in masks.items():
            rows.append(
                {
                    "method": method,
                    "group": group_name,
                    "n": int(mask.sum()),
                    "mae_cm": float(mean_absolute_error(actual[mask], values[mask])),
                    "rmse_cm": float(root_mean_squared_error(actual[mask], values[mask])),
                    "r2": float(r2_score(actual[mask], values[mask])),
                    "bias_cm": float(np.mean(values[mask] - actual[mask])),
                }
            )
    return pd.DataFrame(rows)


def evaluation_row(
    name: str,
    split: str,
    y: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    weights: np.ndarray,
) -> dict[str, Any]:
    row: dict[str, Any] = {"model": name, "split": split, "n": len(y), "positive_n": int(y.sum())}
    row.update(probability_metrics(y, probabilities))
    row.update(threshold_metrics(y, probabilities, threshold))
    weighted = probability_metrics(y, probabilities, weights)
    weighted.update(threshold_metrics(y, probabilities, threshold, weights))
    row.update({f"weighted_{key}": value for key, value in weighted.items()})
    row["threshold"] = threshold
    return row


def simplex_weights(count: int, step: float = 0.1) -> list[np.ndarray]:
    units = int(round(1.0 / step))
    results = []
    for composition in itertools.product(range(units + 1), repeat=count):
        if sum(composition) == units:
            results.append(np.asarray(composition, dtype=float) / units)
    return results


def predict_artifact(artifact: dict[str, Any], frame: pd.DataFrame) -> np.ndarray:
    """Return the calibrated current-screening score for a feature frame."""
    missing = sorted(set(artifact["features"]).difference(frame.columns))
    if missing:
        raise ValueError(f"Missing inference features: {missing}")
    probabilities = []
    weights = []
    for family, weight in artifact["ensemble_weights"].items():
        pipeline = artifact["pipelines"][family]
        calibrator = artifact["calibrators"][family]
        raw = pipeline.predict_proba(frame[artifact["features"]])[:, 1]
        probabilities.append(apply_platt(calibrator, raw))
        weights.append(weight)
    return np.average(np.column_stack(probabilities), axis=1, weights=np.asarray(weights, dtype=float))


def main() -> None:  # noqa: C901 - experiment orchestration is intentionally linear
    args = parse_args()
    config = load_config(args.config)
    validate_contract(config)
    data = load_cohort(args.input, config)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.model_output_dir.mkdir(parents=True, exist_ok=True)

    train = data.loc[data["split"].eq("train")].reset_index(drop=True)
    validation = data.loc[data["split"].eq("validation")].reset_index(drop=True)
    test = data.loc[data["split"].eq("test")].reset_index(drop=True)
    target = config["target"]
    features = config["numeric_features"] + config["categorical_features"]
    y_train = train[target].to_numpy(dtype=int)
    y_validation = validation[target].to_numpy(dtype=int)
    y_test = test[target].to_numpy(dtype=int)
    train_weights = normalized_weights(train["survey_weight"])
    validation_weights = normalized_weights(validation["survey_weight"])
    test_weights = normalized_weights(test["survey_weight"])
    validation_floor = (
        config["selection"]["minimum_test_specificity"] + config["selection"]["validation_specificity_buffer"]
    )

    waist_report = waist_estimator_oof_report(train, config)
    waist_report.to_csv(args.output_dir / "waist_estimator_oof_metrics.csv", index=False)

    oof_rows: list[dict[str, Any]] = []
    family_winners: dict[str, tuple[Candidate, np.ndarray]] = {}
    for candidate in candidate_grid(config["seed"]):
        print(f"OOF {candidate.name}", flush=True)
        cache_path = args.model_output_dir / f"{candidate.name}_oof.npy"
        if cache_path.exists():
            oof = np.load(cache_path)
            if len(oof) != len(train):
                raise ValueError(f"Invalid OOF cache length for {candidate.name}")
        else:
            oof = oof_predictions(candidate, train, config)
            np.save(cache_path, oof)
        calibrator = fit_platt(oof, y_train, train_weights)
        calibrated = apply_platt(calibrator, oof)
        threshold, threshold_row = select_threshold(y_train, calibrated, validation_floor)
        row = {
            "candidate": candidate.name,
            "family": candidate.family,
            "threshold": threshold,
            **probability_metrics(y_train, calibrated),
            **threshold_row,
        }
        oof_rows.append(row)
        current = family_winners.get(candidate.family)
        key = (row["recall"], row["auprc"], row["specificity"])
        if current is None:
            family_winners[candidate.family] = (candidate, oof)
        else:
            current_row = next(item for item in oof_rows if item["candidate"] == current[0].name)
            current_key = (current_row["recall"], current_row["auprc"], current_row["specificity"])
            if key > current_key:
                family_winners[candidate.family] = (candidate, oof)

    pd.DataFrame(oof_rows).sort_values(["recall", "auprc", "specificity"], ascending=False).to_csv(
        args.output_dir / "oof_candidate_search.csv", index=False
    )

    fitted: dict[str, tuple[Pipeline, LogisticRegression]] = {}
    validation_probabilities: dict[str, np.ndarray] = {}
    test_probabilities: dict[str, np.ndarray] = {}
    validation_rows: list[dict[str, Any]] = []
    for family, (candidate, oof_raw) in family_winners.items():
        print(f"Fit family winner {candidate.name}", flush=True)
        pipeline = build_pipeline(config, candidate.estimator)
        fit_pipeline(pipeline, train[features], y_train, train_weights)
        calibrator = fit_platt(oof_raw, y_train, train_weights)
        validation_raw = pipeline.predict_proba(validation[features])[:, 1]
        test_raw = pipeline.predict_proba(test[features])[:, 1]
        validation_probabilities[family] = apply_platt(calibrator, validation_raw)
        test_probabilities[family] = apply_platt(calibrator, test_raw)
        fitted[family] = (pipeline, calibrator)

    ensemble_specs: list[tuple[str, np.ndarray]] = []
    families = sorted(validation_probabilities)
    ensemble_specs.append(("equal_soft_vote", np.repeat(1 / len(families), len(families))))
    for weights in simplex_weights(len(families), step=0.1):
        ensemble_specs.append(("blend_" + "_".join(f"{value:.1f}" for value in weights), weights))

    candidate_probabilities = dict(validation_probabilities)
    candidate_test_probabilities = dict(test_probabilities)
    for name, weights in ensemble_specs:
        candidate_probabilities[name] = np.average(
            np.column_stack([validation_probabilities[family] for family in families]),
            axis=1,
            weights=weights,
        )
        candidate_test_probabilities[name] = np.average(
            np.column_stack([test_probabilities[family] for family in families]),
            axis=1,
            weights=weights,
        )

    best_name = ""
    best_key = (-1.0, -1.0, -1.0)
    best_threshold = 0.5
    for name, probabilities in candidate_probabilities.items():
        threshold, _ = select_threshold(y_validation, probabilities, validation_floor)
        row = evaluation_row(name, "validation", y_validation, probabilities, threshold, validation_weights)
        passes_lift = row["auprc_lift"] >= config["selection"]["minimum_auprc_lift"]
        row["selection_eligible"] = bool(passes_lift and row["specificity"] >= validation_floor)
        validation_rows.append(row)
        if row["selection_eligible"]:
            key = (row["recall"], row["auprc"], row["specificity"])
            if key > best_key:
                best_name = name
                best_key = key
                best_threshold = threshold

    validation_table = pd.DataFrame(validation_rows).sort_values(
        ["selection_eligible", "recall", "auprc", "specificity"], ascending=False
    )
    validation_table.to_csv(args.output_dir / "validation_leaderboard.csv", index=False)
    if not best_name:
        raise RuntimeError("No validation candidate passed the pre-registered constraints")

    selected_validation = evaluation_row(
        best_name,
        "validation",
        y_validation,
        candidate_probabilities[best_name],
        best_threshold,
        validation_weights,
    )
    selected_test = evaluation_row(
        best_name,
        "test",
        y_test,
        candidate_test_probabilities[best_name],
        best_threshold,
        test_weights,
    )
    selected_test["test_specificity_constraint_passed"] = bool(
        selected_test["specificity"] >= config["selection"]["minimum_test_specificity"]
    )
    pd.DataFrame([selected_validation, selected_test]).to_csv(
        args.output_dir / "selected_model_metrics.csv", index=False
    )

    age_rows: list[dict[str, Any]] = []
    age_groups = {
        "19-44": test["age"].between(19, 44),
        "45-64": test["age"].between(45, 64),
        "65+": test["age"].ge(65),
    }
    for label, mask in age_groups.items():
        positions = np.flatnonzero(mask.to_numpy())
        row = evaluation_row(
            best_name,
            label,
            y_test[positions],
            candidate_test_probabilities[best_name][positions],
            best_threshold,
            test_weights[positions],
        )
        age_rows.append(row)
    pd.DataFrame(age_rows).to_csv(args.output_dir / "selected_model_age_metrics.csv", index=False)

    if best_name in fitted:
        selected_weights = {best_name: 1.0}
    else:
        selected_weights = {
            family: float(weight)
            for family, weight in zip(
                families,
                next(weights for name, weights in ensemble_specs if name == best_name),
                strict=True,
            )
            if weight > 0
        }
    artifact = {
        "model_key": "diabetes_current_screening",
        "model_version": config["model_version"],
        "feature_schema_version": config["feature_schema_version"],
        "threshold_version": config["threshold_version"],
        "threshold": best_threshold,
        "selected_candidate": best_name,
        "ensemble_weights": selected_weights,
        "features": features,
        "pipelines": {family: fitted[family][0] for family in selected_weights},
        "calibrators": {family: fitted[family][1] for family in selected_weights},
        "task": "current_cross_sectional_screening_not_future_incidence",
        "disclaimer": "현재 위험 신호 선별 보조용이며 진단·미래 발병확률·의료 조언이 아닙니다.",
    }
    artifact_path = args.model_output_dir / f"{config['model_version']}.joblib"
    joblib.dump(artifact, artifact_path)

    manifest = {
        "experiment_id": config["experiment_id"],
        "source_file": args.input.name,
        "source_sha256": sha256_file(args.input),
        "config_sha256": sha256_file(args.config),
        "library_versions": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": version("scikit-learn"),
            "lightgbm": version("lightgbm"),
        },
        "target_definition": "현재 미진단 성인의 횡단면 당뇨 임상 기준 해당 여부",
        "split_summary": {
            split_name: {
                "years": config["split_contract"][split_name],
                "n": len(frame),
                "positive_n": int(frame[target].sum()),
                "positive_rate": float(frame[target].mean()),
            }
            for split_name, frame in (("train", train), ("validation", validation), ("test", test))
        },
        "selection_rule": {
            "primary": "recall",
            "tie_breakers": ["auprc", "specificity"],
            "validation_specificity_floor": validation_floor,
            "test_specificity_floor": config["selection"]["minimum_test_specificity"],
        },
        "waist_estimator_oof": waist_report.to_dict(orient="records"),
        "selected_validation": selected_validation,
        "selected_test": selected_test,
        "selected_weights": selected_weights,
        "artifact_path_local_only": str(artifact_path),
        "promotion_status": "candidate_internal_not_for_diagnosis_or_personal_probability_display",
    }
    (args.output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"selected": best_name, "validation": selected_validation, "test": selected_test}, indent=2))


if __name__ == "__main__":
    main()
