from __future__ import annotations

import hashlib
import secrets
from collections import Counter
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException, status
from tortoise.transactions import in_transaction

from app.dtos.engagement import (
    ChallengeBarrierCreateRequest,
    ContentCompleteRequest,
    EncouragementCreateRequest,
    InvitationCreateRequest,
    SharedChallengeCreateRequest,
)
from app.models.engagement import EducationContent, Invitation, SharedChallengeGroup
from app.models.users import User
from app.repositories.engagement_repository import EngagementRepository
from app.repositories.health_repository import HealthRepository

EDUCATION_CATALOG = (
    {
        "slug": "week-1-understand-risk",
        "week_number": 1,
        "title": "위험 선별 결과 이해하기",
        "summary": "예측 결과는 향후 위험을 살펴보는 건강교육 정보이며 당뇨병 진단이 아닙니다.",
        "quiz_question": "이 서비스의 예측 결과는 당뇨병 진단인가요?",
        "quiz_answer": "아니요",
    },
    {
        "slug": "week-2-daily-activity",
        "week_number": 2,
        "title": "일상에서 활동 늘리기",
        "summary": "실천 가능한 작은 활동 목표를 정하고 기록하면서 자신에게 맞는 습관을 찾습니다.",
        "quiz_question": "목표가 너무 어렵다면 작은 목표로 조정해도 되나요?",
        "quiz_answer": "네",
    },
    {
        "slug": "week-3-meal-routine",
        "week_number": 3,
        "title": "식사 습관 기록하기",
        "summary": "식사 기록을 통해 자신의 패턴을 확인하되 특정 식품을 치료법처럼 표현하지 않습니다.",
        "quiz_question": "식사 기록만으로 당뇨병 치료 효과를 판단할 수 있나요?",
        "quiz_answer": "아니요",
    },
    {
        "slug": "week-4-restart",
        "week_number": 4,
        "title": "중단해도 다시 시작하기",
        "summary": "실천하지 못한 이유를 확인하고 목표·시간·챌린지를 조정해 다시 시작합니다.",
        "quiz_question": "하루 실패하면 4주 챌린지를 모두 포기해야 하나요?",
        "quiz_answer": "아니요",
    },
)
EDUCATION_SOURCE = {
    "source_title": "CDC PreventT2 Curriculum",
    "source_url": "https://www.cdc.gov/diabetes-prevention/php/lifestyle-change-resources/t2-curriculum.html",
}

BARRIER_SUGGESTIONS = {
    "no_time": ("change_time", "실천 시간을 일정에 맞게 바꿔보세요."),
    "forgot": ("restart_tomorrow", "눈에 잘 보이는 곳에 목표를 두고 내일부터 다시 시작해 보세요."),
    "physical_discomfort": ("pause", "무리하지 말고 중단하세요. 증상이 지속되면 의료진과 상의하세요."),
    "goal_too_hard": ("reduce_goal", "목표를 더 작고 실천 가능한 수준으로 조정해 보세요."),
    "environment": ("change_challenge", "현재 환경에서 가능한 다른 챌린지로 바꿔보세요."),
    "other": ("restart_tomorrow", "이유를 기록하고 다음 날 다시 시작해 보세요."),
}

ENCOURAGEMENT_TEXT = {
    "cheer": "오늘도 함께 천천히 실천해요!",
    "great_job": "오늘 실천 정말 잘했어요!",
    "keep_going": "완벽하지 않아도 괜찮아요. 계속 이어가요!",
    "together": "같이 하니까 더 든든해요!",
}


