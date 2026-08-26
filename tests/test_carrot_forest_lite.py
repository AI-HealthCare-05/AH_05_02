from __future__ import annotations

from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise import Tortoise

from app.core.db.databases import TORTOISE_APP_MODELS
from app.main import app
from app.models.engagement import SharedChallengeGroup, SharedChallengeMember
from app.models.health import Challenge, ChallengeCycle, ChallengeLog, UserChallenge
from app.models.users import User


async def signup_and_login(client: AsyncClient, email: str) -> tuple[User, dict[str, str]]:
    signup = {
        "email": email,
        "password": "Password123!",
        "gender": "FEMALE",
        "birth_date": "1982-04-12",
    }
    response = await client.post("/api/v1/auth/signup", json=signup)
    assert response.status_code == status.HTTP_201_CREATED
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": signup["password"]})
    assert login.status_code == status.HTTP_200_OK
    return await User.get(email=email), {"Authorization": f"Bearer {login.json()['access_token']}"}


async def complete_three_challenges(user: User, prefix: str) -> None:
    cycle = await ChallengeCycle.create(
        user_id=user.id,
        cycle_number=1,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=27),
    )
    for index in range(3):
        challenge = await Challenge.create(
            code=f"{prefix}-{index}",
            title=f"테스트 챌린지 {index}",
            category="activity",
            daily_goal="하루 한 번",
            description="통합 테스트",
            safety_copy="몸 상태를 우선하세요.",
            source_title="테스트 근거",
            source_url="https://example.com",
        )
        selected = await UserChallenge.create(
            user_id=user.id,
            cycle_id=cycle.id,
            challenge_id=challenge.id,
        )
        await ChallengeLog.create(
            user_id=user.id,
            user_challenge_id=selected.id,
            log_date=date.today(),
            is_completed=True,
        )


@pytest.mark.asyncio
async def test_carrot_forest_lite_group_reward_avatar_and_object_flow() -> None:
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            owner, owner_headers = await signup_and_login(client, "forest-owner@example.com")
            member, member_headers = await signup_and_login(client, "forest-member@example.com")
            member_three, _ = await signup_and_login(client, "forest-member-three@example.com")
            member_four, _ = await signup_and_login(client, "forest-member-four@example.com")
            member_five, _ = await signup_and_login(client, "forest-member-five@example.com")
            outsider, outsider_headers = await signup_and_login(client, "forest-outsider@example.com")
            assert outsider.id not in {owner.id, member.id}

            group = await SharedChallengeGroup.create(
                owner_user_id=owner.id,
                challenge_id=1,
                title="가족 건강 챌린지",
                common_goal="매일 세 가지 실천",
                start_date=date.today(),
                end_date=date.today() + timedelta(days=6),
            )
            await SharedChallengeMember.create(
                group_id=group.id,
                user_id=owner.id,
                personal_goal="하루 3개",
                status="active",
            )
            await SharedChallengeMember.create(
                group_id=group.id,
                user_id=member.id,
                personal_goal="하루 3개",
                status="active",
            )
            for extra_member in (member_three, member_four, member_five):
                await SharedChallengeMember.create(
                    group_id=group.id,
                    user_id=extra_member.id,
                    personal_goal="하루 3개",
                    status="active",
                )

            missing = await client.get(f"/api/v1/forest/spaces/{group.id}", headers=owner_headers)
            assert missing.status_code == status.HTTP_404_NOT_FOUND

            created = await client.post(
                "/api/v1/forest/spaces",
                headers=owner_headers,
                json={"group_id": group.id, "name": "우리 당근의 숲"},
            )
            assert created.status_code == status.HTTP_201_CREATED
            initial = created.json()["data"]
            assert initial["today"] == {
                "completed": 0,
                "target": 15,
                "group_reward_ready": False,
                "group_reward_claimed": False,
            }
            assert initial["me"]["carrot_balance"] == 100
            assert initial["sharing_scope"] == ["challenge_status", "avatar", "forest_objects"]
            assert "건강정보" in initial["privacy_notice"]

            forbidden = await client.get(f"/api/v1/forest/spaces/{group.id}", headers=outsider_headers)
            assert forbidden.status_code == status.HTTP_404_NOT_FOUND

            await complete_three_challenges(owner, "owner")
            await complete_three_challenges(member, "member")
            await complete_three_challenges(member_three, "member-three")
            await complete_three_challenges(member_four, "member-four")
            await complete_three_challenges(member_five, "member-five")

            ready = await client.get(f"/api/v1/forest/spaces/{group.id}", headers=member_headers)
            assert ready.status_code == status.HTTP_200_OK
            assert ready.json()["data"]["today"]["completed"] == 15
            assert ready.json()["data"]["today"]["group_reward_ready"] is True

            reward = await client.post(
                f"/api/v1/forest/spaces/{group.id}/rewards/group-daily",
                headers=owner_headers,
            )
            assert reward.status_code == status.HTTP_200_OK
            reward_data = reward.json()["data"]
            assert reward_data["carrot_amount"] == 50
            assert reward_data["item_code"]
            assert reward_data["carrot_balance"] == 150

            duplicate = await client.post(
                f"/api/v1/forest/spaces/{group.id}/rewards/group-daily",
                headers=owner_headers,
            )
            assert duplicate.status_code == status.HTTP_409_CONFLICT

            avatar = await client.patch(
                "/api/v1/forest/avatar",
                headers=owner_headers,
                json={
                    "display_name": "세준",
                    "hair_code": "midnight_short",
                    "outfit_code": "garden_overall",
                    "accessory_code": reward_data["item_code"],
                },
            )
            assert avatar.status_code == status.HTTP_200_OK
            assert avatar.json()["data"]["display_name"] == "세준"

            placed = await client.post(
                f"/api/v1/forest/spaces/{group.id}/objects",
                headers=owner_headers,
                json={"object_code": "sunflower", "position_x": 35, "position_y": 70},
            )
            assert placed.status_code == status.HTTP_201_CREATED
            assert placed.json()["data"]["carrot_balance"] == 130

            home = await client.get(f"/api/v1/forest/spaces/{group.id}", headers=owner_headers)
            home_data = home.json()["data"]
            assert home_data["me"]["accessory_code"] == reward_data["item_code"]
            assert home_data["objects"][0]["object_code"] == "sunflower"
            assert "prediction" not in str(home_data).lower()
    finally:
        await Tortoise.close_connections()
