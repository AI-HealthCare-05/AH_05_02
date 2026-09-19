from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ml.baseline.age_baseline import (  # noqa: E402
    _metric_row,
    age_group,
    deterministic_stratified_sample,
    harmonize_row,
)


@pytest.mark.parametrize(
    ("age", "expected"),
    [(19, "19-44"), (44, "19-44"), (45, "45-64"), (64, "45-64"), (65, "65+"), (105, "65+")],
)
def test_age_group_boundaries(age: int, expected: str) -> None:
    assert age_group(age) == expected


def test_harmonize_source_specific_sex_and_activity() -> None:
    klosa = harmonize_row(
        "klosa",
        {
            "participant_id": "p1",
            "survey_wave": "1",
            "split": "train",
            "target_diabetes_incident_next_wave": "1",
            "age": "70",
            "sex": "5",
            "bmi": "24.5",
            "current_smoker": "0",
            "regular_exercise": "1",
        },
    )
    knhanes = harmonize_row(
        "knhanes",
        {
            "record_key": "r1",
            "split": "train",
            "target_diabetes_clinical": "0",
            "age": "35",
            "sex": "2",
            "bmi": "22.1",
            "current_smoker": "1",
            "aerobic_activity": "0",
        },
    )
    assert klosa["features"] == [70.0, 1.0, 24.5, 0.0, 1.0]
    assert knhanes["features"] == [35.0, 1.0, 22.1, 1.0, 0.0]


def test_stratified_sample_is_reproducible_and_retains_strata() -> None:
    rows = [
        {
            "row_id": str(index),
            "age_group": "19-44" if index < 10 else "65+",
            "target": index % 2,
        }
        for index in range(20)
    ]
    first = deterministic_stratified_sample(rows, limit=8, seed=7, dataset="knhanes", split="train")
    second = deterministic_stratified_sample(rows, limit=8, seed=7, dataset="knhanes", split="train")
    assert [row["row_id"] for row in first] == [row["row_id"] for row in second]
    assert {(row["age_group"], row["target"]) for row in first} == {
        ("19-44", 0),
        ("19-44", 1),
        ("65+", 0),
        ("65+", 1),
    }


def test_metric_row_reports_confusion_matrix_and_rates() -> None:
    pytest.importorskip("sklearn")
    metrics = _metric_row([0, 0, 1, 1], [0.1, 0.8, 0.4, 0.9], 0.5)
    assert (metrics["tn"], metrics["fp"], metrics["fn"], metrics["tp"]) == (1, 1, 1, 1)
    assert metrics["recall"] == pytest.approx(0.5)
    assert metrics["specificity"] == pytest.approx(0.5)
