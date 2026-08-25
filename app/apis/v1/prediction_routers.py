from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.apis.responses import envelope
from app.dependencies.security import get_request_user
from app.dtos.ai_jobs import prediction_job_response
from app.dtos.health import PredictionJobCreateRequest
from app.models.health import Prediction
from app.models.users import User
from app.prediction.contracts import ACTIVE_MODEL
from app.repositories.health_repository import HealthRepository
from app.services.ai_jobs import create_prediction_job, get_prediction_job

prediction_router = APIRouter(tags=["Prediction"])

RISK_LABELS = {"low": "낮음", "caution": "주의", "high": "높음"}
PUBLIC_DISCLAIMER = "이 결과는 당뇨병 진단이 아닌 미래 발병 위험 선별 및 건강교육 정보입니다."
DEVELOPMENT_DISCLAIMER = (
    "개발용 추론 연결은 완료되었지만 검토된 임계값이 없어 개인 위험 범주와 확률을 제공하지 않습니다."
)


@prediction_router.get("/models/active")
async def active_models() -> dict[str, object]:
    return envelope(
        {
            "items": [
                {
                    **ACTIVE_MODEL.model_dump(),
                    "threshold_approved": ACTIVE_MODEL.threshold_is_approved,
                    "public_result_available": ACTIVE_MODEL.threshold_is_approved,
                }
            ]
        }
    )


@prediction_router.post("/prediction-jobs", status_code=status.HTTP_202_ACCEPTED)
async def enqueue_prediction_job(
    request: PredictionJobCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    try:
        job = await create_prediction_job(user, request)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": str(exc), "message": "현재 상태에서는 예측 작업을 생성할 수 없습니다."},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": str(exc), "message": "모델 입력 계약을 확인해 주세요."},
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    data = prediction_job_response(job).model_dump()
    data["status_url"] = f"/api/v1/prediction-jobs/{job.job_id}"
    return envelope(data)


@prediction_router.get("/prediction-jobs/{job_id}")
async def read_prediction_job(
    job_id: str,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    job = await get_prediction_job(job_id, user.id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="예측 작업을 찾을 수 없습니다.")
    return envelope(prediction_job_response(job).model_dump())


def prediction_payload(item: Prediction) -> dict[str, object]:
    promotion_status = (
        "approved"
        if item.result_status == "approved" and item.threshold_version != "unapproved"
        else "development_only"
    )
    public_category = item.risk_category if promotion_status == "approved" else None
    return {
        "prediction_id": item.id,
        "checkup_id": item.health_checkup_id,
        "model_key": item.model_key,
        "outcome_definition": item.outcome_definition,
        "result_status": item.result_status,
        "promotion_status": promotion_status,
        "risk_category": public_category,
        "risk_category_label": RISK_LABELS.get(public_category, "검토 중"),
        "model_version": item.model_version,
        "feature_schema_version": item.feature_schema_version,
        "threshold_version": item.threshold_version,
        "model_population": item.model_population,
        "predicted_at": item.predicted_at,
        "disclaimer": PUBLIC_DISCLAIMER if public_category else DEVELOPMENT_DISCLAIMER,
        "raw_probability_exposed": False,
    }


@prediction_router.get("/predictions/latest")
async def latest_prediction(user: Annotated[User, Depends(get_request_user)]) -> dict[str, object]:
    item = await HealthRepository().latest_prediction(user.id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="예측 결과를 찾을 수 없습니다.")
    return envelope(prediction_payload(item))


@prediction_router.get("/predictions")
async def list_predictions(user: Annotated[User, Depends(get_request_user)]) -> dict[str, object]:
    items = await HealthRepository().list_predictions(user.id)
    return envelope({"items": [prediction_payload(item) for item in items]})


@prediction_router.get("/predictions/{prediction_id}")
async def read_prediction(
    prediction_id: int,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    item = await HealthRepository().get_prediction(prediction_id, user.id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="예측 결과를 찾을 수 없습니다.")
    return envelope(prediction_payload(item))


@prediction_router.get("/predictions/{prediction_id}/risk-factors")
async def read_risk_factors(
    prediction_id: int,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    item = await HealthRepository().get_prediction(prediction_id, user.id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="예측 결과를 찾을 수 없습니다.")
    return envelope(
        {
            "prediction_id": item.id,
            "status": item.explanation_status,
            "items": [],
            "message": "검증된 설명 방법이 준비되기 전에는 위험·보호 요인을 표시하지 않습니다.",
            "shap_claimed": False,
        }
    )
