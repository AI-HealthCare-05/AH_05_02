"""Service-facing inference for the KNHANES current screening model.

This model screens for a current diabetes-related clinical signal among adults
without a reported diagnosis. It does not diagnose diabetes and its score must
not be combined with the separate KLoSA future-incidence model.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from src.ml.modeling.knhanes_current_screening import predict_artifact

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = REPOSITORY_ROOT / (
    "models/registry/diabetes_current_screening/candidates/knhanes-current-screening-v050.json"
)


class CurrentScreeningArtifactUnavailableError(RuntimeError):
    """Raised when the configured local model artifact is unavailable."""


class CurrentScreeningContractError(RuntimeError):
    """Raised when a manifest, payload, and artifact do not share one contract."""


@dataclass(frozen=True)
class LoadedCurrentScreeningModel:
    artifact: dict[str, Any]
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
        raise CurrentScreeningArtifactUnavailableError(f"model manifest is missing: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise CurrentScreeningContractError(f"invalid model manifest: {path}") from exc
    if manifest.get("model_key") != "diabetes_current_screening":
        raise CurrentScreeningContractError("manifest model_key must be diabetes_current_screening")
    if manifest.get("task_type") != "current_cross_sectional_screening":
        raise CurrentScreeningContractError("manifest task_type is not current screening")
    if not manifest.get("features"):
        raise CurrentScreeningContractError("manifest has no feature contract")
    return manifest


def _validate_artifact(artifact: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(artifact, dict):
        raise CurrentScreeningContractError("model artifact must be a mapping bundle")
    if artifact.get("model_key") not in {
        "diabetes_current_screening",
        "knhanes_current_diabetes_screening",  # compatibility with the reproduced v0.5 binary
    }:
        raise CurrentScreeningContractError("artifact model_key is invalid")
    for key in ("model_version", "feature_schema_version", "threshold_version"):
        if artifact.get(key) != manifest.get(key):
            raise CurrentScreeningContractError(f"artifact {key} does not match manifest")
    if tuple(artifact.get("features", ())) != tuple(manifest["features"]):
        raise CurrentScreeningContractError("artifact features do not match manifest")
    if abs(float(artifact.get("threshold", -1)) - float(manifest["threshold"])) > 1e-12:
        raise CurrentScreeningContractError("artifact threshold does not match manifest")
    return artifact


def load_current_screening_model(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    model_path: Path | None = None,
) -> LoadedCurrentScreeningModel:
    """Load a locally provisioned artifact and verify its immutable contract."""

    manifest = _load_manifest(manifest_path)
    if model_path is None:
        model_path = REPOSITORY_ROOT / manifest["artifact_local_path"]
    if not model_path.is_file():
        raise CurrentScreeningArtifactUnavailableError(
            f"current-screening artifact is missing; reproduce or provision it at {model_path}"
        )
    if _sha256(model_path) != manifest.get("artifact_sha256"):
        raise CurrentScreeningContractError("model artifact SHA-256 does not match manifest")
    try:
        artifact = joblib.load(model_path)
    except Exception as exc:  # joblib can surface multiple deserialization errors
        raise CurrentScreeningContractError("model artifact could not be deserialized") from exc
    return LoadedCurrentScreeningModel(artifact=_validate_artifact(artifact, manifest), manifest=manifest)


def predict_with_loaded_current_model(
    loaded: LoadedCurrentScreeningModel,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Run one record and return a diagnosis-safe current-screening response."""

    unknown = sorted(set(payload).difference(loaded.manifest["features"]))
    if unknown:
        raise CurrentScreeningContractError(f"unknown input fields: {unknown}")
    frame = pd.DataFrame([{name: payload.get(name) for name in loaded.manifest["features"]}])
    score = round(float(predict_artifact(loaded.artifact, frame)[0]), 12)
    threshold = float(loaded.manifest["threshold"])
    signal_detected = score >= threshold
    return {
        "disease_type": "diabetes",
        "prediction_type": "current_screening",
        "model_key": "diabetes_current_screening",
        "screening_signal_detected": signal_detected,
        "screening_result_label": "검사 권고" if signal_detected else "현재 위험 신호 낮음",
        "risk_score_internal": score,
        "model_version": loaded.manifest["model_version"],
        "feature_schema_version": loaded.manifest["feature_schema_version"],
        "threshold_version": loaded.manifest["threshold_version"],
        "output_status": "screening_not_diagnosis",
        "disclaimer": (
            "현재 당뇨 관련 위험 신호를 선별하는 건강교육용 결과이며 진단이 아닙니다. "
            "확인이 필요하면 의료기관에서 검사를 받으세요."
        ),
    }


def predict_current_diabetes_screening(
    payload: Mapping[str, Any],
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    model_path: Path | None = None,
) -> dict[str, Any]:
    """Load and run the registered current-screening model for one record."""

    loaded = load_current_screening_model(manifest_path=manifest_path, model_path=model_path)
    return predict_with_loaded_current_model(loaded, payload)
