from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.apis.responses import envelope
from app.dependencies.security import get_request_user
from app.dtos.engagement import (
    ChallengeBarrierCreateRequest,
    ConnectionSharingRequest,
    ContentCompleteRequest,
    EncouragementCreateRequest,
    InvitationAcceptRequest,
    InvitationCreateRequest,
    SharedChallengeCreateRequest,
)
from app.models.users import User
from app.services.engagement import EngagementService

engagement_router = APIRouter(tags=["Behavior change and together"])


@engagement_router.post("/user-challenges/{user_challenge_id}/barriers", status_code=status.HTTP_201_CREATED)
async def create_barrier(
    user_challenge_id: int,
    request: ChallengeBarrierCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    return envelope(await EngagementService().record_barrier(user, user_challenge_id, request))


@engagement_router.get("/weekly-reports/current")
async def current_weekly_report(user: Annotated[User, Depends(get_request_user)]) -> dict[str, object]:
    return envelope(await EngagementService().weekly_report(user))


@engagement_router.get("/education-contents")
async def list_education_contents(user: Annotated[User, Depends(get_request_user)]) -> dict[str, object]:
    return envelope(await EngagementService().education_contents(user))


@engagement_router.put("/education-contents/{content_id}/progress")
async def complete_education_content(
    content_id: int,
    request: ContentCompleteRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    return envelope(await EngagementService().complete_content(user, content_id, request))


@engagement_router.post("/invitations", status_code=status.HTTP_201_CREATED)
async def create_invitation(
    request: InvitationCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    return envelope(await EngagementService().create_invitation(user, request))


@engagement_router.get("/invitations")
async def list_invitations(user: Annotated[User, Depends(get_request_user)]) -> dict[str, object]:
    return envelope(await EngagementService().invitation_list(user))


@engagement_router.post("/invitations/accept")
async def accept_invitation(
    request: InvitationAcceptRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    return envelope(await EngagementService().accept_invitation(user, request.token))


@engagement_router.get("/connections")
async def list_connections(user: Annotated[User, Depends(get_request_user)]) -> dict[str, object]:
    return envelope(await EngagementService().connections(user))


@engagement_router.patch("/connections/{connection_id}/sharing-scope")
async def update_connection_sharing(
    connection_id: int,
    request: ConnectionSharingRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    return envelope(await EngagementService().update_connection_sharing(user, connection_id, request))


@engagement_router.delete("/connections/{connection_id}")
async def disconnect_connection(
    connection_id: int, user: Annotated[User, Depends(get_request_user)]
) -> dict[str, object]:
    return envelope(await EngagementService().close_connection(user, connection_id))


@engagement_router.post("/connections/{connection_id}/block")
async def block_connection(connection_id: int, user: Annotated[User, Depends(get_request_user)]) -> dict[str, object]:
    return envelope(await EngagementService().close_connection(user, connection_id, blocked=True))


@engagement_router.post("/shared-challenge-groups", status_code=status.HTTP_201_CREATED)
async def create_shared_challenge_group(
    request: SharedChallengeCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    service = EngagementService()
    group = await service.create_shared_group(user, request)
    return envelope(await service.group_payload(group, user.id))


@engagement_router.get("/shared-challenge-groups")
async def list_shared_challenge_groups(user: Annotated[User, Depends(get_request_user)]) -> dict[str, object]:
    return envelope(await EngagementService().list_shared_groups(user))


@engagement_router.post("/shared-challenge-groups/{group_id}/accept")
async def accept_shared_challenge_group(
    group_id: int,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    return envelope(await EngagementService().accept_shared_group(user, group_id))


@engagement_router.post("/shared-challenge-groups/{group_id}/encouragements", status_code=status.HTTP_201_CREATED)
async def create_encouragement(
    group_id: int,
    request: EncouragementCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    return envelope(await EngagementService().encourage(user, group_id, request))
