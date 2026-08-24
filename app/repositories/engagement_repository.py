from __future__ import annotations

from datetime import date
from typing import Any

from tortoise.expressions import Q

from app.models.engagement import (
    ChallengeBarrier,
    Connection,
    ContentProgress,
    EducationContent,
    Encouragement,
    Invitation,
    SharedChallengeGroup,
    SharedChallengeMember,
)
from app.models.health import ChallengeLog, UserChallenge


class EngagementRepository:
    async def create_barrier(self, **values: Any) -> ChallengeBarrier:
        return await ChallengeBarrier.create(**values)

    async def list_barriers(self, user_id: int, start_date: date | None = None) -> list[ChallengeBarrier]:
        query = ChallengeBarrier.filter(user_id=user_id)
        if start_date is not None:
            query = query.filter(log_date__gte=start_date)
        return await query.order_by("-log_date", "-id")

    async def content_catalog(self) -> list[EducationContent]:
        return await EducationContent.filter(is_active=True).order_by("week_number")

    async def content_progress(self, user_id: int) -> dict[int, ContentProgress]:
        items = await ContentProgress.filter(user_id=user_id)
        return {item.content_id: item for item in items}

    async def get_content(self, content_id: int) -> EducationContent | None:
        return await EducationContent.get_or_none(id=content_id, is_active=True)

    async def complete_content(self, **values: Any) -> ContentProgress:
        item, _ = await ContentProgress.update_or_create(
            defaults={key: value for key, value in values.items() if key not in {"user_id", "content_id"}},
            user_id=values["user_id"],
            content_id=values["content_id"],
        )
        return item

    async def create_invitation(self, **values: Any) -> Invitation:
        return await Invitation.create(**values)

    async def pending_invitation_for(self, inviter_user_id: int, invitee_email: str) -> Invitation | None:
        return await Invitation.filter(
            inviter_user_id=inviter_user_id, invitee_email=invitee_email, status="pending"
        ).first()

    async def invitation_by_hash(self, token_hash: str) -> Invitation | None:
        return await Invitation.get_or_none(token_hash=token_hash)

    async def list_invitations(self, user_id: int, email: str) -> tuple[list[Invitation], list[Invitation]]:
        sent = await Invitation.filter(inviter_user_id=user_id).order_by("-created_at")
        received = await Invitation.filter(invitee_email=email).order_by("-created_at")
        return sent, received

    async def create_connection(self, **values: Any) -> Connection:
        item, _ = await Connection.update_or_create(
            defaults={
                "relation_type": values["relation_type"],
                "status": "active",
                "sharing_scope": ["challenge_status"],
                "disconnected_at": None,
            },
            user_a_id=values["user_a_id"],
            user_b_id=values["user_b_id"],
        )
        return item

    async def active_connection(self, first_user_id: int, second_user_id: int) -> Connection | None:
        user_a_id, user_b_id = sorted((first_user_id, second_user_id))
        return await Connection.get_or_none(user_a_id=user_a_id, user_b_id=user_b_id, status="active")

    async def list_connections(self, user_id: int) -> list[Connection]:
        return await Connection.filter(Q(user_a_id=user_id) | Q(user_b_id=user_id), status="active").order_by(
            "-created_at"
        )

    async def connection_for_user(self, connection_id: int, user_id: int) -> Connection | None:
        return await Connection.filter(
            Q(user_a_id=user_id) | Q(user_b_id=user_id), id=connection_id, status="active"
        ).first()

    async def create_shared_group(self, **values: Any) -> SharedChallengeGroup:
        return await SharedChallengeGroup.create(**values)

    async def add_shared_member(self, **values: Any) -> SharedChallengeMember:
        return await SharedChallengeMember.create(**values)

    async def get_shared_member(self, group_id: int, user_id: int) -> SharedChallengeMember | None:
        return await SharedChallengeMember.get_or_none(group_id=group_id, user_id=user_id)

    async def get_shared_group_for_user(self, group_id: int, user_id: int) -> SharedChallengeGroup | None:
        member = await self.get_shared_member(group_id, user_id)
        if member is None:
            return None
        return await SharedChallengeGroup.get_or_none(id=group_id)

    async def list_shared_groups(self, user_id: int) -> list[SharedChallengeGroup]:
        memberships = await SharedChallengeMember.filter(user_id=user_id)
        ids = [item.group_id for item in memberships]
        return [] if not ids else await SharedChallengeGroup.filter(id__in=ids).order_by("-created_at")

    async def shared_members(self, group_id: int) -> list[SharedChallengeMember]:
        return await SharedChallengeMember.filter(group_id=group_id).order_by("id")

    async def completed_days(self, user_id: int, challenge_id: int, start_date: date, end_date: date) -> int:
        selected = await UserChallenge.filter(user_id=user_id, challenge_id=challenge_id)
        ids = [item.id for item in selected]
        if not ids:
            return 0
        logs = await ChallengeLog.filter(
            user_id=user_id,
            user_challenge_id__in=ids,
            log_date__gte=start_date,
            log_date__lte=end_date,
            is_completed=True,
        )
        return len({item.log_date for item in logs})

    async def create_encouragement(self, **values: Any) -> Encouragement:
        return await Encouragement.create(**values)

    async def list_encouragements(self, group_id: int) -> list[Encouragement]:
        return await Encouragement.filter(group_id=group_id).order_by("-created_at", "-id")
