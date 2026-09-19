"""Versioned research Shapley explanations, independent of public approval."""

from math import comb

import numpy as np
import pandas as pd

from src.ml.inference.model_explanations import DISPLAY_NAMES, MODIFIABLE


def select_factors(items, *, elevated):
    """Select up to three real attributions; never manufacture the other sign."""
    if type(elevated) is not bool:
        raise ValueError("A validated binary/elevated result is required")
    groups = {}
    for direction in ("increase", "decrease"):
        groups[direction] = sorted(
            (
                item
                for item in items
                if item["direction"] == direction
                and np.isfinite(item["contribution"])
                and abs(item["contribution"]) > 1e-10
            ),
            key=lambda item: (-abs(item["contribution"]), item["feature"]),
        )
    first, second = ("increase", "decrease") if elevated else ("decrease", "increase")
    return groups[first][:2] + groups[second][:1]


def _result(values, *, reference, score, method, baseline, model_version, elevated):
    if not np.isfinite([reference, score, *values.values()]).all():
        raise ValueError("Nonfinite SHAP explanation")
    if not np.isclose(reference + sum(values.values()), score, atol=1e-8, rtol=0):
        raise ValueError("SHAP additivity failed")
    # Serializes deterministically despite last-bit parallel RF reduction jitter.
    values = {feature: round(float(value), 12) for feature, value in values.items()}
    reference, score = round(float(reference), 12), round(float(score), 12)
    items = []
    for feature, value in values.items():
        direction = "increase" if value > 0 else "decrease" if value < 0 else "neutral"
        items.append(
            {
                "feature": feature,
                "display_name": DISPLAY_NAMES.get(feature, feature),
                "direction": direction,
                "display_group": "caution" if value > 0 else "positive" if value < 0 else "neutral",
                "contribution": float(value),
                "absolute_contribution": abs(float(value)),
                "modifiable": feature in MODIFIABLE,
                "message": "입력 정보가 기준값 대비 당뇨 위험을 "
                + ("높이는" if value > 0 else "낮추는" if value < 0 else "바꾸지 않는")
                + " 방향으로 반영되었습니다.",
            }
        )
    selected = select_factors(items, elevated=elevated)
    return {
        "status": "research_only",
        "display_allowed": False,
        "method": method,
        "explanation_version": "three-factor-shap-v1",
        "model_version": model_version,
        "output_space": "risk_score",
        "reference_value": float(reference),
        "score": float(score),
        "baseline_definition": baseline,
        "additive_to_score": True,
        "additivity_verified": True,
        "shap_claimed": True,
        "selection_policy": "elevated-2-caution-1-positive-otherwise-2-positive-1-caution-v1",
        "selection_status": "complete" if len(selected) == 3 else "insufficient_directional_factors",
        "items": selected,
        "all_items": items,
        "other_contribution": round(sum(values.values()) - sum(i["contribution"] for i in selected), 12),
        "limitations": [
            "not causal",
            "not a diagnosis",
            "correlated features affect attribution",
            "selected items alone do not sum to the score",
        ],
    }


def explain_today(frame, score_batch, *, model_version, elevated):
    """Exact grouped Shapley values over ALL coalitions of missing input groups.

    The reference is the frozen pipeline's all-missing input, not a population
    average. Height/weight/BMI form one player to preserve their dependency.
    Every coalition passes through waist estimation, preprocessing, both models,
    both Platt calibrators and the final weighted sum without refitting anything.
    """
    if len(frame) != 1 or len(frame.columns) > 14:
        raise ValueError("Today requires one row with at most fourteen features")
    dependent_groups = {
        "body_measurements": ("height_cm", "weight_kg", "waist_cm", "bmi"),
        "blood_pressure": ("systolic_bp", "diastolic_bp"),
        "family_history": ("diabetes_family_history", "hypertension_family_history"),
    }
    grouped_features = {feature for features in dependent_groups.values() for feature in features}
    groups = {c: [c] for c in frame if c not in grouped_features}
    for group_name, features in dependent_groups.items():
        present = [feature for feature in features if feature in frame]
        if present:
            groups[group_name] = present
    names = list(groups)
    n = len(names)
    if n > 10:
        raise ValueError("Today grouped SHAP requires at most ten independent input groups")
    rows = []
    for mask in range(1 << n):
        rows.append(
            {
                c: frame.iloc[0][c]
                if any(mask & (1 << j) and c in groups[name] for j, name in enumerate(names))
                else np.nan
                for c in frame
            }
        )
    scores = np.asarray(score_batch(pd.DataFrame(rows, columns=frame.columns)), dtype=float)
    if scores.shape != (1 << n,) or not np.isfinite(scores).all():
        raise ValueError("Invalid coalition scores")
    values = {}
    for j, name in enumerate(names):
        values[name] = sum(
            (scores[mask | (1 << j)] - scores[mask]) / (n * comb(n - 1, mask.bit_count()))
            for mask in range(1 << n)
            if not mask & (1 << j)
        )
    return _result(
        values,
        reference=scores[0],
        score=scores[-1],
        method="exact_grouped_shap_missing_reference_v1",
        baseline="all input groups missing; frozen Train-fitted preprocessing; not population average",
        model_version=model_version,
        elevated=elevated,
    )


def explain_tomorrow(frame, pipeline, *, model_version, elevated):
    """Positive-class RF TreeSHAP with one-hot/indicator aggregation."""
    import shap

    if len(frame) != 1:
        raise ValueError("TreeSHAP requires exactly one row")
    preprocessing = pipeline.named_steps["preprocessing"]
    classifier = pipeline.named_steps["classifier"]
    positive = list(classifier.classes_).index(1)
    transformed = preprocessing.transform(frame)
    explanation = shap.TreeExplainer(classifier, feature_perturbation="tree_path_dependent")(transformed)
    raw = explanation.values[0, :, positive]
    grouped = dict.fromkeys(frame.columns, 0.0)
    for name, value in zip(preprocessing.get_feature_names_out(), raw, strict=True):
        name = name.split("__", 1)[-1].removeprefix("missingindicator_")
        matches = [feature for feature in frame if name == feature or name.startswith(feature + "_")]
        if not matches:
            raise ValueError("Unmapped transformed feature")
        grouped[max(matches, key=len)] += float(value)
    result = _result(
        grouped,
        reference=explanation.base_values[0, positive],
        score=pipeline.predict_proba(frame)[0, positive],
        method="treeshap_tree_path_dependent_v1",
        baseline="training path counts in frozen RF trees",
        model_version=model_version,
        elevated=elevated,
    )
    result["explainer_library_version"] = shap.__version__
    return result


def safe_explanation(explain, *args, **kwargs):
    """XAI failure must not discard a successful prediction or expose internals."""
    try:
        return explain(*args, **kwargs)
    except Exception:
        return {
            "status": "unavailable",
            "display_allowed": False,
            "shap_claimed": False,
            "items": [],
            "model_version": kwargs.get("model_version"),
            "message": "주요 요인 설명을 제공할 수 없습니다.",
        }
