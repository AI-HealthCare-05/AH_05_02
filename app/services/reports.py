"""Lifestyle report service (report-v1.4-draft).

Implements `GET /api/v1/reports?period=week|four-week|all` per
docs handed off in `report-handoff-20260907/BACKEND_IMPLEMENTATION_REQUEST.md` and
`API_CONTRACT.md`. See `docs/frontend/REPORT_CHALLENGE_FREQUENCY_MAPPING_20260908.md`
for why challenge frequency is sometimes unconfirmed, and the module docstring below each
function for the specific spec section it implements.

Known, deliberate scope cuts (flagged for the design/product team, not silent guesses):

- No persisted report snapshot: `report_id` is a deterministic, recomputed key
  (`rpt-<period>-<as_of_date>`), not a stored artifact. Four-week/all PDF export was
  explicitly excluded from this phase's scope (BACKEND_IMPLEMENTATION_REQUEST.md §4), so
  nothing currently needs a report_id to resolve to byte-identical content later; `week`
  PDF continues to use the existing, untouched `/weekly-reports/current/pdf` endpoint.
  Because the cycles endpoint always recomputes against the *authenticated caller's own*
  data (it never trusts an identity embedded in report_id), passing another user's
  report_id cannot leak their data — it just recomputes the caller's own report instead.
- The "user week" anchor is the caller's current active/scheduled cycle's start_date
  weekday; if none exists, the most recently-ended cycle's start_date is used instead so
  `four-week`/`all` remain meaningful between cycles. This is one of the "5 questions"
  BACKEND_IMPLEMENTATION_REQUEST.md §6 explicitly leaves for backend to decide/report back.
  A user who has never started any cycle gets an empty report.
- Weekly goal windows are anchored to *each cycle's own* start_date. Consecutive cycles are
  expected to share the same weekday (§5.1), so this matches the "user week" anchor in the
  steady-state case; a cycle that legitimately starts on a different weekday than an older
  cycle it's being compared against (e.g. inside a `four-week`/`all` query spanning cycles)
  is a genuine edge case the source doc itself leaves for later agreement, not something
  this module invents a policy for beyond "generate each cycle's own aligned windows".
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import HTTPException, status

from app.core import config
from app.models.health import ChallengeCycle, ChallengeLog, UserChallenge
from app.models.users import User
from app.repositories.engagement_repository import EngagementRepository
from app.repositories.health_repository import HealthRepository
from app.services.engagement import BARRIER_SUGGESTIONS

PeriodKey = Literal["week", "four-week", "all"]
VALID_PERIODS: tuple[PeriodKey, ...] = ("week", "four-week", "all")

DISCLAIMER = "기록 변화와 수행률은 질병 위험 감소, 진단 또는 치료 효과를 의미하지 않습니다."
CYCLES_PAGE_SIZE = 10


def today_kst() -> date:
    return datetime.now(config.TIMEZONE).date()


def report_id_for(period: PeriodKey, as_of: date) -> str:
    return f"rpt-{period}-{as_of.isoformat()}"


def _parse_report_id(report_id: str) -> tuple[PeriodKey, date] | None:
    parts = report_id.split("-", 2)
    if len(parts) != 3 or parts[0] != "rpt" or parts[1] not in VALID_PERIODS:
        return None
    try:
        as_of = date.fromisoformat(parts[2])
    except ValueError:
        return None
    return parts[1], as_of  # type: ignore[return-value]


def _round1(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator * 100, 1)


@dataclass(frozen=True)
class GoalWindow:
    start_date: date
    end_date: date


def _resolve_status(window: GoalWindow, as_of: date, logs: list[ChallengeLog]) -> tuple[str, date | None]:
    """One rule for both daily (1-day window) and weekly (7-day window) evaluation.

    "완료가 우선" — a true log anywhere in the window wins regardless of whether the window
    has ended yet, so a weekly goal finished early still shows completed before its week is
    over (§5.1, §5.3). A same-day false log never demotes an ongoing (not yet ended) window
    below "pending" (§5.2: "오늘 false를 입력해도... pending으로 유지").
    """

    completed_dates = sorted(log.log_date for log in logs if log.is_completed)
    if completed_dates:
        return "completed", completed_dates[0]
    if window.start_date > as_of:
        return "future", None
    if window.end_date < as_of:
        return ("not_completed" if logs else "unrecorded"), None
    return "pending", None


def _daily_windows(lo: date, hi: date) -> list[GoalWindow]:
    if lo > hi:
        return []
    return [GoalWindow(d, d) for d in _date_range(lo, hi)]


def _date_range(lo: date, hi: date):
    d = lo
    while d <= hi:
        yield d
        d += timedelta(days=1)


def _weekly_windows(cycle_start: date, cycle_end: date, period_start: date, period_end: date) -> list[GoalWindow]:
    windows: list[GoalWindow] = []
    block_start = cycle_start
    while block_start <= cycle_end:
        block_end = min(block_start + timedelta(days=6), cycle_end)
        if block_end >= period_start and block_start <= period_end:
            windows.append(GoalWindow(block_start, block_end))
        block_start = block_start + timedelta(days=7)
    return windows


@dataclass
class ChallengeAccumulator:
    challenge_code: str
    title: str
    frequency: str | None
    target_count: int | None
    user_challenge_ids: list[int]
    practiced_dates: set[date]
    completed_count: int = 0
    evaluated_completed_count: int = 0
    evaluated_target_count: int = 0
    unrecorded_count: int = 0
    planned_count: int = 0
    record_dates: set[date] = None  # type: ignore[assignment]
    goal_windows: list[dict[str, object]] | None = None

    def __post_init__(self) -> None:
        if self.record_dates is None:
            self.record_dates = set()
        if self.goal_windows is None:
            self.goal_windows = []


async def _week_anchor_cycle(health_repo: HealthRepository, user_id: int) -> ChallengeCycle | None:
    cycle = await health_repo.active_cycle(user_id)
    if cycle is not None:
        return cycle
    return await ChallengeCycle.filter(user_id=user_id).order_by("-end_date", "-id").first()


async def _first_started_cycle(user_id: int, as_of: date) -> ChallengeCycle | None:
    return await ChallengeCycle.filter(user_id=user_id, start_date__lte=as_of).order_by("start_date", "id").first()


def _week_bounds(anchor_start: date, as_of: date) -> tuple[date, date]:
    if as_of < anchor_start:
        start = anchor_start
    else:
        week_index = (as_of - anchor_start).days // 7
        start = anchor_start + timedelta(days=week_index * 7)
    return start, start + timedelta(days=6)


@dataclass
class PeriodBounds:
    key: PeriodKey
    start_date: date | None
    end_date: date
    effective_start_date: date | None
    effective_end_date: date | None
    is_partial: bool
    as_of_date: date

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "timezone": "Asia/Seoul",
            "as_of_date": self.as_of_date,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "effective_start_date": self.effective_start_date,
            "effective_end_date": self.effective_end_date,
            "is_partial": self.is_partial,
        }


async def _compute_period(period: PeriodKey, anchor: ChallengeCycle | None, as_of: date, user_id: int) -> PeriodBounds:
    if anchor is None:
        return PeriodBounds(period, None, as_of, None, None, True, as_of)

    if period == "week":
        start, end = _week_bounds(anchor.start_date, as_of)
        effective_end = min(end, as_of)
        effective_start = start if effective_end >= start else None
        is_partial = end > as_of or effective_start is None
        return PeriodBounds(period, start, end, effective_start, effective_end, is_partial, as_of)

    if period == "four-week":
        current_week_start, _ = _week_bounds(anchor.start_date, as_of)
        end = current_week_start - timedelta(days=1)
        start = current_week_start - timedelta(days=28)
        first = await _first_started_cycle(user_id, as_of)
        effective_start = max(start, first.start_date) if first is not None and first.start_date <= end else None
        effective_end = end if effective_start is not None else None
        is_partial = effective_start is not None and effective_start > start
        return PeriodBounds(period, start, end, effective_start, effective_end, is_partial, as_of)

    # all
    first = await _first_started_cycle(user_id, as_of)
    start = first.start_date if first is not None else None
    effective_start = start
    effective_end = as_of if start is not None else None
    return PeriodBounds(period, start, as_of, effective_start, effective_end, True, as_of)


async def _selected_user_challenges_overlapping(
    user_id: int, period_start: date | None, period_end: date
) -> list[UserChallenge]:
    query = ChallengeCycle.filter(user_id=user_id, end_date__gte=(period_start or date.min))
    query = query.filter(start_date__lte=period_end)
    cycles = await query
    if not cycles:
        return []
    cycle_by_id = {cycle.id: cycle for cycle in cycles}
    user_challenges = await UserChallenge.filter(user_id=user_id, cycle_id__in=list(cycle_by_id)).order_by("id")
    for uc in user_challenges:
        uc._cycle = cycle_by_id[uc.cycle_id]  # type: ignore[attr-defined]
    return user_challenges


async def _logs_by_user_challenge(user_challenge_ids: list[int]) -> dict[int, list[ChallengeLog]]:
    if not user_challenge_ids:
        return {}
    logs = await ChallengeLog.filter(user_challenge_id__in=user_challenge_ids).order_by("log_date")
    grouped: dict[int, list[ChallengeLog]] = {uc_id: [] for uc_id in user_challenge_ids}
    for log in logs:
        grouped[log.user_challenge_id].append(log)
    return grouped


def _summary_dict(acc: ChallengeAccumulator, *, include_goal_windows: bool) -> dict[str, object]:
    if acc.frequency not in ("daily", "weekly"):
        return {
            "challenge_code": acc.challenge_code,
            "title": acc.title,
            "frequency": "unconfirmed",
            "planned_count": None,
            "practiced_days": None,
            "completed_count": None,
            "evaluated_completed_count": None,
            "evaluated_target_count": None,
            "completion_rate": None,
            "unrecorded_count": None,
            "record_count": len(acc.record_dates),
            "record_dates": sorted(acc.record_dates),
            "goal_windows": [],
        }
    return {
        "challenge_code": acc.challenge_code,
        "title": acc.title,
        "frequency": acc.frequency,
        "planned_count": acc.planned_count,
        "practiced_days": len(acc.practiced_dates),
        "completed_count": acc.completed_count,
        "evaluated_completed_count": acc.evaluated_completed_count,
        "evaluated_target_count": acc.evaluated_target_count,
        "completion_rate": _round1(acc.evaluated_completed_count, acc.evaluated_target_count),
        "unrecorded_count": acc.unrecorded_count,
        "record_count": acc.completed_count,
        "record_dates": sorted(acc.practiced_dates),
        "goal_windows": acc.goal_windows if include_goal_windows else [],
    }


def _apply_window(
    acc: ChallengeAccumulator,
    window: GoalWindow,
    as_of: date,
    window_logs: list[ChallengeLog],
    *,
    include_goal_windows: bool,
) -> None:
    resolved_status, completed_on = _resolve_status(window, as_of, window_logs)
    ended = window.end_date < as_of
    if resolved_status == "completed":
        acc.completed_count += 1
        if completed_on is not None:
            acc.practiced_dates.add(completed_on)
    elif resolved_status == "unrecorded" and ended:
        acc.unrecorded_count += 1
    if ended:
        acc.evaluated_target_count += 1
        if resolved_status == "completed":
            acc.evaluated_completed_count += 1
    if include_goal_windows:
        acc.goal_windows.append(
            {
                "start_date": window.start_date,
                "end_date": window.end_date,
                "status": resolved_status,
                "completed_on": completed_on,
            }
        )


async def _accumulate_challenges(
    user_challenges: list[UserChallenge],
    as_of: date,
    *,
    windows_for: Callable[[UserChallenge, ChallengeCycle], list[GoalWindow]],
    unconfirmed_bounds_for: Callable[[UserChallenge, ChallengeCycle], tuple[date, date]],
    include_goal_windows: bool,
) -> list[dict[str, object]]:
    """Shared per-challenge accumulation used by both the report-period view
    (`_build_challenge_summaries`) and the per-cycle view (`_summaries_for_user_challenges`).
    The two callers differ only in how they bound each UserChallenge's evaluation window
    (clipped to a requested report period vs. to that challenge's own cycle), so that
    difference is the only thing passed in."""

    if not user_challenges:
        return []
    challenge_ids = {uc.challenge_id for uc in user_challenges}
    catalog = await HealthRepository().challenge_map(list(challenge_ids))
    logs_by_uc = await _logs_by_user_challenge([uc.id for uc in user_challenges])

    accumulators: dict[int, ChallengeAccumulator] = {}
    for uc in user_challenges:
        cycle: ChallengeCycle = uc._cycle  # type: ignore[attr-defined]
        challenge = catalog.get(uc.challenge_id)
        title = uc.title_snapshot or (challenge.title if challenge else str(uc.challenge_id))
        acc = accumulators.setdefault(
            uc.challenge_id,
            ChallengeAccumulator(
                challenge_code=(challenge.code if challenge else str(uc.challenge_id)),
                title=title,
                frequency=uc.frequency,
                target_count=uc.target_count,
                user_challenge_ids=[],
                practiced_dates=set(),
            ),
        )
        acc.user_challenge_ids.append(uc.id)
        logs = logs_by_uc.get(uc.id, [])

        if uc.frequency not in ("daily", "weekly"):
            # unconfirmed: record-only, never evaluated (§5.1 — do not guess a denominator).
            lo, hi = unconfirmed_bounds_for(uc, cycle)
            for log in logs:
                if lo <= log.log_date <= hi:
                    acc.record_dates.add(log.log_date)
            continue

        windows = windows_for(uc, cycle)
        acc.planned_count += len(windows)
        for window in windows:
            window_logs = [log for log in logs if window.start_date <= log.log_date <= window.end_date]
            _apply_window(acc, window, as_of, window_logs, include_goal_windows=include_goal_windows)

    return [
        _summary_dict(acc, include_goal_windows=include_goal_windows)
        for acc in sorted(accumulators.values(), key=lambda a: a.challenge_code)
    ]


async def _build_challenge_summaries(
    user_id: int, period: PeriodBounds, *, include_goal_windows: bool
) -> list[dict[str, object]]:
    """Work items B + C: per-challenge goal windows, daily/weekly evaluation, unconfirmed
    record-only handling, clipped to the requested report period. Merges selections of the
    same catalog challenge across cycles overlapping the period (§6: "challenge_code는 같은
    목표 정의일 때만 회차 간 합산")."""

    if period.start_date is None:
        return []
    user_challenges = await _selected_user_challenges_overlapping(user_id, period.start_date, period.end_date)
    if not user_challenges:
        return []

    def windows_for(uc: UserChallenge, cycle: ChallengeCycle) -> list[GoalWindow]:
        if uc.frequency == "daily":
            return _daily_windows(max(cycle.start_date, period.start_date), min(cycle.end_date, period.end_date))
        return _weekly_windows(cycle.start_date, cycle.end_date, period.start_date, period.end_date)

    def unconfirmed_bounds_for(_uc: UserChallenge, cycle: ChallengeCycle) -> tuple[date, date]:
        return max(cycle.start_date, period.start_date), min(cycle.end_date, period.end_date)

    return await _accumulate_challenges(
        user_challenges,
        period.as_of_date,
        windows_for=windows_for,
        unconfirmed_bounds_for=unconfirmed_bounds_for,
        include_goal_windows=include_goal_windows,
    )


def _summary_counts(challenges: list[dict[str, object]]) -> dict[str, object]:
    scored = [c for c in challenges if c["frequency"] != "unconfirmed"]
    practiced_dates: set[date] = set()
    for c in scored:
        practiced_dates.update(c["record_dates"])  # record_dates == completion dates for scored challenges
    evaluated_completed = sum(c["evaluated_completed_count"] for c in scored)
    evaluated_target = sum(c["evaluated_target_count"] for c in scored)
    return {
        "practiced_days": len(practiced_dates),
        "completed_count": sum(c["completed_count"] for c in scored),
        "evaluated_completed_count": evaluated_completed,
        "evaluated_target_count": evaluated_target,
        "completion_rate": _round1(evaluated_completed, evaluated_target),
        "unrecorded_count": sum(c["unrecorded_count"] for c in scored),
        "planned_count": sum(c["planned_count"] for c in scored),
    }


async def _participation_days(user_id: int, period: PeriodBounds) -> int:
    if period.start_date is None:
        return 0
    cycles = await ChallengeCycle.filter(
        user_id=user_id, end_date__gte=period.start_date, start_date__lte=period.end_date
    )
    days: set[date] = set()
    for cycle in cycles:
        lo = max(cycle.start_date, period.start_date)
        hi = min(cycle.end_date, period.end_date)
        days.update(_date_range(lo, hi))
    return len(days)


async def _completed_cycles_count(user_id: int, period: PeriodBounds) -> int:
    if period.start_date is None:
        return 0
    return await ChallengeCycle.filter(
        user_id=user_id, status="completed", end_date__gte=period.start_date, end_date__lte=period.end_date
    ).count()


def _headline(status_value: str, practiced_days: int, completion_rate: float | None) -> str:
    if status_value == "empty":
        return "아직 기록이 없어요. 첫 실천을 기록해 보세요."
    if practiced_days == 0:
        return "이번 기간에는 아직 실천 기록이 없어요. 오늘부터 시작해 보세요."
    if completion_rate is None:
        return "점검 기록을 모았어요."
    if completion_rate >= 80:
        return f"이번 기간 목표의 {completion_rate}%를 달성했어요. 잘 이어가고 있어요."
    if completion_rate >= 40:
        return f"이번 기간 달성률은 {completion_rate}%예요. 어려웠던 이유를 확인해 보세요."
    return f"이번 기간 달성률은 {completion_rate}%예요. 작은 것부터 다시 시작해도 괜찮아요."


def _highlights(challenges: list[dict[str, object]]) -> list[dict[str, object]]:
    candidates = [
        c
        for c in challenges
        if c["frequency"] != "unconfirmed" and c["evaluated_target_count"] >= 3 and c["evaluated_completed_count"] >= 1
    ]
    candidates.sort(key=lambda c: (-c["completion_rate"], -c["evaluated_target_count"], c["challenge_code"]))
    if not candidates:
        return []
    best = candidates[0]
    return [
        {
            "type": "steady_habit",
            "message": f"'{best['title']}'을(를) 꾸준히 실천하고 있어요.",
            "challenge_code": best["challenge_code"],
        }
    ]


def _needs_support(challenges: list[dict[str, object]], exclude_code: str | None) -> dict[str, object] | None:
    candidates = [
        c
        for c in challenges
        if c["frequency"] != "unconfirmed"
        and c["evaluated_target_count"] >= 3
        and c["completion_rate"] is not None
        and c["completion_rate"] < 100
    ]
    if exclude_code is not None:
        below = [c for c in candidates if c["challenge_code"] != exclude_code]
        excluded = next((c for c in candidates if c["challenge_code"] == exclude_code), None)
        if excluded is not None:
            below = [c for c in below if c["completion_rate"] < excluded["completion_rate"]]
        candidates = below
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c["completion_rate"], c["challenge_code"]))
    return candidates[0]


