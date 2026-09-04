from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.ml.experiments import runner
from src.ml.experiments.manifest import load_manifest

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = (
    ROOT / "experiments" / "diabetes_incidence" / "ensembles" / "rf25_first_interval_survival_ensemble_v001"
)


def _globals() -> dict:
    manifest = load_manifest(EXPERIMENT_DIR / "experiment.json")
    return runner._load_entrypoint(manifest).__globals__


class FixedHazardModel:
    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        hazard = np.full(len(frame), 0.1)
        return np.column_stack((1 - hazard, hazard))


def test_first_interval_is_preserved_and_curve_is_monotonic() -> None:
    predict = _globals()["predict_first_interval_curve"]
    base_features = _globals()["BASE_FEATURES"]
    origins = pd.DataFrame([{feature: 0 for feature in base_features}])

    two = predict(FixedHazardModel(), origins, np.array([0.2]), horizon_years=2)
    six = predict(FixedHazardModel(), origins, np.array([0.2]), horizon_years=6)

    assert two[0] == pytest.approx(0.2)
    assert six[0] == pytest.approx(1 - 0.8 * 0.9 * 0.9)
    assert six[0] > two[0]


def test_first_interval_rejects_invalid_probability() -> None:
    predict = _globals()["predict_first_interval_curve"]
    base_features = _globals()["BASE_FEATURES"]
    origins = pd.DataFrame([{feature: 0 for feature in base_features}])

    with pytest.raises(ValueError, match="첫 구간 위험"):
        predict(FixedHazardModel(), origins, np.array([1.1]), horizon_years=2)
