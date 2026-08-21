"""Internal inference adapter for a frozen recall-ensemble artifact."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


def load_artifact(path: Path) -> dict[str, Any]:
    return joblib.load(path)


def _base_probabilities(artifact: dict[str, Any], frame: pd.DataFrame) -> dict[str, np.ndarray]:
    return {name: model.predict_proba(frame)[:, 1] for name, model in artifact["base_models"].items()}


def _tree_candidate_probabilities(
    artifact: dict[str, Any], base: dict[str, np.ndarray], candidate: str
) -> np.ndarray | None:
    tree_order = artifact.get("tree_base_model_order", [])
    if not tree_order:
        return None
    tree_matrix = np.column_stack([base[name] for name in tree_order])
    if candidate == "tree_soft_voting_equal":
        return tree_matrix.mean(axis=1)
    if candidate == "tree_oof_blending":
        return sum(base[name] * artifact["tree_blend_weights"][name] for name in tree_order)
    if candidate == "tree_stacking":
        return artifact["tree_stacker"].predict_proba(tree_matrix)[:, 1]
    return None


def _candidate_probabilities(artifact: dict[str, Any], base: dict[str, np.ndarray]) -> np.ndarray:
    candidate = artifact["final_candidate"]
    if candidate in base:
        return base[candidate]
    order = artifact["base_model_order"]
    matrix = np.column_stack([base[name] for name in order])
    if candidate == "soft_voting_equal":
        return matrix.mean(axis=1)
    if candidate == "oof_blending":
        return sum(base[name] * artifact["blend_weights"][name] for name in order)
    if candidate == "stacking":
        return artifact["stacker"].predict_proba(matrix)[:, 1]
    tree_probability = _tree_candidate_probabilities(artifact, base, candidate)
    if tree_probability is not None:
        return tree_probability
    if candidate.endswith("_sigmoid_calibrated"):
        source_name = artifact["validation_winner"]
        source = base.get(source_name)
        if source is None and source_name == "stacking":
            source = artifact["stacker"].predict_proba(matrix)[:, 1]
        if source is None:
            source = _tree_candidate_probabilities(artifact, base, source_name)
        if source is None:
            raise ValueError(f"Unsupported calibration source: {source_name}")
        eps = np.finfo(float).eps
        logits = np.log(np.clip(source, eps, 1 - eps) / np.clip(1 - source, eps, 1 - eps))
        return artifact["calibrator"].predict_proba(logits.reshape(-1, 1))[:, 1]
    raise ValueError(f"Unsupported final candidate: {candidate}")


def predict_internal(artifact: dict[str, Any], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return internal screening outputs; these are not validated personal probabilities."""
    required = set(artifact["feature_columns"])
    frame = pd.DataFrame(records)
    missing = required - set(frame.columns)
    extra = set(frame.columns) - required
    if missing or extra:
        raise ValueError(f"Feature schema mismatch; missing={sorted(missing)}, extra={sorted(extra)}")
    frame = frame[artifact["feature_columns"]]
    probabilities = _candidate_probabilities(artifact, _base_probabilities(artifact, frame))
    candidate = artifact["final_candidate"]
    threshold = float(artifact["thresholds"][candidate])
    threshold_version = artifact["threshold_versions"][candidate]
    return [
        {
            "risk_score_internal": float(probability),
            "screen_positive_internal": bool(probability >= threshold),
            "model_version": artifact["model_version"],
            "feature_schema_version": artifact["feature_schema_version"],
            "threshold_version": threshold_version,
            "promotion_status": "candidate_internal_not_for_personal_probability_display",
            "disclaimer": "진단·처방이 아닌 내부 위험 선별 후보 결과",
        }
        for probability in probabilities
    ]
