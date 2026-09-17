# Health reanalysis storage compatibility

The current health form no longer collects `self_rated_health` or
`meal_count_yesterday`. The storage DTO and database now allow these legacy
fields to be null. Existing values remain unchanged; new records do not invent
answers to satisfy the old storage contract.

Apply migration `26_20260917120000_optional_legacy_health_fields` before serving
the updated API against an existing database. Fresh databases use nullable
columns from the model definition.

Verification: `tests/test_mvp_demo_flow.py` runs the authenticated consent,
eligibility, health storage, prediction and challenge flow both with and without
the legacy fields. On 8025, verify Home > health management > new record > edit >
review > save and reanalyse, then confirm the analysis screen opens.
