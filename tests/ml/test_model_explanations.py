from src.ml.inference.model_explanations import model_comparison_guidance


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
