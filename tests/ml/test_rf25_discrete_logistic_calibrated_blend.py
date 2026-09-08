from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.ml.experiments import runner
from src.ml.experiments.manifest import load_manifest

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = (
    ROOT / "experiments" / "diabetes_incidence" / "ensembles" / "rf25_discrete_logistic_calibrated_blend_v001"
)


def _globals() -> dict:
    manifest = load_manifest(EXPERIMENT_DIR / "experiment.json")
    return runner._load_entrypoint(manifest).__globals__


def test_blend_respects_weights_and_endpoints() -> None:
    blend = _globals()["blend_probabilities"]
    rf = np.array([0.1, 0.7])
    logistic = np.array([0.3, 0.5])

    assert np.allclose(blend(rf, logistic, 1.0), rf)
    assert np.allclose(blend(rf, logistic, 0.0), logistic)
    assert np.allclose(blend(rf, logistic, 0.25), np.array([0.25, 0.55]))


def test_blend_rejects_invalid_weight_and_length() -> None:
    blend = _globals()["blend_probabilities"]
    with pytest.raises(ValueError, match="가중치"):
        blend(np.array([0.1]), np.array([0.2]), 1.1)
    with pytest.raises(ValueError, match="길이"):
        blend(np.array([0.1]), np.array([0.2, 0.3]), 0.5)


def test_platt_calibration_returns_finite_probabilities() -> None:
    namespace = _globals()
    target = pd.Series([0, 0, 0, 1, 1, 1])
    raw = np.array([0.01, 0.03, 0.10, 0.40, 0.65, 0.90])

    calibrator = namespace["fit_platt"](target, raw)
    calibrated = namespace["apply_platt"](calibrator, raw)

    assert np.isfinite(calibrated).all()
    assert ((0 <= calibrated) & (calibrated <= 1)).all()
    assert np.all(np.diff(calibrated) > 0)
