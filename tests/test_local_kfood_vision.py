import pytest

from app.core import config
from app.vision.food_vision import FoodVisionError, FoodVisionResult, get_food_vision_provider
from app.vision.local_kfood import threshold_decision
from app.vision.openai_vlm import needs_vlm, supplement_with_vlm


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


def _result(food: float, vegetable: float, reliable: bool = True) -> FoodVisionResult:
    return FoodVisionResult(
        provider_kind="local_kfood_cv",
        predicted_category="확인불가",
        contains_vegetable=False,
        vegetable_confidence=None,
        food_coverage_percent=food,
        vegetable_ratio_percent=vegetable,
        reliable=reliable,
        model_version="local-v1",
        decision_status="uncertain",
    )


def test_vlm_is_only_used_for_borderline_or_unreliable_results() -> None:
    assert needs_vlm(_result(55, 40))
    assert needs_vlm(_result(70, 25))
    assert needs_vlm(_result(70, 40, False))
    assert not needs_vlm(_result(70, 40))
    assert not needs_vlm(_result(40, 10))


@pytest.mark.asyncio
async def test_vlm_can_promote_borderline_visible_vegetables(monkeypatch: pytest.MonkeyPatch) -> None:
    async def verify(_self, _image):
        return {
            "is_meal_photo": True,
            "challenge_relevant": True,
            "vegetables_clearly_visible": True,
            "image_quality_adequate": True,
            "multiple_images_or_screen_capture": False,
            "uncertainty_reasons": [],
        }

    monkeypatch.setattr("app.vision.openai_vlm.OpenAIVegetableVerifier.verify", verify)
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")
    result = await supplement_with_vlm(_result(58, 28), b"image")
    assert result.decision_status == "valid"
    assert result.provider_kind == "local_kfood_openai_vlm"
