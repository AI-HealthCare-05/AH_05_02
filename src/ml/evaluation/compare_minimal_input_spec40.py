"""Compare frozen eight-feature baselines and RF25 at Validation specificity 0.40."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.ml.evaluation.compare_klosa_thresholds import choose_threshold_for_specificity
from src.ml.inference.diabetes_standard import load_standard_model
from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.modeling.train_klosa_diabetes_sample import evaluate
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET
from src.ml.preprocessing.diabetes_api_features import STANDARD_MODEL_FEATURES


def main() -> None:  # noqa: C901 - keep threshold freezing before Test explicit
    """Use existing fitted preprocessing; never fit or select using Test."""
    cohort = pd.read_pickle("data/processed/official_v1/klosa_diabetes_incidence_stage3_25features_v1.pkl")
    train, validation, test = split_grouped_cohort(cohort, random_state=42)
    groups = [set(frame.pid) for frame in (train, validation, test)]
    assert not any(groups[a] & groups[b] for a, b in ((0, 1), (0, 2), (1, 2)))
    candidates = []
    for path in sorted(Path("experiments/diabetes_incidence/baselines").glob("*/metrics.json")):
        record = json.loads(path.read_text())
        artifact = Path(record["artifact"]["path"])
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == record["artifact"]["sha256"]
        bundle = joblib.load(artifact)
        candidates.append((path.parent.name, bundle["pipeline"], record["features"], False, record))
    loaded = load_standard_model()
    for masked in (False, True):
        name = "tuned_rf25_required_only" if masked else "tuned_rf25_observed"
        candidates.append((name, loaded.pipeline, list(STANDARD_MODEL_FEATURES), masked, None))
    selected = []
    for name, pipeline, features, masked, historical in candidates:
        pipeline.set_params(**{key: 1 for key in pipeline.get_params() if key.endswith("__n_jobs")})
        x_validation = validation[features].copy()
        x_test = test[features].copy()
        if masked:
            for column in STANDARD_MODEL_FEATURES[8:]:
                x_validation[column] = np.nan
                x_test[column] = np.nan
        p_validation = pipeline.predict_proba(x_validation)[:, 1]
        threshold = choose_threshold_for_specificity(validation[TARGET], p_validation, minimum_specificity=0.40)
        selected.append((name, pipeline, x_test, threshold, p_validation, historical))
    # All eight thresholds are frozen before Test evaluation begins.
    results = []
    for name, pipeline, x_test, threshold, p_validation, historical in selected:
        p_test = pipeline.predict_proba(x_test)[:, 1]
        if historical is not None:
            previous = evaluate(test[TARGET], p_test, historical["test"]["threshold"])
            # At a probability exactly on the old boundary, summation order can
            # change a single decision by machine precision. Record this below.
            delta = {
                key: previous["confusion_matrix"][key] - historical["test"]["confusion_matrix"][key]
                for key in ("tn", "fp", "fn", "tp")
            }
            assert max(abs(value) for value in delta.values()) <= 1, (name, delta)
            for key in ("auroc", "auprc"):
                assert np.isclose(previous[key], historical["test"][key], atol=1e-8, rtol=0)
        row = {"model": name, "threshold": threshold}
        if historical is not None:
            row["historical_confusion_delta_at_old_threshold"] = delta
        for split, frame, probabilities in (("validation", validation, p_validation), ("test", test, p_test)):
            metrics = evaluate(frame[TARGET], probabilities, threshold)
            cm = metrics["confusion_matrix"]
            metrics["precision"] = cm["tp"] / (cm["tp"] + cm["fp"])
            row[split] = metrics
        results.append(row)
    results.sort(key=lambda row: (row["validation"]["recall"], row["validation"]["specificity"]), reverse=True)
    report = {
        "purpose": "research_screening_sensitivity_analysis_not_operational_promotion",
        "policy": "Validation specificity >= 0.40; maximize Recall then Specificity; no refit",
        "test_caveat": "Previously inspected historical holdout, not new independent validation",
        "historical_baselines_reproduced": True,
        "results": results,
    }
    output = Path("outputs/ml/minimal_input_spec40_comparison")
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
