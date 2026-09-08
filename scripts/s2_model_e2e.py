"""S2-MDL local diagnostic: FE/BE contract -> Redis Worker -> DB -> API.

Run only against a local environment with S2_MODEL_RUNTIME_ENABLED=true.
No model binary or credential is embedded in this script.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time

import httpx


async def _data(response: httpx.Response) -> dict:
    if response.is_error:
        raise RuntimeError(f"HTTP {response.status_code} {response.request.url.path}: {response.text}")
    payload = response.json()
    return payload.get("data", payload)


async def _wait_for_prediction(client: httpx.AsyncClient, headers: dict[str, str], job_id: str) -> dict:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        job = await _data(await client.get(f"/api/v1/prediction-jobs/{job_id}", headers=headers))
        if job["status"] == "succeeded":
            prediction_id = job.get("prediction_id")
            assert isinstance(prediction_id, int), "S2-API-002: succeeded job has no integer prediction_id"
            return await _data(await client.get(f"/api/v1/predictions/{prediction_id}", headers=headers))
        if job["status"] == "failed":
            raise RuntimeError(f"{job.get('error_code')}: {job.get('error')}")
        await asyncio.sleep(0.5)
    raise TimeoutError("S2-RUN-001: prediction job polling timed out")


async def run(base_url: str) -> dict:
    unique = str(time.time_ns())
    email = f"s2-model-{unique}@example.com"
    password = "S2ModelTest123!"
    async with httpx.AsyncClient(base_url=base_url, timeout=15) as client:
        await _data(
            await client.post(
                "/api/v1/auth/signup",
                json={"name": "S2 모델 점검", "email": email, "password": password, "terms_agreed": True},
            )
        )
        login = await _data(
            await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        )
        headers = {"Authorization": f"Bearer {login['access_token']}"}
        birthday = "1970-04-12"
        await _data(
            await client.patch(
                "/api/v1/users/me/profile",
                headers=headers,
                json={"birthday": birthday, "gender": "FEMALE"},
            )
        )
        await _data(
            await client.post(
                "/api/v1/consents",
                headers=headers,
                json={"consent_item": "health_data", "version": "1.0", "is_agreed": True},
            )
        )
        await _data(
            await client.post(
                "/api/v1/eligibility-checks",
                headers=headers,
                json={
                    "birth_date": birthday,
                    "has_diabetes_diagnosis": False,
                    "has_urgent_warning_sign": False,
                    "population_in_scope": True,
                },
            )
        )
        checkup = await _data(
            await client.post(
                "/api/v1/health-checkups",
                headers=headers,
                json={
                    "checkup_type": "initial",
                    "checkup_date": "2026-09-07",
                    "height_cm": 162,
                    "weight_kg": 68,
                    "waist_cm": 86,
                    "systolic_bp": 128,
                    "diastolic_bp": 79,
                    "self_rated_health": "fair",
                    "meal_count_yesterday": 3,
                    "regular_exercise": True,
                    "smoking_status": "never",
                    "current_drinker": False,
                    "exercise_days_per_week": 3,
                    "exercise_minutes": 30,
                    "annual_household_income_10k_krw": 4800,
                    "health_satisfaction_score": 6,
                    "economic_satisfaction_score": 6,
                    "overall_quality_of_life_score": 7,
                    "hypertension_diagnosis": False,
                    "cancer_diagnosis": False,
                    "chronic_lung_disease_diagnosis": False,
                    "liver_disease_diagnosis": False,
                    "heart_disease_diagnosis": False,
                    "cerebrovascular_disease_diagnosis": False,
                    "psychiatric_disease_diagnosis": False,
                    "arthritis_rheumatism_diagnosis": False,
                    "education_level": "code_3",
                    "marital_status": "code_1",
                    "household_structure": "multi_person",
                    "depressed_feeling_last_week": "code_1",
                    "sleep_difficulty_last_week": "code_1",
                },
            )
        )
        results = {}
        for key in ("diabetes_current_screening", "diabetes_incidence"):
            job = await _data(
                await client.post(
                    "/api/v1/prediction-jobs",
                    headers=headers,
                    json={"checkup_id": checkup["checkup_id"], "model_key": key},
                )
            )
            results[key] = await _wait_for_prediction(client, headers, job["job_id"])

    current = results["diabetes_current_screening"]
    future = results["diabetes_incidence"]
    assert current["model_version"] == "knhanes-shared7-sk180-research-v1"
    assert future["model_version"] == "rf25-first-interval-survival-ensemble-v1"
    for prediction in results.values():
        assert prediction["preview_only"] is True
        assert prediction["display_allowed"] is False
        assert prediction["operational_model_activated"] is False
        assert prediction["risk_category"] is None
        assert prediction["decision_threshold"] is None
        assert prediction["raw_probability_exposed"] is False
        assert prediction["preview_signal_level"] in {"low", "caution", "high"}
    points = future["age_risk_forecast"]["points"]
    assert [point["display_label"].split("년", 1)[0] for point in points] == ["2", "4", "6"]
    assert all("display_percent" not in point for point in points)
    return {
        "status": "S2-MDL-PASS",
        "current": {
            "prediction_id": current["prediction_id"],
            "model_version": current["model_version"],
            "preview_signal_level": current["preview_signal_level"],
        },
        "future": {
            "prediction_id": future["prediction_id"],
            "model_version": future["model_version"],
            "preview_signal_level": future["preview_signal_level"],
            "horizons": [point["display_label"] for point in points],
        },
        "safety": {
            "display_allowed": False,
            "operational_model_activated": False,
            "raw_probability_exposed": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8022")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.base_url)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