async def _barriers(user_id: int, period: PeriodBounds, user_challenge_ids: list[int]) -> dict[str, object]:
    if period.start_date is None or not user_challenge_ids:
        return {"total_count": 0, "items": []}
    items = await EngagementRepository().list_barriers(
        user_id, period.start_date, period.end_date, user_challenge_ids=user_challenge_ids
    )
    counts = Counter(item.reason_code for item in items)
    ranked = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return {
        "total_count": sum(counts.values()),
        "items": [
            {"reason_code": code, "label": BARRIER_SUGGESTIONS.get(code, (code, code))[1], "count": count}
            for code, count in ranked[:2]
        ],
    }


async def _trend_buckets(user_id: int, anchor: ChallengeCycle, as_of: date) -> list[dict[str, object]]:
    current_week_start, _ = _week_bounds(anchor.start_date, as_of)
    buckets: list[dict[str, object]] = []
    for i in range(4, 0, -1):
        start = current_week_start - timedelta(days=7 * i)
        end = start + timedelta(days=6)
        bucket_period = PeriodBounds("week", start, end, start, min(end, as_of), end > as_of, as_of)
        challenges = await _build_challenge_summaries(user_id, bucket_period, include_goal_windows=False)
        counts = _summary_counts(challenges)
        eligible_days = min((min(end, as_of) - start).days + 1, 7) if start <= as_of else 0
        # 요청서 §2.3(작업 D)의 "참여일" — 이 버킷 구간 안에서 실제로 활성 회차가 있었던 날수.
        # `eligible_days`(as_of 기준 경과한 달력일수, 완전히 지난 버킷은 사실상 항상 7)와는 다른
        # 개념이다 — 첫 회차가 버킷 중간에 시작한 사용자는 이 값이 7보다 작아야 한다.
        participation_days = await _participation_days(user_id, bucket_period)
        buckets.append(
            {
                "start_date": start,
                "end_date": end,
                "is_partial": end > as_of,
                "eligible_days": max(0, eligible_days),
                "participation_days": participation_days,
                **counts,
            }
        )
    return buckets


