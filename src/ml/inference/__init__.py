"""Synchronous, service-facing ML inference interfaces."""

from typing import Any

__all__ = [
    "CurrentScreeningArtifactUnavailableError",
    "CurrentScreeningContractError",
    "ModelArtifactUnavailableError",
    "ModelContractError",
    "predict_current_diabetes_screening",
    "predict_diabetes_risk",
]


def __getattr__(name: str) -> Any:
    """Load the standard inference module lazily for clean module execution."""

    if name in {
        "CurrentScreeningArtifactUnavailableError",
        "CurrentScreeningContractError",
        "predict_current_diabetes_screening",
    }:
        from src.ml.inference import diabetes_current_screening

        return getattr(diabetes_current_screening, name)
    if name in {"ModelArtifactUnavailableError", "ModelContractError", "predict_diabetes_risk"}:
        from src.ml.inference import diabetes_standard

        return getattr(diabetes_standard, name)
    raise AttributeError(name)
