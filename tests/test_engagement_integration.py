from __future__ import annotations

from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise import Tortoise

from app.core.db.databases import TORTOISE_APP_MODELS
from app.main import app


async def signup_and_login(client: AsyncClient, email: str) -> dict[str, str]:
    signup = {
        "email": email,
        "password": "Password123!",
        "gender": "FEMALE",
        "birth_date": "1965-04-12",
    }
    response = await client.post("/api/v1/auth/signup", json=signup)
    assert response.status_code == status.HTTP_201_CREATED
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": signup["password"]})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_education_invitation_connection_and_empty_report_flow() -> None:
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            inviter_headers = await signup_and_login(client, "inviter@example.com")

            report = await client.get("/api/v1/weekly-reports/current", headers=inviter_headers)
            assert report.status_code == status.HTTP_200_OK
            assert report.json()["data"]["status"] == "empty"
            assert "치료 효과" in report.json()["data"]["disclaimer"]

            contents = await client.get("/api/v1/education-contents", headers=inviter_headers)
            assert contents.status_code == status.HTTP_200_OK
            first_content = contents.json()["data"]["items"][0]
            completion = await client.put(
                f"/api/v1/education-contents/{first_content['content_id']}/progress",
                headers=inviter_headers,
                json={"quiz_answer": "아니요"},
            )
            assert completion.json()["data"]["is_correct"] is True

            invitation = await client.post(
                "/api/v1/invitations",
                headers=inviter_headers,
                json={"invitee_email": "family@example.com", "relation_type": "family"},
            )
            assert invitation.status_code == status.HTTP_201_CREATED
            invitation_data = invitation.json()["data"]
            assert invitation_data["sharing_scope"] == ["challenge_status"]
            assert "health" not in invitation_data

            invitee_headers = await signup_and_login(client, "family@example.com")
            accepted = await client.post(
                "/api/v1/invitations/accept",
                headers=invitee_headers,
                json={"token": invitation_data["token"]},
            )
            assert accepted.status_code == status.HTTP_200_OK
            assert accepted.json()["data"]["sharing_scope"] == ["challenge_status"]

            connections = await client.get("/api/v1/connections", headers=invitee_headers)
            assert len(connections.json()["data"]["items"]) == 1
            assert connections.json()["data"]["items"][0]["health_data_shared"] is False

            inviter_connections = await client.get("/api/v1/connections", headers=inviter_headers)
            invitee_user_id = inviter_connections.json()["data"]["items"][0]["connected_user_id"]
            challenges = await client.get("/api/v1/challenges")
            challenge_id = challenges.json()["data"]["items"][0]["challenge_id"]
            group = await client.post(
                "/api/v1/shared-challenge-groups",
                headers=inviter_headers,
                json={
                    "title": "가족 걷기",
                    "challenge_id": challenge_id,
                    "start_date": date.today().isoformat(),
                    "end_date": (date.today() + timedelta(days=6)).isoformat(),
                    "common_goal": "각자 주 5일 실천",
                    "owner_goal": "하루 30분 걷기",
                    "members": [{"user_id": invitee_user_id, "personal_goal": "하루 10분 걷기"}],
                },
            )
            assert group.status_code == status.HTTP_201_CREATED
            group_data = group.json()["data"]
            invited_member = next(item for item in group_data["members"] if not item["is_me"])
            assert invited_member["status"] == "pending"

            accepted_group = await client.post(
                f"/api/v1/shared-challenge-groups/{group_data['group_id']}/accept", headers=invitee_headers
            )
            assert accepted_group.status_code == status.HTTP_200_OK
            active_member = next(item for item in accepted_group.json()["data"]["members"] if item["is_me"])
            assert active_member["status"] == "active"

            encouragement = await client.post(
                f"/api/v1/shared-challenge-groups/{group_data['group_id']}/encouragements",
                headers=inviter_headers,
                json={"recipient_user_id": invitee_user_id, "template_code": "together"},
            )
            assert encouragement.status_code == status.HTTP_201_CREATED
            assert "같이" in encouragement.json()["data"]["message"]
    finally:
        await Tortoise.close_connections()
