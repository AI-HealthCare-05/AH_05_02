from src.ml.evaluation.compare_klosa_top_balanced_model_weights import (
    preprocessing_contract,
    top_balanced_candidates,
    weight_variants,
)


def test_top_balanced_candidates_and_weight_variants_are_fixed() -> None:
    candidates = top_balanced_candidates()

    assert [(item.rank, item.stage, item.model_name) for item in candidates] == [
        (1, 3, "random_forest"),
        (2, 4, "random_forest"),
        (3, 2, "random_forest"),
        (4, 4, "xgboost"),
        (5, 4, "logistic_regression"),
    ]
    assert len(candidates[0].features) == 25
    assert len(candidates[1].features) == 30
    assert len(candidates[2].features) == 20
    assert [name for name, _ in weight_variants("random_forest", 38.0)] == [
        "unweighted",
        "balanced",
        "balanced_subsample",
    ]
    assert weight_variants("xgboost", 38.0)[1][1] == {"classifier__scale_pos_weight": 38.0}


def test_preprocessing_contract_fixes_leakage_controls() -> None:
    contract = preprocessing_contract(random_state=7, minimum_validation_recall=0.85)

    assert contract["cohort"]["feature_timepoint"] == "t0_only"
    assert contract["split"] == {
        "unit": "pid",
        "ratio": "70/15/15",
        "stratification": "whether_pid_ever_has_event",
        "random_state": 7,
        "pid_overlap": 0,
    }
    assert contract["pipeline_fit"] == "train_only"
    assert contract["threshold"]["source"] == "validation_only"
    assert contract["threshold"]["minimum_recall"] == 0.85
    assert contract["threshold"]["test_use"] == "reporting_only"
