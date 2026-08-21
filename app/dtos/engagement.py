from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

BarrierReason = Literal["no_time", "forgot", "physical_discomfort", "goal_too_hard", "environment", "other"]
AdjustmentCode = Literal["reduce_goal", "change_time", "change_challenge", "pause", "restart_tomorrow"]


class ChallengeBarrierCreateRequest(BaseModel):
    log_date: date
    reason_code: BarrierReason
    adjustment_code: AdjustmentCode | None = None
    note: str | None = Field(default=None, max_length=200)


class ContentCompleteRequest(BaseModel):
    quiz_answer: str = Field(min_length=1, max_length=100)


class InvitationCreateRequest(BaseModel):
    invitee_email: EmailStr
    relation_type: Literal["family", "friend", "guardian"]


class InvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class SharedChallengeMemberRequest(BaseModel):
    user_id: int = Field(gt=0)
    personal_goal: str = Field(min_length=2, max_length=100)


class SharedChallengeCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    challenge_id: int = Field(gt=0)
    start_date: date
    end_date: date
    common_goal: str = Field(min_length=2, max_length=150)
    owner_goal: str = Field(min_length=2, max_length=100)
    members: list[SharedChallengeMemberRequest] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def validate_dates_and_members(self) -> SharedChallengeCreateRequest:
        if self.end_date < self.start_date:
            raise ValueError("종료일은 시작일보다 빠를 수 없습니다.")
        ids = [item.user_id for item in self.members]
        if len(ids) != len(set(ids)):
            raise ValueError("같은 사용자를 중복 초대할 수 없습니다.")
        return self


class EncouragementCreateRequest(BaseModel):
    recipient_user_id: int = Field(gt=0)
    template_code: Literal["cheer", "great_job", "keep_going", "together"]
