from pathlib import Path

import numpy as np
import pandas as pd

from src.ml.modeling.klosa_feature_expansion import (
    build_incident_frame,
    feature_bundles,
    threshold_sensitivity,
)


def test_feature_bundles_expand_core_without_target_columns() -> None:
    bundles = feature_bundles()
    assert len(bundles["core_8"]["numeric_features"]) + len(bundles["core_8"]["categorical_features"]) == 8
    assert "target_diabetes_incident_next_wave" not in str(bundles)
    assert "diabetes_event" not in str(bundles)
    assert (
        len(bundles["core_8_plus_longitudinal"]["numeric_features"])
        + len(bundles["core_8_plus_longitudinal"]["categorical_features"])
        == 22
    )


def test_history_features_only_use_prior_rows(tmp_path: Path) -> None:
    rows = []
    for participant_id, split in (("a", "train"), ("b", "test")):
        for wave, bmi, target in ((1, 20.0, 0), (2, 22.0, 1)):
            rows.append(
                {
                    "participant_id": participant_id,
                    "survey_wave": wave,
                    "survey_year": 2004 + wave * 2,
                    "split": split,
                    "eligible_diabetes_incident": True,
                    "target_diabetes_incident_next_wave": target,
                    "diagnosed_through_wave_hypertension": False,
                    "age": 50 + wave,
                    "bmi": bmi,
                    "self_rated_health": 3,
                    "meal_count_yesterday": 3,
                    "sex": 1,
                    "regular_exercise": wave - 1,
                    "current_smoker": 0,
                    "current_drinker": 0,
                }
            )
    path = tmp_path / "panel.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    result = build_incident_frame(path)
    second = result.loc[(result["participant_id"] == "a") & (result["survey_wave"] == 2)].iloc[0]
    assert second["prior_bmi"] == 20.0
    assert second["bmi_change"] == 2.0
    assert second["prior_regular_exercise"] == 0
    assert second["regular_exercise_changed"] == 1


def test_first_observation_has_no_synthetic_prior(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        [
            {
                "participant_id": "a",
                "survey_wave": 1,
                "survey_year": 2006,
                "split": "train",
                "eligible_diabetes_incident": True,
                "target_diabetes_incident_next_wave": 0,
                "diagnosed_through_wave_hypertension": False,
                "age": 55,
                "bmi": 23.0,
                "self_rated_health": 3,
                "meal_count_yesterday": 3,
                "sex": 1,
                "regular_exercise": 0,
                "current_smoker": 0,
                "current_drinker": 0,
            }
        ]
    )
    path = tmp_path / "panel.csv"
    frame.to_csv(path, index=False)
    result = build_incident_frame(path)
    assert result.loc[0, "prior_observation_available"] == 0
    assert pd.isna(result.loc[0, "prior_bmi"])
    assert pd.isna(result.loc[0, "bmi_change"])


def test_threshold_sensitivity_uses_validation_targets() -> None:
    y = np.asarray([0, 0, 0, 0, 1, 1])
    probabilities = np.asarray([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    config = {
        "exploratory_specificity_targets": [0.5, 0.75],
        "selection_constraints": {
            "minimum_specificity": 0.5,
            "minimum_auprc_lift": 1.0,
        },
        "threshold_grid": {"minimum": 0.1, "maximum": 0.6, "points": 6},
        "reliability_bins": 3,
    }
    rows = threshold_sensitivity(y, probabilities, y, probabilities, 1 / 3, config)
    assert len(rows) == 2
    assert rows[1]["validation_specificity"] >= 0.75