class EngagementService:
    def __init__(self) -> None:
        self.repo = EngagementRepository()
        self.health_repo = HealthRepository()

    async def record_barrier(
        self, user: User, user_challenge_id: int, request: ChallengeBarrierCreateRequest
    ) -> dict[str, object]:
        selected = await self.health_repo.get_user_challenge(user_challenge_id, user.id)
        if selected is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="선택한 챌린지를 찾을 수 없습니다.")
        suggested_code, suggestion = BARRIER_SUGGESTIONS[request.reason_code]
        item = await self.repo.create_barrier(
            user_id=user.id,
            user_challenge_id=user_challenge_id,
            **request.model_dump(),
        )
        return {
            "barrier_id": item.id,
            "reason_code": item.reason_code,
            "selected_adjustment": item.adjustment_code,
            "suggested_adjustment": suggested_code,
            "suggestion": suggestion,
            "medical_notice": "몸이 불편한 경우 챌린지보다 휴식과 의료진의 안내를 우선하세요.",
        }

    async def weekly_report(self, user: User) -> dict[str, object]:
        cycle = await self.health_repo.active_cycle(user.id)
        if cycle is None:
            return {
                "status": "empty",
                "message": "진행 중인 챌린지를 시작하면 주간 리포트를 확인할 수 있습니다.",
                "disclaimer": "생활습관 기록은 진단이나 치료 효과를 의미하지 않습니다.",
            }
        today = min(date.today(), cycle.end_date)
        start = max(cycle.start_date, today - timedelta(days=6))
        selected = await self.health_repo.list_user_challenges(cycle.id, user.id)
        catalog = await self.health_repo.challenge_map([item.challenge_id for item in selected])
        rows = []
        for item in selected:
            logs = await self.health_repo.logs_for_user_challenge(item.id, user.id, start, today)
            completed = sum(1 for log in logs if log.is_completed)
            planned = max(0, (today - start).days + 1)
            rows.append(
                {
                    "user_challenge_id": item.id,
                    "title": catalog[item.challenge_id].title,
                    "completed": completed,
                    "planned": planned,
                    "completion_rate": round(completed / planned * 100, 1) if planned else 0.0,
                }
            )
        barriers = await self.repo.list_barriers(user.id, start)
        common_reason = Counter(item.reason_code for item in barriers).most_common(1)
        suggested_code, suggestion = (
            BARRIER_SUGGESTIONS[common_reason[0][0]]
            if common_reason
            else ("restart_tomorrow", "현재 목표를 이어가세요.")
        )
        total_completed = sum(row["completed"] for row in rows)
        total_planned = sum(row["planned"] for row in rows)
        return {
            "status": "ready",
            "period": {"start_date": start, "end_date": today},
            "completion": {
                "completed": total_completed,
                "planned": total_planned,
                "rate": round(total_completed / total_planned * 100, 1) if total_planned else 0.0,
            },
            "best_habit": max(rows, key=lambda row: row["completion_rate"], default=None),
            "needs_support": min(rows, key=lambda row: row["completion_rate"], default=None),
            "challenge_details": rows,
            "barrier_summary": dict(Counter(item.reason_code for item in barriers)),
            "next_adjustment": {"code": suggested_code, "message": suggestion},
            "disclaimer": "기록 변화와 수행률은 질병 위험 감소, 진단 또는 치료 효과를 의미하지 않습니다.",
        }

    async def ensure_education_catalog(self) -> list[EducationContent]:
        for content in EDUCATION_CATALOG:
            await EducationContent.update_or_create(
                defaults={**content, **EDUCATION_SOURCE, "is_active": True}, slug=content["slug"]
            )
        return await self.repo.content_catalog()

    async def education_contents(self, user: User) -> dict[str, object]:
        items = await self.ensure_education_catalog()
        progress = await self.repo.content_progress(user.id)
        return {
            "items": [
                {
                    "content_id": item.id,
                    "week_number": item.week_number,
                    "title": item.title,
                    "summary": item.summary,
                    "quiz_question": item.quiz_question,
                    "completed": item.id in progress,
                    "is_correct": progress[item.id].is_correct if item.id in progress else None,
                    "source": {"title": item.source_title, "url": item.source_url},
                }
                for item in items
            ],
            "medical_notice": "교육 콘텐츠는 일반 건강정보이며 진단·처방을 대신하지 않습니다.",
        }

    async def complete_content(self, user: User, content_id: int, request: ContentCompleteRequest) -> dict[str, object]:
        content = await self.repo.get_content(content_id)
        if content is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="교육 콘텐츠를 찾을 수 없습니다.")
        normalized = request.quiz_answer.strip().casefold()
        is_correct = normalized == content.quiz_answer.strip().casefold()
        progress = await self.repo.complete_content(
            user_id=user.id,
            content_id=content.id,
            quiz_answer=request.quiz_answer,
            is_correct=is_correct,
        )
        return {"content_id": content.id, "completed_at": progress.completed_at, "is_correct": is_correct}

    async def create_invitation(self, user: User, request: InvitationCreateRequest) -> dict[str, object]:
        email = str(request.invitee_email).strip().lower()
        if email == user.email.lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="자기 자신을 초대할 수 없습니다."
            )
        existing = await self.repo.pending_invitation_for(user.id, email)
        if existing is not None and existing.expires_at > datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="아직 유효한 초대가 있습니다.")
        raw_token = secrets.token_urlsafe(32)
        item = await self.repo.create_invitation(
            inviter_user_id=user.id,
            invitee_email=email,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            relation_type=request.relation_type,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        return {
            "invitation_id": item.id,
            "invitee_email": item.invitee_email,
            "relation_type": item.relation_type,
            "token": raw_token,
            "expires_at": item.expires_at,
            "sharing_scope": ["challenge_status"],
            "notice": "초대 토큰은 이 응답에서만 확인할 수 있습니다. 건강정보와 예측 결과는 공유되지 않습니다.",
        }

    async def accept_invitation(self, user: User, raw_token: str) -> dict[str, object]:
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        item = await self.repo.invitation_by_hash(token_hash)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="초대를 찾을 수 없습니다.")
        if item.status != "pending" or item.expires_at <= datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="만료되었거나 처리된 초대입니다.")
        if item.invitee_email.lower() != user.email.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="초대받은 계정으로 로그인해 주세요.")
        user_a_id, user_b_id = sorted((item.inviter_user_id, user.id))
        async with in_transaction():
            connection = await self.repo.create_connection(
                user_a_id=user_a_id, user_b_id=user_b_id, relation_type=item.relation_type
            )
            item.status = "accepted"
            item.accepted_by_user_id = user.id
            item.accepted_at = datetime.now(UTC)
            await item.save(update_fields=["status", "accepted_by_user_id", "accepted_at"])
        return {
            "connection_id": connection.id,
            "relation_type": connection.relation_type,
            "sharing_scope": connection.sharing_scope,
        }

    async def invitation_list(self, user: User) -> dict[str, object]:
        sent, received = await self.repo.list_invitations(user.id, user.email.lower())

        def payload(item: Invitation) -> dict[str, object]:
            return {
                "invitation_id": item.id,
                "invitee_email": item.invitee_email,
                "relation_type": item.relation_type,
                "status": item.status,
                "expires_at": item.expires_at,
                "created_at": item.created_at,
            }

        return {"sent": [payload(item) for item in sent], "received": [payload(item) for item in received]}

    async def connections(self, user: User) -> dict[str, object]:
        items = await self.repo.list_connections(user.id)
        return {
            "items": [
                {
                    "connection_id": item.id,
                    "connected_user_id": item.user_b_id if item.user_a_id == user.id else item.user_a_id,
                    "relation_type": item.relation_type,
                    "sharing_scope": item.sharing_scope,
                    "health_data_shared": False,
                }
                for item in items
            ]
        }

    async def create_shared_group(self, user: User, request: SharedChallengeCreateRequest) -> SharedChallengeGroup:
        challenges = await self.health_repo.challenge_map([request.challenge_id])
        if request.challenge_id not in challenges:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지를 찾을 수 없습니다.")
        for member in request.members:
            if member.user_id == user.id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="본인은 별도로 추가하지 않습니다."
                )
            if await self.repo.active_connection(user.id, member.user_id) is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="연결된 가족·친구만 참여시킬 수 있습니다."
                )
        async with in_transaction():
            group = await self.repo.create_shared_group(
                owner_user_id=user.id,
                challenge_id=request.challenge_id,
                title=request.title,
                common_goal=request.common_goal,
                start_date=request.start_date,
                end_date=request.end_date,
            )
            await self.repo.add_shared_member(
                group_id=group.id,
                user_id=user.id,
                personal_goal=request.owner_goal,
                status="active",
                accepted_at=datetime.now(UTC),
            )
            for member in request.members:
                await self.repo.add_shared_member(group_id=group.id, **member.model_dump())
        return group

    async def group_payload(self, group: SharedChallengeGroup, user_id: int) -> dict[str, object]:
        members = await self.repo.shared_members(group.id)
        progress = [
            {
                "user_id": member.user_id,
                "personal_goal": member.personal_goal,
                "status": member.status,
                "completed_days": await self.repo.completed_days(
                    member.user_id, group.challenge_id, group.start_date, min(date.today(), group.end_date)
                )
                if member.status == "active"
                else 0,
                "is_me": member.user_id == user_id,
            }
            for member in members
        ]
        encouragements = await self.repo.list_encouragements(group.id)
        return {
            "group_id": group.id,
            "title": group.title,
            "challenge_id": group.challenge_id,
            "common_goal": group.common_goal,
            "start_date": group.start_date,
            "end_date": group.end_date,
            "status": group.status,
            "members": progress,
            "encouragements": [
                {
                    "encouragement_id": item.id,
                    "sender_user_id": item.sender_user_id,
                    "recipient_user_id": item.recipient_user_id,
                    "template_code": item.template_code,
                    "message": ENCOURAGEMENT_TEXT[item.template_code],
                    "created_at": item.created_at,
                }
                for item in encouragements
            ],
            "sharing_notice": "공동 챌린지에는 수행 상태만 공유되며 건강정보·예측 결과는 포함되지 않습니다.",
        }

    async def list_shared_groups(self, user: User) -> dict[str, object]:
        groups = await self.repo.list_shared_groups(user.id)
        return {"items": [await self.group_payload(group, user.id) for group in groups]}

    async def accept_shared_group(self, user: User, group_id: int) -> dict[str, object]:
        member = await self.repo.get_shared_member(group_id, user.id)
        if member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공동 챌린지 초대를 찾을 수 없습니다.")
        if member.status != "active":
            member.status = "active"
            member.accepted_at = datetime.now(UTC)
            await member.save(update_fields=["status", "accepted_at"])
        group = await self.repo.get_shared_group_for_user(group_id, user.id)
        return await self.group_payload(group, user.id)

    async def encourage(self, user: User, group_id: int, request: EncouragementCreateRequest) -> dict[str, object]:
        group = await self.repo.get_shared_group_for_user(group_id, user.id)
        if group is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공동 챌린지를 찾을 수 없습니다.")
        members = await self.repo.shared_members(group.id)
        member_ids = {item.user_id for item in members if item.status == "active"}
        if request.recipient_user_id not in member_ids or request.recipient_user_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="응원을 보낼 참여자를 확인해 주세요."
            )
        item = await self.repo.create_encouragement(
            group_id=group.id,
            sender_user_id=user.id,
            **request.model_dump(),
        )
        return {
            "encouragement_id": item.id,
            "template_code": item.template_code,
            "message": ENCOURAGEMENT_TEXT[item.template_code],
            "created_at": item.created_at,
        }
