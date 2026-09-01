from tortoise import fields
from tortoise.models import Model


class ModelRegistry(Model):
    """DB-backed model registry entry (docs/ERD_v8.dbml).

    Today only `diabetes_incidence` is fully wired via `.env` +
    `app.prediction.contracts.ACTIVE_MODEL` (kept as-is to avoid touching a
    working path). This table is the source of truth for *additional* model
    keys such as `diabetes_lifetime_risk` (v3.0 연령별 당뇨 위험 전망), which
    have no approved artifact yet. A model_key only becomes usable once an
    operator inserts an `is_active=True` row here with a verified artifact.
    """

    id = fields.BigIntField(primary_key=True)
    model_key = fields.CharField(max_length=100, db_index=True)
    model_version = fields.CharField(max_length=100)
    model_type = fields.CharField(max_length=40, default="binary_classifier")
    promotion_status = fields.CharField(max_length=40, default="candidate_only")
    artifact_local_path = fields.CharField(max_length=255, null=True)
    artifact_sha256 = fields.CharField(max_length=128, null=True)
    feature_schema_version = fields.CharField(max_length=100)
    target_definition_version = fields.CharField(max_length=100, null=True)
    calibration_version = fields.CharField(max_length=100, null=True)
    threshold_version = fields.CharField(max_length=100, null=True)
    min_age = fields.IntField()
    max_age = fields.IntField(null=True)
    model_population = fields.CharField(max_length=120)
    outcome_definition = fields.CharField(max_length=200, null=True)
    is_active = fields.BooleanField(default=False, db_index=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "model_registry"
        unique_together = (("model_key", "model_version"),)

    @classmethod
    async def active_for(cls, model_key: str) -> "ModelRegistry | None":
        return await cls.filter(model_key=model_key, is_active=True).order_by("-created_at").first()
