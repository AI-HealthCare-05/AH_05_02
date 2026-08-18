from tortoise import fields
from tortoise.models import Model


class AIJob(Model):
    job_id = fields.CharField(max_length=36, pk=True)
    task_type = fields.CharField(max_length=50)
    status = fields.CharField(max_length=20, default="queued", index=True)
    request_payload = fields.JSONField()
    result = fields.JSONField(null=True)
    error = fields.TextField(null=True)
    worker_name = fields.CharField(max_length=100, null=True)
    attempts = fields.IntField(default=0)
    model_version = fields.CharField(max_length=100, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)

    class Meta:
        table = "ai_jobs"
