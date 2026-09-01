from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol

from app.core import config
from app.prediction.contracts import ACTIVE_MODEL
if TYPE_CHECKING:
    from src.ml.inference.diabetes_standard import LoadedDiabetesModel
    from src.ml.preprocessing.diabetes_api_features import DiabetesRiskInput

RiskCategory = Literal["low", "caution", "high"]


@dataclass(frozen=True)
class ProviderResult:
    internal_score: float | None
    risk_category: RiskCategory | None
    model_version: str
    feature_schema_version: str
    input_schema_version: str
    preprocessing_version: str
    target_definition_version: str
    calibration_version: str
    model_artifact_digest: str | None
    threshold_version: str
    decision_threshold: float | None
    promotion_status: str
    explanation_status: str = "not_available"


class PredictionProvider(Protocol):
    provider_kind: str

    async def predict(
        self,
        payload: DiabetesRiskInput | Mapping[str, Any],
        *,
        as_of_date: date,
    ) -> ProviderResult: ...


class DevelopmentPredictionProvider:
    """Exercises the async integration without fabricating a medical prediction."""

    provider_kind = "development"

    async def predict(
        self,
        payload: DiabetesRiskInput | Mapping[str, Any],
        *,
        as_of_date: date,
    ) -> ProviderResult:
        required = {
            "birth_date",
            "sex",
            "height_cm",
            "weight_kg",
            "smoking_status",
            "current_drinker",
            "regular_exercise",
            "exercise_days_per_week",
            "exercise_minutes",
            "previously_diagnosed_diabetes",
        }
        if not required.issubset(payload):
            raise ValueError("invalid diabetes risk input: required fields are missing")
        return ProviderResult(
            internal_score=None,
            risk_category=None,
            model_version=ACTIVE_MODEL.version,
            feature_schema_version=ACTIVE_MODEL.feature_schema_version,
            input_schema_version=ACTIVE_MODEL.input_schema_version,
            preprocessing_version=ACTIVE_MODEL.preprocessing_version,
            target_definition_version=ACTIVE_MODEL.target_definition_version,
            calibration_version=ACTIVE_MODEL.calibration_version,
            model_artifact_digest=ACTIVE_MODEL.model_artifact_digest,
            threshold_version=ACTIVE_MODEL.threshold_version,
            decision_threshold=None,
            promotion_status="development_only",
        )


class ArtifactPredictionProvider:
    provider_kind = "artifact"

    async def predict(
        self,
        payload: DiabetesRiskInput | Mapping[str, Any],
        *,
        as_of_date: date,
    ) -> ProviderResult:
        from src.ml.inference.diabetes_standard import predict_with_loaded_model
        from src.ml.preprocessing.diabetes_api_features import DiabetesRiskInput, parse_diabetes_risk_input

        user_input = payload if isinstance(payload, DiabetesRiskInput) else parse_diabetes_risk_input(dict(payload))
        loaded = await asyncio.to_thread(load_standard_model)
        output = await asyncio.to_thread(predict_with_loaded_model, loaded, user_input, as_of_date=as_of_date)
        return ProviderResult(
            internal_score=float(output["risk_score"]),
            risk_category=output["risk_category"],
            model_version=output["model_version"],
            feature_schema_version=output["feature_schema_version"],
            input_schema_version=output["input_schema_version"],
            preprocessing_version=loaded.manifest["preprocessing_version"],
            target_definition_version=ACTIVE_MODEL.target_definition_version,
            calibration_version=ACTIVE_MODEL.calibration_version,
            model_artifact_digest=loaded.manifest["artifact_sha256"],
            threshold_version=output["threshold_version"],
            decision_threshold=float(output["decision_threshold"]),
            promotion_status=loaded.manifest["promotion_status"],
        )


@lru_cache(maxsize=1)
def load_standard_model() -> LoadedDiabetesModel:
    from src.ml.inference.diabetes_standard import load_standard_model as load_candidate_model

    model_path = Path(config.MODEL_URI) if config.MODEL_URI else None
    return load_candidate_model(manifest_path=Path(config.MODEL_MANIFEST_URI), model_path=model_path)


def get_prediction_provider() -> PredictionProvider:
    if config.PREDICTION_PROVIDER == "development":
        return DevelopmentPredictionProvider()
    if config.PREDICTION_PROVIDER == "artifact":
        return ArtifactPredictionProvider()
    raise RuntimeError(f"지원하지 않는 PREDICTION_PROVIDER입니다: {config.PREDICTION_PROVIDER}")
