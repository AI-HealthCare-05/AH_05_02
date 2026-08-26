import asyncio
from datetime import UTC, datetime
from typing import Any

from ai_worker.model_loader import load_model
from app.prediction import PredictionFeatures, get_prediction_provider

MEDICAL_NOTICE = "이 결과는 시스템 연동 확인 또는 위험 선별 보조용이며 진단·처방이 아닙니다."


async def run_task_with_timeout(task_type: str, payload: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    return await asyncio.wait_for(run_task(task_type, payload), timeout=timeout_seconds)


async def run_task(task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if task_type == "demo_inference":
        await asyncio.sleep(0.5)
        return {
            "is_demo": True,
            "pipeline": "redis-stream-consumer-group",
            "received_fields": sorted(payload),
            "processed_at": datetime.now(UTC).isoformat(),
            "medical_notice": MEDICAL_NOTICE,
        }

    if task_type == "model_inference":
        features = payload.get("features")
        if not isinstance(features, list) or not features:
            raise ValueError("model_inference payload에는 비어 있지 않은 features 배열이 필요합니다.")
        model = load_model()
        prediction = await asyncio.to_thread(model.predict, [features])
        result: dict[str, Any] = {
            "prediction": prediction[0].item() if hasattr(prediction[0], "item") else prediction[0],
            "is_demo": False,
            "medical_notice": MEDICAL_NOTICE,
        }
        if hasattr(model, "predict_proba"):
            probabilities = await asyncio.to_thread(model.predict_proba, [features])
            result["probabilities"] = probabilities[0].tolist()
        return result

    if task_type == "diabetes_incidence":
        features = payload.get("features")
        if not isinstance(features, dict):
            raise ValueError("diabetes_incidence payload에는 features 객체가 필요합니다.")
        validated = PredictionFeatures.model_validate(features)
        provider = get_prediction_provider()
        result = await provider.predict(validated)
        return {
            "model_key": "diabetes_incidence",
            "outcome_definition": "next_observation_new_diabetes_diagnosis",
            "internal_score": result.internal_score,
            "risk_category": result.risk_category,
            "model_version": result.model_version,
            "feature_schema_version": result.feature_schema_version,
            "input_schema_version": result.input_schema_version,
            "preprocessing_version": result.preprocessing_version,
            "target_definition_version": result.target_definition_version,
            "calibration_version": result.calibration_version,
            "model_artifact_digest": result.model_artifact_digest,
            "threshold_version": result.threshold_version,
            "decision_threshold": result.decision_threshold,
            "promotion_status": result.promotion_status,
            "explanation_status": result.explanation_status,
            "medical_notice": MEDICAL_NOTICE,
        }

    raise ValueError(f"지원하지 않는 task_type입니다: {task_type}")
