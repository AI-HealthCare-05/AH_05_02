"""Synchronous single-user diabetes prediction orchestration."""

from datetime import UTC, datetime
from uuid import uuid4

from src.backend.api.v1.schemas.prediction import (
    PredictionPreviewData,
    PredictionPreviewRequest,
    SafetyNotice,
)
from src.backend.core.exceptions import PredictionNotAllowedError
from src.ml.inference.diabetes_model import predict_single_user
from src.ml.preprocessing.diabetes_input import to_diabetes_model_input

# KLoSA-based model's validated age range (SERVICE_SCOPE_AND_SAFETY_COPY.md SS2-1).
# Temporary hardcoded bound for the preview endpoint; replace with the active
# model card's min_age/max_age once ml.model_registry is implemented.
MIN_MODEL_AGE = 45
MAX_MODEL_AGE = 105


def _ensure_policy_eligible(request: PredictionPreviewRequest) -> None:
    """Policy-based exclusions that must return 403, not 422.

    Per SERVICE_SCOPE_AND_SAFETY_COPY.md SS6-1/6-2: prediction requests
    blocked because of prior diagnosis or the active model's validated
    age range are policy exclusions (403 PREDICTION_NOT_ALLOWED), distinct
    from input-format/range errors (422 MODEL_INPUT_INVALID) which stay in
    PredictionPreviewRequest.validate_input_consistency.
    """
    age = request.age_years()
    if age < MIN_MODEL_AGE or age > MAX_MODEL_AGE:
        raise PredictionNotAllowedError(
            reason_code="MODEL_AGE_OUT_OF_RANGE",
            message="현재 모델이 충분히 검증된 연령 범위가 아니어서 개인화 예측을 제공하지 않습니다. 일반 건강정보는 계속 확인할 수 있습니다.",
        )
    if request.previously_diagnosed_diabetes:
        raise PredictionNotAllowedError(
            reason_code="DIAGNOSED_DIABETES",
            message="당뇨병을 이미 진단받은 분을 위한 예측이 아닙니다. 검사·치료·복약은 담당 의료진의 지침을 따라주세요.",
            next_action="medical_guidance_information",
        )


def create_prediction_preview(request: PredictionPreviewRequest) -> PredictionPreviewData:
    _ensure_policy_eligible(request)
    model_input = to_diabetes_model_input(request)
    inference = predict_single_user(model_input)

    return PredictionPreviewData(
        prediction_id=uuid4(),
        condition="diabetes",
        model_type="future_incidence",
        data_source="klosa",
        outcome_definition="next_observation_new_diabetes_diagnosis",
        # API_SPEC.md v2 SS9: "점수 필드는 risk_score로 통일" — expose it directly.
        # This reverses the earlier SERVICE_SCOPE_AND_SAFETY_COPY.md guidance to
        # keep raw probabilities internal-only; v2 is treated as the newer,
        # confirmed decision (flagged for the team to double-check).
        risk_score=round(inference.score, 4),
        # 2026-08-20 모델 연동 Q&A SS6, 안 B 채택: 임계값이 승인되기 전에는
        # low/caution/high 범주, 한글 라벨, 임계값, 이진 판정을 반환하지 않는다.
        risk_category=None,
        risk_category_label=None,
        decision_threshold=None,
        predicted_class=None,
        # All six version fields now come straight from the loaded model
        # bundle's metadata (src/ml/model_registry.py), not hardcoded
        # strings here — previously feature_schema_version/preprocessing_version/
        # calibration_version were stale placeholders that didn't match the
        # real bundle. Single source of truth going forward is the bundle itself.
        model_version=inference.model_version,
        target_definition_version=inference.target_definition_version,
        input_schema_version=inference.input_schema_version,
        feature_schema_version=inference.feature_schema_version,
        preprocessing_version=inference.preprocessing_version,
        calibration_version=inference.calibration_version,
        predicted_at=datetime.now(UTC),
        # TODO(PM/model team confirm): is_temporary was originally True only
        # because this endpoint called a dummy stub. Now that the real
        # KLoSA pipeline is wired in, is it still "temporary" because the
        # operational threshold/risk_category aren't approved yet (안 B),
        # or should it flip to False now that inference itself is real?
        # Left as True since that's a policy call, not a code bug — flag
        # to 정세준/양준혁 rather than deciding silently here.
        is_temporary=True,
        safety_notice=SafetyNotice(
            summary="다음 약 2년의 관찰기간 동안 신규 당뇨병 진단 위험을 선별한 참고 결과입니다.",
            message="이 결과는 의료진의 진단이나 처방을 대신하지 않습니다.",
        ),
    )
