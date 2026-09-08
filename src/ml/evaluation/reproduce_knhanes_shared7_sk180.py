"""Refit shared7 under sklearn 1.8.0; never deserialize a 1.9 model here."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from src.ml.evaluation.compare_knhanes_shared_inputs import EXPECTED_CSV, import_file, variants


def estimators():
    # Extracted with get_params() in the original 1.9 runtime. In both versions,
    # lbfgs + l1_ratio=0 implements L2; no fitted state is transferred.
    return {
        "logistic": LogisticRegression(
            C=10.0,
            class_weight="balanced",
            l1_ratio=0.0,
            max_iter=4000,
            n_jobs=4,
            random_state=20260831,
            solver="lbfgs",
            tol=0.0001,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=400,
            min_samples_leaf=40,
            class_weight="balanced_subsample",
            random_state=20260831,
            n_jobs=4,
        ),
    }


def main():  # noqa: C901 - fixed train/validation/test protocol kept explicit
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if version("scikit-learn") != "1.8.0":
        raise RuntimeError("This reproduction requires scikit-learn 1.8.0")
    if args.output_dir.exists():
        raise FileExistsError("Use a new output directory")
    handoff = args.handoff_dir.resolve()
    for line in (handoff / "SHA256SUMS.txt").read_text().splitlines():
        digest, relative = line.split(maxsplit=1)
        source = (handoff / relative).resolve()
        if not source.is_relative_to(handoff) or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError("Handoff integrity check failed")
    source = Path("data/processed/official_v1/knhanes_cleaned_2016_2024.csv")
    raw = source.read_bytes()
    if hashlib.sha256(raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest() != EXPECTED_CSV:
        raise ValueError("Dataset checksum mismatch")
    import_file("src.ml.modeling.transformers", handoff / "src/ml/modeling/transformers.py")
    trainer = import_file(
        "src.ml.modeling.knhanes_current_screening", handoff / "src/ml/modeling/knhanes_current_screening.py"
    )
    config = variants(json.loads((handoff / "configs/knhanes_current_screening_recall_v061.json").read_text()))[
        "shared7"
    ]
    cohort = trainer.load_cohort(source, config)
    splits = {
        name: cohort.loc[cohort.split.eq(name)].reset_index(drop=True) for name in ("train", "validation", "test")
    }
    expected = json.loads((handoff / "experiment_manifest.json").read_text())["split_summary"]
    for name, frame in splits.items():
        if len(frame) != expected[name]["n"] or int(frame[config["target"]].sum()) != expected[name]["positive_n"]:
            raise ValueError("Split counts mismatch")
    train, validation, test = [splits[name] for name in ("train", "validation", "test")]
    features = config["numeric_features"] + config["categorical_features"]
    weights = trainer.normalized_weights(train.survey_weight)
    software = {name: version(name) for name in ("scikit-learn", "numpy", "pandas", "joblib", "scipy")}
    software["python"] = platform.python_version()
    bundle = {
        "features": features,
        "pipelines": {},
        "calibrators": {},
        "ensemble_weights": {"logistic": 0.7, "random_forest": 0.3},
        "model_key": "diabetes_current_screening",
        "model_version": "knhanes-shared7-sk180-research-v1",
        "feature_schema_version": "knhanes-shared7-v1",
        "threshold_version": "shared7-sk180-validation-spec042-v1",
        "config": config,
        "software": software,
        "operational_model_activated": False,
    }
    params = {}
    for name, estimator in estimators().items():
        print(f"Training {name}: 5 train-year OOF folds and full Train", flush=True)
        params[name] = estimator.get_params()
        candidate = trainer.Candidate(name=name, family=name, estimator=estimator)
        oof = trainer.oof_predictions(candidate, train, config)
        bundle["calibrators"][name] = trainer.fit_platt(oof, train[config["target"]].to_numpy(), weights)
        pipeline = trainer.build_pipeline(config, estimator)
        trainer.fit_pipeline(pipeline, train[features], train[config["target"]].to_numpy(), weights)
        bundle["pipelines"][name] = pipeline
    vp = trainer.predict_artifact(bundle, validation)
    threshold, _ = trainer.select_threshold(validation[config["target"]].to_numpy(), vp, 0.42)
    bundle["threshold"] = threshold
    print(f"Validation threshold frozen: {threshold}", flush=True)
    metrics = {}
    for name, frame, probabilities in (
        ("validation", validation, vp),
        ("test", test, trainer.predict_artifact(bundle, test)),
    ):
        metrics[name] = trainer.evaluation_row(
            name,
            name,
            frame[config["target"]].to_numpy(),
            probabilities,
            threshold,
            trainer.normalized_weights(frame.survey_weight),
        )
    example = pd.DataFrame(
        [dict(age=56, height_cm=162.0, weight_kg=68.0, bmi=68 / 1.62**2, sex=2, current_smoker=0, education=np.nan)]
    )[features]
    repeated = [round(float(trainer.predict_artifact(bundle, example)[0]), 15) for _ in range(5)]
    if len(set(repeated)) != 1:
        raise AssertionError("Rounded fixed inference is not deterministic")
    args.output_dir.mkdir(parents=True)
    artifact = args.output_dir / "model.joblib"
    joblib.dump(bundle, artifact, compress=3)
    reloaded = joblib.load(artifact)
    if round(float(trainer.predict_artifact(reloaded, example)[0]), 15) != repeated[0]:
        raise AssertionError("Reloaded model does not reproduce fixed input")
    report = {
        "model_version": bundle["model_version"],
        "software": software,
        "parameters": params,
        "threshold": threshold,
        "metrics": metrics,
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "csv_sha256": hashlib.sha256(raw).hexdigest(),
        "split_summary": expected,
        "fixed_input_score": repeated[0],
        "fixed_input_education": "missing",
        "limits": [
            "research only",
            "historical Test repeatedly inspected",
            "Python and NumPy versions also differ from original runtime",
        ],
    }
    (args.output_dir / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