async def _cycles_page(user_id: int, cursor: int | None, limit: int) -> tuple[list[dict[str, object]], int | None]:
    query = ChallengeCycle.filter(user_id=user_id, status__in=["active", "completed", "stopped", "terminated"])
    if cursor is not None:
        query = query.filter(id__lt=cursor)
    cycles = await query.order_by("-id").limit(limit + 1)
    has_more = len(cycles) > limit
    cycles = cycles[:limit]
    next_cursor = str(cycles[-1].id) if has_more and cycles else None

    items: list[dict[str, object]] = []
    for cycle in cycles:
        user_challenges = await HealthRepository().list_user_challenges(cycle.id, user_id)
        period = PeriodBounds(
            "all",
            cycle.start_date,
            cycle.end_date,
            cycle.start_date,
            min(cycle.end_date, today_kst()),
            True,
            today_kst(),
        )
        for uc in user_challenges:
            uc._cycle = cycle  # type: ignore[attr-defined]
        challenges = await _summaries_for_user_challenges(user_challenges, period)
        counts = _summary_counts(challenges)
        items.append(
            {
                "cycle_id": str(cycle.id),
                "cycle_number": cycle.cycle_number,
                "start_date": cycle.start_date,
                "end_date": cycle.end_date,
                "status": cycle.status,
                "selected_challenges": [
                    {"challenge_code": c["challenge_code"], "title": c["title"]} for c in challenges
                ],
                **counts,
            }
        )
    return items, next_cursor


