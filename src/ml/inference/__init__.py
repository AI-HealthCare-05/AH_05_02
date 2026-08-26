"""Synchronous, service-facing ML inference interfaces."""

from src.ml.inference.diabetes_standard import (
    ModelArtifactUnavailableError,
    ModelContractError,
    predict_diabetes_risk,
)

__all__ = [
    "ModelArtifactUnavailableError",
    "ModelContractError",
    "predict_diabetes_risk",
]
