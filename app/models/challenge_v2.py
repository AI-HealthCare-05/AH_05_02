from tortoise import fields
from tortoise.models import Model


class ChallengeV2Enrollment(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(unique=True)
    mode = fields.CharField(max_length=20)
    starts_on = fields.DateField()
    preferences = fields.JSONField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "challenge_v2_enrollments"


class ChallengeV2Day(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    assigned_date = fields.DateField()
    cycle_id = fields.BigIntField(null=True)
    policy_version = fields.CharField(max_length=30, default="2.1")
    eligibility_snapshot = fields.JSONField()
    exception_reasons = fields.JSONField(default=list)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "challenge_v2_days"
        unique_together = (("user_id", "assigned_date"),)


class ChallengeV2Assignment(Model):
    id = fields.BigIntField(primary_key=True)
    day_id = fields.BigIntField(db_index=True)
    slot = fields.IntField()
    revision = fields.IntField(default=1)
    replacement_reason = fields.CharField(max_length=30, null=True)
    goal = fields.JSONField()
    status = fields.CharField(max_length=20, default="assigned")
    verification_status = fields.CharField(max_length=20, default="not_required")

    class Meta:
        table = "challenge_v2_assignments"
        unique_together = (("day_id", "slot", "revision"),)


class ChallengeV2Session(Model):
    id = fields.BigIntField(primary_key=True)
    assignment_id = fields.BigIntField(db_index=True)
    session_index = fields.IntField()
    performed_at = fields.DatetimeField()
    values = fields.JSONField()
    recorded_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "challenge_v2_sessions"
        unique_together = (("assignment_id", "session_index"),)


class ChallengeV2Evidence(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    day_id = fields.BigIntField(db_index=True)
    assignment_id = fields.BigIntField(db_index=True)
    evidence_index = fields.IntField()
    content_hash = fields.CharField(max_length=64)
    mime = fields.CharField(max_length=30, default="image/jpeg")
    content = fields.BinaryField(null=True)
    submitted_at = fields.DatetimeField(auto_now_add=True)
    deletion_due_at = fields.DatetimeField()
    verification_status = fields.CharField(max_length=20, default="not_required")
    generation = fields.IntField(default=1)

    class Meta:
        table = "challenge_v2_evidence"
        unique_together = (("day_id", "content_hash"), ("assignment_id", "evidence_index"))


class ChallengeV2Review(Model):
    id = fields.BigIntField(primary_key=True)
    evidence_id = fields.BigIntField(db_index=True)
    evidence_generation = fields.IntField()
    reviewer_id = fields.BigIntField()
    status = fields.CharField(max_length=20)
    criteria_results = fields.JSONField()
    reason = fields.CharField(max_length=500)
    reviewed_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "challenge_v2_reviews"
        unique_together = (("evidence_id", "evidence_generation"),)


class ChallengeV2Reward(Model):
    """Personal reward ledger, separate from group-scoped ForestReward; same wallet/inventory."""

    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    day_id = fields.BigIntField(db_index=True)
    source_key = fields.CharField(max_length=100, unique=True)
    carrot_amount = fields.IntField()
    item_code = fields.CharField(max_length=40, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "challenge_v2_rewards"
