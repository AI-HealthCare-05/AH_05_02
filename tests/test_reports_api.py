from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise import Tortoise

from app.core.db.databases import TORTOISE_APP_MODELS
from app.main import app
from app.models.engagement import ChallengeBarrier
from app.models.health import Challenge, ChallengeCycle, ChallengeLog, UserChallenge
from app.services.challenges import ChallengeService


async def signup_and_login(client: AsyncClient, email: str) -> dict[str, str]:
    signup = {"name": "테스트 사용자", "email": email, "password": "Password123!", "terms_agreed": True}
    response = await client.post("/api/v1/auth/signup", json=signup)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": signup["password"]})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _user_id_by_email(email: str) -> int:
    from app.models.users import User

    user = await User.get(email=email)
    return user.id


async def _make_cycle(user_id: int, start: date, *, codes: list[str], status_: str = "active") -> ChallengeCycle:
    challenges = {c.code: c async for c in Challenge.filter(code__in=codes)}
    cycle_number = await ChallengeCycle.filter(user_id=user_id).count() + 1
    cycle = await ChallengeCycle.create(
        user_id=user_id,
        cycle_number=cycle_number,
        start_date=start,
        end_date=start + timedelta(days=27),
        status=status_,
    )
    for code in codes:
        challenge = challenges[code]
        await UserChallenge.create(
            user_id=user_id,
            cycle_id=cycle.id,
            challenge_id=challenge.id,
            frequency=challenge.frequency,
            target_count=challenge.target_count,
            title_snapshot=challenge.title,
            definition_version=challenge.definition_version,
        )
    return cycle


async def _log(user_id: int, user_challenge_id: int, day: date, completed: bool) -> None:
    await ChallengeLog.update_or_create(
        defaults={"user_id": user_id, "is_completed": completed, "source": "self_report"},
        user_challenge_id=user_challenge_id,
        log_date=day,
    )


async def _barrier(user_id: int, user_challenge_id: int, day: date, reason_code: str) -> ChallengeBarrier:
    return await ChallengeBarrier.create(
        user_id=user_id, user_challenge_id=user_challenge_id, log_date=day, reason_code=reason_code
    )


@asynccontextmanager
async def db_session():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
    await ChallengeService().ensure_catalog()
    try:
        yield
    finally:
        await Tortoise.close_connections()


@pytest.mark.asyncio
async def test_week_period_anchors_to_cycle_start_weekday_and_marks_daily_status() -> None:
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await signup_and_login(client, "week@example.com")
        user_id = await _user_id_by_email("week@example.com")

        # A Wednesday: anchor start date determines the "user week" (R01).
        wednesday = date(2026, 8, 26)
        assert wednesday.weekday() == 2
        cycle = await _make_cycle(user_id, wednesday, codes=["regular_meals_log"])
        user_challenge = await UserChallenge.get(cycle_id=cycle.id)

        # Complete Wed/Thu, explicitly miss Fri, leave the rest unrecorded, "today" = Sat.
        today = wednesday + timedelta(days=3)
        await _log(user_id, user_challenge.id, wednesday, True)
        await _log(user_id, user_challenge.id, wednesday + timedelta(days=1), True)
        await _log(user_id, user_challenge.id, wednesday + timedelta(days=2), False)

        import app.services.reports as reports_module

        reports_module.today_kst = lambda: today  # freeze "as of" for this test

        response = await client.get("/api/v1/reports", params={"period": "week"}, headers=headers)
        assert response.status_code == status.HTTP_200_OK, response.text
        data = response.json()["data"]
        assert data["status"] == "ready"
        assert data["period"]["start_date"] == wednesday.isoformat()
        assert data["period"]["end_date"] == (wednesday + timedelta(days=6)).isoformat()

        challenge = data["challenges"][0]
        windows = {w["start_date"]: w["status"] for w in challenge["goal_windows"]}
        assert windows[wednesday.isoformat()] == "completed"
        assert windows[(wednesday + timedelta(days=1)).isoformat()] == "completed"
        assert windows[(wednesday + timedelta(days=2)).isoformat()] == "not_completed"
        assert windows[today.isoformat()] == "pending"  # today, no log yet
        assert windows[(today + timedelta(days=1)).isoformat()] == "future"
        assert len(challenge["goal_windows"]) == 7
        assert challenge["evaluated_target_count"] == 3  # wed/thu/fri already ended
        assert challenge["evaluated_completed_count"] == 2
        assert challenge["completion_rate"] == pytest.approx(66.7, abs=0.05)
        # Item 13 of §5 완료 조건: the safety disclaimer must also appear on a "ready" (non-empty)
        # report, not just on the empty-state response (already covered separately).
        assert "치료" in data["disclaimer"] or "진단" in data["disclaimer"]


