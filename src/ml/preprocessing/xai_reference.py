"""Select a reproducible, private Train-only explanation reference."""

import numpy as np
import pandas as pd


def select_reference(data, *, features, train_years, sample_size=128, seed=20261001):
    train = data.loc[
        data["split"].eq("train")
        & data["survey_year"].isin(train_years)
        & data["eligible_diabetes_undiagnosed"].eq(True)
        & data["cohort_19_plus"].eq(True)
        & data["target_diabetes_clinical"].notna()
        & data["survey_weight"].gt(0)
    ].copy()
    if len(train) < sample_size:
        raise ValueError("Insufficient eligible Train reference rows")
    strata = list(train.groupby(["survey_year", "sex"], sort=True))
    mass = np.array([part.survey_weight.sum() for _, part in strata], dtype=float)
    allocation = sample_size * mass / mass.sum()
    counts = np.floor(allocation).astype(int)
    for i in np.argsort(-(allocation - counts), kind="stable")[: sample_size - counts.sum()]:
        counts[i] += 1
    selected = [
        part.sample(n=int(counts[i]), weights="survey_weight", random_state=seed + i)
        for i, (_, part) in enumerate(strata)
        if counts[i]
    ]
    return pd.concat(selected).loc[:, features].reset_index(drop=True), len(train)
