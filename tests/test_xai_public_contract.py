from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ai_worker import handlers
from app.apis.v1 import prediction_routers


def _explanation(**overrides):
    value = {
        "status": "research_only",
        "display_allowed": False,
        "shap_claimed": True,
        "additivity_verified": True,
        "selection_status": "complete",
        "method": "treeshap_tree_path_dependent_v1",
        "explanation_version": "three-factor-shap-v1",
        "model_version": "rf25-tuned-education4-v2",
        "output_space": "risk_score",
        "additive_to_score": True,
        "reference_value": 0.02,
        "selection_policy": "elevated-2-caution-1-positive-otherwise-2-positive-1-caution-v1",
        "items": [{"feature": "bmi", "contribution": 0.01}],
    }
    value.update(overrides)
    return value


def test_independent_xai_gate_requires_explicit_approval(monkeypatch):
    monkeypatch.setattr(handlers.config, "XAI_DISPLAY_ALLOWED", False)
    assert handlers._release_explanation(_explanation(), operational=True)["display_allowed"] is False
    monkeypatch.setattr(handlers.config, "XAI_DISPLAY_ALLOWED", True)
    released = handlers._release_explanation(_explanation(), operational=True)
    assert released["status"] == "approved" and released["display_allowed"] is True
    assert handlers._release_explanation(_explanation(), operational=False)["display_allowed"] is False


@pytest.mark.asyncio
async def test_public_risk_factor_endpoint_returns_persisted_approved_contract(monkeypatch):
    prediction = SimpleNamespace(
        id=91,
        job_id="job-91",
        display_allowed=True,
        operational_model_activated=True,
        explanation_status="approved",
    )
    factor = SimpleNamespace(
        factor_name="bmi",
        display_name="BMI",
        impact_direction="increase",
        importance_score=0.01,
        display_order=1,
        is_modifiable=True,
        message="당뇨 위험을 높이는 방향으로 반영되었습니다.",
    )
    monkeypatch.setattr(prediction_routers.HealthRepository, "get_prediction", AsyncMock(return_value=prediction))
    monkeypatch.setattr(prediction_routers.HealthRepository, "risk_factors", AsyncMock(return_value=[factor]))
    monkeypatch.setattr(
        prediction_routers.PredictionJob,
        "get_or_none",
        AsyncMock(
            return_value=SimpleNamespace(result={"explanation": _explanation(status="approved", display_allowed=True)})
        ),
    )
    response = await prediction_routers.read_risk_factors(91, SimpleNamespace(id=7))
    data = response["data"]
    assert data["status"] == "approved"
    assert data["shap_claimed"] is True and data["display_allowed"] is True
    assert data["items"][0]["contribution"] == 0.01


@pytest.mark.asyncio
async def test_public_risk_factor_endpoint_fails_closed_without_approval(monkeypatch):
    prediction = SimpleNamespace(
        id=91,
        job_id="job-91",
        display_allowed=True,
        operational_model_activated=True,
        explanation_status="research_only",
    )
    monkeypatch.setattr(prediction_routers.HealthRepository, "get_prediction", AsyncMock(return_value=prediction))
    response = await prediction_routers.read_risk_factors(91, SimpleNamespace(id=7))
    data = response["data"]
    assert data["items"] == []
    assert data["shap_claimed"] is False and data["display_allowed"] is False
