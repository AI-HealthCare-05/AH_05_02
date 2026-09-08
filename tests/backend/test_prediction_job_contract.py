import asyncio

from ai_worker.db import CREATE_PREDICTION_JOBS_TABLE
from app.models.prediction_jobs import PredictionJob


def test_prediction_job_model_and_worker_use_the_canonical_table() -> None:
    assert PredictionJob._meta.db_table == "prediction_jobs"
    assert "CREATE TABLE IF NOT EXISTS prediction_jobs" in CREATE_PREDICTION_JOBS_TABLE
    for field_name in (
        "input_schema_version",
        "preprocessing_version",
        "target_definition_version",
        "calibration_version",
        "model_artifact_digest",
    ):
        assert field_name in PredictionJob._meta.fields_map
        assert field_name in CREATE_PREDICTION_JOBS_TABLE


def test_prediction_job_migration_bootstraps_the_canonical_table() -> None:
    module = __import__(
        "app.core.db.migrations.models.5_20260825000000_rename_ai_jobs_to_prediction_jobs",
        fromlist=["upgrade"],
    )

    sql = asyncio.run(module.upgrade(None))

    assert "CREATE TABLE IF NOT EXISTS `prediction_jobs`" in sql
    assert "idx_prediction_jobs_status" in sql


def test_provenance_migration_keeps_internal_values_out_of_public_contract() -> None:
    module = __import__(
        "app.core.db.migrations.models.6_20260825010000_prediction_provenance_and_risk_factors",
        fromlist=["upgrade"],
    )
    sql = asyncio.run(module.upgrade(None))

    assert "class_probabilities" in sql
    assert "decision_threshold" in sql
    assert "CREATE TABLE IF NOT EXISTS `risk_factors`" in sql
    assert "explanation_version" in sql
