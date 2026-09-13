"""Deterministic research explanations and cross-model guidance.

The local attribution method is deliberately not called SHAP. It measures the
score change when one feature is replaced by missing and the fitted pipeline's
Train-only missing-value policy is applied. It is descriptive, not causal.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import pandas as pd

DISPLAY_NAMES = {
    "age": "나이",
    "sex": "성별",
    "height_cm": "키",
    "weight_kg": "체중",
    "bmi": "BMI",
    "waist_cm": "허리둘레",
    "smoking_status": "흡연 상태",
    "current_smoker": "현재 흡연",
    "current_drinker": "현재 음주",
    "regular_exercise": "규칙적 운동",
    "exercise_days_per_week": "주당 운동일수",
    "exercise_minutes": "1회 운동시간",
    "hypertension_diagnosis": "고혈압 진단력",
    "heart_disease_diagnosis": "심장질환 진단력",
    "cerebrovascular_disease_diagnosis": "뇌혈관질환 진단력",
    "education": "교육 수준",
    "education_level": "교육 수준",
}

MODIFIABLE = {
    "weight_kg",
    "bmi",
    "waist_cm",
    "smoking_status",
    "current_smoker",
    "current_drinker",
    "regular_exercise",
    "exercise_days_per_week",
    "exercise_minutes",
}


def explain_by_missingness_perturbation(
    frame: pd.DataFrame,
    score: Callable[[pd.DataFrame], float],
    *,
    maximum_items: int = 5,
) -> dict[str, Any]:
    """Rank local score changes against the model's fitted missing policy."""

    if len(frame) != 1:
        raise ValueError("local explanation requires exactly one row")
    baseline = float(score(frame))
    if not np.isfinite(baseline):
        raise ValueError("baseline score is not finite")
    items = []
    for feature in frame.columns:
        perturbed = frame.copy()
        # There is exactly one row, so replacing the whole column avoids
        # pandas bool/string dtype assignment warnings without changing any
        # other feature.
        perturbed[feature] = np.nan
        missing_score = float(score(perturbed))
        if not np.isfinite(missing_score):
            continue
        contribution = baseline - missing_score
        items.append(
            {
                "feature": feature,
                "display_name": DISPLAY_NAMES.get(feature, feature),
                "direction": "increase" if contribution > 0 else "decrease" if contribution < 0 else "neutral",
                "contribution": round(contribution, 12),
                "absolute_contribution": round(abs(contribution), 12),
                "modifiable": feature in MODIFIABLE,
                "message": (
                    "이 입력은 결측 기준값과 비교해 모델 점수를 높이는 방향이었습니다."
                    if contribution > 0
                    else "이 입력은 결측 기준값과 비교해 모델 점수를 낮추는 방향이었습니다."
                    if contribution < 0
                    else "이 입력의 국소 점수 변화는 관찰되지 않았습니다."
                ),
            }
        )
    items.sort(key=lambda item: (-item["absolute_contribution"], item["feature"]))
    return {
        "status": "research_only",
        "method": "missingness_perturbation_v1",
        "explanation_version": "local-missingness-perturbation-v1",
        "output_space": "risk_score",
        "additive_to_score": False,
        "reference_value": None,
        "baseline_definition": "same record with one feature set to missing and fitted Train-only preprocessing applied",
        "score": round(baseline, 12),
        "items": items[:maximum_items],
        "shap_claimed": False,
        "display_allowed": False,
        "limitations": [
            "not SHAP",
            "not causal",
            "correlated features can share or mask influence",
            "missingness may itself be informative",
        ],
    }


def model_comparison_guidance(
    *,
    current_signal: bool | None,
    future_category: str | None,
    results_available: Sequence[bool] = (True, True),
    display_allowed: bool = False,
) -> dict[str, Any]:
    """Explain current/future disagreement without treating either as diagnosis."""

    if len(results_available) != 2 or not all(results_available):
        return {
            "status": "incomplete",
            "code": "MODEL_RESULT_INCOMPLETE",
            "display_allowed": False,
            "title": "일부 분석 결과를 확인할 수 없습니다",
            "message": "모델 파일 누락이나 분석 실패는 낮은 위험을 의미하지 않습니다.",
        }
    if current_signal is None or future_category not in {"low", "caution", "high"}:
        return {
            "status": "not_displayable",
            "code": "MODEL_RESULT_NOT_PUBLIC",
            "display_allowed": False,
            "title": "분석 결과 검토 중",
            "message": "승인되지 않은 내부 점수로 사용자 안내를 만들지 않습니다.",
        }
    if current_signal and future_category == "low":
        code = "CURRENT_SIGNAL_FUTURE_LOW"
        title = "현재 신호와 미래 전망의 기준이 다릅니다"
        message = "현재 신호 확인을 우선하세요. 미래 모델의 낮음은 현재 상태를 배제하거나 진단하지 않습니다."
    elif not current_signal and future_category in {"caution", "high"}:
        code = "CURRENT_LOW_FUTURE_ELEVATED"
        title = "현재 신호는 낮지만 미래 위험 요인이 관찰됐습니다"
        message = "현재 진단을 뜻하지 않으며 정기 검사와 생활습관 점검을 위한 선별 정보입니다."
    elif current_signal:
        code = "BOTH_SIGNALS_ELEVATED"
        title = "현재 신호 확인이 우선입니다"
        message = "두 결과 모두 진단이 아니며, 현재 신호는 의료기관 검사를 통해 확인해야 합니다."
    else:
        code = "BOTH_SIGNALS_LOW"
        title = "두 선별 결과에서 높은 신호가 관찰되지 않았습니다"
        message = "낮은 선별 결과도 당뇨병을 배제하지 않으며 정기적인 건강 확인이 필요합니다."
    return {
        "status": "available" if display_allowed else "research_only",
        "code": code,
        "display_allowed": display_allowed,
        "title": title,
        "message": message,
        "medical_notice": "현재 상태와 미래 위험을 서로 다른 모델로 선별한 결과이며 진단·처방이 아닙니다.",
    }
