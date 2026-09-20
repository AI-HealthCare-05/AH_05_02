from tortoise import fields
from tortoise.models import Model


class WearableConnection(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    provider = fields.CharField(max_length=40)
    status = fields.CharField(max_length=20, default="active", db_index=True)
    scopes = fields.JSONField(default=lambda: ["activity"])
    connected_at = fields.DatetimeField(auto_now_add=True)
    disconnected_at = fields.DatetimeField(null=True)

    class Meta:
        table = "wearable_connections"
        unique_together = (("user_id", "provider"),)


class WearableDailySummary(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    connection_id = fields.BigIntField(db_index=True)
    summary_date = fields.DateField()
    steps = fields.IntField(null=True)
    active_minutes = fields.IntField(null=True)
    sleep_minutes = fields.IntField(null=True)
    resting_heart_rate = fields.IntField(null=True)
    source = fields.CharField(max_length=40)
    quality = fields.CharField(max_length=20, default="user_confirmed")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "wearable_daily_summaries"
        unique_together = (("user_id", "connection_id", "summary_date"),)


class FoodAnalysis(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    image_name = fields.CharField(max_length=200)
    provider = fields.CharField(max_length=40, default="development_mock")
    predicted_category = fields.CharField(max_length=50)
    confidence = fields.FloatField(null=True)
    confirmed_category = fields.CharField(max_length=50, null=True)
    status = fields.CharField(max_length=30, default="needs_confirmation")
    created_at = fields.DatetimeField(auto_now_add=True)
    confirmed_at = fields.DatetimeField(null=True)

    class Meta:
        table = "food_analyses"


class OcrDraft(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    document_name = fields.CharField(max_length=200)
    provider = fields.CharField(max_length=40, default="development_mock")
    extracted_fields = fields.JSONField(default=dict)
    status = fields.CharField(max_length=30, default="needs_confirmation")
    created_at = fields.DatetimeField(auto_now_add=True)
    confirmed_at = fields.DatetimeField(null=True)

    class Meta:
        table = "ocr_drafts"


class NotificationPreference(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(unique=True)
    in_app_enabled = fields.BooleanField(default=True)
    challenge_reminder_enabled = fields.BooleanField(default=True)
    weekly_report_enabled = fields.BooleanField(default=True)
    quiet_start_hour = fields.IntField(default=21)
    quiet_end_hour = fields.IntField(default=8)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "notification_preferences"


class InAppNotification(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    notification_type = fields.CharField(max_length=40)
    title = fields.CharField(max_length=100)
    message = fields.CharField(max_length=300)
    is_read = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    read_at = fields.DatetimeField(null=True)

    class Meta:
        table = "in_app_notifications"
