import numpy as np
import pandas as pd

from src.ml.inference.model_explanations import (
    explain_by_missingness_perturbation,
    model_comparison_guidance,
)


def test_local_explanation_is_deterministic_and_never_claims_shap():
    frame = pd.DataFrame([{"age": 60.0, "bmi": 28.0}])

    def score(value):
        row = value.fillna({"age": 50.0, "bmi": 22.0}).iloc[0]
        return float(row.age / 100 + row.bmi / 100)

    first = explain_by_missingness_perturbation(frame, score)
    assert first == explain_by_missingness_perturbation(frame, score)
    assert first["method"] == "missingness_perturbation_v1"
    assert first["shap_claimed"] is False and first["display_allowed"] is False
    assert first["items"][0]["feature"] == "age"


def test_explanation_skips_nonfinite_perturbation():
    frame = pd.DataFrame([{"age": 60.0}])
    result = explain_by_missingness_perturbation(
        frame,
        lambda value: 0.2 if np.isfinite(value.iloc[0].age) else float("nan"),
    )
    assert result["items"] == []


def test_conflict_guidance_prioritizes_current_confirmation():
    result = model_comparison_guidance(current_signal=True, future_category="low", display_allowed=True)
    assert result["code"] == "CURRENT_SIGNAL_FUTURE_LOW"
    assert result["display_allowed"] is True
    assert "현재" in result["message"]


def test_missing_model_is_never_presented_as_low_risk():
    result = model_comparison_guidance(
        current_signal=False,
        future_category="low",
        results_available=(True, False),
        display_allowed=True,
    )
    assert result["code"] == "MODEL_RESULT_INCOMPLETE"
    assert result["display_allowed"] is False
    assert "낮은 위험" in result["message"]
