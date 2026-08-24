"""Compare class-weight variants for the top five R/S-balanced candidates."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_worker.ml.build_klosa_diabetes_cohort import TARGET
from ai_worker.ml.build_klosa_diabetes_mental_rhythm_cohort import (
    MENTAL_RHYTHM_CATEGORICAL_FEATURES,
    MENTAL_RHYTHM_EXTENDED_FEATURES,
    MENTAL_RHYTHM_NUMERIC_FEATURES,
)
from ai_worker.ml.build_klosa_diabetes_physical_function_cohort import (
    PHYSICAL_FUNCTION_CATEGORICAL_FEATURES,
    PHYSICAL_FUNCTION_EXTENDED_FEATURES,
    PHYSICAL_FUNCTION_NUMERIC_FEATURES,
    build_physical_function_cohort,
)
from ai_worker.ml.build_klosa_diabetes_socioeconomic_cohort import (
    SOCIOECONOMIC_CATEGORICAL_FEATURES,
    SOCIOECONOMIC_EXTENDED_FEATURES,
    SOCIOECONOMIC_NUMERIC_FEATURES,
)
from ai_worker.ml.compare_klosa_thresholds import choose_threshold_for_recall
from ai_worker.ml.train_klosa_diabetes_extended_features import (
    make_extended_pipeline,
)
from ai_worker.ml.train_klosa_diabetes_pooled import split_grouped_cohort
from ai_worker.ml.train_klosa_diabetes_sample import assert_no_leakage, evaluate


@dataclass(frozen=True)
class Candidate:
    rank: int
    stage: int
    model_name: str
    features: list[str]
    numeric_features: list[str]
    categorical_features: list[str]


def top_balanced_candidates() -> list[Candidate]:
    socioeconomic_numeric = [*SOCIOECONOMIC_NUMERIC_FEATURES]
    socioeconomic_categorical = [*SOCIOECONOMIC_CATEGORICAL_FEATURES]
    mental_numeric = [
        *socioeconomic_numeric,
        *MENTAL_RHYTHM_NUMERIC_FEATURES,
    ]
    mental_categorical = [
        *socioeconomic_categorical,
        *MENTAL_RHYTHM_CATEGORICAL_FEATURES,
    ]
    physical_numeric = [
        *mental_numeric,
        *PHYSICAL_FUNCTION_NUMERIC_FEATURES,
    ]
    physical_categorical = [
        *mental_categorical,
        *PHYSICAL_FUNCTION_CATEGORICAL_FEATURES,
    ]
    return [
        Candidate(
            1,
            3,
            "random_forest",
            MENTAL_RHYTHM_EXTENDED_FEATURES,
            mental_numeric,
            mental_categorical,
        ),
        Candidate(
            2,
            4,
            "random_forest",
            PHYSICAL_FUNCTION_EXTENDED_FEATURES,
            physical_numeric,
            physical_categorical,
        ),
        Candidate(
            3,
            2,
            "random_forest",
            SOCIOECONOMIC_EXTENDED_FEATURES,
            socioeconomic_numeric,
            socioeconomic_categorical,
        ),
        Candidate(
            4,
            4,
            "xgboost",
            PHYSICAL_FUNCTION_EXTENDED_FEATURES,
            physical_numeric,
            physical_categorical,
        ),
        Candidate(
            5,
            4,
            "logistic_regression",
            PHYSICAL_FUNCTION_EXTENDED_FEATURES,
            physical_numeric,
            physical_categorical,
        ),
    ]


def weight_variants(
    model_name: str,
    positive_class_ratio: float,
) -> list[tuple[str, dict[str, Any]]]:
    if model_name == "random_forest":
        return [
            ("unweighted", {"classifier__class_weight": None}),
            ("balanced", {"classifier__class_weight": "balanced"}),
            (
                "balanced_subsample",
                {"classifier__class_weight": "balanced_subsample"},
            ),
        ]
    if model_name == "logistic_regression":
        return [
            ("unweighted", {"classifier__class_weight": None}),
            ("balanced", {"classifier__class_weight": "balanced"}),
        ]
    if model_name == "xgboost":
        return [
            ("unweighted", {"classifier__scale_pos_weight": 1.0}),
            (
                "balanced_ratio",
                {"classifier__scale_pos_weight": positive_class_ratio},
            ),
        ]
    raise ValueError(f"Unsupported model: {model_name}")


def preprocessing_contract(
    random_state: int = 42,
    minimum_validation_recall: float = 0.80,
) -> dict[str, Any]:
    """Return the fixed preprocessing and evaluation policy for reproduction."""

    return {
        "cohort": {
            "unit": "KLoSA person-period across wave transitions 1->2 through 9->10",
            "eligibility": "diabetes_status_t0=5 and diabetes_status_t1 in {1,5}",
            "target": TARGET,
            "feature_timepoint": "t0_only",
            "special_missing_values": "negative_numeric_codes_are_missing",
        },
        "feature_transforms_before_split": {
            "bmi": "weight_kg / (height_cm / 100)^2; height 120-220 cm; weight 25-250 kg",
            "household_income": "log1p(nonnegative_household_income)",
            "wellbeing_scores": "values_outside_0_to_100_are_missing",
            "physical_function": ("ADL 0-7; IADL 0-10; grip 1-80 kg; values outside ranges are missing"),
        },
        "split": {
            "unit": "pid",
            "ratio": "70/15/15",
            "stratification": "whether_pid_ever_has_event",
            "random_state": random_state,
            "pid_overlap": 0,
        },
        "pipeline_fit": "train_only",
        "numeric": {
            "imputation": "median_with_missing_indicator",
            "scaling": "StandardScaler_for_logistic_regression_only",
        },
        "categorical": {
            "imputation": "most_frequent",
            "encoding": "one_hot_handle_unknown_ignore",
        },
        "threshold": {
            "source": "validation_only",
            "minimum_recall": minimum_validation_recall,
            "policy": "maximize_specificity_subject_to_minimum_recall",
            "test_use": "reporting_only",
        },
        "probability_calibration": "none",
    }


def run_experiment(
    data_dir: Path,
    output_dir: Path,
    random_state: int = 42,
    minimum_validation_recall: float = 0.80,
) -> dict[str, Any]:
    cohort = build_physical_function_cohort(data_dir)
    train, validation, test = split_grouped_cohort(cohort, random_state)
    positives = int(train[TARGET].sum())
    negatives = int(len(train) - positives)
    positive_class_ratio = negatives / positives
    candidate_results = []
    for candidate in top_balanced_candidates():
        assert_no_leakage(candidate.features)
        variants = []
        for variant_name, parameters in weight_variants(
            candidate.model_name,
            positive_class_ratio,
        ):
            model = make_extended_pipeline(
                candidate.model_name,
                random_state,
                additional_numeric_features=candidate.numeric_features,
                additional_categorical_features=candidate.categorical_features,
            )
            model.set_params(**parameters)
            model.fit(train[candidate.features], train[TARGET])
            validation_probabilities = model.predict_proba(validation[candidate.features])[:, 1]
            test_probabilities = model.predict_proba(test[candidate.features])[:, 1]
            threshold = choose_threshold_for_recall(
                validation[TARGET],
                validation_probabilities,
                minimum_recall=minimum_validation_recall,
            )
            variants.append(
                {
                    "weight_variant": variant_name,
                    "parameters": parameters,
                    "threshold": threshold,
                    "validation": evaluate(
                        validation[TARGET],
                        validation_probabilities,
                        threshold,
                    ),
                    "test": evaluate(test[TARGET], test_probabilities, threshold),
                }
            )
        candidate_results.append(
            {
                "original_balanced_accuracy_rank": candidate.rank,
                "stage": candidate.stage,
                "model": candidate.model_name,
                "feature_count": len(candidate.features),
                "variants": variants,
            }
        )

    result = {
        "status": "research_class_weight_comparison_not_for_deployment",
        "comparison_policy": ("same_full_cohort_pid_split_and_validation_recall_0.80_threshold; test_reporting_only"),
        "random_state": random_state,
        "minimum_validation_recall": minimum_validation_recall,
        "preprocessing": preprocessing_contract(
            random_state,
            minimum_validation_recall,
        ),
        "train_class_counts": {
            "positive": positives,
            "negative": negatives,
            "negative_to_positive_ratio": positive_class_ratio,
        },
        "splits": {
            "train": len(train),
            "validation": len(validation),
            "test": len(test),
        },
        "candidates": candidate_results,
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
        default=Path("data/raw/klosa/20260413/extracted"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/klosa_top_balanced_model_weights"),
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
