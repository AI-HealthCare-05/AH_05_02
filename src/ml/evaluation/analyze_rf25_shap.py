"""Generate privacy-safe TreeSHAP summaries for the frozen RF25 candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort

DEFAULT_MODEL = Path("models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib")
DEFAULT_DATA = Path("data/processed/official_v1/klosa_diabetes_incidence_stage3_25features_v1.pkl")


def _source_feature(transformed_name: str, features: list[str]) -> str:
    name = transformed_name.split("__", 1)[-1].removeprefix("missingindicator_")
    matches = [feature for feature in features if name == feature or name.startswith(f"{feature}_")]
    if not matches:
        raise ValueError(f"Cannot map transformed feature: {transformed_name}")
    return max(matches, key=len)


def _group_shap(values: np.ndarray, transformed_names: list[str], features: list[str]) -> pd.DataFrame:
    grouped = pd.DataFrame(index=np.arange(values.shape[0]))
    sources = [_source_feature(name, features) for name in transformed_names]
    for feature in features:
        positions = [index for index, source in enumerate(sources) if source == feature]
        grouped[feature] = values[:, positions].sum(axis=1)
    return grouped


def analyze(model_path: Path, data_path: Path, output_dir: Path, sample_size: int) -> None:
    bundle = joblib.load(model_path)
    pipeline = bundle["pipeline"]
    pipeline.set_params(**{key: 1 for key in pipeline.get_params() if key.endswith("__n_jobs")})
    features = list(bundle["features"])
    cohort = pd.read_pickle(data_path)
    _, _, test = split_grouped_cohort(cohort, random_state=42)
    sample = test.sample(n=min(sample_size, len(test)), random_state=42).reset_index(drop=True)

    preprocessing = pipeline.named_steps["preprocessing"]
    classifier = pipeline.named_steps["classifier"]
    transformed = preprocessing.transform(sample[features])
    transformed_names = preprocessing.get_feature_names_out().tolist()
    explanation = shap.TreeExplainer(classifier)(transformed)
    positive_values = explanation.values[:, :, 1]
    positive_base = explanation.base_values[:, 1]
    probabilities = classifier.predict_proba(transformed)[:, 1]
    if not np.allclose(positive_base + positive_values.sum(axis=1), probabilities, atol=1e-10):
        raise AssertionError("TreeSHAP additivity check failed")

    grouped = _group_shap(positive_values, transformed_names, features)
    global_summary = pd.DataFrame(
        {
            "feature": features,
            "mean_abs_shap": [grouped[column].abs().mean() for column in features],
            "mean_signed_shap": [grouped[column].mean() for column in features],
        }
    ).sort_values("mean_abs_shap", ascending=False, ignore_index=True)

    order = np.argsort(probabilities)
    selected = {
        "low": int(order[0]),
        "near_threshold": int(np.abs(probabilities - float(bundle["threshold"])).argmin()),
        "high": int(order[-1]),
    }
    local = []
    for label, row_index in selected.items():
        contributions = grouped.iloc[row_index].sort_values(key=abs, ascending=False)
        local.append(
            {
                "case": label,
                "risk_probability": float(probabilities[row_index]),
                "threshold": float(bundle["threshold"]),
                "base_probability": float(positive_base[row_index]),
                "top_contributions": [
                    {
                        "feature": feature,
                        "feature_value": None
                        if pd.isna(sample.at[row_index, feature])
                        else str(sample.at[row_index, feature]),
                        "shap_probability_contribution": float(value),
                    }
                    for feature, value in contributions.iloc[:8].items()
                ],
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    global_summary.to_csv(output_dir / "global_feature_importance.csv", index=False)
    (output_dir / "local_explanations.json").write_text(
        json.dumps(
            {
                "method": "TreeSHAP tree_path_dependent",
                "model_version": bundle.get("model_version"),
                "feature_schema_version": bundle.get("feature_schema_version"),
                "sample": {"split": "test", "size": len(sample), "random_state": 42},
                "additivity_verified": True,
                "interpretation_warning": (
                    "SHAP describes model behavior, not causality, diagnosis, or treatment advice."
                ),
                "cases": local,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    plot = global_summary.head(15).sort_values("mean_abs_shap")
    figure, axis = plt.subplots(figsize=(9, 6))
    axis.barh(plot["feature"], plot["mean_abs_shap"], color="#3478BF")
    axis.set_xlabel("Mean |TreeSHAP contribution| to diabetes-risk probability")
    axis.set_title("RF25 global TreeSHAP importance (fixed Test sample)")
    figure.tight_layout()
    figure.savefig(output_dir / "global_feature_importance.png", dpi=160)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=Path("outputs/ml/rf25_shap_analysis"))
    parser.add_argument("--sample-size", type=int, default=1000)
    args = parser.parse_args()
    analyze(args.model, args.data, args.output, args.sample_size)


if __name__ == "__main__":
    main()