async def _summaries_for_user_challenges(
    user_challenges: list[UserChallenge], period: PeriodBounds
) -> list[dict[str, object]]:
    """Same aggregation as `_build_challenge_summaries` but over an already-fetched
    UserChallenge list, bounded by each challenge's own cycle instead of a report period
    (used by cycle pagination, which needs exactly one cycle's rows, and never shows
    per-day goal_windows)."""

    if not user_challenges:
        return []
    as_of = period.as_of_date

    def windows_for(uc: UserChallenge, cycle: ChallengeCycle) -> list[GoalWindow]:
        elapsed_end = min(cycle.end_date, as_of)
        if uc.frequency == "daily":
            return _daily_windows(cycle.start_date, elapsed_end)
        return _weekly_windows(cycle.start_date, cycle.end_date, cycle.start_date, elapsed_end)

    def unconfirmed_bounds_for(_uc: UserChallenge, cycle: ChallengeCycle) -> tuple[date, date]:
        return cycle.start_date, cycle.end_date

    return await _accumulate_challenges(
        user_challenges,
        as_of,
        windows_for=windows_for,
        unconfirmed_bounds_for=unconfirmed_bounds_for,
        include_goal_windows=False,
    )


class ReportService:
    def __init__(self) -> None:
        self.health_repo = HealthRepository()

    async def build_report(self, user: User, period: PeriodKey) -> dict[str, object]:
        as_of = today_kst()
        anchor = await _week_anchor_cycle(self.health_repo, user.id)
        bounds = await _compute_period(period, anchor, as_of, user.id)
        challenges = await _build_challenge_summaries(user.id, bounds, include_goal_windows=(period == "week"))
        counts = _summary_counts(challenges)
        participation_days = await _participation_days(user.id, bounds)
        completed_cycles_count = await _completed_cycles_count(user.id, bounds)

        has_selection = bool(challenges)
        has_activity = counts["practiced_days"] > 0 or any(
            c["frequency"] == "unconfirmed" and c["record_count"] > 0 for c in challenges
        )
        if not has_selection:
            report_status = "empty"
            empty_reason = "no_challenges"
        elif not has_activity and counts["planned_count"] == 0:
            report_status = "empty"
            empty_reason = "no_participation_in_period"
        else:
            report_status = "ready"
            empty_reason = None

        # Barriers/highlights/next-action are only shown for `week` (API_CONTRACT §2.4);
        # `four-week` keeps barriers as an independent card, `all` shows none of these.
        selected_uc_ids = await self._selected_ids_for_barriers(user.id, bounds)
        barriers = (
            await _barriers(user.id, bounds, selected_uc_ids)
            if period in ("week", "four-week")
            else {"total_count": 0, "items": []}
        )
        highlights = _highlights(challenges) if period == "week" else []
        needs_support = (
            _needs_support(challenges, highlights[0]["challenge_code"] if highlights else None)
            if period == "week"
            else None
        )
        next_adjustment = None
        if period == "week" and barriers["items"]:
            top_reason = barriers["items"][0]["reason_code"]
            code, message = BARRIER_SUGGESTIONS.get(top_reason, ("restart_tomorrow", "현재 목표를 이어가세요."))
            next_adjustment = {"code": code, "message": message}

        next_action = (
            self._next_action(report_status, counts)
            if period == "week"
            else {
                "code": "view_guidance",
                "label": "자세히 보기",
                "message": "습관별 현황을 확인해 보세요.",
            }
        )

        trend = {"unit": None, "buckets": []}
        if period == "four-week" and anchor is not None:
            trend = {"unit": "week", "buckets": await _trend_buckets(user.id, anchor, as_of)}

        cycles_page = {"items": [], "next_cursor": None}
        if period == "all":
            items, next_cursor = await _cycles_page(user.id, None, CYCLES_PAGE_SIZE)
            cycles_page = {"items": items, "next_cursor": next_cursor}

        headline = _headline(report_status, counts["practiced_days"], counts["completion_rate"])

        return {
            "contract_version": "report-v1.4-draft",
            "status": report_status,
            "empty_reason": empty_reason,
            "report_id": report_id_for(period, as_of),
            # §3 API 공통 조건: 날짜는 Asia/Seoul YYYY-MM-DD, 시각(timestamp)은 ISO 8601 UTC.
            "generated_at": datetime.now(UTC),
            "period": bounds.to_dict(),
            "summary": {
                **counts,
                "participation_days": participation_days,
                "completed_cycles_count": completed_cycles_count,
            },
            "headline": headline,
            "challenges": [{k: v for k, v in c.items() if not k.startswith("_")} for c in challenges],
            "trend": trend,
            "highlights": highlights,
            "needs_support": needs_support,
            "next_adjustment": next_adjustment,
            "barriers": barriers,
            "next_action": next_action,
            "cycles": cycles_page,
            "availability": {"wearable": "not_connected", "health_measurements": "not_in_scope"},
            "disclaimer": DISCLAIMER,
        }

    async def _selected_ids_for_barriers(self, user_id: int, bounds: PeriodBounds) -> list[int]:
        if bounds.start_date is None:
            return []
        user_challenges = await _selected_user_challenges_overlapping(user_id, bounds.start_date, bounds.end_date)
        return [uc.id for uc in user_challenges]

    def _next_action(self, report_status: str, counts: dict[str, object]) -> dict[str, object]:
        if report_status == "empty":
            return {"code": "start_cycle", "label": "챌린지 시작하기", "message": "생활습관 챌린지를 시작해 보세요."}
        if counts["unrecorded_count"] > 0 or counts["planned_count"] > counts["completed_count"]:
            return {"code": "record_today", "label": "오늘 기록하기", "message": "오늘의 실천을 기록해 보세요."}
        return {"code": "continue_cycle", "label": "계속 실천하기", "message": "지금처럼 계속 실천해 보세요."}

    async def cycles_page(self, user: User, cursor: str | None, limit: int) -> dict[str, object]:
        cursor_id = None
        if cursor is not None:
            try:
                cursor_id = int(cursor)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "error_code": "INVALID_CURSOR",
                        "message": "cursor 값이 올바르지 않습니다.",
                        "retryable": False,
                    },
                ) from exc
        items, next_cursor = await _cycles_page(user.id, cursor_id, limit)
        return {"items": items, "next_cursor": next_cursor}


def resolve_report_id(report_id: str) -> tuple[PeriodKey, date]:
    parsed = _parse_report_id(report_id)
    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "REPORT_NOT_FOUND", "message": "리포트를 찾을 수 없습니다.", "retryable": False},
        )
    return parsed
