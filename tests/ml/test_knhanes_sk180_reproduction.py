import json
from pathlib import Path

from src.ml.evaluation.compare_knhanes_shared_inputs import variants
from src.ml.evaluation.reproduce_knhanes_shared7_sk180 import estimators


def test_frozen_shared7_parameters():
    models = estimators()
    lr = models["logistic"].get_params()
    rf = models["random_forest"].get_params()
    assert lr["C"] == 10 and lr["class_weight"] == "balanced"
    assert lr["solver"] == "lbfgs" and lr["l1_ratio"] == 0
    assert rf["n_estimators"] == 400 and rf["min_samples_leaf"] == 40
    assert rf["class_weight"] == "balanced_subsample"
    assert lr["random_state"] == rf["random_state"] == 20260831


def test_shared8_waist_contract_enables_train_only_estimator():
    config = json.loads(Path("configs/knhanes_current_screening_recall_v061.json").read_text())
    candidate = variants(config)["shared7_waist"]
    assert candidate["numeric_features"] == ["age", "height_cm", "weight_kg", "bmi", "waist_cm"]
    assert candidate["categorical_features"] == ["sex", "current_smoker", "education"]
    assert candidate["waist_estimator"]["enabled"] is True
