"""Standard single-record inference boundary for the RF diabetes candidate.

Only load trusted joblib artifacts whose SHA-256 is pinned in the candidate
manifest. Results are research risk-screening information, not diagnosis or
treatment advice.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import joblib

from src.ml.evaluation.diabetes_risk_categories import categorize_risk_score
from src.ml.preprocessing.diabetes_api_features import (
    STANDARD_MODEL_FEATURES,
    DiabetesRiskInput,
    build_standard_model_frame,
    parse_diabetes_risk_input,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CANDIDATE_MANIFEST = REPOSITORY_ROOT / (
    "models/registry/diabetes_incidence/candidates/rf_25features_v001-20260825T045054926974Z.json"
)


class ModelArtifactUnavailableError(RuntimeError):
    """Raised when the configured local model artifact cannot be loaded safely."""


class ModelContractError(RuntimeError):
    """Raised when the manifest and model bundle do not share one contract."""


@dataclass(frozen=True)
class LoadedDiabetesModel:
    pipeline: Any
    manifest: dict[str, Any]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        while chunk := artifact.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _load_candidate_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ModelArtifactUnavailableError(f"model candidate manifest is missing: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelContractError(f"invalid model candidate manifest: {path}") from exc
    if not isinstance(manifest, dict):
        raise ModelContractError(f"invalid model candidate manifest: {path}")
    if tuple(manifest.get("features", ())) != STANDARD_MODEL_FEATURES:
        raise ModelContractError("candidate manifest feature order is invalid")
    required_metrics = {"recall", "specificity", "auroc", "auprc"}
    if not required_metrics.issubset(manifest.get("metrics", {})):
        raise ModelContractError("candidate manifest is missing required metrics")
    return manifest


def _resolve_model_path(
    manifest: dict[str, Any],
    configured_path: Path | None,
) -> Path:
    if configured_path is None:
        relative_path = manifest.get("artifact_local_path")
        if not isinstance(relative_path, str):
            raise ModelContractError("candidate manifest has no artifact_local_path")
        configured_path = REPOSITORY_ROOT / relative_path
    if not configured_path.is_file():
        raise ModelArtifactUnavailableError(
            "model artifact is missing; reproduce it with "
            f"`./scripts/ml-experiment.sh run {manifest.get('experiment_id', '<id>')}` "
            f"or provision the verified artifact at: {configured_path}"
        )
    return configured_path


def _validate_bundle(bundle: Any, manifest: dict[str, Any]) -> Any:
    if not isinstance(bundle, dict) or "pipeline" not in bundle:
        raise ModelContractError("model artifact is not a supported pipeline bundle")
    if tuple(bundle.get("features", ())) != STANDARD_MODEL_FEATURES:
        raise ModelContractError("model feature order does not match the API feature contract")
    if bundle.get("feature_schema_version") != manifest.get("feature_schema_version"):
        raise ModelContractError("model feature schema version does not match manifest")
    if abs(float(bundle.get("threshold", -1)) - manifest["thresholds"]["high"]) > 1e-12:
        raise ModelContractError("model decision threshold does not match manifest")
    return bundle["pipeline"]


def load_standard_model(
    *,
    manifest_path: Path = DEFAULT_CANDIDATE_MANIFEST,
    model_path: Path | None = None,
) -> LoadedDiabetesModel:
    """Load and contract-check the trusted candidate model."""

    manifest = _load_candidate_manifest(manifest_path)
    configured_path = _resolve_model_path(manifest, model_path)

    expected_sha256 = manifest.get("artifact_sha256")
    if not isinstance(expected_sha256, str) or _sha256(configured_path) != expected_sha256:
        raise ModelContractError("model artifact SHA-256 does not match candidate manifest")
    try:
        bundle = joblib.load(configured_path)
    except Exception as exc:  # joblib may surface several deserialization errors
        raise ModelContractError("model artifact could not be deserialized") from exc
    pipeline = _validate_bundle(bundle, manifest)
    return LoadedDiabetesModel(pipeline=pipeline, manifest=manifest)


def predict_with_loaded_model(
    loaded: LoadedDiabetesModel,
    user_input: DiabetesRiskInput,
    *,
    as_of_date: date,
) -> dict[str, Any]:
    """Run deterministic single-record risk-screening inference."""

    frame = build_standard_model_frame(user_input, as_of_date=as_of_date)
    score = float(loaded.pipeline.predict_proba(frame)[0, 1])
    thresholds = loaded.manifest["thresholds"]
    category = categorize_risk_score(
        score,
        moderate_threshold=float(thresholds["moderate"]),
        high_threshold=float(thresholds["high"]),
    )
    return {
        "disease_type": "diabetes",
        "task_type": "binary_incidence_risk_screening",
        "risk_score": score,
        "risk_category": category,
        "risk_category_label": {
            "low": "낮음",
            "moderate": "중간",
            "high": "높음",
        }[category],
        "model_version": loaded.manifest["model_version"],
        "feature_schema_version": loaded.manifest["feature_schema_version"],
        "input_schema_version": loaded.manifest["input_schema_version"],
        "threshold_version": loaded.manifest["threshold_version"],
        "decision_threshold": float(thresholds["high"]),
        "output_status": "research_screening_candidate_not_operationally_approved",
        "disclaimer": (
            "향후 신규 당뇨병 의사진단 위험을 선별하기 위한 연구용 점수이며 "
            "진단이나 처방이 아닙니다. 의료적 판단은 의료진과 상의하세요."
        ),
    }


def predict_diabetes_risk(
    payload: DiabetesRiskInput | Mapping[str, Any],
    *,
    as_of_date: date,
    manifest_path: Path = DEFAULT_CANDIDATE_MANIFEST,
    model_path: Path | None = None,
) -> dict[str, Any]:
    """Standard web-service callable for one diabetes risk-screening request."""

    user_input = payload if isinstance(payload, DiabetesRiskInput) else parse_diabetes_risk_input(dict(payload))
    loaded = load_standard_model(manifest_path=manifest_path, model_path=model_path)
    return predict_with_loaded_model(loaded, user_input, as_of_date=as_of_date)
