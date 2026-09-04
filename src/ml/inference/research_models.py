"""Opt-in research serving boundary; does not activate public models."""

from __future__ import annotations

import hashlib
import json
import warnings
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.exceptions import InconsistentVersionWarning

from src.ml.inference.diabetes_first_interval_survival_ensemble import (
    load_first_interval_ensemble,
    predict_with_loaded_first_interval_ensemble,
)
from src.ml.preprocessing.diabetes_api_features import build_standard_model_frame, parse_diabetes_risk_input

ROOT = Path(__file__).resolve().parents[3]
FEATURES = ("age", "height_cm", "weight_kg", "bmi", "sex", "current_smoker", "education")
SHARED_MANIFEST = ROOT / "models/registry/diabetes_current_screening/candidates/knhanes-shared7-sk180-v1.json"


class ResearchArtifactUnavailableError(RuntimeError):
    """Trusted local artifact has not been provisioned."""


class ResearchModelContractError(RuntimeError):
    """Runtime or artifact contract mismatch; never fabricate a result."""


def validated_input(payload: dict, as_of_date: date):
    user_input = parse_diabetes_risk_input(payload)
    if user_input.education_level not in (None, "code_1", "code_2", "code_3", "code_4"):
        raise ValueError("education_level must be code_1 to code_4 or null")
    frame = build_standard_model_frame(user_input, as_of_date=as_of_date)
    return user_input, frame


def shared7_frame(payload: dict, *, as_of_date: date) -> pd.DataFrame:
    user_input, frame = validated_input(payload, as_of_date)
    row = {
        "age": int(frame.iloc[0]["age"]),
        "height_cm": float(user_input.height_cm),
        "weight_kg": float(user_input.weight_kg),
        "bmi": float(frame.iloc[0]["bmi"]),
        "sex": 1 if user_input.sex == "male" else 2,
        "current_smoker": int(user_input.smoking_status == "current"),
        "education": np.nan if user_input.education_level is None else int(user_input.education_level[-1]),
    }
    return pd.DataFrame([row], columns=FEATURES)


def _runtime():
    if sklearn.__version__ != "1.8.0":
        raise ResearchModelContractError("Research models require scikit-learn 1.8.0")


@lru_cache(maxsize=2)
def load_shared7(model_path: str = "") -> tuple[dict, dict]:
    _runtime()
    manifest = json.loads(SHARED_MANIFEST.read_text())
    path = Path(model_path) if model_path else ROOT / manifest["artifact_local_path"]
    if not path.is_file():
        raise ResearchArtifactUnavailableError("Shared7 model is not provisioned")
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["artifact_sha256"]:
        raise ResearchModelContractError("Shared7 SHA-256 mismatch")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", InconsistentVersionWarning)
            bundle = joblib.load(path)
        for key in ("model_key", "model_version", "feature_schema_version", "threshold_version", "threshold"):
            if bundle[key] != manifest[key]:
                raise ValueError(f"Shared7 {key} mismatch")
        if tuple(bundle["features"]) != FEATURES or tuple(manifest["features"]) != FEATURES:
            raise ValueError("Shared7 feature order mismatch")
        if bundle["ensemble_weights"] != {"logistic": 0.7, "random_forest": 0.3}:
            raise ValueError("Shared7 weights mismatch")
    except Exception as exc:
        raise ResearchModelContractError("Invalid shared7 artifact") from exc
    # RF parallel reduction introduces tiny float jitter. Fixed serial serving
    # does not refit or change any tree and makes reduction order deterministic.
    bundle["pipelines"]["random_forest"]["model"].set_params(n_jobs=1)
    return bundle, manifest


@lru_cache(maxsize=2)
def load_ensemble(model_path: str = ""):
    _runtime()
    with warnings.catch_warnings():
        warnings.simplefilter("error", InconsistentVersionWarning)
        loaded = load_first_interval_ensemble(model_path=Path(model_path) if model_path else None)
    loaded.bundle["rf_model"]["classifier"].set_params(n_jobs=1)
    return loaded


def predict_shared7(payload: dict, *, as_of_date: date, model_path: str = "") -> dict[str, Any]:
    frame = shared7_frame(payload, as_of_date=as_of_date)
    bundle, manifest = load_shared7(model_path)
    probabilities = []
    for name, weight in bundle["ensemble_weights"].items():
        raw = np.clip(bundle["pipelines"][name].predict_proba(frame)[:, 1], 1e-6, 1 - 1e-6)
        logits = np.log(raw / (1 - raw)).reshape(-1, 1)
        probabilities.append(weight * bundle["calibrators"][name].predict_proba(logits)[:, 1])
    score = float(np.sum(probabilities, axis=0)[0])
    if not np.isfinite(score) or not 0 <= score <= 1:
        raise ResearchModelContractError("Invalid screening score")
    return {
        "model_key": manifest["model_key"],
        "model_version": manifest["model_version"],
        "input_schema_version": manifest["input_schema_version"],
        "feature_schema_version": manifest["feature_schema_version"],
        "threshold_version": manifest["threshold_version"],
        "threshold_scope": "current_screening",
        "screening_decision_threshold": manifest["threshold"],
        "risk_score_internal": round(score, 15),
        "screening_signal_detected": score >= manifest["threshold"],
        "artifact_sha256": manifest["artifact_sha256"],
        "as_of_date": as_of_date.isoformat(),
        "display_allowed": False,
        "promotion_status": "research_candidate_only",
        "output_status": "research_candidate_not_operationally_approved",
        "disclaimer": "현재 당뇨 관련 위험 선별 연구 신호이며 진단·처방 또는 미래 발병확률이 아닙니다.",
    }


def predict_research_model(model: str, payload: dict, *, as_of_date: date, model_path: str = "") -> dict:
    if model == "shared7":
        return predict_shared7(payload, as_of_date=as_of_date, model_path=model_path)
    if model == "first-interval":
        user_input, _ = validated_input(payload, as_of_date)
        loaded = load_ensemble(model_path)
        return predict_with_loaded_first_interval_ensemble(loaded, user_input, as_of_date=as_of_date)
    raise ValueError("Unknown research model")
