import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.ml.inference.shap_explanations import explain_today, explain_tomorrow, safe_explanation, select_factors


def test_selection_signed_top_three_and_shortage():
    items = [
        {"feature": str(i), "direction": "increase" if v > 0 else "decrease", "contribution": v}
        for i, v in enumerate([0.2, -0.3, 0.1, -0.1, 0, float("nan")])
    ]
    assert [i["contribution"] for i in select_factors(items, elevated=True)] == [0.2, 0.1, -0.3]
    assert [i["contribution"] for i in select_factors(items, elevated=False)] == [-0.3, -0.1, 0.2]
    assert len(select_factors(items[:1], elevated=False)) == 1
    with pytest.raises(ValueError):
        select_factors(items, elevated=None)


def test_exact_shap_allocates_interactions_and_preserves_body_group():
    frame = pd.DataFrame([dict(age=1.0, sex=1.0, height_cm=170.0, weight_kg=70.0, bmi=24.0)])

    def score(rows):
        # The three derived/related body inputs are always masked together.
        assert (rows.height_cm.isna() == rows.bmi.isna()).all()
        assert (rows.weight_kg.isna() == rows.bmi.isna()).all()
        x = rows.fillna(0)
        return (0.1 + 0.1 * x.age + 0.1 * x.sex + 0.2 * x.age * x.sex).to_numpy()

    result = explain_today(frame, score, model_version="synthetic-v1", elevated=True)
    values = {i["feature"]: i["contribution"] for i in result["all_items"]}
    assert values["age"] == pytest.approx(0.2)
    assert values["sex"] == pytest.approx(0.2)
    assert values["body_measurements"] == 0
    assert result["reference_value"] == pytest.approx(0.1)
    assert result["score"] == pytest.approx(0.5)
    assert result["shap_claimed"] and result["additivity_verified"]
    assert result["display_allowed"] is False
    assert result["selection_status"] == "insufficient_directional_factors"
    assert result == explain_today(frame, score, model_version="synthetic-v1", elevated=True)


def test_today14_groups_dependent_inputs_and_remains_additive():
    frame = pd.DataFrame([{
        "age": 56.0, "height_cm": 162.0, "weight_kg": 68.0, "waist_cm": 91.0,
        "bmi": 25.9, "systolic_bp": 130.0, "diastolic_bp": 80.0, "sex": 2.0,
        "current_smoker": 0.0, "education": 3.0, "region": 1.0,
        "diabetes_family_history": 0.0, "hypertension_family_history": 0.0,
        "alcohol_frequency": 2.0,
    }])

    def score(rows):
        assert (rows.height_cm.isna() == rows.waist_cm.isna()).all()
        assert (rows.systolic_bp.isna() == rows.diastolic_bp.isna()).all()
        assert (rows.diabetes_family_history.isna() == rows.hypertension_family_history.isna()).all()
        return 0.01 + rows.notna().sum(axis=1).to_numpy() / 1000

    result = explain_today(frame, score, model_version="today14", elevated=True)
    features = {item["feature"] for item in result["all_items"]}
    assert {"body_measurements", "blood_pressure", "family_history"} <= features
    assert result["reference_value"] + sum(i["contribution"] for i in result["all_items"]) == pytest.approx(
        result["score"]
    )


def test_tree_shap_groups_onehot_and_missing_indicators():
    x = pd.DataFrame({"age": [40.0, 50.0, np.nan, 70.0, 80.0, 90.0], "sex": ["a", "b"] * 3})
    prep = ColumnTransformer(
        [("num", SimpleImputer(add_indicator=True), ["age"]), ("cat", OneHotEncoder(sparse_output=False), ["sex"])]
    )
    pipeline = Pipeline(
        [("preprocessing", prep), ("classifier", RandomForestClassifier(n_estimators=5, max_depth=2, random_state=42))]
    ).fit(x, [0, 0, 1, 0, 1, 1])
    result = explain_tomorrow(x.iloc[[2]], pipeline, model_version="synthetic-rf", elevated=True)
    assert {i["feature"] for i in result["all_items"]} == {"age", "sex"}
    assert result["reference_value"] + sum(i["contribution"] for i in result["all_items"]) == pytest.approx(
        pipeline.predict_proba(x.iloc[[2]])[0, 1]
    )
    assert result["reference_value"] + sum(i["contribution"] for i in result["items"]) + result[
        "other_contribution"
    ] == pytest.approx(result["score"])
    assert result["display_allowed"] is False


def test_failed_xai_returns_unavailable_without_fabricating_factors():
    def broken(**kwargs):
        raise RuntimeError("private input or artifact details")

    result = safe_explanation(broken, model_version="test")
    assert result["status"] == "unavailable"
    assert result["items"] == [] and result["shap_claimed"] is False
    assert "private" not in str(result)