@pytest.mark.asyncio
async def test_unrecorded_day_status_is_distinct_from_explicit_miss() -> None:
    """§5.2/item 3: a past day with NO log at all ("unrecorded") must render a different
    goal_window status than a past day explicitly logged as not completed ("not_completed") —
    the earlier anchor test only exercised completed/not_completed/pending/future, so this
    closes the one status value ("unrecorded") that test never actually asserted per-day."""
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await signup_and_login(client, "unrecordedday@example.com")
        user_id = await _user_id_by_email("unrecordedday@example.com")

        monday = date(2026, 8, 24)
        assert monday.weekday() == 0
        cycle = await _make_cycle(user_id, monday, codes=["regular_meals_log"])
        user_challenge = await UserChallenge.get(cycle_id=cycle.id)

        await _log(user_id, user_challenge.id, monday, True)  # Mon: completed
        await _log(user_id, user_challenge.id, monday + timedelta(days=1), False)  # Tue: explicit miss
        # Wed/Thu/Fri (offsets 2-4): no log created at all -> must be "unrecorded", not "not_completed".

        import app.services.reports as reports_module

        saturday = monday + timedelta(days=5)
        reports_module.today_kst = lambda: saturday

        response = await client.get("/api/v1/reports", params={"period": "week"}, headers=headers)
        data = response.json()["data"]
        windows = {w["start_date"]: w["status"] for w in data["challenges"][0]["goal_windows"]}

        assert windows[monday.isoformat()] == "completed"
        assert windows[(monday + timedelta(days=1)).isoformat()] == "not_completed"
        for offset in (2, 3, 4):
            assert windows[(monday + timedelta(days=offset)).isoformat()] == "unrecorded"
        assert windows[saturday.isoformat()] == "pending"
        assert windows[(saturday + timedelta(days=1)).isoformat()] == "future"


@pytest.mark.asyncio
async def test_unconfirmed_challenge_never_gets_a_fabricated_rate() -> None:
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await signup_and_login(client, "unconfirmed@example.com")
        user_id = await _user_id_by_email("unconfirmed@example.com")
        monday = date(2026, 8, 24)
        cycle = await _make_cycle(user_id, monday, codes=["brisk_walk_30m"])  # unconfirmed frequency
        user_challenge = await UserChallenge.get(cycle_id=cycle.id)
        await _log(user_id, user_challenge.id, monday, True)

        import app.services.reports as reports_module

        reports_module.today_kst = lambda: monday + timedelta(days=1)

        response = await client.get("/api/v1/reports", params={"period": "week"}, headers=headers)
        data = response.json()["data"]
        challenge = data["challenges"][0]
        assert challenge["frequency"] == "unconfirmed"
        assert challenge["completion_rate"] is None
        assert challenge["planned_count"] is None
        assert challenge["record_count"] == 1
        assert challenge["record_dates"] == [monday.isoformat()]
        assert challenge["goal_windows"] == []


