from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from app.core import config
from app.prediction.contracts import ACTIVE_MODEL, PredictionFeatures

RiskCategory = Literal["low", "caution", "high"]


@dataclass(frozen=True)
class ProviderResult:
    internal_score: float | None
    risk_category: RiskCategory | None
    model_version: str
    feature_schema_version: str
    threshold_version: str
    promotion_status: str
    explanation_status: str = "not_available"


class PredictionProvider(Protocol):
    provider_kind: str

    async def predict(self, features: PredictionFeatures) -> ProviderResult: ...


class DevelopmentPredictionProvider:
    """Exercises the async integration without fabricating a medical prediction."""

    provider_kind = "development"

    async def predict(self, features: PredictionFeatures) -> ProviderResult:
        # Contract validation is the only inference performed by this provider.
        features.as_model_record()
        return ProviderResult(
            internal_score=None,
            risk_category=None,
            model_version=ACTIVE_MODEL.version,
            feature_schema_version=ACTIVE_MODEL.feature_schema_version,
            threshold_version=ACTIVE_MODEL.threshold_version,
            promotion_status="development_only",
        )


class ArtifactPredictionProvider:
    provider_kind = "artifact"

    async def predict(self, features: PredictionFeatures) -> ProviderResult:
        raise RuntimeError(
            "검토된 모델 artifact provider가 아직 연결되지 않았습니다. "
            "PR #4 병합 후 모델 경로와 승인된 threshold version을 설정해 주세요."
        )


def get_prediction_provider() -> PredictionProvider:
    if config.PREDICTION_PROVIDER == "development":
        return DevelopmentPredictionProvider()
    if config.PREDICTION_PROVIDER == "artifact":
        return ArtifactPredictionProvider()
    raise RuntimeError(f"지원하지 않는 PREDICTION_PROVIDER입니다: {config.PREDICTION_PROVIDER}")
