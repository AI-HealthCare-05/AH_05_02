from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from src.ml.evaluation.diabetes_risk_categories import categorize_risk_score
from src.ml.inference.diabetes_standard import (
    LoadedDiabetesModel,
    ModelArtifactUnavailableError,
    load_standard_model,
    predict_with_loaded_model,
)
from src.ml.modeling.train_klosa_diabetes_sample import assert_no_leakage
from src.ml.preprocessing.build_klosa_diabetes_mental_rhythm_cohort import (
    MENTAL_RHYTHM_EXTENDED_FEATURES,
)
from src.ml.preprocessing.diabetes_api_features import (
    API_INPUT_CONTRACT,
    OPTIONAL_API_FIELDS,
    REQUIRED_API_FIELDS,
    STANDARD_MODEL_FEATURES,
    DiabetesRiskInput,
    build_standard_model_frame,
    parse_diabetes_risk_input,
)


class FixedScorePipeline:
    def __init__(self, score: float = 0.02) -> None:
        self.score = score

    def predict_proba(self, frame):
        assert tuple(frame.columns) == STANDARD_MODEL_FEATURES
        return np.array([[1.0 - self.score, self.score]])


def fixed_input(**overrides) -> DiabetesRiskInput:
    values = {
        "birth_date": date(1960, 4, 15),
        "sex": "female",
        "height_cm": 160.0,
        "weight_kg": 62.0,
        "smoking_status": "never",
        "current_drinker": False,
        "regular_exercise": True,
        "exercise_days_per_week": 3,
        "exercise_minutes": 40,
        "previously_diagnosed_diabetes": False,
    }
    values.update(overrides)
    return DiabetesRiskInput(**values)


def candidate_manifest() -> dict:
    return {
        "model_version": "rf-25features-v001-run-test",
        "feature_schema_version": "klosa_stage3_25features_v1",
        "input_schema_version": "diabetes-incidence-api-25features-v1",
        "threshold_version": "validation-recall-090-080-v1",
        "thresholds": {"moderate": 0.0167, "high": 0.0224},
    }


def test_api_contract_defines_required_optional_units_and_ranges() -> None:
    assert set(API_INPUT_CONTRACT) == {
        *REQUIRED_API_FIELDS,
        *OPTIONAL_API_FIELDS,
    }
    assert API_INPUT_CONTRACT["height_cm"]["unit"] == "cm"
    assert API_INPUT_CONTRACT["exercise_days_per_week"]["range"] == [0, 7]
    assert API_INPUT_CONTRACT["health_satisfaction_score"]["required"] is False
    assert API_INPUT_CONTRACT["hypertension_diagnosis"]["type"] == ("boolean|null")


def test_model_frame_has_training_order_and_safe_missing_values() -> None:
    frame = build_standard_model_frame(
        fixed_input(regular_exercise=False),
        as_of_date=date(2026, 8, 26),
    )

    assert tuple(frame.columns) == STANDARD_MODEL_FEATURES
    assert list(STANDARD_MODEL_FEATURES) == MENTAL_RHYTHM_EXTENDED_FEATURES
    assert frame.loc[0, "exercise_days_per_week"] == 0
    assert frame.loc[0, "exercise_minutes"] == 0
    assert np.isnan(frame.loc[0, "log_household_income"])
    assert np.isnan(frame.loc[0, "hypertension_diagnosis"])


def test_standard_features_pass_leakage_guard() -> None:
    assert_no_leakage(list(STANDARD_MODEL_FEATURES))


def test_fixed_input_inference_is_deterministic_and_versioned() -> None:
    loaded = LoadedDiabetesModel(
        pipeline=FixedScorePipeline(),
        manifest=candidate_manifest(),
    )

    first = predict_with_loaded_model(
        loaded,
        fixed_input(),
        as_of_date=date(2026, 8, 26),
    )
    second = predict_with_loaded_model(
        loaded,
        fixed_input(),
        as_of_date=date(2026, 8, 26),
    )

    assert first == second
    assert first["risk_score"] == pytest.approx(0.02)
    assert first["risk_category"] == "moderate"
    assert first["model_version"] == "rf-25features-v001-run-test"
    assert first["feature_schema_version"] == "klosa_stage3_25features_v1"
    assert first["threshold_version"] == "validation-recall-090-080-v1"
    assert "진단이나 처방이 아닙니다" in first["disclaimer"]


@pytest.mark.parametrize(
    ("score", "expected"),
    [(0.01, "low"), (0.02, "moderate"), (0.03, "high")],
)
def test_risk_categories(score: float, expected: str) -> None:
    assert (
        categorize_risk_score(
            score,
            moderate_threshold=0.0167,
            high_threshold=0.0224,
        )
        == expected
    )


def test_missing_model_file_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ModelArtifactUnavailableError, match="model artifact is missing"):
        load_standard_model(model_path=tmp_path / "missing-model.joblib")


def test_previously_diagnosed_user_is_rejected() -> None:
    with pytest.raises(ValueError, match="ineligible"):
        build_standard_model_frame(
            fixed_input(previously_diagnosed_diabetes=True),
            as_of_date=date(2026, 8, 26),
        )


def test_required_category_cannot_be_null() -> None:
    with pytest.raises(ValueError, match="sex is required"):
        build_standard_model_frame(
            fixed_input(sex=None),  # type: ignore[arg-type]
            as_of_date=date(2026, 8, 26),
        )


def test_json_input_parsing_accepts_iso_birth_date() -> None:
    parsed = parse_diabetes_risk_input(
        {
            **fixed_input().__dict__,
            "birth_date": "1960-04-15",
        }
    )

    assert parsed.birth_date == date(1960, 4, 15)


def test_candidate_manifest_records_metrics_contract_and_reproduction() -> None:
    path = Path("models/registry/diabetes_incidence/candidates/rf_25features_v001-20260825T045054926974Z.json")
    manifest = json.loads(path.read_text(encoding="utf-8"))

    assert manifest["features"] == list(STANDARD_MODEL_FEATURES)
    assert {"recall", "specificity", "auroc", "auprc"} <= set(manifest["metrics"])
    assert manifest["artifact_local_path"].startswith("outputs/ml/")
    assert manifest["artifact_git_policy"] == ("local_only_do_not_commit_model_binary")
    assert manifest["reproduce"]["run"] == ("./scripts/ml-experiment.sh run rf_25features_v001")