@pytest.mark.asyncio
async def test_weekly_challenge_completes_at_most_once_and_summary_uses_weighted_average() -> None:
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await signup_and_login(client, "weekly@example.com")
        user_id = await _user_id_by_email("weekly@example.com")
        wednesday = date(2026, 8, 5)
        cycle = await _make_cycle(user_id, wednesday, codes=["strength_twice_weekly", "regular_meals_log"])
        strength_challenge = await Challenge.get(code="strength_twice_weekly")
        daily_challenge = await Challenge.get(code="regular_meals_log")
        strength = await UserChallenge.get(cycle_id=cycle.id, challenge_id=strength_challenge.id)
        daily = await UserChallenge.get(cycle_id=cycle.id, challenge_id=daily_challenge.id)

        # Week 1 (wed..tue): strength completed twice (target=2) -> fully met early.
        await _log(user_id, strength.id, wednesday, True)
        await _log(user_id, strength.id, wednesday + timedelta(days=2), True)
        for offset in range(7):
            await _log(user_id, daily.id, wednesday + timedelta(days=offset), True)

        import app.services.reports as reports_module

        as_of = wednesday + timedelta(days=10)  # into week 2, week 1 fully ended
        reports_module.today_kst = lambda: as_of

        response = await client.get("/api/v1/reports", params={"period": "week"}, headers=headers)
        data = response.json()["data"]
        by_code = {c["challenge_code"]: c for c in data["challenges"]}
        assert by_code["strength_twice_weekly"]["completed_count"] == 0  # week 2 has no completion yet
        assert by_code["strength_twice_weekly"]["evaluated_target_count"] == 0  # week 2 not ended yet

        response_prev = await client.get("/api/v1/reports", params={"period": "four-week"}, headers=headers)
        prev = response_prev.json()["data"]
        by_code_prev = {c["challenge_code"]: c for c in prev["challenges"]}
        assert by_code_prev["strength_twice_weekly"]["completed_count"] == 1  # 1 window, done once
        assert by_code_prev["strength_twice_weekly"]["evaluated_completed_count"] == 1
        assert by_code_prev["strength_twice_weekly"]["evaluated_target_count"] == 1

        # summary.completion_rate must be sum(numerator)/sum(denominator), not avg of per-habit rates.
        summary = prev["summary"]
        assert summary["evaluated_completed_count"] == 1 + 7  # strength(1/1) + daily(7/7)
        assert summary["evaluated_target_count"] == 1 + 7
        assert summary["completion_rate"] == 100.0


