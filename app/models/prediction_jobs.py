from tortoise import fields
from tortoise.models import Model


class PredictionJob(Model):
    """Durable audit record for an asynchronous prediction request."""

    job_id = fields.CharField(max_length=36, primary_key=True)
    task_type = fields.CharField(max_length=50)
    status = fields.CharField(max_length=20, default="queued", db_index=True)
    request_payload = fields.JSONField()
    result = fields.JSONField(null=True)
    error = fields.TextField(null=True)
    worker_name = fields.CharField(max_length=100, null=True)
    attempts = fields.IntField(default=0)
    model_version = fields.CharField(max_length=100, null=True)
    model_key = fields.CharField(max_length=100, default="diabetes_incidence")
    feature_schema_version = fields.CharField(max_length=100, null=True)
    input_schema_version = fields.CharField(max_length=100, null=True)
    preprocessing_version = fields.CharField(max_length=100, null=True)
    target_definition_version = fields.CharField(max_length=100, null=True)
    calibration_version = fields.CharField(max_length=100, null=True)
    model_artifact_digest = fields.CharField(max_length=128, null=True)
    threshold_version = fields.CharField(max_length=100, null=True)
    user_id = fields.BigIntField(null=True, db_index=True)
    health_checkup_id = fields.BigIntField(null=True, db_index=True)
    input_as_of_date = fields.DateField(null=True)
    prediction_id = fields.BigIntField(null=True)
    error_code = fields.CharField(max_length=50, null=True)
    retryable = fields.BooleanField(default=False)
    retry_after_seconds = fields.IntField(null=True)
    deadline_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)

    class Meta:
        table = "prediction_jobs"
