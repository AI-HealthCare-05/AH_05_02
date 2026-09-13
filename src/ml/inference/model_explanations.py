"""Shared display metadata and deterministic cross-model guidance.

Actual research-only Shapley implementations live in ``shap_explanations``.
Nothing in this module turns a research explanation into a public result.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

DISPLAY_NAMES = {
    "body_measurements": "체격 정보 (키·체중·BMI)",
    "log_household_income": "가구소득",
    "arthritis_rheumatism_diagnosis": "관절염·류머티즘 진단력",
    "health_satisfaction_score": "건강 만족도",
    "economic_satisfaction_score": "경제 만족도",
    "overall_quality_of_life_score": "삶의 만족도",
    "sleep_difficulty_last_week": "지난주 수면 어려움",
    "depressed_feeling_last_week": "지난주 우울감",
    "marital_status": "혼인 상태",
    "household_structure": "가구 형태",
    "chronic_lung_disease_diagnosis": "만성 폐질환 진단력",
    "cancer_diagnosis": "암 진단력",
    "psychiatric_disease_diagnosis": "정신과 질환 진단력",
    "liver_disease_diagnosis": "간질환 진단력",
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
