import numpy as np

from src.ml.modeling.knhanes_full_comparison import (
    cross_fitted_stacker,
    fit_postprocessors,
    per_model_summary,
    transformed_probabilities,
)


def test_cross_fitted_stacker_returns_complete_oof_probabilities():
    y = np.array([0, 1] * 10)
    base = {
        "a": np.linspace(0.1, 0.9, len(y)),
        "b": np.linspace(0.9, 0.1, len(y)),
    }

    oof, final = cross_fitted_stacker(base, ["a", "b"], y, folds=2, seed=7)

    assert len(oof) == len(y)
    assert np.all((oof >= 0) & (oof <= 1))
    assert hasattr(final, "predict_proba")


def test_postprocessors_generate_bounded_probabilities():
    y = np.array([0, 0, 0, 1, 1, 1])
    oof = {"model": np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])}
    processors = fit_postprocessors(oof, y, seed=7)

    variants = transformed_probabilities(oof, processors)["model"]

    assert set(variants) == {"raw", "sigmoid", "isotonic"}
    assert all(np.all((values >= 0) & (values <= 1)) for values in variants.values())


def test_per_model_summary_uses_validation_choice_not_test_ranking():
    validation = [
        {
            "model": "m",
            "model_group": "baseline",
            "postprocessing": "raw_threshold_tuned",
            "candidate": "m_raw",
            "selection_eligible": True,
            "constraints_passed": True,
            "recall": 0.8,
            "auprc": 0.2,
            "specificity": 0.6,
            "brier_skill_score": 0.1,
        },
        {
            "model": "m",
            "model_group": "baseline",
            "postprocessing": "sigmoid_threshold_tuned",
            "candidate": "m_sigmoid",
            "selection_eligible": True,
            "constraints_passed": True,
            "recall": 0.7,
            "auprc": 0.3,
            "specificity": 0.7,
            "brier_skill_score": 0.2,
        },
    ]
    test = [
        {
            "candidate": candidate,
            "auroc": 0.7,
            "auprc": 0.2,
            "recall": recall,
            "specificity": 0.6,
            "brier": 0.1,
            "brier_skill_score": 0.1,
            "expected_calibration_error": 0.1,
            "constraints_passed": True,
        }
        for candidate, recall in (("m_raw", 0.6), ("m_sigmoid", 0.99))
    ]

    summary = per_model_summary(validation, test)

    assert summary[0]["validation_selected_postprocessing"] == "raw_threshold_tuned"
