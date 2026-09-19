from app.models.challenge_v2 import ChallengeV2Assignment, ChallengeV2Day, ChallengeV2Session


class ChallengeV2Repository:
    async def day(self, user_id, assigned_date):
        return await ChallengeV2Day.get_or_none(user_id=user_id, assigned_date=assigned_date)

    async def assignments(self, day_id):
        return await ChallengeV2Assignment.filter(day_id=day_id).exclude(status="replaced").order_by("slot")

    async def sessions(self, assignment_id):
        return await ChallengeV2Session.filter(assignment_id=assignment_id).order_by("session_index")
