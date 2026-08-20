"""KLoSA-based diabetes future-incidence binary inference adapter."""

from dataclasses import dataclass

import pandas as pd

from src.ml.model_registry import load_diabetes_model_bundle
from src.ml.preprocessing.diabetes_input import WEB_MODEL_FEATURES, DiabetesModelInput


@dataclass(frozen=True)
class DiabetesInferenceResult:
    score: float
    model_version: str
    target_definition_version: str
    input_schema_version: str
    feature_schema_version: str
    preprocessing_version: str
    calibration_version: str


def predict_single_user(model_input: DiabetesModelInput) -> DiabetesInferenceResult:
    """Run the real KLoSA baseline pipeline for one user.

    Returns an uncalibrated research probability only. Per the 2026-08-20
    모델 연동 Q&A SS6 (안 B 채택), the operational decision threshold has
    not been approved, so this adapter never derives a risk_category or
    predicted_class from the score — the service layer keeps those null.
    """
    required = set(WEB_MODEL_FEATURES)
    missing = required.difference(model_input)
    if missing:
        raise ValueError(f"Missing model inputs: {sorted(missing)}")

    bundle = load_diabetes_model_bundle()
    metadata = bundle["metadata"]

    model_frame = pd.DataFrame([model_input], columns=WEB_MODEL_FEATURES)
    score = float(bundle["pipeline"].predict_proba(model_frame)[0, 1])

    return DiabetesInferenceResult(
        score=score,
        model_version=metadata["model_version"],
        target_definition_version=metadata["target_definition_version"],
        input_schema_version=metadata["input_schema_version"],
        feature_schema_version=metadata["feature_set_version"],
        preprocessing_version=metadata["preprocessing_version"],
        calibration_version=metadata["calibration_version"],
    )
