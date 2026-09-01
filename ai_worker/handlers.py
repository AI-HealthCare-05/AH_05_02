import asyncio
from datetime import UTC, date, datetime
from typing import Any

from ai_worker.model_loader import load_model
from app.prediction import get_prediction_provider
from app.prediction.contracts import CURRENT_SCREENING_MODEL

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
        model_input = payload.get("input")
        as_of_date_raw = payload.get("as_of_date")
        if not isinstance(model_input, dict) or not isinstance(as_of_date_raw, str):
            raise ValueError("diabetes_incidence payload에는 input 객체와 as_of_date가 필요합니다.")
        try:
            as_of_date = date.fromisoformat(as_of_date_raw)
        except ValueError as exc:
            raise ValueError("as_of_date must use YYYY-MM-DD") from exc
        provider = get_prediction_provider()
        result = await provider.predict(model_input, as_of_date=as_of_date)
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
            "input_as_of_date": as_of_date.isoformat(),
            "medical_notice": MEDICAL_NOTICE,
        }

    if task_type == "diabetes_current_screening":
        model_input = payload.get("input")
        if not isinstance(model_input, dict):
            raise ValueError("diabetes_current_screening payload에는 input 객체가 필요합니다.")
        from src.ml.inference.diabetes_current_screening import (
            load_current_screening_model,
            predict_with_loaded_current_model,
        )

        loaded = await asyncio.to_thread(load_current_screening_model)
        output = await asyncio.to_thread(predict_with_loaded_current_model, loaded, model_input)
        operational = (
            loaded.manifest.get("operational_model_activated") is True
            and loaded.manifest.get("promotion_status") == "approved"
        )
        signal = bool(output["screening_signal_detected"])
        return {
            "model_key": CURRENT_SCREENING_MODEL.model_key,
            "outcome_definition": CURRENT_SCREENING_MODEL.outcome_definition,
            "internal_score": output["risk_score_internal"],
            "risk_category": ("high" if signal else "low") if operational else None,
            "screening_signal_detected": signal if operational else None,
            "model_version": output["model_version"],
            "feature_schema_version": output["feature_schema_version"],
            "input_schema_version": CURRENT_SCREENING_MODEL.input_schema_version,
            "preprocessing_version": CURRENT_SCREENING_MODEL.preprocessing_version,
            "target_definition_version": CURRENT_SCREENING_MODEL.target_definition_version,
            "calibration_version": CURRENT_SCREENING_MODEL.calibration_version,
            "model_artifact_digest": loaded.manifest.get("artifact_sha256"),
            "threshold_version": output["threshold_version"],
            "decision_threshold": loaded.manifest.get("threshold") if operational else None,
            "promotion_status": "approved" if operational else "development_only",
            "output_status": "screening_not_diagnosis" if operational else "screening_model_pending_approval",
            "model_population": CURRENT_SCREENING_MODEL.model_population,
            "explanation_status": "not_available",
            "medical_notice": "현재 당뇨 관련 위험 신호 선별 결과이며 진단·처방이 아닙니다.",
        }

    raise ValueError(f"지원하지 않는 task_type입니다: {task_type}")
