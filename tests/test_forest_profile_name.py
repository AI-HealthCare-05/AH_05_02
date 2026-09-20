from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.core.db.databases import TORTOISE_APP_MODELS
from app.main import app
from app.models.engagement import SharedChallengeGroup, SharedChallengeMember
from app.models.forest import ForestAvatar, ForestInventory, ForestSpace
from app.models.users import User
from app.repositories.forest_repository import ForestRepository
from app.services.jwt import JwtService

pytestmark = pytest.mark.asyncio(loop_scope="session")
COSMETICS = {"hair_code": "silver_bob", "outfit_code": "garden_overall", "accessory_code": "none"}


@pytest_asyncio.fixture(loop_scope="session")
async def accounts():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
    try:
        users = []
        for index, name in enumerate(("처음이름", "친구이름", None)):
            users.append(
                await User.create(
                    email=f"forest-profile-{index}@example.com",
                    hashed_password="not-a-login",
                    gender="FEMALE",
                    birthday=date(1980, 1, 1),
                    name=name,
                )
            )
        yield users
    finally:
        await Tortoise.close_connections()


def headers(user):
    return {"Authorization": f"Bearer {JwtService().create_access_token(user)}"}


async def test_profile_rename_syncs_existing_avatar_and_all_group_views_without_cross_account_update(accounts):
    owner, member, _ = accounts
    owner_avatar = await ForestAvatar.create(user_id=owner.id, display_name="과거별명", carrot_balance=987, **COSMETICS)
    member_avatar = await ForestAvatar.create(user_id=member.id, display_name="과거친구", carrot_balance=654)
    await ForestInventory.create(user_id=owner.id, item_code="flower_pin", acquired_source="group_daily_reward")
    group = await SharedChallengeGroup.create(
        owner_user_id=owner.id,
        challenge_id=1,
        title="이름 동기화 테스트",
        common_goal="하루 세 가지",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=6),
    )
    await ForestSpace.create(group_id=group.id, created_by_user_id=owner.id)
    for user in (owner, member):
        await SharedChallengeMember.create(
            group_id=group.id, user_id=user.id, personal_goal="하루 3개", status="active"
        )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        initial = await client.get(f"/api/v1/forest/spaces/{group.id}", headers=headers(owner))
        assert initial.status_code == 200
        initial_data = initial.json()["data"]
        assert initial_data["me"]["display_name"] == owner.name
        assert [row["display_name"] for row in initial_data["members"]] == [owner.name, member.name]
        await member_avatar.refresh_from_db()
        assert member_avatar.display_name == member.name
        member_updated_at = member_avatar.updated_at

        renamed = await client.patch(
            "/api/v1/users/me", headers=headers(owner), json={"name": "새프로필이름", "user_id": member.id}
        )
        assert renamed.status_code == 200
        assert renamed.json()["id"] == owner.id
        assert renamed.json()["name"] == "새프로필이름"
        # The profile transaction persists the name even before the next forest read.
        await owner_avatar.refresh_from_db()
        assert owner_avatar.display_name == "새프로필이름"
        assert owner_avatar.carrot_balance == 987
        assert {field: getattr(owner_avatar, field) for field in COSMETICS} == COSMETICS
        await member_avatar.refresh_from_db()
        await member.refresh_from_db()
        assert member.name == member_avatar.display_name == "친구이름"
        assert member_avatar.carrot_balance == 654
        assert member_avatar.updated_at == member_updated_at

        for viewer in (owner, member):
            response = await client.get(f"/api/v1/forest/spaces/{group.id}", headers=headers(viewer))
            assert response.status_code == 200
            data = response.json()["data"]
            expected_me = "새프로필이름" if viewer.id == owner.id else "친구이름"
            assert data["me"]["display_name"] == expected_me
            rows = {row["user_id"]: row for row in data["members"]}
            assert rows[owner.id]["display_name"] == rows[owner.id]["avatar"]["display_name"] == "새프로필이름"
            assert rows[member.id]["display_name"] == rows[member.id]["avatar"]["display_name"] == "친구이름"
        assert await ForestInventory.filter(user_id=owner.id).values_list("item_code", flat=True) == ["flower_pin"]


@pytest.mark.parametrize("legacy_fields", [{}, {"display_name": "별도이름"}, {"display_name": None}])
async def test_avatar_only_saves_cosmetics_and_ignores_optional_legacy_name(accounts, legacy_fields):
    owner, member, _ = accounts
    avatar = await ForestAvatar.create(user_id=owner.id, display_name="과거별명", carrot_balance=321)
    other = await ForestAvatar.create(user_id=member.id, display_name=member.name, carrot_balance=456)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/forest/avatar",
            headers=headers(owner),
            json={**COSMETICS, **legacy_fields, "user_id": member.id},
        )
        assert response.status_code == 200
        assert response.json()["data"] == {"display_name": owner.name, "carrot_balance": 321, **COSMETICS}
    await avatar.refresh_from_db()
    await owner.refresh_from_db()
    await other.refresh_from_db()
    assert avatar.display_name == owner.name == "처음이름"
    assert other.display_name == member.name == "친구이름"
    assert other.carrot_balance == 456
    assert other.outfit_code == "orange_hoodie"


@pytest.mark.parametrize("existing_avatar", [False, True])
async def test_nameless_account_uses_generic_name_never_email(accounts, existing_avatar):
    _, _, user = accounts
    if existing_avatar:
        await ForestAvatar.create(user_id=user.id, display_name=user.email.split("@", 1)[0])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch("/api/v1/forest/avatar", headers=headers(user), json=COSMETICS)
        assert response.status_code == 200
        assert response.json()["data"]["display_name"] == "숲지기"
        assert "forest-profile" not in response.text
    assert (await ForestAvatar.get(user_id=user.id)).display_name == "숲지기"
    assert (await User.get(id=user.id)).name is None


async def test_profile_rename_does_not_initialize_forest_and_rejects_invalid_name(accounts):
    owner, _, _ = accounts
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        renamed = await client.patch("/api/v1/users/me", headers=headers(owner), json={"name": "새이름"})
        assert renamed.status_code == 200
        assert not await ForestAvatar.filter(user_id=owner.id).exists()
        for invalid_name in ("", "한", "이" * 21):
            rejected = await client.patch("/api/v1/users/me", headers=headers(owner), json={"name": invalid_name})
            assert rejected.status_code == 422
        unchanged = await client.patch("/api/v1/users/me", headers=headers(owner), json={"name": None})
        assert unchanged.status_code == 200
        assert unchanged.json()["name"] == "새이름"
    assert (await User.get(id=owner.id)).name == "새이름"
    assert await ForestAvatar.all().count() == 0


async def test_profile_rename_rolls_back_when_avatar_sync_fails(accounts, monkeypatch):
    owner, _, _ = accounts
    await ForestAvatar.create(user_id=owner.id, display_name=owner.name)

    async def failed_sync(self, user):
        raise RuntimeError("simulated sync failure")

    monkeypatch.setattr(ForestRepository, "sync_existing_avatar_name", failed_sync)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.patch("/api/v1/users/me", headers=headers(owner), json={"name": "실패이름"})
        assert response.status_code == 500
    assert (await User.get(id=owner.id)).name == owner.name
    assert (await ForestAvatar.get(user_id=owner.id)).display_name == owner.name
