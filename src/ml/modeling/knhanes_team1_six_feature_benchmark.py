"""Reproduce the public Team 1 six-feature KNHANES method on Team 2's cohort.

This is a methodological benchmark, not a copy of another team's model or
score. It fixes Team 2's undiagnosed-adult target and temporal split, derives
the two activity features from the official raw KNHANES fields, and compares
Logistic Regression and Random Forest with OOF Platt calibration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pyreadstat
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.ml.modeling.knhanes_current_screening import (
    apply_platt,
    evaluation_row,
    fit_platt,
    predict_artifact,
    probability_metrics,
    select_threshold,
)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "configs" / "knhanes_team1_six_feature_benchmark.json"

ACTIVITY_COLUMNS = [
    "ID",
    "BE3_75",
    "BE3_76",
    "BE3_77",
    "BE3_78",
    "BE3_85",
    "BE3_86",
    "BE3_87",
    "BE3_88",
    "BE5_1",
]
FEATURES = [
    "age",
    "sex",
    "height_cm",
    "weight_kg",
    "leisure_aerobic_moderate_equivalent_min_week",
    "strength_days_week",
]
STRENGTH_CODE_TO_DAYS = {1: 0.0, 2: 1.0, 3: 2.0, 4: 3.0, 5: 4.0, 6: 5.0}


@dataclass(frozen=True)
class Candidate:
    name: str
    family: str
    estimator: Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def weekly_minutes(frame: pd.DataFrame, columns: tuple[str, str, str, str]) -> pd.Series:
    participation = pd.to_numeric(frame[columns[0]], errors="coerce")
    days = pd.to_numeric(frame[columns[1]], errors="coerce")
    hours = pd.to_numeric(frame[columns[2]], errors="coerce")
    minutes = pd.to_numeric(frame[columns[3]], errors="coerce")
    valid_yes = (
        participation.eq(1)
        & days.between(1, 7)
        & days.mod(1).eq(0)
        & hours.between(0, 23)
        & hours.mod(1).eq(0)
        & minutes.between(0, 59)
        & minutes.mod(1).eq(0)
    )
    result = pd.Series(np.nan, index=frame.index, dtype=float)
    result.loc[participation.eq(2)] = 0.0
    result.loc[valid_yes] = days.loc[valid_yes] * (60.0 * hours.loc[valid_yes] + minutes.loc[valid_yes])
    return result


def derive_activity(frame: pd.DataFrame) -> pd.DataFrame:
    leisure_vigorous = weekly_minutes(frame, ("BE3_75", "BE3_76", "BE3_77", "BE3_78"))
    leisure_moderate = weekly_minutes(frame, ("BE3_85", "BE3_86", "BE3_87", "BE3_88"))
    strength_raw = pd.to_numeric(frame["BE5_1"], errors="coerce")
    return pd.DataFrame(
        {
            "record_key": frame["record_key"],
            "leisure_aerobic_moderate_equivalent_min_week": leisure_moderate + 2.0 * leisure_vigorous,
            "strength_days_week": strength_raw.map(STRENGTH_CODE_TO_DAYS),
        }
    )


def load_activity(raw_root: Path, years: list[int]) -> pd.DataFrame:
    frames = []
    for year in years:
        paths = sorted((raw_root / str(year)).glob("*.sav"))
        if len(paths) != 1:
            raise FileNotFoundError(f"Expected one KNHANES SAV for {year}, found {len(paths)}")
        raw, _ = pyreadstat.read_sav(str(paths[0]), usecols=ACTIVITY_COLUMNS)
        raw["record_key"] = str(year) + ":" + raw["ID"].astype(str)
        frames.append(derive_activity(raw))
    activity = pd.concat(frames, ignore_index=True)
    if activity["record_key"].duplicated().any():
        raise ValueError("Raw KNHANES activity keys must be unique")
    return activity


def load_benchmark_frame(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str]]:
    cleaned_path = ROOT / config["cleaned_input"]
    raw_root = ROOT / config["raw_sav_root"]
    needed = [
        "record_key",
        "survey_year",
        "split",
        "survey_weight",
        "target_diabetes_clinical",
        "eligible_diabetes_undiagnosed",
        "cohort_19_plus",
        *config["team2_artifact_features"],
    ]
    cleaned = pd.read_csv(cleaned_path, usecols=list(dict.fromkeys(needed)))
    years = sorted(cleaned["survey_year"].unique().astype(int).tolist())
    activity = load_activity(raw_root, years)
    merged = cleaned.merge(activity, on="record_key", how="left", validate="one_to_one")
    eligible = (
        merged["eligible_diabetes_undiagnosed"] & merged["cohort_19_plus"] & merged["target_diabetes_clinical"].notna()
    )
    merged = merged.loc[eligible].copy()
    merged["target_diabetes_clinical"] = merged["target_diabetes_clinical"].astype(int)
    hashes = {"cleaned_sha256": sha256_file(cleaned_path)}
    return merged, hashes


def candidate_grid(seed: int, n_estimators: int) -> list[Candidate]:
    candidates = []
    for c_value in (0.01, 0.1, 1.0, 10.0, 100.0):
        for class_weight in (None, "balanced"):
            suffix = "none" if class_weight is None else "balanced"
            candidates.append(
                Candidate(
                    f"lr_c{c_value:g}_cw_{suffix}",
                    "logistic",
                    Pipeline(
                        [
                            ("scale", StandardScaler()),
                            (
                                "model",
                                LogisticRegression(
                                    C=c_value,
                                    class_weight=class_weight,
                                    max_iter=5000,
                                    random_state=seed,
                                ),
                            ),
                        ]
                    ),
                )
            )
    for depth in (4, 8, None):
        for leaf in (5, 20, 50):
            for max_features in ("sqrt", 1.0):
                for class_weight in (None, "balanced"):
                    suffix = "none" if class_weight is None else "balanced"
                    candidates.append(
                        Candidate(
                            f"rf_d{depth}_leaf{leaf}_mf{max_features}_cw_{suffix}",
                            "random_forest",
                            RandomForestClassifier(
                                n_estimators=n_estimators,
                                criterion="log_loss",
                                max_depth=depth,
                                min_samples_leaf=leaf,
                                max_features=max_features,
                                class_weight=class_weight,
                                bootstrap=True,
                                n_jobs=-1,
                                random_state=seed,
                            ),
                        )
                    )
    return candidates


def oof_predict(candidate: Candidate, train: pd.DataFrame) -> np.ndarray:
    y = train["target_diabetes_clinical"].to_numpy(dtype=int)
    groups = train["survey_year"].to_numpy()
    splitter = GroupKFold(n_splits=len(np.unique(groups)))
    predictions = np.zeros(len(train), dtype=float)
    for fit_index, holdout_index in splitter.split(train, y, groups):
        model = clone(candidate.estimator)
        model.fit(train.iloc[fit_index][FEATURES], y[fit_index])
        predictions[holdout_index] = model.predict_proba(train.iloc[holdout_index][FEATURES])[:, 1]
    return predictions


def choose_calibration(raw_oof: np.ndarray, y: np.ndarray) -> tuple[str, Any, np.ndarray]:
    identity_brier = probability_metrics(y, raw_oof)["brier"]
    calibrator = fit_platt(raw_oof, y, np.ones(len(y), dtype=float))
    calibrated = apply_platt(calibrator, raw_oof)
    calibrated_brier = probability_metrics(y, calibrated)["brier"]
    if calibrated_brier < identity_brier:
        return "platt", calibrator, calibrated
    return "identity", None, raw_oof


def calibrate(name: str, calibrator: Any, raw: np.ndarray) -> np.ndarray:
    return apply_platt(calibrator, raw) if name == "platt" else raw


def run(config: dict[str, Any]) -> None:
    output_dir = ROOT / config["output_dir"]
    model_dir = ROOT / config["model_output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    full, hashes = load_benchmark_frame(config)
    complete = full.dropna(subset=FEATURES).copy()
    splits = {
        name: complete.loc[complete["split"].eq(name)].reset_index(drop=True)
        for name in ("train", "validation", "test")
    }
    train = splits["train"]
    y_train = train["target_diabetes_clinical"].to_numpy(dtype=int)
    search_rows = []
    selected: dict[str, dict[str, Any]] = {}

    for candidate in candidate_grid(config["seed"], config["random_forest_n_estimators"]):
        raw_oof = oof_predict(candidate, train)
        calibration_name, calibrator, oof = choose_calibration(raw_oof, y_train)
        metrics = probability_metrics(y_train, oof)
        row = {
            "candidate": candidate.name,
            "family": candidate.family,
            "calibration": calibration_name,
            **metrics,
        }
        search_rows.append(row)
        current = selected.get(candidate.family)
        rank = (metrics["brier"], -metrics["auprc"], -metrics["auroc"])
        if current is None or rank < current["rank"]:
            selected[candidate.family] = {
                "candidate": candidate,
                "calibration_name": calibration_name,
                "calibrator": calibrator,
                "raw_oof": raw_oof,
                "rank": rank,
            }

    pd.DataFrame(search_rows).sort_values(["family", "brier", "auprc"], ascending=[True, True, False]).to_csv(
        output_dir / "oof_candidate_search.csv", index=False
    )

    result_rows = []
    artifacts = {}
    minimum_specificity = config["minimum_validation_specificity"]
    for family, chosen in selected.items():
        model = clone(chosen["candidate"].estimator).fit(train[FEATURES], y_train)
        validation = splits["validation"]
        y_validation = validation["target_diabetes_clinical"].to_numpy(dtype=int)
        validation_raw = model.predict_proba(validation[FEATURES])[:, 1]
        validation_probability = calibrate(chosen["calibration_name"], chosen["calibrator"], validation_raw)
        threshold, _ = select_threshold(y_validation, validation_probability, minimum_specificity)
        for split_name in ("validation", "test"):
            frame = splits[split_name]
            y = frame["target_diabetes_clinical"].to_numpy(dtype=int)
            raw = model.predict_proba(frame[FEATURES])[:, 1]
            probability = calibrate(chosen["calibration_name"], chosen["calibrator"], raw)
            result_rows.append(
                evaluation_row(
                    f"team1_six_feature_{family}",
                    split_name,
                    y,
                    probability,
                    threshold,
                    frame["survey_weight"].to_numpy(dtype=float),
                )
            )
        artifacts[family] = {
            "candidate": chosen["candidate"].name,
            "pipeline": model,
            "calibration": chosen["calibration_name"],
            "calibrator": chosen["calibrator"],
            "threshold": threshold,
        }
        if chosen["calibration_name"] != "platt":
            forced_calibrator = fit_platt(chosen["raw_oof"], y_train, np.ones(len(y_train), dtype=float))
            forced_validation_probability = apply_platt(forced_calibrator, validation_raw)
            forced_threshold, _ = select_threshold(y_validation, forced_validation_probability, minimum_specificity)
            for split_name in ("validation", "test"):
                frame = splits[split_name]
                y = frame["target_diabetes_clinical"].to_numpy(dtype=int)
                probability = apply_platt(forced_calibrator, model.predict_proba(frame[FEATURES])[:, 1])
                result_rows.append(
                    evaluation_row(
                        f"team1_six_feature_{family}_forced_platt",
                        split_name,
                        y,
                        probability,
                        forced_threshold,
                        frame["survey_weight"].to_numpy(dtype=float),
                    )
                )
            artifacts[f"{family}_forced_platt"] = {
                "candidate": chosen["candidate"].name,
                "pipeline": model,
                "calibration": "platt",
                "calibrator": forced_calibrator,
                "threshold": forced_threshold,
            }

    team2_artifact = joblib.load(ROOT / config["team2_artifact"])
    validation = splits["validation"]
    test = splits["test"]
    team2_validation_probability = predict_artifact(team2_artifact, validation)
    team2_threshold, _ = select_threshold(
        validation["target_diabetes_clinical"].to_numpy(dtype=int),
        team2_validation_probability,
        minimum_specificity,
    )
    for split_name, frame in (("validation", validation), ("test", test)):
        result_rows.append(
            evaluation_row(
                "team2_v061_same_complete_case",
                split_name,
                frame["target_diabetes_clinical"].to_numpy(dtype=int),
                predict_artifact(team2_artifact, frame),
                team2_threshold,
                frame["survey_weight"].to_numpy(dtype=float),
            )
        )

    results = pd.DataFrame(result_rows)
    results.to_csv(output_dir / "same_cohort_comparison.csv", index=False)
    counts = []
    for split_name in ("train", "validation", "test"):
        before = full.loc[full["split"].eq(split_name)]
        after = splits[split_name]
        counts.append(
            {
                "split": split_name,
                "eligible_before_complete_case": len(before),
                "six_feature_complete_case": len(after),
                "retention_rate": len(after) / len(before),
                "positive_n": int(after["target_diabetes_clinical"].sum()),
                "prevalence": float(after["target_diabetes_clinical"].mean()),
            }
        )
    pd.DataFrame(counts).to_csv(output_dir / "cohort_counts.csv", index=False)
    manifest = {
        "experiment_id": config["experiment_id"],
        "comparison_scope": "Team 1 public six-feature method on Team 2 undiagnosed cohort and temporal split",
        "not_exact_team1_score_reproduction": True,
        "reason": "Target/cohort and year roles are fixed to Team 2 for fair service comparison; nested 5x4 is replaced by survey-year OOF candidate evaluation.",
        "features": FEATURES,
        "activity_formula": "leisure moderate min/week + 2 * leisure vigorous min/week",
        "strength_mapping": STRENGTH_CODE_TO_DAYS,
        "complete_case": True,
        "imputation": False,
        "clipping": False,
        "selection": "minimum calibrated OOF Brier within family",
        "threshold": f"maximum validation Recall subject to Specificity >= {minimum_specificity}",
        "selected": {
            family: {
                "candidate": value["candidate"].name,
                "calibration": value["calibration_name"],
                "threshold": artifacts[family]["threshold"],
            }
            for family, value in selected.items()
        },
        "input_hashes": hashes,
        "raw_medical_data_committed": False,
        "disclaimer": "Current risk-signal screening only; not diagnosis or future incidence.",
    }
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    joblib.dump(
        {"features": FEATURES, "models": artifacts, "manifest": manifest},
        model_dir / "team1-six-feature-benchmark.joblib",
    )


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    run(config)


if __name__ == "__main__":
    main()
