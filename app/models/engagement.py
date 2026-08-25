from tortoise import fields
from tortoise.models import Model


class ChallengeBarrier(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    user_challenge_id = fields.BigIntField(db_index=True)
    log_date = fields.DateField()
    reason_code = fields.CharField(max_length=40)
    adjustment_code = fields.CharField(max_length=40, null=True)
    note = fields.CharField(max_length=200, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "challenge_barriers"


class EducationContent(Model):
    id = fields.BigIntField(primary_key=True)
    slug = fields.CharField(max_length=80, unique=True)
    week_number = fields.IntField()
    title = fields.CharField(max_length=120)
    summary = fields.TextField()
    quiz_question = fields.CharField(max_length=300)
    quiz_answer = fields.CharField(max_length=100)
    source_title = fields.CharField(max_length=200)
    source_url = fields.CharField(max_length=500)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "education_contents"


class ContentProgress(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    content_id = fields.BigIntField(db_index=True)
    quiz_answer = fields.CharField(max_length=100)
    is_correct = fields.BooleanField()
    completed_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "content_progress"
        unique_together = (("user_id", "content_id"),)


class Invitation(Model):
    id = fields.BigIntField(primary_key=True)
    inviter_user_id = fields.BigIntField(db_index=True)
    invitee_email = fields.CharField(max_length=255, db_index=True)
    token_hash = fields.CharField(max_length=64, unique=True)
    relation_type = fields.CharField(max_length=20)
    status = fields.CharField(max_length=20, default="pending", db_index=True)
    expires_at = fields.DatetimeField()
    accepted_by_user_id = fields.BigIntField(null=True)
    accepted_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "invitations"


class Connection(Model):
    id = fields.BigIntField(primary_key=True)
    user_a_id = fields.BigIntField(db_index=True)
    user_b_id = fields.BigIntField(db_index=True)
    relation_type = fields.CharField(max_length=20)
    status = fields.CharField(max_length=20, default="active", db_index=True)
    sharing_scope = fields.JSONField(default=lambda: ["challenge_status"])
    created_at = fields.DatetimeField(auto_now_add=True)
    disconnected_at = fields.DatetimeField(null=True)

    class Meta:
        table = "connections"
        unique_together = (("user_a_id", "user_b_id"),)


class SharedChallengeGroup(Model):
    id = fields.BigIntField(primary_key=True)
    owner_user_id = fields.BigIntField(db_index=True)
    challenge_id = fields.BigIntField(db_index=True)
    title = fields.CharField(max_length=100)
    common_goal = fields.CharField(max_length=150)
    start_date = fields.DateField()
    end_date = fields.DateField()
    status = fields.CharField(max_length=20, default="active", db_index=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "shared_challenge_groups"


class SharedChallengeMember(Model):
    id = fields.BigIntField(primary_key=True)
    group_id = fields.BigIntField(db_index=True)
    user_id = fields.BigIntField(db_index=True)
    personal_goal = fields.CharField(max_length=100)
    status = fields.CharField(max_length=20, default="pending", db_index=True)
    joined_at = fields.DatetimeField(auto_now_add=True)
    accepted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "shared_challenge_members"
        unique_together = (("group_id", "user_id"),)


class Encouragement(Model):
    id = fields.BigIntField(primary_key=True)
    group_id = fields.BigIntField(db_index=True)
    sender_user_id = fields.BigIntField(db_index=True)
    recipient_user_id = fields.BigIntField(db_index=True)
    template_code = fields.CharField(max_length=30)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "encouragements"
