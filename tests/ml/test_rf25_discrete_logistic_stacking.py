from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.ml.experiments import runner
from src.ml.experiments.manifest import load_manifest

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = ROOT / "experiments" / "diabetes_incidence" / "ensembles" / "rf25_discrete_logistic_stacking_v001"


def _globals() -> dict:
    manifest = load_manifest(EXPERIMENT_DIR / "experiment.json")
    return runner._load_entrypoint(manifest).__globals__


def test_stack_features_have_fixed_order_and_finite_logits() -> None:
    features = _globals()["stack_features"](
        np.array([0.0, 0.8]),
        np.array([0.2, 1.0]),
    )

    assert features.shape == (2, 2)
    assert np.isfinite(features).all()
    assert features[1, 0] > features[0, 0]
    assert features[1, 1] > features[0, 1]


def test_stack_features_reject_different_lengths() -> None:
    with pytest.raises(ValueError, match="길이"):
        _globals()["stack_features"](np.array([0.1]), np.array([0.2, 0.3]))
