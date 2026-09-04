from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.ml.modeling.discrete_time_survival import BASE_FEATURES, predict_cumulative_risk


class ConstantHazardModel:
    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        hazards = frame["interval_index"].to_numpy(dtype=float) / 100
        return np.column_stack([1 - hazards, hazards])


def test_cumulative_risk_is_monotonic_and_uses_all_intervals() -> None:
    origins = pd.DataFrame([{feature: 0 for feature in BASE_FEATURES}])
    model = ConstantHazardModel()

    risk_2 = predict_cumulative_risk(model, origins, horizon_years=2)[0]
    risk_4 = predict_cumulative_risk(model, origins, horizon_years=4)[0]
    risk_18 = predict_cumulative_risk(model, origins, horizon_years=18)[0]

    assert risk_2 == pytest.approx(0.01)
    assert risk_4 == pytest.approx(1 - (0.99 * 0.98))
    assert risk_2 < risk_4 < risk_18