@pytest.mark.asyncio
async def test_four_week_excludes_current_week_and_has_exactly_four_buckets() -> None:
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await signup_and_login(client, "fourweek@example.com")
        user_id = await _user_id_by_email("fourweek@example.com")
        monday = date(2026, 7, 1)
        await _make_cycle(user_id, monday, codes=["regular_meals_log"])

        import app.services.reports as reports_module

        as_of = monday + timedelta(days=35)  # well past the first cycle
        reports_module.today_kst = lambda: as_of

        response = await client.get("/api/v1/reports", params={"period": "four-week"}, headers=headers)
        data = response.json()["data"]
        assert data["trend"]["unit"] == "week"
        buckets = data["trend"]["buckets"]
        assert len(buckets) == 4
        current_week_start = monday + timedelta(days=((as_of - monday).days // 7) * 7)
        for bucket in buckets:
            assert date.fromisoformat(bucket["end_date"]) < current_week_start


@pytest.mark.asyncio
async def test_all_period_paginates_cycles_and_rejects_cross_user_report_id() -> None:
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers_a = await signup_and_login(client, "alluser@example.com")
        user_a = await _user_id_by_email("alluser@example.com")
        headers_b = await signup_and_login(client, "otheruser@example.com")

        start = date(2026, 1, 5)
        for i in range(13):
            await _make_cycle(
                user_a, start + timedelta(days=28 * i), codes=["regular_meals_log"], status_="completed"
            )

        import app.services.reports as reports_module

        as_of = start + timedelta(days=28 * 13 + 5)
        reports_module.today_kst = lambda: as_of

        response = await client.get("/api/v1/reports", params={"period": "all"}, headers=headers_a)
        data = response.json()["data"]
        assert len(data["cycles"]["items"]) == 10
        assert data["cycles"]["next_cursor"] is not None
        assert data["summary"]["completed_cycles_count"] == 13

        page2 = await client.get(
            f"/api/v1/reports/{data['report_id']}/cycles",
            params={"cursor": data["cycles"]["next_cursor"]},
            headers=headers_a,
        )
        assert page2.status_code == status.HTTP_200_OK
        assert len(page2.json()["data"]["items"]) == 3
        assert page2.json()["data"]["next_cursor"] is None

        # Another user's own reports/cycles call must never see user A's data (R15).
        own_cycles = await client.get(
            f"/api/v1/reports/{data['report_id']}/cycles", headers=headers_b
        )
        assert own_cycles.status_code == status.HTTP_200_OK
        assert own_cycles.json()["data"]["items"] == []

        week_report_id = "rpt-week-2026-09-08"
        wrong_period = await client.get(f"/api/v1/reports/{week_report_id}/cycles", headers=headers_a)
        assert wrong_period.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_all_period_cycle_selected_challenges_keep_their_title_snapshot() -> None:
    """Item 9 of §5 완료 조건: a cycle's `selected_challenges` must show the challenge title
    exactly as it was when the user picked it (`title_snapshot`), not whatever the catalog
    calls it later — otherwise a past cycle's report would silently reword itself whenever
    the product team edits the catalog's wording."""
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await signup_and_login(client, "titlesnapshot@example.com")
        user_id = await _user_id_by_email("titlesnapshot@example.com")

        cycle = await _make_cycle(user_id, date(2026, 6, 1), codes=["regular_meals_log"], status_="completed")

        # The catalog wording changes AFTER selection (e.g. a later product-copy edit).
        challenge = await Challenge.get(code="regular_meals_log")
        original_title = challenge.title
        challenge.title = "완전히 새로운 문구로 바뀐 제목"
        await challenge.save(update_fields=["title"])

        import app.services.reports as reports_module

        reports_module.today_kst = lambda: date(2026, 7, 1)

        response = await client.get("/api/v1/reports", params={"period": "all"}, headers=headers)
        data = response.json()["data"]
        item = next(c for c in data["cycles"]["items"] if c["cycle_id"] == str(cycle.id))
        assert item["selected_challenges"] == [
            {"challenge_code": "regular_meals_log", "title": original_title}
        ]


@pytest.mark.asyncio
async def test_four_week_bucket_sums_match_top_level_summary() -> None:
    """R09/R10: the 4 trend buckets partition the exact same date range the four-week
    summary covers, so their per-bucket evaluated_target/completed/unrecorded counts must
    add up to the top-level summary's counts — never a separately-drifting computation."""
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await signup_and_login(client, "bucketsum@example.com")
        user_id = await _user_id_by_email("bucketsum@example.com")
        monday = date(2026, 7, 1)

        # A long-running cycle (42 days) so it fully covers the four-week window computed below.
        challenge = await Challenge.get(code="regular_meals_log")
        cycle = await ChallengeCycle.create(
            user_id=user_id, cycle_number=1, start_date=monday, end_date=monday + timedelta(days=41), status="active"
        )
        user_challenge = await UserChallenge.create(
            user_id=user_id,
            cycle_id=cycle.id,
            challenge_id=challenge.id,
            frequency=challenge.frequency,
            target_count=challenge.target_count,
            title_snapshot=challenge.title,
            definition_version=challenge.definition_version,
        )
        # Mixed completion so evaluated_completed/unrecorded both vary across buckets.
        for offset in range(35):
            if offset % 3 != 0:
                await _log(user_id, user_challenge.id, monday + timedelta(days=offset), True)

        import app.services.reports as reports_module

        as_of = monday + timedelta(days=35)
        reports_module.today_kst = lambda: as_of

        response = await client.get("/api/v1/reports", params={"period": "four-week"}, headers=headers)
        data = response.json()["data"]
        buckets = data["trend"]["buckets"]
        assert len(buckets) == 4

        summary = data["summary"]
        for key in ("evaluated_completed_count", "evaluated_target_count", "completed_count", "unrecorded_count"):
            assert sum(b[key] for b in buckets) == summary[key], key


@pytest.mark.asyncio
async def test_period_challenges_exclude_non_overlapping_old_cycle_selection() -> None:
    """Item 4 of §5 완료 조건: the response's `challenges` array must only include challenges
    actually selected in a cycle overlapping the requested period — a challenge the same user
    picked in an old, already-ended cycle that does not overlap the four-week window must not
    reappear just because the user selected it once before."""
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await signup_and_login(client, "periodscope@example.com")
        user_id = await _user_id_by_email("periodscope@example.com")
        anchor = date(2026, 8, 3)

        # Old cycle, long ended before the four-week window, picked a DIFFERENT challenge.
        await _make_cycle(user_id, anchor - timedelta(days=60), codes=["brisk_walk_30m"], status_="completed")
        # Current cycle overlapping the period picked only regular_meals_log.
        await _make_cycle(user_id, anchor, codes=["regular_meals_log"], status_="active")

        import app.services.reports as reports_module

        as_of = anchor + timedelta(days=35)
        reports_module.today_kst = lambda: as_of  # four-week period == [anchor+7, anchor+34]

        response = await client.get("/api/v1/reports", params={"period": "four-week"}, headers=headers)
        data = response.json()["data"]
        codes = {c["challenge_code"] for c in data["challenges"]}
        assert codes == {"regular_meals_log"}


@pytest.mark.asyncio
async def test_four_week_bucket_participation_days_reflects_actual_enrollment() -> None:
    """작업 D 요청 표: 각 4주 bucket은 '실천일'뿐 아니라 '참여일'도 반환해야 한다. `eligible_days`
    는 as_of 기준으로 그 버킷 구간이 달력상 얼마나 지났는지(완전히 지난 버킷은 사실상 항상 7)만
    나타내므로, 사용자가 아직 회차를 시작하지 않았던 과거 구간에서도 7을 보고해 '참여했다'는 착시를
    준다. `participation_days`는 그 구간에 실제로 활성 회차가 있었던 날수만 세야 한다 — 첫 회차를
    지금 막 시작한 사용자라면 지난 4주 각 버킷 모두 0이어야 한다."""
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await signup_and_login(client, "bucketparticipation@example.com")
        user_id = await _user_id_by_email("bucketparticipation@example.com")

        # The user's only cycle starts TODAY — the four trend buckets are entirely before it.
        today = date(2026, 9, 8)
        assert today.weekday() == 1  # Tuesday: harmless, just documents the fixture's anchor weekday
        await _make_cycle(user_id, today, codes=["regular_meals_log"])

        import app.services.reports as reports_module

        reports_module.today_kst = lambda: today

        response = await client.get("/api/v1/reports", params={"period": "four-week"}, headers=headers)
        data = response.json()["data"]
        buckets = data["trend"]["buckets"]
        assert len(buckets) == 4
        for bucket in buckets:
            assert bucket["eligible_days"] == 7  # fully in the past relative to as_of
            assert bucket["participation_days"] == 0  # but the user wasn't enrolled yet


@pytest.mark.asyncio
async def test_barriers_scoped_to_period_selected_challenge_and_deduped() -> None:
    """Work item F: the four-week barriers card must exclude a barrier whose date falls
    outside the period, exclude a barrier tied to a challenge not selected in this period
    (a stale row against an old, non-overlapping cycle), and collapse a corrected
    resubmission (same user_challenge_id + log_date) to only its latest row."""
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await signup_and_login(client, "barrierscope@example.com")
        user_id = await _user_id_by_email("barrierscope@example.com")
        anchor = date(2026, 8, 3)

        old_cycle = await _make_cycle(user_id, anchor - timedelta(days=60), codes=["regular_meals_log"], status_="completed")
        old_uc = await UserChallenge.get(cycle_id=old_cycle.id)

        current_cycle = await _make_cycle(user_id, anchor, codes=["regular_meals_log"], status_="active")
        current_uc = await UserChallenge.get(cycle_id=current_cycle.id)

        import app.services.reports as reports_module

        as_of = anchor + timedelta(days=35)
        reports_module.today_kst = lambda: as_of  # four-week period == [anchor+7, anchor+34]

        await _barrier(user_id, current_uc.id, anchor + timedelta(days=10), "forgot")  # in scope
        await _barrier(user_id, current_uc.id, anchor + timedelta(days=40), "no_time")  # outside period date range
        await _barrier(user_id, old_uc.id, anchor + timedelta(days=12), "environment")  # challenge not selected now
        # Corrected resubmission: same (user_challenge_id, log_date), later row must win.
        await _barrier(user_id, current_uc.id, anchor + timedelta(days=15), "goal_too_hard")
        await _barrier(user_id, current_uc.id, anchor + timedelta(days=15), "no_time")

        response = await client.get("/api/v1/reports", params={"period": "four-week"}, headers=headers)
        data = response.json()["data"]
        barriers = data["barriers"]
        assert barriers["total_count"] == 2
        reason_codes = {item["reason_code"] for item in barriers["items"]}
        assert reason_codes == {"forgot", "no_time"}


@pytest.mark.asyncio
async def test_fetching_additional_cycles_page_does_not_change_top_level_summary() -> None:
    """§2.4/R14: paging through /reports/{report_id}/cycles is read-only and must never
    mutate or otherwise change what a follow-up GET /reports?period=all reports."""
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await signup_and_login(client, "pagesummary@example.com")
        user_id = await _user_id_by_email("pagesummary@example.com")

        start = date(2026, 1, 5)
        for i in range(13):
            await _make_cycle(user_id, start + timedelta(days=28 * i), codes=["regular_meals_log"], status_="completed")

        import app.services.reports as reports_module

        as_of = start + timedelta(days=28 * 13 + 5)
        reports_module.today_kst = lambda: as_of

        first = await client.get("/api/v1/reports", params={"period": "all"}, headers=headers)
        before = first.json()["data"]
        assert before["cycles"]["next_cursor"] is not None

        page2 = await client.get(
            f"/api/v1/reports/{before['report_id']}/cycles",
            params={"cursor": before["cycles"]["next_cursor"]},
            headers=headers,
        )
        assert page2.status_code == status.HTTP_200_OK
        assert len(page2.json()["data"]["items"]) == 3

        second = await client.get("/api/v1/reports", params={"period": "all"}, headers=headers)
        after = second.json()["data"]
        assert after["summary"] == before["summary"]
        assert after["report_id"] == before["report_id"]
        assert after["cycles"] == before["cycles"]


@pytest.mark.asyncio
async def test_weekly_report_pdf_never_leaks_another_users_content() -> None:
    """The existing `/weekly-reports/current/pdf` endpoint (untouched by this feature, and
    out of scope for the report-v1.4-draft PDF work) takes no report_id/user_id from the
    request at all — it always builds the *authenticated caller's own* active-cycle report
    (`EngagementService.weekly_report(user)` keyed only by `user.id` from the auth
    dependency). So there is no identifier a client could swap to fetch someone else's PDF;
    this test confirms that structurally by checking each user's PDF bytes contain only
    that user's own report text and never the other user's, and that an unauthenticated
    request is rejected outright."""
    from app.apis.v1.wellness_routers import _pdf_text

    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers_a = await signup_and_login(client, "pdfuser_a@example.com")
        user_a = await _user_id_by_email("pdfuser_a@example.com")
        headers_b = await signup_and_login(client, "pdfuser_b@example.com")

        today = date.today()
        cycle = await _make_cycle(user_a, today - timedelta(days=6), codes=["regular_meals_log"])
        user_challenge = await UserChallenge.get(cycle_id=cycle.id)
        for offset in range(7):
            await _log(user_a, user_challenge.id, today - timedelta(days=offset), True)
        # user_b never started a cycle -> weekly_report() returns the "empty" shape.

        unauthenticated = await client.get("/api/v1/weekly-reports/current/pdf")
        assert unauthenticated.status_code == status.HTTP_401_UNAUTHORIZED

        pdf_a = await client.get("/api/v1/weekly-reports/current/pdf", headers=headers_a)
        pdf_b = await client.get("/api/v1/weekly-reports/current/pdf", headers=headers_b)
        assert pdf_a.status_code == status.HTTP_200_OK
        assert pdf_b.status_code == status.HTTP_200_OK
        assert pdf_a.content != pdf_b.content

        ready_marker = _pdf_text("상태: ready").encode("ascii")
        empty_marker = _pdf_text("상태: empty").encode("ascii")
        record_marker = _pdf_text("기록 요약: 최근 7일 동안 계획한 활동의 100.0%를 기록했습니다. 현재 실천 목표를 이어가 보세요.").encode(
            "ascii"
        )
        empty_message_marker = _pdf_text(
            "기록 요약: 진행 중인 챌린지를 시작하면 주간 리포트를 확인할 수 있습니다."
        ).encode("ascii")

        assert ready_marker in pdf_a.content and record_marker in pdf_a.content
        assert empty_marker not in pdf_a.content and empty_message_marker not in pdf_a.content

        assert empty_marker in pdf_b.content and empty_message_marker in pdf_b.content
        assert ready_marker not in pdf_b.content and record_marker not in pdf_b.content


@pytest.mark.asyncio
async def test_empty_report_when_no_cycle_ever_started() -> None:
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await signup_and_login(client, "empty@example.com")
        response = await client.get("/api/v1/reports", params={"period": "week"}, headers=headers)
        data = response.json()["data"]
        assert data["status"] == "empty"
        assert data["empty_reason"] == "no_challenges"
        assert data["challenges"] == []
        assert data["summary"]["completion_rate"] is None
        assert "치료" in data["disclaimer"] or "진단" in data["disclaimer"]


@pytest.mark.asyncio
async def test_invalid_period_is_rejected() -> None:
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await signup_and_login(client, "badperiod@example.com")
        response = await client.get("/api/v1/reports", params={"period": "month"}, headers=headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json()["detail"]["error_code"] == "INVALID_PERIOD"


@pytest.mark.asyncio
async def test_generated_at_is_utc_and_response_is_marked_private_no_store() -> None:
    """§3 API 공통 조건: 시각(timestamp)은 ISO 8601 UTC로, 민감 응답은
    Cache-Control: private, no-store로 반환한다 — 성공 응답뿐 아니라 이 라우트들이 던지는
    에러 응답(422/404)에도 app/main.py의 미들웨어를 통해 똑같이 적용돼야 한다."""
    async with db_session(), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await signup_and_login(client, "cachecontrol@example.com")

        ok = await client.get("/api/v1/reports", params={"period": "week"}, headers=headers)
        assert ok.status_code == status.HTTP_200_OK
        assert ok.json()["data"]["generated_at"].endswith("Z")
        assert ok.headers["cache-control"] == "private, no-store"

        invalid_period = await client.get("/api/v1/reports", params={"period": "month"}, headers=headers)
        assert invalid_period.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert invalid_period.headers["cache-control"] == "private, no-store"

        wrong_period_cycles = await client.get(
            "/api/v1/reports/rpt-week-2026-09-08/cycles", headers=headers
        )
        assert wrong_period_cycles.status_code == status.HTTP_404_NOT_FOUND
        assert wrong_period_cycles.headers["cache-control"] == "private, no-store"

        unauthenticated_pdf = await client.get("/api/v1/weekly-reports/current/pdf")
        assert unauthenticated_pdf.status_code == status.HTTP_401_UNAUTHORIZED
        assert unauthenticated_pdf.headers["cache-control"] == "private, no-store"
