"""Verify the predeclared feature ablation, without private data or artifacts."""

from src.ml.evaluation.compare_knhanes_shared_inputs import variants


def test_education_ablation_changes_only_education():
    config = {"derived_numeric_features": [], "waist_estimator": {"enabled": True}}
    result = variants(config, education_ablation=True)
    assert set(result) == {"shared7", "shared6_no_education"}
    full = result["shared7"]
    reduced = result["shared6_no_education"]
    assert full["numeric_features"] == reduced["numeric_features"]
    assert full["categorical_features"] == reduced["categorical_features"] + ["education"]
    assert not reduced["waist_estimator"]["enabled"]


def test_variants_are_nested_and_do_not_mutate_source():
    source = {
        "numeric_features": ["age", "waist_cm"],
        "categorical_features": ["sex"],
        "derived_numeric_features": [
            "waist_height_ratio",
            "waist_was_estimated",
            "waist_expected_cm",
            "waist_minus_expected_cm",
        ],
        "waist_estimator": {"enabled": True},
    }
    configs = variants(source)
    assert len(configs) == 4
    for name, config in configs.items():
        features = config["numeric_features"] + config["categorical_features"]
        assert len(features) == 7 + ("waist" in name) + ("family" in name)
        assert len(features) == len(set(features))
        assert ("waist_cm" in features) == config["waist_estimator"]["enabled"]
        assert ("diabetes_family_history" in features) == ("family" in name)
        assert not {"fasting_glucose", "hba1c", "diabetes_diagnosed", "alcohol_frequency", "aerobic_activity"} & set(
            features
        )
        assert bool(config["derived_numeric_features"]) == ("waist" in name)
    assert source["numeric_features"] == ["age", "waist_cm"]
    assert source["waist_estimator"]["enabled"] is True
