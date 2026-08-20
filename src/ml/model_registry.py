"""Active model, feature schema, population, and horizon registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib

# Repo root, resolved from this file's location so the bundle loads
# correctly regardless of the process's current working directory.
_REPO_ROOT = Path(__file__).resolve().parents[2]

DIABETES_MODEL_BUNDLE_PATH = _REPO_ROOT / "models/baselines/klosa_diabetes_incidence_pooled/model.joblib"

_diabetes_bundle_cache: dict[str, Any] | None = None


def load_diabetes_model_bundle() -> dict[str, Any]:
    """Load (and cache) the KLoSA diabetes-incidence model bundle.

    The bundle is a dict with "pipeline" (a fitted sklearn Pipeline with
    "preprocessing"/"classifier" steps) and "metadata" (model_version,
    target_definition_version, input_schema_version, feature_set_version,
    preprocessing_version, calibration_version, supported age range, etc).
    Only load bundles produced by this project from a trusted location —
    joblib deserializes arbitrary objects.
    """
    global _diabetes_bundle_cache
    if _diabetes_bundle_cache is None:
        bundle = joblib.load(DIABETES_MODEL_BUNDLE_PATH)
        if not isinstance(bundle, dict) or "pipeline" not in bundle or "metadata" not in bundle:
            raise ValueError("invalid KLoSA model bundle")
        _diabetes_bundle_cache = bundle
    return _diabetes_bundle_cache
