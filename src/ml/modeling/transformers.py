"""Reusable, serializable feature transformers for ML serving artifacts."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline


class AnthropometricWaistEstimator(BaseEstimator, TransformerMixin):
    """Fill missing waist circumference without overwriting measurements."""

    def __init__(
        self,
        enabled: bool = True,
        predictors: tuple[str, ...] = ("height_cm", "weight_kg", "age", "sex"),
        seed: int = 20260831,
    ) -> None:
        self.enabled = enabled
        self.predictors = predictors
        self.seed = seed

    def fit(self, x: pd.DataFrame, y: Any = None) -> AnthropometricWaistEstimator:
        frame = x.copy()
        observed = frame["waist_cm"].notna()
        if not observed.any():
            raise ValueError("At least one observed waist_cm value is required")
        self.fallback_ = float(frame.loc[observed, "waist_cm"].median())
        self.model_ = None
        if self.enabled and int(observed.sum()) >= 100:
            self.model_ = Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                    (
                        "regressor",
                        HistGradientBoostingRegressor(
                            learning_rate=0.05,
                            max_iter=180,
                            max_leaf_nodes=15,
                            min_samples_leaf=30,
                            l2_regularization=2.0,
                            random_state=self.seed,
                        ),
                    ),
                ]
            )
            self.model_.fit(frame.loc[observed, list(self.predictors)], frame.loc[observed, "waist_cm"])
        return self

    def transform(self, x: pd.DataFrame) -> pd.DataFrame:
        frame = x.copy()
        missing = frame["waist_cm"].isna()
        frame["waist_was_estimated"] = missing.astype(float)
        if self.model_ is None:
            expected = np.repeat(self.fallback_, len(frame))
        else:
            expected = self.model_.predict(frame.loc[:, list(self.predictors)])
        expected = np.clip(expected, 45.0, 160.0)
        frame["waist_expected_cm"] = expected
        if missing.any():
            frame.loc[missing, "waist_cm"] = expected[missing.to_numpy()]
        frame["waist_minus_expected_cm"] = frame["waist_cm"] - frame["waist_expected_cm"]
        valid_height = frame["height_cm"].where(frame["height_cm"].gt(0))
        frame["waist_height_ratio"] = frame["waist_cm"] / valid_height
        return frame
