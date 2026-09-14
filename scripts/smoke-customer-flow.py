from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import date

import httpx


def require(response: httpx.Response, expected: int, label: str) -> dict:
    if response.status_code != expected:
        raise RuntimeError(f"{label}: HTTP {response.status_code} {response.text[:300]}")
    if "application/json" not in response.headers.get("content-type", ""):
        return {}
    return response.json()


async def run(base_url: str) -> None:
    results: list[dict[str, object]] = []
    stamp = int(time.time())
    signup = {
        "email": f"customer-smoke-{stamp}@example.com",
        "password": "Password123!",
        "terms_agreed": True,
    }

    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=30) as client:
        for path in ("/", "/forest", "/api/docs", "/api/health"):
            response = await client.get(path)
            require(response, 200, path)
            results.append({"check": path, "status": "ok"})

        require(await client.post("/api/v1/auth/signup", json=signup), 201, "signup")
        login = require(
            await client.post(
                "/api/v1/auth/login",
                json={"email": signup["email"], "password": signup["password"]},
            ),
            200,
            "login",
        )
        headers = {"Authorization": f"Bearer {login['access_token']}"}
        results.append({"check": "signup_and_login", "status": "ok"})

        require(
            await client.patch(
                "/api/v1/users/me/profile",
                headers=headers,
                json={"birthday": "1965-04-12", "gender": "FEMALE"},
            ),
            200,
            "profile",
        )
        require(
            await client.post(
                "/api/v1/consents",
                headers=headers,
                json={"consent_item": "health_data", "version": "1.0", "is_agreed": True},
            ),
            201,
            "consent",
        )
        require(
            await client.post(
                "/api/v1/eligibility-checks",
                headers=headers,
                json={
                    "birth_date": "1965-04-12",
                    "has_diabetes_diagnosis": False,
                    "has_urgent_warning_sign": False,
                    "population_in_scope": True,
                },
            ),
            200,
            "eligibility",
        )
        input_schema = require(
            await client.get("/api/v1/health-checkups/input-schema"),
            200,
            "health_input_schema",
        )
        feature_schema_version = input_schema["data"]["feature_schema_version"]
        checkup = require(
            await client.post(
                "/api/v1/health-checkups",
                headers=headers,
                json={
                    "checkup_type": "initial",
                    "checkup_date": date.today().isoformat(),
                    "height_cm": 160,
                    "weight_kg": 62,
                    "waist_cm": 78,
                    "systolic_bp": 128,
                    "diastolic_bp": 78,
                    "self_rated_health": "fair",
                    "meal_count_yesterday": 3,
                    "smoking_status": "never",
                    "regular_exercise": False,
                    "current_drinker": False,
                    "exercise_days_per_week": 0,
                    "exercise_minutes": 0,
                    "feature_schema_version": feature_schema_version,
                },
            ),
            201,
            "health_checkup",
        )
        checkup_id = checkup["data"]["checkup_id"]
        results.append({"check": "onboarding_and_health_input", "status": "ok"})

        prediction_ids: list[int] = []
        for model_key in ("diabetes_current_screening", "diabetes_incidence"):
            job = require(
                await client.post(
                    "/api/v1/prediction-jobs",
                    headers=headers,
                    json={"checkup_id": checkup_id, "model_key": model_key},
                ),
                202,
                model_key,
            )
            data = job["data"]
            if data["status"] != "succeeded" or not data.get("prediction_id"):
                raise RuntimeError(f"{model_key}: unexpected job result {data}")
            prediction_id = int(data["prediction_id"])
            prediction_ids.append(prediction_id)
            require(
                await client.get(f"/api/v1/predictions/{prediction_id}", headers=headers),
                200,
                f"prediction:{model_key}",
            )
            results.append({"check": model_key, "status": "ok", "mode": "development_demo"})

        recommendations = require(
            await client.get(
                f"/api/v1/challenge-recommendations?prediction_id={prediction_ids[-1]}",
                headers=headers,
            ),
            200,
            "challenge_recommendations",
        )
        challenge_id = recommendations["data"]["items"][0]["challenge_id"]
        cycle = require(
            await client.post(
                "/api/v1/challenge-cycles",
                headers=headers,
                json={
                    "start_date": date.today().isoformat(),
                    "challenge_ids": [challenge_id],
                    "prediction_id": prediction_ids[-1],
                },
            ),
            201,
            "challenge_cycle",
        )
        user_challenge_id = cycle["data"]["user_challenges"][0]["user_challenge_id"]
        require(
            await client.put(
                f"/api/v1/user-challenges/{user_challenge_id}/logs/{date.today().isoformat()}",
                headers=headers,
                json={"is_completed": True, "value": 1, "source": "self_report", "note": None},
            ),
            200,
            "challenge_log",
        )
        require(await client.get("/api/v1/dashboard/summary", headers=headers), 200, "dashboard")
        require(await client.get("/api/v1/weekly-reports/current", headers=headers), 200, "weekly_report")
        pdf = await client.get("/api/v1/weekly-reports/current/pdf", headers=headers)
        require(pdf, 200, "weekly_report_pdf")
        if not pdf.content.startswith(b"%PDF"):
            raise RuntimeError("weekly_report_pdf: invalid PDF signature")
        results.append({"check": "challenge_dashboard_and_report", "status": "ok"})

    print(json.dumps({"status": "ok", "base_url": base_url, "checks": results}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a customer-PC HTTP smoke test without exposing secrets.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    asyncio.run(run(args.base_url))


if __name__ == "__main__":
    main()
