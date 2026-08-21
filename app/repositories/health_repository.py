from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.models.health import (
    Challenge,
    ChallengeCycle,
    ChallengeLog,
    Consent,
    EligibilityCheck,
    FollowUpAction,
    HealthCheckup,
    Prediction,
    UserChallenge,
)


class HealthRepository:
    async def active_consent(self, user_id: int) -> Consent | None:
        return await Consent.filter(user_id=user_id, is_agreed=True, withdrawn_at=None).order_by("-agreed_at").first()

    async def create_consent(self, **values: Any) -> Consent:
        return await Consent.create(**values)

    async def list_consents(self, user_id: int) -> list[Consent]:
        return await Consent.filter(user_id=user_id).order_by("-created_at")

    async def get_consent(self, consent_id: int, user_id: int) -> Consent | None:
        return await Consent.get_or_none(id=consent_id, user_id=user_id)

    async def create_eligibility(self, **values: Any) -> EligibilityCheck:
        return await EligibilityCheck.create(**values)

    async def latest_eligibility(self, user_id: int) -> EligibilityCheck | None:
        return await EligibilityCheck.filter(user_id=user_id).order_by("-created_at", "-id").first()

    async def create_checkup(self, **values: Any) -> HealthCheckup:
        return await HealthCheckup.create(**values)

    async def get_checkup(self, checkup_id: int, user_id: int) -> HealthCheckup | None:
        return await HealthCheckup.get_or_none(id=checkup_id, user_id=user_id)

    async def list_checkups(self, user_id: int) -> list[HealthCheckup]:
        return await HealthCheckup.filter(user_id=user_id).order_by("-checkup_date", "-id")

    async def get_prediction(self, prediction_id: int, user_id: int) -> Prediction | None:
        return await Prediction.get_or_none(id=prediction_id, user_id=user_id)

    async def latest_prediction(self, user_id: int) -> Prediction | None:
        return await Prediction.filter(user_id=user_id).order_by("-predicted_at", "-id").first()

    async def list_predictions(self, user_id: int) -> list[Prediction]:
        return await Prediction.filter(user_id=user_id).order_by("-predicted_at", "-id")

    async def active_cycle(self, user_id: int) -> ChallengeCycle | None:
        return await ChallengeCycle.filter(user_id=user_id, status__in=["scheduled", "active"]).order_by("-id").first()

    async def get_cycle(self, cycle_id: int, user_id: int) -> ChallengeCycle | None:
        return await ChallengeCycle.get_or_none(id=cycle_id, user_id=user_id)

    async def list_user_challenges(self, cycle_id: int, user_id: int) -> list[UserChallenge]:
        return await UserChallenge.filter(cycle_id=cycle_id, user_id=user_id).order_by("id")

    async def get_user_challenge(self, user_challenge_id: int, user_id: int) -> UserChallenge | None:
        return await UserChallenge.get_or_none(id=user_challenge_id, user_id=user_id)

    async def logs_for_cycle(self, cycle_id: int, user_id: int) -> list[ChallengeLog]:
        user_challenges = await self.list_user_challenges(cycle_id, user_id)
        ids = [item.id for item in user_challenges]
        if not ids:
            return []
        return await ChallengeLog.filter(user_id=user_id, user_challenge_id__in=ids).order_by("log_date", "id")

    async def logs_for_user_challenge(
        self, user_challenge_id: int, user_id: int, start_date: date | None, end_date: date | None
    ) -> list[ChallengeLog]:
        query = ChallengeLog.filter(user_challenge_id=user_challenge_id, user_id=user_id)
        if start_date is not None:
            query = query.filter(log_date__gte=start_date)
        if end_date is not None:
            query = query.filter(log_date__lte=end_date)
        return await query.order_by("log_date")

    async def upsert_log(
        self, *, user_challenge_id: int, user_id: int, log_date: date, values: dict[str, Any]
    ) -> ChallengeLog:
        item, _ = await ChallengeLog.update_or_create(
            defaults={"user_id": user_id, **values},
            user_challenge_id=user_challenge_id,
            log_date=log_date,
        )
        return item

    async def open_follow_up(self, user_id: int) -> FollowUpAction | None:
        return await FollowUpAction.filter(user_id=user_id, acknowledged_at=None).order_by("-created_at", "-id").first()

    async def list_follow_ups(self, user_id: int) -> list[FollowUpAction]:
        return await FollowUpAction.filter(user_id=user_id).order_by("-created_at", "-id")

    async def get_follow_up(self, action_id: int, user_id: int) -> FollowUpAction | None:
        return await FollowUpAction.get_or_none(id=action_id, user_id=user_id)

    async def stop_active_cycles(self, user_id: int, reason: str) -> int:
        return await ChallengeCycle.filter(user_id=user_id, status__in=["scheduled", "active"]).update(
            status="terminated", ended_reason=reason
        )

    async def count_cycles(self, user_id: int) -> int:
        return await ChallengeCycle.filter(user_id=user_id).count()

    async def challenge_map(self, challenge_ids: list[int] | None = None) -> dict[int, Challenge]:
        query = Challenge.filter(is_active=True)
        if challenge_ids is not None:
            query = query.filter(id__in=challenge_ids)
        return {item.id: item for item in await query.order_by("id")}

    async def acknowledge_follow_up(self, item: FollowUpAction, at: datetime) -> FollowUpAction:
        item.acknowledged_at = at
        await item.save(update_fields=["acknowledged_at"])
        return item
