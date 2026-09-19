"""Compare the base 8 features with a t0-comorbidity extended feature set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from src.ml.evaluation.compare_klosa_thresholds import choose_threshold_for_recall
from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.modeling.train_klosa_diabetes_sample import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    evaluate,
)
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET, WEB_MODEL_FEATURES
from src.ml.preprocessing.build_klosa_diabetes_extended_cohort import (
    COMORBIDITY_FEATURES,
    EXTENDED_MODEL_FEATURES,
    build_extended_cohort,
)

MODEL_NAMES = ["logistic_regression", "random_forest", "xgboost"]


def make_extended_pipeline(
    model_name: str,
    random_state: int = 42,
    additional_numeric_features: list[str] | None = None,
    additional_categorical_features: list[str] | None = None,
) -> Pipeline:
    numeric_steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median", add_indicator=True))]
    if model_name == "logistic_regression":
        numeric_steps.append(("scaler", StandardScaler()))
    numeric = Pipeline(numeric_steps)
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("one_hot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessing = ColumnTransformer(
        [
            (
                "numeric",
                numeric,
                [*NUMERIC_FEATURES, *(additional_numeric_features or [])],
            ),
            (
                "categorical",
                categorical,
                [
                    *CATEGORICAL_FEATURES,
                    *COMORBIDITY_FEATURES,
                    *(additional_categorical_features or []),
                ],
            ),
        ]
    )
    if model_name == "logistic_regression":
        classifier = LogisticRegression(
            class_weight=None,
            max_iter=2000,
            random_state=random_state,
        )
    elif model_name == "random_forest":
        classifier = RandomForestClassifier(
            n_estimators=500,
            max_depth=8,
            min_samples_leaf=20,
            max_features="sqrt",
            class_weight=None,
            n_jobs=-1,
            random_state=random_state,
        )
    elif model_name == "xgboost":
        classifier = XGBClassifier(
            n_estimators=400,
            max_depth=3,
            learning_rate=0.03,
            min_child_weight=20,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=5.0,
            scale_pos_weight=1.0,
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            n_jobs=-1,
            random_state=random_state,
        )
    else:
        raise ValueError(f"Unsupported model: {model_name}")
    return Pipeline([("preprocessing", preprocessing), ("classifier", classifier)])


def run_experiment(
    data_dir: Path,
    output_dir: Path,
    random_state: int = 42,
    minimum_validation_recall: float = 0.80,
) -> dict[str, Any]:
    cohort = build_extended_cohort(data_dir)
    train, validation, test = split_grouped_cohort(cohort, random_state)
    results = []
    for model_name in MODEL_NAMES:
        model = make_extended_pipeline(model_name, random_state)
        model.fit(train[EXTENDED_MODEL_FEATURES], train[TARGET])
        validation_probabilities = model.predict_proba(validation[EXTENDED_MODEL_FEATURES])[:, 1]
        test_probabilities = model.predict_proba(test[EXTENDED_MODEL_FEATURES])[:, 1]
        threshold = choose_threshold_for_recall(
            validation[TARGET],
            validation_probabilities,
            minimum_recall=minimum_validation_recall,
        )
        results.append(
            {
                "model": model_name,
                "feature_set": "base_8_plus_t0_comorbidities_8_v1",
                "feature_count": len(EXTENDED_MODEL_FEATURES),
                "threshold_selection": {
                    "dataset": "validation",
                    "minimum_recall": minimum_validation_recall,
                    "threshold": threshold,
                    "status": "research_only_not_operational",
                },
                "validation": evaluate(validation[TARGET], validation_probabilities, threshold),
                "test": evaluate(test[TARGET], test_probabilities, threshold),
            }
        )

    missing = {feature: float(cohort[feature].isna().mean()) for feature in COMORBIDITY_FEATURES}
    result = {
        "status": "research_feature_expansion_not_for_deployment",
        "comparison_policy": ("same_pid_split_and_fixed_model_settings; test_reporting_only"),
        "base_features": WEB_MODEL_FEATURES,
        "added_features": COMORBIDITY_FEATURES,
        "extended_features": EXTENDED_MODEL_FEATURES,
        "comorbidity_missing_rate": missing,
        "splits": {
            "train": len(train),
            "validation": len(validation),
            "test": len(test),
        },
        "results": results,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


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
        default=Path("experiments/diabetes_incidence/candidates/klosa_diabetes_extended_comorbidities"),
    )
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--minimum-validation-recall", type=float, default=0.80)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_experiment(
        args.data_dir,
        args.output_dir,
        args.random_state,
        args.minimum_validation_recall,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
