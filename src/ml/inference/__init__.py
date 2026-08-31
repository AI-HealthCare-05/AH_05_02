"""Synchronous, service-facing ML inference interfaces."""

from typing import Any

__all__ = [
    "ModelArtifactUnavailableError",
    "ModelContractError",
    "predict_diabetes_risk",
]


def __getattr__(name: str) -> Any:
    """Load the standard inference module lazily for clean module execution."""

    if name in __all__:
        from src.ml.inference import diabetes_standard

        return getattr(diabetes_standard, name)
    raise AttributeError(name)
