"""표준 공통 분할로 KLoSA 25변수 Random Forest를 재현한다."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from src.ml.evaluation.compare_klosa_thresholds import choose_threshold_for_recall
from src.ml.modeling.train_klosa_diabetes_extended_features import make_extended_pipeline
from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.modeling.train_klosa_diabetes_sample import assert_no_leakage, evaluate
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET
from src.ml.preprocessing.build_klosa_diabetes_mental_rhythm_cohort import (
    MENTAL_RHYTHM_CATEGORICAL_FEATURES,
    MENTAL_RHYTHM_EXTENDED_FEATURES,
    MENTAL_RHYTHM_NUMERIC_FEATURES,
    build_mental_rhythm_cohort,
)
from src.ml.preprocessing.build_klosa_diabetes_socioeconomic_cohort import (
    SOCIOECONOMIC_CATEGORICAL_FEATURES,
    SOCIOECONOMIC_NUMERIC_FEATURES,
)

RANDOM_STATE = 42
MINIMUM_VALIDATION_RECALL = 0.80
COHORT_FILENAME = "klosa_diabetes_incidence_stage3_25features_v1.pkl"
SOURCE_DATASET_PATH = Path("data/interim/source_extract/klosa/20260413")
FEATURES = list(MENTAL_RHYTHM_EXTENDED_FEATURES)


def _load_or_build_official_cohort(root: Path, dataset_dir: Path) -> pd.DataFrame:
    """Git 제외 official_v1에 행 단위 코호트를 만들거나 기존 사본을 읽는다."""

    cohort_path = dataset_dir / COHORT_FILENAME
    if cohort_path.is_file():
        cohort = pd.read_pickle(cohort_path)
    else:
        source_dir = root / SOURCE_DATASET_PATH
        if not source_dir.is_dir():
            raise FileNotFoundError(f"공통 코호트와 KLoSA 원자료가 모두 없습니다: {cohort_path}, {source_dir}")
        cohort = build_mental_rhythm_cohort(source_dir)
        dataset_dir.mkdir(parents=True, exist_ok=True)
        cohort.to_pickle(cohort_path)

    required = {"pid", TARGET, *FEATURES}
    missing = sorted(required.difference(cohort.columns))
    if missing:
        raise ValueError(f"official_v1 코호트에 필수 열이 없습니다: {missing}")
    if len(FEATURES) != 25 or len(set(FEATURES)) != 25:
        raise AssertionError("RF 25변수 스키마가 정확히 25개 고유 변수여야 합니다.")
    assert_no_leakage(FEATURES)
    return cohort[["pid", *FEATURES, TARGET]].copy()


def _assert_participant_split(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> None:
    pid_sets = [set(frame["pid"]) for frame in (train, validation, test)]
    if any(pid_sets[left] & pid_sets[right] for left, right in ((0, 1), (0, 2), (1, 2))):
        raise AssertionError("동일 PID가 둘 이상의 분할에 포함됐습니다.")


def _runner_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    confusion = raw["confusion_matrix"]
    return {
        "recall": raw["recall"],
        "specificity": raw["specificity"],
        "auroc": raw["auroc"],
        "auprc": raw["auprc"],
        "f1": raw["f1"],
        "brier_score": raw["brier_score"],
        "threshold": raw["threshold"],
        "confusion_matrix": {
            "true_positive": confusion["tp"],
            "false_positive": confusion["fp"],
            "true_negative": confusion["tn"],
            "false_negative": confusion["fn"],
        },
    }


def run_experiment(context: dict[str, Any]) -> dict[str, Any]:
    """Train에서만 전처리·학습하고 Validation 임계값으로 Test를 한 번 평가한다."""

    root = Path(context["root"])
    run_dir = Path(context["run_dir"])
    dataset_dir = Path(context["dataset_path"])
    manifest = context["manifest"]

    cohort = _load_or_build_official_cohort(root, dataset_dir)
    train, validation, test = split_grouped_cohort(cohort, random_state=RANDOM_STATE)
    _assert_participant_split(train, validation, test)

    model = make_extended_pipeline(
        "random_forest",
        random_state=RANDOM_STATE,
        additional_numeric_features=[
            *SOCIOECONOMIC_NUMERIC_FEATURES,
            *MENTAL_RHYTHM_NUMERIC_FEATURES,
        ],
        additional_categorical_features=[
            *SOCIOECONOMIC_CATEGORICAL_FEATURES,
            *MENTAL_RHYTHM_CATEGORICAL_FEATURES,
        ],
    )
    model.fit(train[FEATURES], train[TARGET])

    validation_probabilities = model.predict_proba(validation[FEATURES])[:, 1]
    threshold = choose_threshold_for_recall(
        validation[TARGET],
        validation_probabilities,
        minimum_recall=MINIMUM_VALIDATION_RECALL,
    )

    # Test는 모델·전처리·임계값을 모두 확정한 다음 마지막 보고에만 사용한다.
    test_probabilities = model.predict_proba(test[FEATURES])[:, 1]
    test_metrics = evaluate(test[TARGET], test_probabilities, threshold)

    artifact_name = "model.joblib"
    joblib.dump(
        {
            "pipeline": model,
            "threshold": threshold,
            "features": FEATURES,
            "dataset_version": manifest["dataset_version"],
            "split_version": manifest["split_version"],
            "feature_schema_version": manifest["feature_schema_version"],
            "purpose": "risk_screening_and_health_education_research_only",
        },
        run_dir / artifact_name,
    )

    split_summary = {
        name: {"rows": len(frame), "participants": int(frame["pid"].nunique())}
        for name, frame in (("train", train), ("validation", validation), ("test", test))
    }
    return {
        "metrics": _runner_metrics(test_metrics),
        "artifact": artifact_name,
        "notes": (
            "common-split rerun; historical metrics are reference-only and are documented "
            f"separately in README.md; splits={split_summary}"
        ),
    }
