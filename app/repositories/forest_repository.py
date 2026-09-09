from __future__ import annotations

from datetime import date
from typing import Any

from app.models.engagement import SharedChallengeGroup, SharedChallengeMember
from app.models.forest import ForestAvatar, ForestInventory, ForestObject, ForestReward, ForestSpace
from app.models.health import ChallengeLog
from app.models.users import User
from app.repositories.game_repository import GameRepository

WELCOME_CARROTS = 100


def forest_display_name(user: User) -> str:
    """Use the account profile as the single source of truth for forest names."""
    return user.name or "숲지기"


class ForestRepository:
    async def active_member(self, group_id: int, user_id: int) -> SharedChallengeMember | None:
        return await SharedChallengeMember.get_or_none(group_id=group_id, user_id=user_id, status="active")

    async def group(self, group_id: int) -> SharedChallengeGroup | None:
        return await SharedChallengeGroup.get_or_none(id=group_id, status="active")

    async def members(self, group_id: int) -> list[SharedChallengeMember]:
        return await SharedChallengeMember.filter(group_id=group_id, status="active").order_by("id")

    async def users(self, user_ids: list[int]) -> dict[int, User]:
        return {item.id: item for item in await User.filter(id__in=user_ids)}

    async def space(self, group_id: int) -> ForestSpace | None:
        return await ForestSpace.get_or_none(group_id=group_id)

    async def create_space(self, **values: Any) -> ForestSpace:
        return await ForestSpace.create(**values)

    async def avatar(self, user: User) -> ForestAvatar:
        display_name = forest_display_name(user)
        avatar, _ = await ForestAvatar.get_or_create(
            user_id=user.id,
            defaults={"display_name": display_name, "carrot_balance": WELCOME_CARROTS},
        )
        if avatar.display_name != display_name:
            avatar.display_name = display_name
            await avatar.save(update_fields=["display_name", "updated_at"])
        # Wallet (UserWallet) is the single source of truth for the carrot balance shown
        # across the app now. Migrate/grant the balance this row already held (100 for a
        # brand-new avatar, or whatever an existing avatar had accumulated before this
        # switchover) into the wallet exactly once — `credit()` is idempotent on this key,
        # so every call after the first is a no-op.
        await GameRepository().credit(
            user.id,
            avatar.carrot_balance,
            "forest_welcome_bonus",
            str(user.id),
            f"forest-welcome:{user.id}",
        )
        return avatar

    async def sync_existing_avatar_name(self, user: User) -> None:
        """Sync a profile rename without creating an otherwise unused forest avatar."""
        avatar = await ForestAvatar.get_or_none(user_id=user.id)
        display_name = forest_display_name(user)
        if avatar is not None and avatar.display_name != display_name:
            avatar.display_name = display_name
            await avatar.save(update_fields=["display_name", "updated_at"])

    async def avatars(self, users: list[User]) -> dict[int, ForestAvatar]:
        result: dict[int, ForestAvatar] = {}
        for user in users:
            result[user.id] = await self.avatar(user)
        return result

    async def inventory(self, user_id: int) -> list[ForestInventory]:
        return await ForestInventory.filter(user_id=user_id).order_by("acquired_at", "id")

    async def has_item(self, user_id: int, item_code: str) -> bool:
        return await ForestInventory.filter(user_id=user_id, item_code=item_code).exists()

    async def add_item(self, user_id: int, item_code: str, acquired_source: str) -> None:
        await ForestInventory.get_or_create(
            user_id=user_id,
            item_code=item_code,
            defaults={"acquired_source": acquired_source},
        )

    async def objects(self, forest_space_id: int) -> list[ForestObject]:
        return await ForestObject.filter(forest_space_id=forest_space_id).order_by("id")

    async def create_object(self, **values: Any) -> ForestObject:
        return await ForestObject.create(**values)

    async def object(self, forest_space_id: int, object_id: int) -> ForestObject | None:
        return await ForestObject.get_or_none(id=object_id, forest_space_id=forest_space_id)

    async def completed_today(self, user_id: int, today: date) -> int:
        return await ChallengeLog.filter(user_id=user_id, log_date=today, is_completed=True).count()

    async def reward(self, source_key: str) -> ForestReward | None:
        return await ForestReward.get_or_none(source_key=source_key)

    async def create_reward(self, **values: Any) -> ForestReward:
        return await ForestReward.create(**values)
