import numpy as np
import pytest

from src.ml.modeling.inference import predict_internal


class ConstantModel:
    def __init__(self, probability: float) -> None:
        self.probability = probability

    def predict_proba(self, frame):
        positive = np.full(len(frame), self.probability)
        return np.column_stack([1 - positive, positive])


def _artifact():
    return {
        "base_models": {"logistic_regression": ConstantModel(0.7)},
        "base_model_order": ["logistic_regression"],
        "blend_weights": {"logistic_regression": 1.0},
        "validation_winner": "logistic_regression",
        "final_candidate": "logistic_regression",
        "thresholds": {"logistic_regression": 0.6},
        "threshold_versions": {"logistic_regression": "thr-test"},
        "feature_columns": ["age", "bmi"],
        "feature_schema_version": "schema-test",
        "model_version": "model-test",
    }


def test_internal_inference_returns_versioned_screening_output():
    result = predict_internal(_artifact(), [{"age": 70, "bmi": 25.0}])[0]

    assert result["risk_score_internal"] == pytest.approx(0.7)
    assert result["screen_positive_internal"] is True
    assert result["threshold_version"] == "thr-test"


def test_internal_inference_rejects_schema_mismatch():
    with pytest.raises(ValueError, match="Feature schema mismatch"):
        predict_internal(_artifact(), [{"age": 70, "unexpected": 1}])


def test_tree_stacking_candidate_uses_tree_meta_learner():
    artifact = _artifact()
    artifact.update(
        {
            "base_models": {
                "random_forest": ConstantModel(0.4),
                "xgboost": ConstantModel(0.5),
                "lightgbm": ConstantModel(0.6),
            },
            "base_model_order": ["random_forest", "xgboost", "lightgbm"],
            "tree_base_model_order": ["random_forest", "xgboost", "lightgbm"],
            "tree_stacker": ConstantModel(0.8),
            "final_candidate": "tree_stacking",
            "thresholds": {"tree_stacking": 0.7},
            "threshold_versions": {"tree_stacking": "thr-tree"},
        }
    )

    result = predict_internal(artifact, [{"age": 70, "bmi": 25.0}])[0]

    assert result["risk_score_internal"] == pytest.approx(0.8)
    assert result["screen_positive_internal"] is True
