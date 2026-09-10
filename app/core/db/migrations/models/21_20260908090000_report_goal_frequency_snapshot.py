from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = False

# Best-effort frequency classification for the existing 29-item production catalog
# (app/services/challenges.py::CHALLENGE_CATALOG). A challenge is only classified here
# when its own title/daily_goal text states an explicit day or week cadence ("하루 1회",
# "주 2회", ...); every other challenge is left with frequency=NULL ("unconfirmed" in the
# API), including challenges whose goal is a cumulative duration rather than a day-count
# (e.g. "주 150분 움직이기" — completing this isn't "N days out of 7", so it does not fit
# the daily/weekly day-count model at all and must not be forced into either bucket).
# Full per-challenge rationale: docs/frontend/REPORT_CHALLENGE_FREQUENCY_MAPPING_20260908.md
DAILY_TARGET_1 = (
    "regular_meals_log",
    "activity_check",
    "two_minute_activity_break",
    "reduce_processed_food",
    "daily_meal_review",
    "smoke_free_today",
)
WEEKLY_TARGETS = {
    "weekly_weight_log": 1,
    "strength_twice_weekly": 2,
    "balance_flex_twice_weekly": 2,
    "weekly_habit_review": 1,
    "walk_three_days_weekly": 3,
    "unsweetened_drink_five_days": 5,
    "vegetables_five_days": 5,
    "whole_grain_three_times": 3,
    "weekly_weight_trend": 1,
}


async def upgrade(db: BaseDBAsyncClient) -> str:
    statements = [
        """
        ALTER TABLE `challenges`
            ADD COLUMN `frequency` VARCHAR(20) NULL AFTER `daily_goal`,
            ADD COLUMN `target_count` INT NULL AFTER `frequency`,
            ADD COLUMN `definition_version` VARCHAR(20) NOT NULL DEFAULT 'v1' AFTER `target_count`;
        """,
        """
        ALTER TABLE `user_challenges`
            ADD COLUMN `frequency` VARCHAR(20) NULL AFTER `challenge_id`,
            ADD COLUMN `target_count` INT NULL AFTER `frequency`,
            ADD COLUMN `title_snapshot` VARCHAR(100) NULL AFTER `target_count`,
            ADD COLUMN `definition_version` VARCHAR(20) NULL AFTER `title_snapshot`;
        """,
    ]
    for code in DAILY_TARGET_1:
        statements.append(f"UPDATE `challenges` SET `frequency`='daily', `target_count`=1 WHERE `code`='{code}';")
    for code, target in WEEKLY_TARGETS.items():
        statements.append(
            f"UPDATE `challenges` SET `frequency`='weekly', `target_count`={target} WHERE `code`='{code}';"
        )
    # Best-effort backfill for selections made before this migration: copy the snapshot
    # from the current catalog row. This cannot recover whatever definition was actually in
    # effect at the historical selection time (nothing was stored then), so it is a one-time
    # approximation, not a true historical snapshot, for any user_challenge created before today.
    statements.append(
        """
        UPDATE `user_challenges` AS uc
        JOIN `challenges` AS c ON c.id = uc.challenge_id
        SET uc.frequency = c.frequency,
            uc.target_count = c.target_count,
            uc.title_snapshot = c.title,
            uc.definition_version = c.definition_version
        WHERE uc.frequency IS NULL AND uc.title_snapshot IS NULL;
        """
    )
    return "\n".join(statements)


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `user_challenges`
            DROP COLUMN `definition_version`,
            DROP COLUMN `title_snapshot`,
            DROP COLUMN `target_count`,
            DROP COLUMN `frequency`;
        ALTER TABLE `challenges`
            DROP COLUMN `definition_version`,
            DROP COLUMN `target_count`,
            DROP COLUMN `frequency`;
    """
