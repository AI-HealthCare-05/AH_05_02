"""Synchronous single-user diabetes prediction orchestration."""

from datetime import UTC, datetime
from uuid import uuid4

from src.backend.api.v1.schemas.prediction import (
    PredictionPreviewData,
    PredictionPreviewRequest,
    SafetyNotice,
)
from src.ml.inference.diabetes_model import predict_single_user
from src.ml.preprocessing.diabetes_input import to_diabetes_model_input


def create_prediction_preview(request: PredictionPreviewRequest) -> PredictionPreviewData:
    model_input = to_diabetes_model_input(request)
    inference = predict_single_user(model_input)

    # Temporary integration-only boundaries. Replace after model validation/mentoring.
    if inference.score < 0.15:
        category, label = "low", "낮음"
    elif inference.score < 0.30:
        category, label = "moderate", "주의"
    else:
        category, label = "high", "높음"

    return PredictionPreviewData(
        prediction_id=uuid4(),
        condition="diabetes",
        model_type="future_incidence",
        data_source="klosa",
        target_horizon="next_wave_about_2y",
        risk_category=category,
        risk_category_label=label,
        predicted_class=inference.predicted_class,
        model_version=inference.model_version,
        target_definition_version="klosa-diabetes-incidence-next-wave-v1",
        input_schema_version="diabetes-incidence-input-v1",
        feature_schema_version="diabetes-incidence-input-v1",
        preprocessing_version="temporary-preprocessing-v1",
        calibration_version="none-v1",
        predicted_at=datetime.now(UTC),
        is_temporary=True,
        safety_notice=SafetyNotice(
            summary="다음 약 2년의 관찰기간 동안 신규 당뇨병 진단 위험을 선별한 참고 결과입니다.",
            message="이 결과는 의료진의 진단이나 처방을 대신하지 않습니다.",
        ),
    )
