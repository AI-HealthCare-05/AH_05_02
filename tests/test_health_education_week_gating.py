"""건강교육 4주 커리큘럼 소프트 락(주차별 퀴즈 잠금) 테스트.

정책: 활성/예정 회차가 있으면 그 회차 시작일 기준으로 "지금이 몇 주차인지" 계산하고, 아직 안 된
미래 주차는 내용은 보여주되(미리보기) 퀴즈 제출만 막는다. 회차가 아예 없는 사용자는 잠금 없이
전부 미리보기 가능(하위 호환 유지 — 원래 동작).
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise import Tortoise

from app.core.db.databases import TORTOISE_APP_MODELS
from app.main import app
from app.models.health import ChallengeCycle
from app.models.users import User


async def signup_and_login(client: AsyncClient, email: str) -> dict[str, str]:
    signup = {"name": "게이팅 테스트 사용자", "email": email, "password": "Password123!", "terms_agreed": True}
    response = await client.post("/api/v1/auth/signup", json=signup)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": signup["password"]})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_quizzes_are_gated_by_cycle_start_date_week_number() -> None:
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "week-gating@example.com")
            user = await User.get(email="week-gating@example.com")

            # 회차 시작일을 10일 전으로 잡으면(0-6일=1주차, 7-13일=2주차) 오늘은 2주차다.
            start = date.today() - timedelta(days=10)
            await ChallengeCycle.create(
                user_id=user.id,
                cycle_number=1,
                start_date=start,
                end_date=start + timedelta(days=27),
                status="active",
            )

            quizzes = await client.get("/api/v1/health-education/quizzes", headers=headers)
            body = quizzes.json()["data"]
            assert body["current_week_number"] == 2

            week1_items = [item for item in body["items"] if item["week_number"] == 1]
            week3_items = [item for item in body["items"] if item["week_number"] == 3]
            assert week1_items and all(item["locked"] is False for item in week1_items)
            assert week3_items and all(item["locked"] is True for item in week3_items)

            # 1주차 문항은 정상 제출 가능.
            week1_answer = await client.post(
                f"/api/v1/health-education/quizzes/{week1_items[0]['quiz_id']}/answers",
                headers=headers,
                json={"answer": "아무 답"},
            )
            assert week1_answer.status_code == status.HTTP_200_OK

            # 3주차(미래) 문항은 제출이 막힌다.
            week3_answer = await client.post(
                f"/api/v1/health-education/quizzes/{week3_items[0]['quiz_id']}/answers",
                headers=headers,
                json={"answer": "아무 답"},
            )
            assert week3_answer.status_code == status.HTTP_403_FORBIDDEN
            assert "3주차" in week3_answer.json()["detail"]

            contents = await client.get("/api/v1/education-contents", headers=headers)
            contents_body = contents.json()["data"]
            assert contents_body["current_week_number"] == 2
            content_week3 = next(item for item in contents_body["items"] if item["week_number"] == 3)
            assert content_week3["locked"] is True
            content_week1 = next(item for item in contents_body["items"] if item["week_number"] == 1)
            assert content_week1["locked"] is False

            progress_week3 = await client.put(
                f"/api/v1/education-contents/{content_week3['content_id']}/progress",
                headers=headers,
                json={"quiz_answer": "아무 답"},
            )
            assert progress_week3.status_code == status.HTTP_403_FORBIDDEN
    finally:
        await Tortoise.close_connections()


@pytest.mark.asyncio
async def test_no_cycle_means_everything_stays_unlocked() -> None:
    """챌린지를 한 번도 시작하지 않은 사용자는 페이싱 기준이 없으므로 전부 미리보기 가능해야 한다
    (게이팅 도입 이전과 동일한 하위 호환 동작)."""
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "no-cycle@example.com")

            quizzes = await client.get("/api/v1/health-education/quizzes", headers=headers)
            body = quizzes.json()["data"]
            assert body["current_week_number"] is None
            assert all(item["locked"] is False for item in body["items"])

            week4_item = next(item for item in body["items"] if item["week_number"] == 4)
            answered = await client.post(
                f"/api/v1/health-education/quizzes/{week4_item['quiz_id']}/answers",
                headers=headers,
                json={"answer": "아무 답"},
            )
            assert answered.status_code == status.HTTP_200_OK
    finally:
        await Tortoise.close_connections()


@pytest.mark.asyncio
async def test_ended_cycle_falls_back_to_fully_unlocked() -> None:
    """회차가 이미 끝났으면(활성 회차 없음) 가장 최근 종료 회차의 시작일 기준으로 계산되고,
    그 시작일은 이미 4주 이상 지났을 것이므로 사실상 전부 열린 것과 같아야 한다."""
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "ended-cycle@example.com")
            user = await User.get(email="ended-cycle@example.com")

            start = date.today() - timedelta(days=60)
            await ChallengeCycle.create(
                user_id=user.id,
                cycle_number=1,
                start_date=start,
                end_date=start + timedelta(days=27),
                status="completed",
            )

            quizzes = await client.get("/api/v1/health-education/quizzes", headers=headers)
            body = quizzes.json()["data"]
            assert body["current_week_number"] == 4
            assert all(item["locked"] is False for item in body["items"])
    finally:
        await Tortoise.close_connections()
