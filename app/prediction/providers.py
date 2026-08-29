from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal, Protocol

import joblib
import pandas as pd

from app.core import config
from app.prediction.contracts import ACTIVE_MODEL, STANDARD_MODEL_FEATURES, PredictionFeatures

RiskCategory = Literal["low", "moderate", "high"]
MODERATE_THRESHOLD = 0.016719708895315412
HIGH_THRESHOLD = 0.022410835788097848


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

    async def predict(self, features: PredictionFeatures) -> ProviderResult:
        bundle = await asyncio.to_thread(load_standard_model)
        score = await asyncio.to_thread(_predict_score, bundle, features.as_model_record())
        category: RiskCategory | None = None
        decision_threshold = None
        if ACTIVE_MODEL.promotion_status == "approved":
            category = "low" if score < MODERATE_THRESHOLD else "moderate" if score < HIGH_THRESHOLD else "high"
            decision_threshold = ACTIVE_MODEL.decision_threshold
        return ProviderResult(
            internal_score=score,
            risk_category=category,
            model_version=ACTIVE_MODEL.version,
            feature_schema_version=ACTIVE_MODEL.feature_schema_version,
            input_schema_version=ACTIVE_MODEL.input_schema_version,
            preprocessing_version=ACTIVE_MODEL.preprocessing_version,
            target_definition_version=ACTIVE_MODEL.target_definition_version,
            calibration_version=ACTIVE_MODEL.calibration_version,
            model_artifact_digest=ACTIVE_MODEL.model_artifact_digest,
            threshold_version=ACTIVE_MODEL.threshold_version,
            decision_threshold=decision_threshold,
            promotion_status=ACTIVE_MODEL.promotion_status,
        )


@lru_cache(maxsize=1)
def load_standard_model() -> object:
    if not config.MODEL_URI:
        raise RuntimeError("MODEL_ARTIFACT_UNAVAILABLE")
    path = Path(config.MODEL_URI)
    if not path.is_file():
        raise RuntimeError("MODEL_ARTIFACT_UNAVAILABLE")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if ACTIVE_MODEL.model_artifact_digest and digest != ACTIVE_MODEL.model_artifact_digest:
        raise RuntimeError("MODEL_DIGEST_MISMATCH")
    bundle = joblib.load(path)
    metadata = bundle.get("metadata", {}) if isinstance(bundle, dict) else {}
    feature_names = metadata.get("features") or metadata.get("feature_names")
    if feature_names != list(STANDARD_MODEL_FEATURES):
        raise RuntimeError("MODEL_CONTRACT_MISMATCH")
    for key, expected in {
        "model_version": ACTIVE_MODEL.version,
        "feature_schema_version": ACTIVE_MODEL.feature_schema_version,
        "input_schema_version": ACTIVE_MODEL.input_schema_version,
        "threshold_version": ACTIVE_MODEL.threshold_version,
    }.items():
        if metadata.get(key) != expected:
            raise RuntimeError("MODEL_CONTRACT_MISMATCH")
    return bundle


def _predict_score(bundle: object, record: dict[str, object]) -> float:
    model = bundle.get("pipeline") if isinstance(bundle, dict) else bundle
    if model is None or not hasattr(model, "predict_proba"):
        raise RuntimeError("MODEL_CONTRACT_MISMATCH")
    frame = pd.DataFrame([record], columns=STANDARD_MODEL_FEATURES)
    return float(model.predict_proba(frame)[0, 1])


def get_prediction_provider() -> PredictionProvider:
    if config.PREDICTION_PROVIDER == "development":
        return DevelopmentPredictionProvider()
    if config.PREDICTION_PROVIDER == "artifact":
        return ArtifactPredictionProvider()
    raise RuntimeError(f"지원하지 않는 PREDICTION_PROVIDER입니다: {config.PREDICTION_PROVIDER}")
