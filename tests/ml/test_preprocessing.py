from __future__ import annotations

import pandas as pd
import pytest

from src.ml.preprocessing.pipeline import (
    add_age_cohorts,
    assign_group_split,
    build_klosa_incident_targets,
    clean_with_registry,
    fit_preprocessing_state,
    transform_model_matrix,
    validate_cohort_coverage,
)
from src.ml.preprocessing.harmonize import harmonize_klosa_wide, harmonize_knhanes
from src.ml.preprocessing.official import (
    add_klosa_incident_targets,
    knhanes_diabetes_source,
    knhanes_hypertension_codes,
)


def test_cleaning_uses_only_variable_specific_missing_codes() -> None:
    raw = pd.DataFrame({"age_raw": [19, 99, 888], "glucose_raw": [88, 99, 888]})
    registry = pd.DataFrame(
        [
            {
                "canonical_name": "age",
                "source_column": "age_raw",
                "dtype": "integer",
                "missing_codes": "888",
                "valid_min": 19,
                "valid_max": 120,
                "review_status": "approved",
            },
            {
                "canonical_name": "glucose",
                "source_column": "glucose_raw",
                "dtype": "float",
                "missing_codes": "888",
                "valid_min": 20,
                "valid_max": 800,
                "review_status": "approved",
            },
        ]
    )
    cleaned, audit = clean_with_registry(raw, registry)
    assert cleaned["glucose"].tolist()[:2] == [88.0, 99.0]
    assert pd.isna(cleaned.loc[2, "age"])
    assert audit["missing_code_count"].sum() == 2


def test_unapproved_registry_is_blocked() -> None:
    raw = pd.DataFrame({"age_raw": [19]})
    registry = pd.DataFrame(
        [{
            "canonical_name": "age",
            "source_column": "age_raw",
            "dtype": "integer",
            "missing_codes": "",
            "valid_min": 19,
            "valid_max": 120,
            "review_status": "needs_codebook",
        }]
    )
    with pytest.raises(ValueError, match="approved"):
        clean_with_registry(raw, registry)


def test_nested_age_cohorts_and_redundancy_warning() -> None:
    data = pd.DataFrame({"age": [45, 50, 65, 80]})
    result = add_age_cohorts(data)
    assert result["cohort_19_plus"].sum() == 4
    assert result["cohort_40_plus"].sum() == 4
    assert result["cohort_65_plus"].sum() == 2
    report = validate_cohort_coverage(result, dataset="KLoSA")
    assert bool(report.loc[1, "same_as_previous_cohort"])


def test_group_split_never_splits_one_person() -> None:
    data = pd.DataFrame({"pid": [1, 1, 2, 2, 3, 3], "wave": [1, 2, 1, 2, 1, 2]})
    split = assign_group_split(data, group_column="pid")
    assert pd.DataFrame({"pid": data["pid"], "split": split}).groupby("pid")["split"].nunique().max() == 1


def test_klosa_incident_target_uses_next_wave_only() -> None:
    data = pd.DataFrame(
        {
            "pid": [1, 1, 1, 2, 2],
            "wave": [1, 2, 3, 1, 2],
            "hypertension_dx": [0, 1, 1, 1, 1],
            "diabetes_dx": [0, 0, 1, 0, 0],
        }
    )
    result = build_klosa_incident_targets(data, person_column="pid", wave_column="wave")
    assert result.loc[0, "target_hypertension_dx_incident_next_wave"] == 1
    assert pd.isna(result.loc[1, "target_hypertension_dx_incident_next_wave"])
    assert result.loc[1, "target_diabetes_dx_incident_next_wave"] == 1


def test_imputation_state_is_fitted_from_train_only() -> None:
    train = pd.DataFrame({"x": [1.0, None, 3.0], "sex": ["M", None, "M"]})
    test = pd.DataFrame({"x": [1000.0, None], "sex": ["F", None]})
    state = fit_preprocessing_state(train, numeric_columns=["x"], categorical_columns=["sex"])
    transformed = transform_model_matrix(test, state)
    assert state.numeric_medians["x"] == 2.0
    assert transformed.loc[1, "x"] == 2.0
    assert not any(column.endswith("_F") for column in transformed.columns)


def test_knhanes_harmonization_blocks_conflicting_aliases() -> None:
    raw = pd.DataFrame({"HE_BMI": [22.0, 23.0], "HE_bmi": [22.0, 99.0]})
    registry = pd.DataFrame(
        [{
            "dataset": "KNHANES",
            "canonical_name": "bmi",
            "source_columns_all": "HE_BMI | HE_bmi",
            "review_status": "approved",
        }]
    )
    with pytest.raises(ValueError, match="값 충돌"):
        harmonize_knhanes(raw, registry, survey_year=2024, source_file="sample.sav")


def test_klosa_wide_is_reshaped_by_wave() -> None:
    raw = pd.DataFrame(
        {"pid": [1, 2], "w01A002_age": [50, 60], "w02A002_age": [52, 62]}
    )
    registry = pd.DataFrame(
        [{
            "dataset": "KLoSA",
            "canonical_name": "age",
            "source_columns_all": "w01A002_age | w02A002_age",
            "review_status": "approved",
        }]
    )
    result, _ = harmonize_klosa_wide(
        raw,
        registry,
        person_column="pid",
        wave_year_map={1: 2006, 2: 2008},
    )
    assert len(result) == 4
    assert result.loc[result["survey_wave"] == 2, "age"].tolist() == [52, 62]


def test_official_knhanes_target_definitions_change_at_documented_years() -> None:
    assert knhanes_hypertension_codes(2021) == ((1, 2, 3), 3)
    assert knhanes_hypertension_codes(2022) == ((1, 2, 3, 4), 4)
    assert knhanes_diabetes_source(2018) == "HE_DM"
    assert knhanes_diabetes_source(2019) == "HE_DM_HbA1c"


def test_official_klosa_target_requires_clean_history_and_adjacent_wave() -> None:
    frame = pd.DataFrame({
        "participant_id": ["clean", "clean", "prior", "prior", "gap", "gap", "missing", "missing"],
        "survey_wave": [1, 2, 1, 2, 1, 3, 1, 2],
        "source_file": ["a"] * 8,
        "age": [50] * 8,
        "hypertension_event": [0, 1, 1, 0, 0, 1, pd.NA, 1],
        "diabetes_event": [0, 0, 0, 0, 0, 1, 0, 0],
    })
    result = add_klosa_incident_targets(frame)
    clean = result.query("participant_id == 'clean' and survey_wave == 1").iloc[0]
    prior = result.query("participant_id == 'prior' and survey_wave == 1").iloc[0]
    gap = result.query("participant_id == 'gap' and survey_wave == 1").iloc[0]
    missing = result.query("participant_id == 'missing' and survey_wave == 1").iloc[0]
    assert clean["target_hypertension_incident_next_wave"] == 1
    assert pd.isna(prior["target_hypertension_incident_next_wave"])
    assert pd.isna(gap["target_hypertension_incident_next_wave"])
    assert pd.isna(missing["target_hypertension_incident_next_wave"])
