"""Display saved inputs without inferring health advice from SHAP signs."""

ALCOHOL = {1: "최근 1년간 전혀 마시지 않음", 2: "월 1회 미만", 3: "월 1회 정도", 4: "월 2~4회",
           5: "주 2~3회", 6: "주 4회 이상", 8: "평생 음주 경험 없음"}
MISSING = "입력하지 않음"


def _number(value, unit=""):
    return MISSING if value is None else f"{float(value):g}{unit}"


def input_label(feature, checkup, screening=None):
    if checkup is None:
        return "저장된 입력값 확인 불가"
    value = getattr(checkup, feature, None)
    if feature == "alcohol_frequency":
        return ALCOHOL.get(getattr(screening, feature, None), MISSING)
    if feature == "blood_pressure":
        return f"수축기 {_number(checkup.systolic_bp, ' mmHg')} · 이완기 {_number(checkup.diastolic_bp, ' mmHg')}"
    if feature == "body_measurements":
        return f"키 {_number(checkup.height_cm, ' cm')} · 체중 {_number(checkup.weight_kg, ' kg')} · BMI {_number(checkup.bmi)} · 허리둘레 {_number(checkup.waist_cm, ' cm')}"
    if feature == "family_history":
        def history(name):
            v = getattr(screening, name, None)
            return MISSING if v is None else "있음" if v else "없음"
        return f"당뇨 {history('diabetes_family_history')} · 고혈압 {history('hypertension_family_history')}"
    if feature == "age":
        return _number(value, "세")
    if feature == "sex":
        return {"male": "남성", "female": "여성"}.get(value, MISSING)
    if feature in {"height_cm", "waist_cm"}:
        return _number(value, " cm")
    if feature == "weight_kg":
        return _number(value, " kg")
    if feature == "bmi":
        return _number(value)
    if feature.endswith("_diagnosis"):
        return MISSING if value is None else "진단받음" if value else "진단받지 않음"
    if feature in {"current_smoker", "current_drinker", "regular_exercise"}:
        return MISSING if value is None else "예" if value else "아니요"
    if feature == "smoking_status":
        return {"never": "비흡연", "former": "과거 흡연", "current": "현재 흡연"}.get(value, MISSING)
    if feature in {"education", "education_level"}:
        return {"code_1": "초등학교 이하", "code_2": "중학교", "code_3": "고등학교", "code_4": "대학교 이상"}.get(checkup.education_level, MISSING)
    if feature == "region":
        return MISSING if getattr(screening, feature, None) is None else f"지역 코드 {screening.region}"
    return MISSING if value is None else str(value)


def model_analysis_payload(prediction, *, approved):
    """Expose an explicitly requested model score only for a public result."""
    import math
    score, threshold = getattr(prediction, "internal_score", None), getattr(prediction, "decision_threshold", None)
    valid = lambda value: type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1
    if not approved or not valid(score) or not valid(threshold):
        return None
    return {"status": "available", "model_score": score, "decision_threshold": threshold,
            "score_minus_threshold": score - threshold, "score_range": [0, 1],
            "disclaimer": "모델의 선별 점수이며 확정 발병 확률이나 진단 결과가 아닙니다."}


def shap_graph_payload(explanation):
    """Return the complete additive graph only when every stored term verifies."""
    import math
    items = explanation.get("all_items")
    reference, score = explanation.get("reference_value"), explanation.get("score")
    valid = lambda value: type(value) in (int, float) and math.isfinite(value)
    if (explanation.get("display_allowed") is not True or explanation.get("additivity_verified") is not True
            or explanation.get("shap_claimed") is not True or not isinstance(items, list) or not 1 <= len(items) <= 128
            or not valid(reference) or not valid(score)):
        return None
    features = set()
    for item in items:
        if (not isinstance(item, dict) or not isinstance(item.get("feature"), str) or not item["feature"]
                or item["feature"] in features or not valid(item.get("contribution"))):
            return None
        features.add(item["feature"])
    total = math.fsum(item["contribution"] for item in items)
    if not math.isclose(reference + total, score, abs_tol=1e-8, rel_tol=0):
        return None
    return {"complete": True, "reference_value": reference, "explained_score": score,
            "contribution_sum": total,
            "items": [{"feature": item["feature"], "display_name": item.get("display_name") or item["feature"],
                       "contribution": item["contribution"]} for item in items]}
