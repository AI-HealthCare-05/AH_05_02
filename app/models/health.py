from tortoise import fields
from tortoise.models import Model


class Consent(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    consent_item = fields.CharField(max_length=50, default="health_data")
    version = fields.CharField(max_length=30)
    is_agreed = fields.BooleanField(default=True)
    agreed_at = fields.DatetimeField(auto_now_add=True)
    withdrawn_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "consents"


class EligibilityCheck(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    age = fields.IntField()
    has_diabetes_diagnosis = fields.BooleanField(default=False)
    has_urgent_warning_sign = fields.BooleanField(default=False)
    population_in_scope = fields.BooleanField(default=True)
    service_eligible = fields.BooleanField()
    target_segment = fields.CharField(max_length=50)
    model_eligible = fields.BooleanField()
    reason_codes = fields.JSONField(default=list)
    next_action = fields.CharField(max_length=80)
    model_key = fields.CharField(max_length=100)
    model_version = fields.CharField(max_length=100)
    feature_schema_version = fields.CharField(max_length=100)
    threshold_version = fields.CharField(max_length=100)
    safety_copy_version = fields.CharField(max_length=50)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "eligibility_checks"


class HealthCheckup(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    eligibility_check_id = fields.BigIntField(db_index=True)
    checkup_type = fields.CharField(max_length=20, default="initial")
    checkup_date = fields.DateField()
    age = fields.IntField()
    sex = fields.CharField(max_length=10)
    height_cm = fields.FloatField()
    weight_kg = fields.FloatField()
    bmi = fields.FloatField()
    waist_cm = fields.FloatField(null=True)
    systolic_bp = fields.IntField(null=True)
    diastolic_bp = fields.IntField(null=True)
    self_rated_health = fields.CharField(max_length=20)
    meal_count_yesterday = fields.IntField()
    regular_exercise = fields.BooleanField()
    current_smoker = fields.BooleanField()
    current_drinker = fields.BooleanField()
    feature_schema_version = fields.CharField(max_length=100)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "health_checkups"


class Prediction(Model):
    id = fields.BigIntField(primary_key=True)
    job_id = fields.CharField(max_length=36, unique=True)
    user_id = fields.BigIntField(db_index=True)
    health_checkup_id = fields.BigIntField(db_index=True)
    model_key = fields.CharField(max_length=100)
    outcome_definition = fields.CharField(max_length=120)
    result_status = fields.CharField(max_length=40)
    risk_category = fields.CharField(max_length=20, null=True)
    internal_score = fields.FloatField(null=True)
    model_version = fields.CharField(max_length=100)
    feature_schema_version = fields.CharField(max_length=100)
    input_schema_version = fields.CharField(max_length=100)
    preprocessing_version = fields.CharField(max_length=100)
    target_definition_version = fields.CharField(max_length=100)
    calibration_version = fields.CharField(max_length=100)
    model_artifact_digest = fields.CharField(max_length=128, null=True)
    threshold_version = fields.CharField(max_length=100)
    decision_threshold = fields.FloatField(null=True)
    class_probabilities = fields.JSONField(null=True)
    output_status = fields.CharField(max_length=80, default="uncalibrated_research_probability_only")
    model_population = fields.CharField(max_length=120)
    explanation_status = fields.CharField(max_length=40, default="not_available")
    disclaimer = fields.TextField()
    predicted_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "predictions"


class RiskFactor(Model):
    id = fields.BigIntField(primary_key=True)
    prediction_id = fields.BigIntField(db_index=True)
    factor_name = fields.CharField(max_length=100)
    display_name = fields.CharField(max_length=100)
    impact_direction = fields.CharField(max_length=20)
    importance_score = fields.FloatField()
    display_order = fields.IntField()
    is_modifiable = fields.BooleanField(default=False)
    message = fields.TextField()
    explanation_version = fields.CharField(max_length=100)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "risk_factors"


class Challenge(Model):
    id = fields.BigIntField(primary_key=True)
    code = fields.CharField(max_length=50, unique=True)
    title = fields.CharField(max_length=100)
    category = fields.CharField(max_length=30)
    daily_goal = fields.CharField(max_length=50)
    description = fields.TextField()
    safety_copy = fields.TextField()
    source_title = fields.CharField(max_length=200)
    source_url = fields.CharField(max_length=500)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "challenges"


class ChallengeCycle(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    prediction_id = fields.BigIntField(null=True, db_index=True)
    cycle_number = fields.IntField()
    start_date = fields.DateField()
    end_date = fields.DateField()
    status = fields.CharField(max_length=20, default="active", db_index=True)
    ended_reason = fields.CharField(max_length=80, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "challenge_cycles"


class UserChallenge(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    cycle_id = fields.BigIntField(db_index=True)
    challenge_id = fields.BigIntField(db_index=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "user_challenges"


class ChallengeLog(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    user_challenge_id = fields.BigIntField(db_index=True)
    log_date = fields.DateField()
    is_completed = fields.BooleanField()
    value = fields.FloatField(null=True)
    source = fields.CharField(max_length=30, default="self_report")
    note = fields.CharField(max_length=200, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "challenge_logs"
        unique_together = (("user_challenge_id", "log_date"),)


class FollowUpAction(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    trigger_source = fields.CharField(max_length=30)
    trigger_entity_id = fields.BigIntField()
    action_type = fields.CharField(max_length=50, default="medical_guidance")
    reason_code = fields.CharField(max_length=80)
    priority = fields.CharField(max_length=20, default="high")
    safety_copy_version = fields.CharField(max_length=50)
    acknowledged_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "follow_up_actions"


class Feedback(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    context_type = fields.CharField(max_length=30)
    prediction_id = fields.BigIntField(null=True, db_index=True)
    recommendation_id = fields.BigIntField(null=True, db_index=True)
    rating = fields.IntField()
    comment = fields.CharField(max_length=500, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "feedbacks"
