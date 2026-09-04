"""Single-record inference for the research first-interval survival ensemble."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from src.ml.modeling.discrete_time_survival import BASE_FEATURES, MODEL_FEATURES
from src.ml.preprocessing.diabetes_api_features import (
    STANDARD_MODEL_FEATURES,
    DiabetesRiskInput,
    build_standard_model_frame,
    parse_diabetes_risk_input,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = REPOSITORY_ROOT / (
    "models/registry/diabetes_incidence/candidates/rf25-first-interval-survival-ensemble-v1.json"
)
EXPECTED_HORIZONS = tuple(range(2, 19, 2))


class EnsembleArtifactUnavailableError(RuntimeError):
    """Raised when the locally provisioned ensemble artifact is unavailable."""


class EnsembleContractError(RuntimeError):
    """Raised when the manifest and artifact contracts do not match."""


@dataclass(frozen=True)
class LoadedFirstIntervalEnsemble:
    bundle: dict[str, Any]
    manifest: dict[str, Any]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EnsembleArtifactUnavailableError(f"ensemble manifest is missing: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise EnsembleContractError(f"invalid ensemble manifest: {path}") from exc
    if manifest.get("model_key") != "diabetes_incidence_multihorizon":
        raise EnsembleContractError("ensemble model_key is invalid")
    if tuple(manifest.get("features", ())) != STANDARD_MODEL_FEATURES:
        raise EnsembleContractError("ensemble feature order is invalid")
    if tuple(manifest.get("horizon_years", ())) != EXPECTED_HORIZONS:
        raise EnsembleContractError("ensemble horizons are invalid")
    return manifest


def _validate_bundle(bundle: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    required = {
        "rf_model",
        "survival_model",
        "rf_calibrator",
        "logistic_calibrator",
        "meta_model",
    }
    if not isinstance(bundle, dict) or not required.issubset(bundle):
        raise EnsembleContractError("ensemble artifact is missing required components")
    if tuple(bundle.get("features", ())) != STANDARD_MODEL_FEATURES:
        raise EnsembleContractError("ensemble artifact feature order is invalid")
    if tuple(bundle.get("horizon_years", ())) != EXPECTED_HORIZONS:
        raise EnsembleContractError("ensemble artifact horizons are invalid")
    if bundle.get("feature_schema_version") != manifest.get("feature_schema_version"):
        raise EnsembleContractError("ensemble feature schema version does not match")
    artifact_thresholds = bundle.get("thresholds", {})
    manifest_thresholds = {str(years): manifest["horizons"][str(years)]["threshold"] for years in EXPECTED_HORIZONS}
    if artifact_thresholds != manifest_thresholds:
        raise EnsembleContractError("ensemble thresholds do not match manifest")
    if any(not np.isfinite(v) or not 0 <= v <= 1 for v in manifest_thresholds.values()):
        raise EnsembleContractError("invalid ensemble thresholds")
    return bundle


def load_first_interval_ensemble(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    model_path: Path | None = None,
) -> LoadedFirstIntervalEnsemble:
    """Load a checksum-pinned research artifact and validate its contract."""

    manifest = _load_manifest(manifest_path)
    if model_path is None:
        model_path = REPOSITORY_ROOT / manifest["artifact_local_path"]
    if not model_path.is_file():
        raise EnsembleArtifactUnavailableError(
            f"first-interval ensemble artifact is missing; provision it at: {model_path}"
        )
    if _sha256(model_path) != manifest.get("artifact_sha256"):
        raise EnsembleContractError("ensemble artifact SHA-256 does not match manifest")
    try:
        bundle = joblib.load(model_path)
    except Exception as exc:
        raise EnsembleContractError("ensemble artifact could not be deserialized") from exc
    return LoadedFirstIntervalEnsemble(
        bundle=_validate_bundle(bundle, manifest),
        manifest=manifest,
    )


def _logit(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped)).reshape(-1, 1)


def _calibrated(calibrator: Any, raw: np.ndarray) -> np.ndarray:
    return calibrator.predict_proba(_logit(raw))[:, 1]


def _first_interval_probability(bundle: dict[str, Any], frame: pd.DataFrame) -> np.ndarray:
    rf_raw = bundle["rf_model"].predict_proba(frame[list(STANDARD_MODEL_FEATURES)])[:, 1]
    interval_frame = frame[list(BASE_FEATURES)].copy()
    interval_frame["interval_index"] = 1
    logistic_raw = bundle["survival_model"].predict_proba(interval_frame[MODEL_FEATURES])[:, 1]
    rf = _calibrated(bundle["rf_calibrator"], rf_raw)
    logistic = _calibrated(bundle["logistic_calibrator"], logistic_raw)
    meta_input = np.column_stack((_logit(rf).ravel(), _logit(logistic).ravel()))
    return bundle["meta_model"].predict_proba(meta_input)[:, 1]


def _cumulative_curve(bundle: dict[str, Any], frame: pd.DataFrame) -> dict[int, float]:
    first = _first_interval_probability(bundle, frame)
    results = {2: float(first[0])}
    survival = 1 - first
    for interval_index in range(2, 10):
        interval_frame = frame[list(BASE_FEATURES)].copy()
        interval_frame["interval_index"] = interval_index
        hazard = bundle["survival_model"].predict_proba(interval_frame[MODEL_FEATURES])[:, 1]
        survival *= 1 - hazard
        results[interval_index * 2] = float(1 - survival[0])
    values = np.asarray(list(results.values()))
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise EnsembleContractError("invalid ensemble cumulative signal")
    if (np.diff(values) < -1e-12).any():
        raise EnsembleContractError("ensemble cumulative curve is not monotonic")
    return results


def predict_with_loaded_first_interval_ensemble(
    loaded: LoadedFirstIntervalEnsemble,
    user_input: DiabetesRiskInput,
    *,
    as_of_date: date,
) -> dict[str, Any]:
    """Return an internal research curve that must not be publicly displayed."""

    frame = build_standard_model_frame(user_input, as_of_date=as_of_date)
    current_age = int(frame.loc[0, "age"])
    curve = _cumulative_curve(loaded.bundle, frame)
    points = []
    for years, score in curve.items():
        threshold = float(loaded.manifest["horizons"][str(years)]["threshold"])
        points.append(
            {
                "horizon_years": years,
                "projected_age": current_age + years,
                "cumulative_risk_signal": round(score, 15),
                "cumulative_risk": None,
                "lower": None,
                "upper": None,
                "screening_signal_detected": score >= threshold,
                "future_incidence_decision_threshold": threshold,
            }
        )
    manifest = loaded.manifest
    return {
        "disease_type": "diabetes",
        "task_type": manifest["task_type"],
        "model_key": manifest["model_key"],
        "risk_curve_status": manifest["risk_curve_status"],
        "availability_reason": manifest["availability_reason"],
        "display_allowed": False,
        "as_of_date": as_of_date.isoformat(),
        "current_age": current_age,
        "curve": points,
        "model_version": manifest["model_version"],
        "feature_schema_version": manifest["feature_schema_version"],
        "input_schema_version": manifest["input_schema_version"],
        "threshold_scope": manifest["threshold_scope"],
        "threshold_version": manifest["threshold_version"],
        "calibration_version": manifest["calibration_version"],
        "output_definition_version": manifest["output_definition_version"],
        "output_status": "research_candidate_not_operationally_approved",
        "disclaimer": (
            "향후 당뇨병 의사진단 위험 선별을 위한 내부 연구 신호이며 확정 발병확률, "
            "진단 또는 처방이 아닙니다. 불확실성 검증 전에는 사용자에게 표시하지 않습니다."
        ),
    }


def predict_first_interval_survival_ensemble(
    payload: DiabetesRiskInput | Mapping[str, Any],
    *,
    as_of_date: date,
    manifest_path: Path = DEFAULT_MANIFEST,
    model_path: Path | None = None,
) -> dict[str, Any]:
    """Load and run the first-interval ensemble for one validated record."""

    user_input = payload if isinstance(payload, DiabetesRiskInput) else parse_diabetes_risk_input(dict(payload))
    loaded = load_first_interval_ensemble(
        manifest_path=manifest_path,
        model_path=model_path,
    )
    return predict_with_loaded_first_interval_ensemble(
        loaded,
        user_input,
        as_of_date=as_of_date,
    )
