import pytest

from app.core import config
from app.vision.food_vision import FoodVisionError, get_food_vision_provider
from app.vision.local_kfood import threshold_decision


def test_ratio_thresholds_require_both_stages() -> None:
    assert threshold_decision(0.60, 0.30, True) == "valid"
    assert threshold_decision(0.5999, 0.90, True) == "invalid_food_ratio"
    assert threshold_decision(0.90, 0.2999, True) == "invalid_vegetable_ratio"


def test_unreliable_result_never_completes() -> None:
    assert threshold_decision(0.90, 0.90, False) == "uncertain"


def test_invalid_numeric_result_is_uncertain() -> None:
    assert threshold_decision(float("nan"), 0.90, True) == "uncertain"
    assert threshold_decision(0.90, float("inf"), True) == "uncertain"


def test_threshold_contract_is_sixty_and_thirty_percent() -> None:
    assert config.FOOD_COVERAGE_PASS_THRESHOLD == 0.60
    assert config.VEGETABLE_RATIO_PASS_THRESHOLD == 0.30


def test_openai_provider_is_retained_but_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "FOOD_VISION_PROVIDER", "openai")

    with pytest.raises(FoodVisionError, match="비활성화"):
        get_food_vision_provider()
