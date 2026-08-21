"""Recall-first diabetes candidate models for KLoSA and KNHANES.

KLoSA and KNHANES are trained and evaluated independently. Hyperparameters and
ensemble weights are selected using out-of-fold training predictions. Decision
thresholds are selected on validation data. Test data are evaluated only after
all choices have been frozen.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    target: str
    entity_id: str
    target_definition: str


SPECS = {
    "klosa": DatasetSpec(
        name="KLoSA",
        target="target_diabetes_incident_next_wave",
        entity_id="participant_id",
        target_definition="t0 미진단자의 다음 인접 조사(약 2년) 신규 당뇨 진단",
    ),
    "knhanes": DatasetSpec(
        name="KNHANES",
        target="target_diabetes_clinical",
        entity_id="record_key",
        target_definition="현재 미진단 성인의 횡단면 당뇨 임상 기준 해당 여부",
    ),
}

LEAKAGE_DENYLIST = {
    "fasting_glucose",
    "hba1c",
    "glucose",
    "diagnosis",
    "medication",
    "target_diabetes_clinical",
    "target_diabetes_incident_next_wave",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_sample(frame: pd.DataFrame, limit: int, seed: int, dataset: str, split: str) -> pd.DataFrame:
    """Retain age-label strata with deterministic SHA-256 ranking."""
    if len(frame) <= limit:
        return frame.sort_values("_row_key").reset_index(drop=True)
    working = frame.copy()
    working["_age_group"] = pd.cut(working["age"], bins=[18, 44, 64, np.inf], labels=["19-44", "45-64", "65+"]).astype(
        "string"
    )
    working["_stratum"] = working["_age_group"] + "|" + working["_target"].astype(str)
    counts = working["_stratum"].value_counts().sort_index()
    ideals = counts * limit / len(working)
    quotas = np.floor(ideals).astype(int).clip(lower=1)
    while int(quotas.sum()) > limit:
        key = min(
            (key for key in quotas.index if quotas[key] > 1), key=lambda item: (ideals[item] - quotas[item], item)
        )
        quotas[key] -= 1
    while int(quotas.sum()) < limit:
        key = max(
            (key for key in quotas.index if quotas[key] < counts[key]),
            key=lambda item: (ideals[item] - quotas[item], item),
        )
        quotas[key] += 1
    selected: list[pd.DataFrame] = []
    for stratum, quota in quotas.items():
        group = working.loc[working["_stratum"] == stratum].copy()
        group["_rank"] = group["_row_key"].map(
            lambda value, stratum=stratum: hashlib.sha256(
                f"{seed}|{dataset}|{split}|{stratum}|{value}".encode()
            ).hexdigest()
        )
        selected.append(group.sort_values("_rank").head(int(quota)))
    return pd.concat(selected).sort_values("_row_key").drop(columns=["_rank"]).reset_index(drop=True)


def load_dataset(path: Path, dataset: str, dataset_config: dict[str, Any]) -> pd.DataFrame:
    spec = SPECS[dataset]
    features = dataset_config["numeric_features"] + dataset_config["categorical_features"]
    lowered = " ".join(features).lower()
    leaked = sorted(item for item in LEAKAGE_DENYLIST if item in lowered)
    if leaked:
        raise ValueError(f"Feature schema contains leakage terms: {leaked}")
    required = {"split", spec.target, spec.entity_id, *features}
    if dataset == "klosa":
        required.add("survey_wave")
    header = set(pd.read_csv(path, nrows=0).columns)
    missing = required - header
    if missing:
        raise ValueError(f"Missing columns in {path}: {sorted(missing)}")
    frame = pd.read_csv(path, usecols=sorted(required), low_memory=False)
    frame = frame.rename(columns={spec.target: "_target"})
    frame["_target"] = pd.to_numeric(frame["_target"], errors="coerce")
    frame = frame.loc[frame["_target"].isin([0, 1])].copy()
    frame["_target"] = frame["_target"].astype(int)
    if dataset == "klosa":
        frame["_row_key"] = frame["participant_id"].astype("string") + ":" + frame["survey_wave"].astype("string")
    else:
        frame["_row_key"] = frame[spec.entity_id].astype("string")
    return frame


def prepare_splits(frame: pd.DataFrame, dataset: str, config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    result = {}
    for split in ("train", "validation", "test"):
        subset = frame.loc[frame["split"] == split].copy()
        result[split] = _stable_sample(
            subset,
            limit=min(int(config["sample_limits"][split]), len(subset)),
            seed=int(config["seed"]),
            dataset=dataset,
            split=split,
        )
    return result


def _preprocessor(dataset_config: dict[str, Any], scale_numeric: bool) -> ColumnTransformer:
    numeric_steps: list[tuple[str, Any]] = [
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
    ]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))
    return ColumnTransformer(
        [
            ("numeric", Pipeline(numeric_steps), dataset_config["numeric_features"]),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                dataset_config["categorical_features"],
            ),
        ],
        remainder="drop",
    )


def build_candidates(dataset_config: dict[str, Any], y_train: np.ndarray, seed: int) -> dict[str, list[BaseEstimator]]:
    negatives = int((y_train == 0).sum())
    positives = int((y_train == 1).sum())
    positive_weight = negatives / max(positives, 1)

    def pipe(model: BaseEstimator, *, scale: bool) -> Pipeline:
        return Pipeline([("preprocess", _preprocessor(dataset_config, scale)), ("model", model)])

    from lightgbm import LGBMClassifier
    from xgboost import XGBClassifier

    return {
        "logistic_regression": [
            pipe(
                LogisticRegression(C=c, class_weight="balanced", max_iter=3000, random_state=seed),
                scale=True,
            )
            for c in (0.1, 1.0, 10.0)
        ],
        "random_forest": [
            pipe(
                RandomForestClassifier(
                    n_estimators=400,
                    max_depth=max_depth,
                    min_samples_leaf=min_leaf,
                    max_features="sqrt",
                    class_weight="balanced_subsample",
                    n_jobs=1,
                    random_state=seed,
                ),
                scale=False,
            )
            for max_depth, min_leaf in ((None, 3), (None, 10), (8, 5))
        ],
        "xgboost": [
            pipe(
                XGBClassifier(
                    n_estimators=350,
                    max_depth=max_depth,
                    learning_rate=learning_rate,
                    min_child_weight=5,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    reg_lambda=2.0,
                    scale_pos_weight=positive_weight,
                    objective="binary:logistic",
                    eval_metric="logloss",
                    tree_method="hist",
                    n_jobs=1,
                    random_state=seed,
                ),
                scale=False,
            )
            for max_depth, learning_rate in ((3, 0.03), (3, 0.08), (5, 0.03))
        ],
        "lightgbm": [
            pipe(
                LGBMClassifier(
                    n_estimators=350,
                    num_leaves=num_leaves,
                    max_depth=max_depth,
                    learning_rate=learning_rate,
                    min_child_samples=30,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    reg_lambda=2.0,
                    scale_pos_weight=positive_weight,
                    deterministic=True,
                    force_col_wise=True,
                    verbosity=-1,
                    n_jobs=1,
                    random_state=seed,
                ),
                scale=False,
            )
            for num_leaves, max_depth, learning_rate in ((15, 5, 0.03), (31, 6, 0.03), (31, 6, 0.08))
        ],
    }


def _cv_splits(frame: pd.DataFrame, dataset: str, folds: int, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    y = frame["_target"].to_numpy()
    if dataset == "klosa":
        splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
        return list(splitter.split(frame, y, groups=frame[SPECS[dataset].entity_id]))
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    return list(splitter.split(frame, y))


def oof_probabilities(
    model: BaseEstimator, frame: pd.DataFrame, folds: list[tuple[np.ndarray, np.ndarray]]
) -> np.ndarray:
    probabilities = np.zeros(len(frame), dtype=float)
    features = frame.drop(columns=["_target", "_row_key"], errors="ignore")
    y = frame["_target"].to_numpy()
    for train_index, holdout_index in folds:
        fold_model = clone(model)
        fold_model.fit(features.iloc[train_index], y[train_index])
        probabilities[holdout_index] = fold_model.predict_proba(features.iloc[holdout_index])[:, 1]
    return probabilities


def metric_row(y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict[str, Any]:
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    prevalence = float(y_true.mean())
    has_both_classes = len(np.unique(y_true)) == 2
    auprc = float(average_precision_score(y_true, probabilities)) if y_true.sum() else math.nan
    return {
        "n": int(len(y_true)),
        "positive_n": int(y_true.sum()),
        "prevalence": prevalence,
        "threshold": float(threshold),
        "auroc": float(roc_auc_score(y_true, probabilities)) if has_both_classes else math.nan,
        "auprc": auprc,
        "auprc_lift": float(auprc / prevalence) if prevalence else math.nan,
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else math.nan,
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "brier": float(brier_score_loss(y_true, probabilities)),
        "predicted_positive_rate": float(predictions.mean()),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def select_threshold(
    y_true: np.ndarray, probabilities: np.ndarray, config: dict[str, Any]
) -> tuple[float, dict[str, Any]]:
    threshold_config = config["threshold_grid"]
    thresholds = np.linspace(
        float(threshold_config["minimum"]),
        float(threshold_config["maximum"]),
        int(threshold_config["points"]),
    )
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
    pool = feasible or candidates
    best = max(pool, key=lambda item: (item["recall"], item["auprc"], item["specificity"], item["threshold"]))
    return float(best["threshold"]), best


def _estimator_signature(model: BaseEstimator) -> str:
    model_params = model.named_steps["model"].get_params(deep=False)
    keep = {
        key: value
        for key, value in model_params.items()
        if key
        in {
            "C",
            "class_weight",
            "max_depth",
            "min_samples_leaf",
            "n_estimators",
            "learning_rate",
            "num_leaves",
            "scale_pos_weight",
        }
    }
    return json.dumps(keep, sort_keys=True, default=str)


def choose_family_models(
    dataset: str,
    train: pd.DataFrame,
    dataset_config: dict[str, Any],
    config: dict[str, Any],
) -> tuple[dict[str, BaseEstimator], dict[str, np.ndarray], list[dict[str, Any]]]:
    seed = int(config["seed"])
    y = train["_target"].to_numpy()
    folds = _cv_splits(train, dataset, int(config["cv_folds"]), seed)
    selected_models: dict[str, BaseEstimator] = {}
    selected_oof: dict[str, np.ndarray] = {}
    search_rows: list[dict[str, Any]] = []
    for family, candidates in build_candidates(dataset_config, y, seed).items():
        family_results = []
        for index, candidate in enumerate(candidates):
            probabilities = oof_probabilities(candidate, train, folds)
            threshold, metrics = select_threshold(y, probabilities, config)
            row = {
                "dataset": SPECS[dataset].name,
                "family": family,
                "candidate_index": index,
                "estimator_params": _estimator_signature(candidate),
                "selection_split": "train_oof",
                **metrics,
            }
            search_rows.append(row)
            family_results.append((metrics, threshold, candidate, probabilities))
        best = max(
            family_results,
            key=lambda item: (
                item[0]["constraints_passed"],
                item[0]["recall"],
                item[0]["auprc"],
                item[0]["specificity"],
            ),
        )
        selected_models[family] = best[2]
        selected_oof[family] = best[3]
    return selected_models, selected_oof, search_rows


def _blend_weights(names: list[str], step: float) -> list[dict[str, float]]:
    units = round(1 / step)
    weights = []
    for values in itertools.product(range(units + 1), repeat=len(names)):
        if sum(values) != units or sum(value > 0 for value in values) < 2:
            continue
        weights.append({name: value / units for name, value in zip(names, values, strict=True)})
    return weights


def _weighted_average(probabilities: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    return sum(probabilities[name] * weight for name, weight in weights.items())


def _sigmoid_calibrator(probabilities: np.ndarray, y: np.ndarray, seed: int) -> LogisticRegression:
    eps = np.finfo(float).eps
    logits = np.log(np.clip(probabilities, eps, 1 - eps) / np.clip(1 - probabilities, eps, 1 - eps))
    calibrator = LogisticRegression(random_state=seed)
    calibrator.fit(logits.reshape(-1, 1), y)
    return calibrator


def _apply_calibrator(calibrator: LogisticRegression, probabilities: np.ndarray) -> np.ndarray:
    eps = np.finfo(float).eps
    logits = np.log(np.clip(probabilities, eps, 1 - eps) / np.clip(1 - probabilities, eps, 1 - eps))
    return calibrator.predict_proba(logits.reshape(-1, 1))[:, 1]


def _threshold_version(dataset: str, model_name: str, threshold: float, experiment_id: str) -> str:
    token = f"{dataset}|{model_name}|{threshold:.6f}|{experiment_id}"
    return "thr-" + hashlib.sha256(token.encode()).hexdigest()[:12]


def _age_group_metrics(
    dataset: str,
    test: pd.DataFrame,
    y_test: np.ndarray,
    probabilities_by_model: dict[str, np.ndarray],
    frozen_thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    age_groups = pd.cut(
        pd.to_numeric(test["age"], errors="coerce"),
        bins=[18, 44, 64, np.inf],
        labels=["19-44", "45-64", "65+"],
    )
    rows = []
    for name, probabilities in probabilities_by_model.items():
        for age_group in ("19-44", "45-64", "65+"):
            mask = (age_groups == age_group).to_numpy()
            if not bool(mask.any()):
                continue
            rows.append(
                {
                    "dataset": SPECS[dataset].name,
                    "target_definition": SPECS[dataset].target_definition,
                    "model": name,
                    "age_group": age_group,
                    "evaluation_split": "test_once_after_freeze",
                    "threshold_source": "validation",
                    **metric_row(y_test[mask], probabilities[mask], frozen_thresholds[name]),
                }
            )
    return rows


def run_dataset(
    dataset: str,
    path: Path,
    config: dict[str, Any],
    output_dir: Path,
    model_dir: Path,
) -> dict[str, Any]:
    dataset_config = config["datasets"][dataset]
    full_frame = load_dataset(path, dataset, dataset_config)
    splits = prepare_splits(full_frame, dataset, config)
    train, validation, test = (splits[name] for name in ("train", "validation", "test"))
    y_train = train["_target"].to_numpy()
    y_validation = validation["_target"].to_numpy()
    y_test = test["_target"].to_numpy()
    feature_columns = dataset_config["numeric_features"] + dataset_config["categorical_features"]

    family_models, oof_predictions, search_rows = choose_family_models(dataset, train, dataset_config, config)
    validation_predictions: dict[str, np.ndarray] = {}
    test_predictions: dict[str, np.ndarray] = {}
    fitted_models: dict[str, BaseEstimator] = {}
    for name, model in family_models.items():
        fitted = clone(model).fit(train[feature_columns], y_train)
        fitted_models[name] = fitted
        validation_predictions[name] = fitted.predict_proba(validation[feature_columns])[:, 1]

    ensemble_oof: dict[str, np.ndarray] = {
        "soft_voting_equal": np.mean(np.column_stack(list(oof_predictions.values())), axis=1)
    }
    ensemble_validation: dict[str, np.ndarray] = {
        "soft_voting_equal": np.mean(np.column_stack(list(validation_predictions.values())), axis=1)
    }
    names = list(oof_predictions)
    weight_candidates = _blend_weights(names, float(config["blend_weight_step"]))
    best_weight_result = None
    for weights in weight_candidates:
        blend = _weighted_average(oof_predictions, weights)
        threshold, metrics = select_threshold(y_train, blend, config)
        result = (metrics, threshold, weights, blend)
        if best_weight_result is None or (
            metrics["constraints_passed"],
            metrics["recall"],
            metrics["auprc"],
            metrics["specificity"],
        ) > (
            best_weight_result[0]["constraints_passed"],
            best_weight_result[0]["recall"],
            best_weight_result[0]["auprc"],
            best_weight_result[0]["specificity"],
        ):
            best_weight_result = result
    assert best_weight_result is not None
    blend_weights = best_weight_result[2]
    ensemble_oof["oof_blending"] = best_weight_result[3]
    ensemble_validation["oof_blending"] = _weighted_average(validation_predictions, blend_weights)

    stacker = LogisticRegression(class_weight="balanced", max_iter=2000, random_state=int(config["seed"]))
    stacker.fit(np.column_stack([oof_predictions[name] for name in names]), y_train)
    ensemble_oof["stacking"] = stacker.predict_proba(np.column_stack([oof_predictions[name] for name in names]))[:, 1]
    ensemble_validation["stacking"] = stacker.predict_proba(
        np.column_stack([validation_predictions[name] for name in names])
    )[:, 1]

    all_validation_predictions = {**validation_predictions, **ensemble_validation}
    all_oof_predictions = {**oof_predictions, **ensemble_oof}
    validation_rows = []
    frozen_thresholds = {}
    for name, probabilities in all_validation_predictions.items():
        threshold, metrics = select_threshold(y_validation, probabilities, config)
        frozen_thresholds[name] = threshold
        validation_rows.append(
            {
                "dataset": SPECS[dataset].name,
                "target_definition": SPECS[dataset].target_definition,
                "model": name,
                "evaluation_split": "validation",
                "threshold_version": _threshold_version(dataset, name, threshold, config["experiment_id"]),
                **metrics,
            }
        )

    eligible_validation = [row for row in validation_rows if row["constraints_passed"]]
    winner_row = max(
        eligible_validation or validation_rows,
        key=lambda row: (row["recall"], row["auprc"], row["specificity"]),
    )
    winner_name = winner_row["model"]
    calibrator = _sigmoid_calibrator(all_oof_predictions[winner_name], y_train, int(config["seed"]))
    calibrated_name = f"{winner_name}_sigmoid_calibrated"
    calibrated_validation = _apply_calibrator(calibrator, all_validation_predictions[winner_name])
    calibrated_threshold, calibrated_metrics = select_threshold(y_validation, calibrated_validation, config)
    frozen_thresholds[calibrated_name] = calibrated_threshold
    validation_rows.append(
        {
            "dataset": SPECS[dataset].name,
            "target_definition": SPECS[dataset].target_definition,
            "model": calibrated_name,
            "evaluation_split": "validation",
            "threshold_version": _threshold_version(
                dataset, calibrated_name, calibrated_threshold, config["experiment_id"]
            ),
            **calibrated_metrics,
        }
    )

    # The final candidate is selected on validation data. Test data is never used
    # to choose a model, threshold, ensemble weight or calibration method.
    final_validation_pool = [
        row for row in validation_rows if bool(row.get("constraints_passed", False))
    ] or validation_rows
    final_validation_winner = max(
        final_validation_pool,
        key=lambda row: (row["recall"], row["auprc"], row["specificity"]),
    )
    final_candidate_name = final_validation_winner["model"]

    # Test access begins only after model, ensemble, calibration and threshold choices are frozen.
    for name, fitted in fitted_models.items():
        test_predictions[name] = fitted.predict_proba(test[feature_columns])[:, 1]
    ensemble_test = {
        "soft_voting_equal": np.mean(np.column_stack(list(test_predictions.values())), axis=1),
        "oof_blending": _weighted_average(test_predictions, blend_weights),
        "stacking": stacker.predict_proba(np.column_stack([test_predictions[name] for name in names]))[:, 1],
    }
    all_test_predictions = {**test_predictions, **ensemble_test}
    all_test_predictions[calibrated_name] = _apply_calibrator(calibrator, all_test_predictions[winner_name])

    test_rows = []
    for validation_row in validation_rows:
        name = validation_row["model"]
        metrics = metric_row(y_test, all_test_predictions[name], frozen_thresholds[name])
        constraints = config["selection_constraints"]
        metrics["constraints_passed"] = bool(
            metrics["specificity"] >= float(constraints["minimum_specificity"])
            and metrics["auprc_lift"] >= float(constraints["minimum_auprc_lift"])
        )
        test_rows.append(
            {
                "dataset": SPECS[dataset].name,
                "target_definition": SPECS[dataset].target_definition,
                "model": name,
                "evaluation_split": "test_once_after_freeze",
                "threshold_source": "validation",
                "threshold_version": validation_row["threshold_version"],
                **metrics,
            }
        )

    ranked_test = sorted(
        test_rows,
        key=lambda row: (row["constraints_passed"], row["recall"], row["auprc"], row["specificity"]),
        reverse=True,
    )
    final_candidate_test = next(row for row in test_rows if row["model"] == final_candidate_name)
    age_group_rows = _age_group_metrics(dataset, test, y_test, all_test_predictions, frozen_thresholds)
    artifact = {
        "base_models": fitted_models,
        "base_model_order": names,
        "blend_weights": blend_weights,
        "stacker": stacker,
        "calibrator": calibrator,
        "validation_winner": winner_name,
        "final_candidate": final_candidate_name,
        "thresholds": frozen_thresholds,
        "threshold_versions": {row["model"]: row["threshold_version"] for row in validation_rows},
        "feature_columns": feature_columns,
        "feature_schema_version": dataset_config["feature_schema_version"],
        "model_version": dataset_config["model_version"],
    }
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / f"{dataset_config['model_version']}.joblib"
    joblib.dump(artifact, model_path)

    for rows, filename in (
        (search_rows, f"{dataset}_oof_search.csv"),
        (validation_rows, f"{dataset}_validation_leaderboard.csv"),
        (ranked_test, f"{dataset}_test_leaderboard.csv"),
        (age_group_rows, f"{dataset}_age_group_test_metrics.csv"),
    ):
        pd.DataFrame(rows).to_csv(output_dir / filename, index=False, encoding="utf-8-sig")

    return {
        "dataset": SPECS[dataset].name,
        "source_file": path.name,
        "source_sha256": _sha256_file(path),
        "target_definition": SPECS[dataset].target_definition,
        "target_type": dataset_config["target_type"],
        "model_version": dataset_config["model_version"],
        "feature_schema_version": dataset_config["feature_schema_version"],
        "features": feature_columns,
        "split_summary": {
            name: {
                "n": len(split),
                "positive_n": int(split["_target"].sum()),
                "positive_rate": float(split["_target"].mean()),
            }
            for name, split in splits.items()
        },
        "validation_winner": winner_name,
        "calibrated_variant": calibrated_name,
        "selection_source": "validation",
        "final_candidate_validation": final_validation_winner,
        "final_candidate_test": final_candidate_test,
        "blend_weights": blend_weights,
        "local_model_path": str(model_path),
        "promotion_status": "candidate_internal_not_for_personal_probability_display",
    }


def run_experiment(
    klosa_path: Path,
    knhanes_path: Path,
    config_path: Path,
    output_dir: Path,
    model_dir: Path,
) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    manifests = [
        run_dataset("klosa", klosa_path, config, output_dir, model_dir),
        run_dataset("knhanes", knhanes_path, config, output_dir, model_dir),
    ]
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(
            {
                "experiment_id": config["experiment_id"],
                "seed": config["seed"],
                "selection_order": ["constraints_passed", "recall", "auprc", "specificity"],
                "selection_constraints": config["selection_constraints"],
                "test_policy": "Test evaluated once after hyperparameters, weights, calibration and thresholds were frozen.",
                "cross_dataset_warning": "KLoSA future incidence and KNHANES current screening scores are not comparable.",
                "redis_role": "Async inference queue, job status and result cache only; not a model performance factor.",
                "datasets": manifests,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "inference_contract.json").write_text(
        json.dumps(
            {
                "request": {
                    "job_type": "model_inference",
                    "disease_type": "diabetes",
                    "dataset_model": "klosa|knhanes",
                    "model_version": "required",
                    "feature_schema_version": "required",
                    "threshold_version": "required",
                    "features": "object keyed by the exact feature schema",
                },
                "prediction_job": {
                    "status": "pending|running|done|failed",
                    "prediction_id": "set only after successful inference",
                },
                "prediction": {
                    "risk_score_internal": "0..1; internal candidate output, not a validated personal probability",
                    "risk_category": "low|moderate|high only after a reviewed mapping is approved",
                    "model_version": "echoed",
                    "feature_schema_version": "echoed",
                    "threshold_version": "echoed",
                    "disclaimer": "진단·처방이 아닌 내부 위험 선별 후보 결과",
                },
                "risk_factor": {
                    "status": "not_implemented_in_this_experiment",
                    "requirement": "Derive only from a validated explanation method and expose source feature metadata.",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--klosa", type=Path, required=True)
    parser.add_argument("--knhanes", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/recall_ensemble.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/sp2_recall_ensemble"))
    parser.add_argument("--model-dir", type=Path, default=Path("models/candidate/sp2_recall_ensemble"))
    args = parser.parse_args()
    run_experiment(args.klosa, args.knhanes, args.config, args.output_dir, args.model_dir)


if __name__ == "__main__":
    main()
