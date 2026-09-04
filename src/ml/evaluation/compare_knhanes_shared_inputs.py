"""Compare shared-input KNHANES candidates with the trusted v0.6.1 handoff."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.base import clone

CORE_NUMERIC = ["age", "height_cm", "weight_kg", "bmi"]
CORE_CATEGORICAL = ["sex", "current_smoker", "education"]
EXPECTED_CSV = "70c2e4a0d71e883a4181589bfb3042413f6f6e13104756b88d24e103e195ddfa"
EXPECTED_MODEL = "ffc6743849973676308703dd6bd5af0f8d557d5f45a8886e6660f86c81b85178"


def variants(config: dict, *, education_ablation: bool = False) -> dict:
    """Predefine features; no outcome-driven feature selection."""
    result = {}
    for name, waist, family in (
        ("shared7", False, False),
        ("shared7_waist", True, False),
        ("shared7_family", False, True),
        ("shared7_waist_family", True, True),
    ):
        candidate = copy.deepcopy(config)
        candidate["numeric_features"] = CORE_NUMERIC + (["waist_cm"] if waist else [])
        candidate["categorical_features"] = CORE_CATEGORICAL + (["diabetes_family_history"] if family else [])
        candidate["derived_numeric_features"] = config["derived_numeric_features"] if waist else []
        candidate["waist_estimator"]["enabled"] = waist
        result[name] = candidate
    if education_ablation:
        reduced = copy.deepcopy(result["shared7"])
        reduced["categorical_features"].remove("education")
        return {"shared7": result["shared7"], "shared6_no_education": reduced}
    return result


def import_file(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:  # noqa: C901 - explicit frozen protocol followed by Test evaluation
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--education-ablation", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    if args.output_dir.exists():
        raise FileExistsError("Use a new run directory; do not overwrite results")
    handoff = args.handoff_dir
    # Verify source integrity before import. The user supplied this trusted team package.
    for line in (handoff / "SHA256SUMS.txt").read_text().splitlines():
        digest, relative = line.split(maxsplit=1)
        assert hashlib.sha256((handoff / relative).read_bytes()).hexdigest() == digest
    assert hashlib.sha256((handoff / "model.joblib").read_bytes()).hexdigest() == EXPECTED_MODEL
    source = Path("data/processed/official_v1/knhanes_cleaned_2016_2024.csv")
    raw = source.read_bytes()
    normalized = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    assert hashlib.sha256(normalized).hexdigest() == EXPECTED_CSV
    import_file("src.ml.modeling.transformers", handoff / "src/ml/modeling/transformers.py")
    trainer = import_file(
        "src.ml.modeling.knhanes_current_screening", handoff / "src/ml/modeling/knhanes_current_screening.py"
    )
    config = json.loads((handoff / "configs/knhanes_current_screening_recall_v061.json").read_text())
    expected = json.loads((handoff / "experiment_manifest.json").read_text())
    original = joblib.load(handoff / "model.joblib")
    cohort = trainer.load_cohort(source, config)
    splits = {
        name: cohort.loc[cohort.split.eq(name)].reset_index(drop=True) for name in ("train", "validation", "test")
    }
    for name, frame in splits.items():
        assert len(frame) == expected["split_summary"][name]["n"]
        assert int(frame[config["target"]].sum()) == expected["split_summary"][name]["positive_n"]
    train, validation, test = [splits[name] for name in ("train", "validation", "test")]
    y_train = train[config["target"]].to_numpy()
    train_weights = trainer.normalized_weights(train.survey_weight)
    args.output_dir.mkdir(parents=True)
    pending = [("original22", original, config)]
    # Fixed original family hyperparameters and blend weights isolate feature changes.
    for name, candidate_config in variants(config, education_ablation=args.education_ablation).items():
        print(f"Training {name}", flush=True)
        trainer.validate_contract(candidate_config)
        features = candidate_config["numeric_features"] + candidate_config["categorical_features"]
        bundle = {
            "features": features,
            "pipelines": {},
            "calibrators": {},
            "ensemble_weights": original["ensemble_weights"],
            "model_version": f"knhanes-shared-input-{name}-research-v1",
            "config": candidate_config,
        }
        for family in original["ensemble_weights"]:
            estimator = clone(original["pipelines"][family]["model"])
            if "n_jobs" in estimator.get_params():
                estimator.set_params(n_jobs=4)
            candidate = trainer.Candidate(name=family, family=family, estimator=estimator)
            oof = trainer.oof_predictions(candidate, train, candidate_config)
            bundle["calibrators"][family] = trainer.fit_platt(oof, y_train, train_weights)
            pipeline = trainer.build_pipeline(candidate_config, estimator)
            trainer.fit_pipeline(pipeline, train[features], y_train, train_weights)
            bundle["pipelines"][family] = pipeline
        pending.append((name, bundle, candidate_config))
    selected = []
    for name, bundle, _candidate_config in pending:
        probabilities = trainer.predict_artifact(bundle, validation)
        threshold, _ = trainer.select_threshold(validation[config["target"]].to_numpy(), probabilities, 0.42)
        metrics = trainer.evaluation_row(
            name,
            "validation",
            validation[config["target"]].to_numpy(),
            probabilities,
            threshold,
            trainer.normalized_weights(validation.survey_weight),
        )
        if name == "original22":
            assert np.isclose(threshold, original["threshold"], rtol=0, atol=1e-12)
            for key in ("recall", "specificity", "auroc", "auprc"):
                assert np.isclose(metrics[key], expected["selected_validation"][key])
        else:
            bundle["threshold"] = threshold
            joblib.dump(bundle, args.output_dir / f"{name}.joblib", compress=3)
        selected.append((name, bundle, threshold, metrics))
    # Freeze all configurations and thresholds before any new Test evaluation.
    results = []
    for name, bundle, threshold, validation_metrics in selected:
        probabilities = trainer.predict_artifact(bundle, test)
        test_metrics = trainer.evaluation_row(
            name,
            "test",
            test[config["target"]].to_numpy(),
            probabilities,
            threshold,
            trainer.normalized_weights(test.survey_weight),
        )
        if name == "original22":
            for key in ("recall", "specificity", "auroc", "auprc"):
                assert np.isclose(test_metrics[key], expected["selected_test"][key])
        results.append(
            {
                "model": name,
                "features": bundle["features"],
                "threshold": threshold,
                "validation": validation_metrics,
                "test": test_metrics,
            }
        )
    results.sort(key=lambda row: (row["validation"]["recall"], row["validation"]["auprc"]), reverse=True)
    report = {
        "protocol": "Fixed v061 LR/RF hyperparameters and 0.7/0.3 blend; train-year OOF Platt; validation spec>=0.42",
        "csv_sha256": hashlib.sha256(raw).hexdigest(),
        "windows_normalized_csv_sha256": EXPECTED_CSV,
        "baseline_artifact_sha256": EXPECTED_MODEL,
        "limits": [
            "historical Test repeatedly inspected",
            "no operational approval",
            "official BMI retained; API-derived BMI equivalence not established",
            "no alcohol or exercise mapping assumed",
            "reduced model hyperparameters not retuned",
        ],
        "results": results,
    }
    (args.output_dir / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
