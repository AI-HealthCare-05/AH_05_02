# 생활습관 리포트 백엔드 회신 (report-handoff-20260907 §6)

`report-handoff-20260907/BACKEND_IMPLEMENTATION_REQUEST.md` §6이 요청한 "구현 전 회신 다섯 항목"에 대한 답변이다. 요청서는 구현 전에 회신부터 받으려 했지만, 이번 작업은 §5 완료 조건을 먼저 전부 구현·테스트한 뒤 그 결과를 그대로 회신 내용으로 정리했다 — 아래 다섯 항목은 계획이 아니라 실제로 반영되어 테스트까지 통과한 내용이다.

구현 위치: `app/services/reports.py`(핵심 로직), `app/apis/v1/reports_routers.py`(라우트), `app/models/health.py` + 마이그레이션 `21_20260908090000_report_goal_frequency_snapshot.py`(스냅샷 컬럼), `docs/frontend/REPORT_CHALLENGE_FREQUENCY_MAPPING_20260908.md`(챌린지 분류 근거), `tests/test_reports_api.py`(테스트 15개). 브랜치 `fix/e2e-integration-signup-and-worker-deps`.

---

## 1. 사용할 최종 API 경로와 기존 `/weekly-reports/current` 유지 방식

**신규 엔드포인트 2개:**
- `GET /api/v1/reports?period=week|four-week|all`
- `GET /api/v1/reports/{report_id}/cycles` (`period=all`일 때만 유효 — 회차 이력 커서 페이지네이션 전용, 다른 period의 report_id로 호출하면 404)

**기존 엔드포인트는 그대로 유지, 응답 스키마 변경 없음:**
- `GET /api/v1/weekly-reports/current` — 프론트가 지금 쓰는 그대로 유지.
- `GET /api/v1/weekly-reports/current/pdf` — `week` 기간의 PDF는 계속 이 엔드포인트를 쓴다. 4주/전체 리포트의 PDF는 요청서 §4가 이번 범위 밖으로 명시했으므로 만들지 않았다.
- 다만 어려움(barrier) 집계 범위 보정(항목 4)은 신규 엔드포인트뿐 아니라 기존 `/weekly-reports/current`에도 같이 적용했다. 응답 필드는 하나도 안 바뀌고, "이번 주에 실제 선택된 챌린지 + 이번 주 날짜 범위"로만 정확히 좁혀지도록 내부 계산만 보정했다.

## 2. 사용자 주 시작일에 사용할 실제 DB 필드 또는 모델 필드

`ChallengeCycle.start_date` (`app/models/health.py`)를 사용한다.

"이번 주" 앵커 회차 선택 규칙: 사용자의 현재 활성/예정 회차(`status`가 `active` 또는 `scheduled`, `HealthRepository.active_cycle`)가 있으면 그 회차의 `start_date`. 없으면 가장 최근에 끝난 회차의 `start_date`로 대체한다(회차 사이 공백 기간에도 4주/전체 리포트가 의미 있게 나오도록 하기 위한 결정 — 이 fallback 정책 자체가 §6이 회신을 요구한 항목이라 이번에 처음 확정했다). 회차를 한 번도 시작한 적 없는 사용자는 빈 리포트(`status: empty`)를 받는다.

참고: 연속 회차는 같은 요일에 시작한다는 전제(§5.1)를 그대로 따랐다. 요일이 다른 회차가 4주/전체 조회에 섞이는 경우(예: 특정 회차만 다른 요일에 시작)는 원본 문서도 "합의 필요"로 남긴 엣지 케이스라, 이번에도 임의로 정책을 만들지 않고 "각 회차 자체의 요일에 맞춰 주 단위를 생성한다"는 원칙만 지켰다.

## 3. 챌린지별 `frequency`와 목표 정의 스냅샷을 현재 저장할 수 있는지 여부

**가능 — 이미 구현·마이그레이션 완료.**

- `challenges` 테이블에 `frequency`(`daily`/`weekly`/`null`), `target_count`, `definition_version` 컬럼 추가(카탈로그 레벨 정의).
- `user_challenges` 테이블에 `frequency`/`target_count`/`title_snapshot`/`definition_version` 컬럼 추가 — 챌린지 선택 시점에 `challenges.py::create_cycle()`이 그대로 스냅샷을 남긴다. 이후 카탈로그 문구가 바뀌거나 같은 챌린지를 다시 선택해도, 이미 진행 중이거나 끝난 회차의 리포트는 소급 변경되지 않는다.
- 단, 실제 운영 카탈로그(`app/services/challenges.py::CHALLENGE_CATALOG`, 29개)는 원래 각 항목이 자유 문장 `daily_goal`만 갖고 있어 구조화된 frequency가 존재하지 않았다. 그래서 문구에 "하루"/"주 N회" 등 빈도가 명시된 경우만 분류(6개 daily, 9개 weekly)하고, 명시되지 않은 14개는 `unconfirmed`로 남겨 마이그레이션 `21_20260908090000_report_goal_frequency_snapshot.py`에서 백필했다. 분류 근거와 "제품팀 검토 필요" 한계는 `docs/frontend/REPORT_CHALLENGE_FREQUENCY_MAPPING_20260908.md`에 정리했다. `unconfirmed` 챌린지는 리포트에서 기록(`record_count`/`record_dates`)만 보여주고 목표·평가·달성률은 전부 `null`로 반환한다 — 임의로 일/주 목표를 추정하지 않는다.
- 부수적으로 발견한 사실: 원본 요청서가 가정한 "4개 챌린지"(가볍게 걷기·식사 리듬 지키기·덜 달게 마시기·정기 점검하기)는 실제 운영 카탈로그가 아니라 `src/frontend/app.js::fallbackChallenges`(오프라인 데모 fallback)였다. 이 내용도 같은 문서에 기록해 두었다.

## 4. 지난 4주·전체 회차 조회와 barrier 범위 보정의 예상 작업 범위

**작업 범위(완료 기준):**
- **지난 4주**: 현재 주를 제외한 정확히 4개의 사용자 주 bucket(§5.1) + 4주 전체 요약(챌린지별 비율의 평균이 아니라 분자·분모 합산 후 계산, R11). `app/services/reports.py::_trend_buckets` / `_compute_period`.
- **전체**: 첫 회차 시작일부터 오늘까지의 요약 + 회차 이력 커서 페이지네이션(페이지당 10개, cursor=마지막 회차 id). `_cycles_page` / `ReportService.cycles_page`. 리포트 자체를 저장하지 않고 매 요청마다 재계산하므로(`report_id`는 결정적 키일 뿐, 저장된 스냅샷이 아님) 데이터 최신성 문제가 없고, 다른 사용자의 `report_id`로 호출해도 항상 호출자 자신의 데이터만 재계산되어 반환된다(크로스유저 접근 불가 — 테스트로 검증).
- **barrier 범위 보정(작업 F)**: 기간 종료일 + 그 기간과 겹치는 회차 + 그 기간에 실제 선택된 챌린지로 한정하고, 같은 (user_challenge_id, 날짜) 재제출은 최신 것만 반영(`EngagementRepository.list_barriers`). 요청서에는 4주 화면만 언급됐지만, 기존 `/weekly-reports/current`의 정확도도 같이 맞추는 게 낫다고 판단해 거기에도 동일 로직을 적용했다(응답 스키마는 불변).
- **실제 변경 규모**: 모델/마이그레이션 1개, 신규 서비스 파일 1개(~700줄), 신규 라우터 파일 1개, 기존 리포지토리/서비스 수정 3개(`engagement_repository.py`, `engagement.py`, `challenges.py`), 테스트 15개. 기존 전체 테스트 스위트 대비 회귀 없음(베이스라인 비교로 확인).

## 5. 구현 후 제공할 테스트 방법 또는 OpenAPI 응답 예시

**테스트 방법**: `pytest tests/test_reports_api.py` (신규 15개, 전부 통과). 각 테스트가 검증하는 것:

- 사용자 주 앵커/7칸 daily 상태 배열/완료·미실천·미기록·진행중·미래 구분
- unconfirmed 챌린지가 임의 목표를 갖지 않음
- weekly 챌린지의 조기 완료 처리 + summary의 가중평균(단순평균 아님)
- 지난 4주 정확히 4개 버킷(현재 주 제외) + 버킷 합계와 전체 요약 일치
- barrier가 기간·회차·선택 챌린지로 정확히 스코프되고 재제출은 dedup됨
- 전체 회차 커서 페이지네이션 + 크로스유저 `report_id`/`cycles` 접근 차단
- 회차 페이지 추가 조회가 상위 summary를 바꾸지 않음
- 회차를 한 번도 시작 안 한 사용자의 빈 리포트, 잘못된 `period` 파라미터의 422
- 기존 주간 PDF 엔드포인트의 크로스유저 접근 불가(신규 작업은 아니지만 같이 검증)

**응답 예시** (아래는 손으로 작성한 목업이 아니라, in-memory SQLite로 띄운 실제 FastAPI 앱이 실제로 반환한 응답을 그대로 캡처한 것이다):

### `GET /api/v1/reports?period=week` (daily 1개 + weekly 1개 + unconfirmed 1개 선택된 사용자)

```json
{
  "data": {
    "contract_version": "report-v1.4-draft",
    "status": "ready",
    "empty_reason": null,
    "report_id": "rpt-week-2026-08-29",
    "generated_at": "2026-09-08T13:24:45.134300+09:00",
    "period": {
      "key": "week",
      "timezone": "Asia/Seoul",
      "as_of_date": "2026-08-29",
      "start_date": "2026-08-26",
      "end_date": "2026-09-01",
      "effective_start_date": "2026-08-26",
      "effective_end_date": "2026-08-29",
      "is_partial": true
    },
    "summary": {
      "practiced_days": 3,
      "completed_count": 4,
      "evaluated_completed_count": 2,
      "evaluated_target_count": 3,
      "completion_rate": 66.7,
      "unrecorded_count": 0,
      "planned_count": 8,
      "participation_days": 7,
      "completed_cycles_count": 0
    },
    "headline": "이번 기간 달성률은 66.7%예요. 어려웠던 이유를 확인해 보세요.",
    "challenges": [
      {
        "challenge_code": "brisk_walk_30m",
        "title": "빠르게 걷기",
        "frequency": "unconfirmed",
        "planned_count": null,
        "practiced_days": null,
        "completed_count": null,
        "evaluated_completed_count": null,
        "evaluated_target_count": null,
        "completion_rate": null,
        "unrecorded_count": null,
        "record_count": 1,
        "record_dates": [
          "2026-08-26"
        ],
        "goal_windows": []
      },
      {
        "challenge_code": "regular_meals_log",
        "title": "규칙적인 식사 횟수 기록하기",
        "frequency": "daily",
        "planned_count": 7,
        "practiced_days": 3,
        "completed_count": 3,
        "evaluated_completed_count": 2,
        "evaluated_target_count": 3,
        "completion_rate": 66.7,
        "unrecorded_count": 0,
        "record_count": 3,
        "record_dates": [
          "2026-08-26",
          "2026-08-27",
          "2026-08-29"
        ],
        "goal_windows": [
          {
            "start_date": "2026-08-26",
            "end_date": "2026-08-26",
            "status": "completed",
            "completed_on": "2026-08-26"
          },
          {
            "start_date": "2026-08-27",
            "end_date": "2026-08-27",
            "status": "completed",
            "completed_on": "2026-08-27"
          },
          {
            "start_date": "2026-08-28",
            "end_date": "2026-08-28",
            "status": "not_completed",
            "completed_on": null
          },
          {
            "start_date": "2026-08-29",
            "end_date": "2026-08-29",
            "status": "completed",
            "completed_on": "2026-08-29"
          },
          {
            "start_date": "2026-08-30",
            "end_date": "2026-08-30",
            "status": "future",
            "completed_on": null
          },
          {
            "start_date": "2026-08-31",
            "end_date": "2026-08-31",
            "status": "future",
            "completed_on": null
          },
          {
            "start_date": "2026-09-01",
            "end_date": "2026-09-01",
            "status": "future",
            "completed_on": null
          }
        ]
      },
      {
        "challenge_code": "strength_twice_weekly",
        "title": "근력운동 주 2회",
        "frequency": "weekly",
        "planned_count": 1,
        "practiced_days": 1,
        "completed_count": 1,
        "evaluated_completed_count": 0,
        "evaluated_target_count": 0,
        "completion_rate": null,
        "unrecorded_count": 0,
        "record_count": 1,
        "record_dates": [
          "2026-08-27"
        ],
        "goal_windows": [
          {
            "start_date": "2026-08-26",
            "end_date": "2026-09-01",
            "status": "completed",
            "completed_on": "2026-08-27"
          }
        ]
      }
    ],
    "trend": {
      "unit": null,
      "buckets": []
    },
    "highlights": [
      {
        "type": "steady_habit",
        "message": "'규칙적인 식사 횟수 기록하기'을(를) 꾸준히 실천하고 있어요.",
        "challenge_code": "regular_meals_log"
      }
    ],
    "needs_support": null,
    "next_adjustment": null,
    "barriers": {
      "total_count": 0,
      "items": []
    },
    "next_action": {
      "code": "record_today",
      "label": "오늘 기록하기",
      "message": "오늘의 실천을 기록해 보세요."
    },
    "cycles": {
      "items": [],
      "next_cursor": null
    },
    "availability": {
      "wearable": "not_connected",
      "health_measurements": "not_in_scope"
    },
    "disclaimer": "기록 변화와 수행률은 질병 위험 감소, 진단 또는 치료 효과를 의미하지 않습니다."
  },
  "meta": {
    "request_id": "req_1a7426d5c45f49d5",
    "timestamp": "2026-09-08T04:24:45.134377Z"
  }
}
```

### `GET /api/v1/reports?period=four-week` (요약 일부 발췌 — daily 챌린지, 4개 버킷)

```json
{
  "contract_version": "report-v1.4-draft",
  "status": "ready",
  "report_id": "rpt-four-week-2026-09-30",
  "period": {
    "key": "four-week",
    "timezone": "Asia/Seoul",
    "as_of_date": "2026-09-30",
    "start_date": "2026-09-02",
    "end_date": "2026-09-29",
    "effective_start_date": "2026-09-02",
    "effective_end_date": "2026-09-29",
    "is_partial": false
  },
  "summary": {
    "practiced_days": 21,
    "completed_count": 21,
    "evaluated_completed_count": 21,
    "evaluated_target_count": 32,
    "completion_rate": 65.6,
    "unrecorded_count": 11,
    "planned_count": 32,
    "participation_days": 28,
    "completed_cycles_count": 0
  },
  "headline": "이번 기간 달성률은 65.6%예요. 어려웠던 이유를 확인해 보세요.",
  "trend": {
    "unit": "week",
    "buckets": [
      {
        "start_date": "2026-09-02",
        "end_date": "2026-09-08",
        "is_partial": false,
        "eligible_days": 7,
        "practiced_days": 5,
        "completed_count": 5,
        "evaluated_completed_count": 5,
        "evaluated_target_count": 8,
        "completion_rate": 62.5,
        "unrecorded_count": 3,
        "planned_count": 8
      },
      {
        "start_date": "2026-09-09",
        "end_date": "2026-09-15",
        "is_partial": false,
        "eligible_days": 7,
        "practiced_days": 5,
        "completed_count": 5,
        "evaluated_completed_count": 5,
        "evaluated_target_count": 8,
        "completion_rate": 62.5,
        "unrecorded_count": 3,
        "planned_count": 8
      },
      {
        "start_date": "2026-09-16",
        "end_date": "2026-09-22",
        "is_partial": false,
        "eligible_days": 7,
        "practiced_days": 5,
        "completed_count": 5,
        "evaluated_completed_count": 5,
        "evaluated_target_count": 8,
        "completion_rate": 62.5,
        "unrecorded_count": 3,
        "planned_count": 8
      },
      {
        "start_date": "2026-09-23",
        "end_date": "2026-09-29",
        "is_partial": false,
        "eligible_days": 7,
        "practiced_days": 6,
        "completed_count": 6,
        "evaluated_completed_count": 6,
        "evaluated_target_count": 8,
        "completion_rate": 75.0,
        "unrecorded_count": 2,
        "planned_count": 8
      }
    ]
  },
  "barriers": {
    "total_count": 0,
    "items": []
  }
}
```

### `GET /api/v1/reports?period=all` (완료된 회차 3개, 요약 일부 발췌)

```json
{
  "contract_version": "report-v1.4-draft",
  "status": "ready",
  "report_id": "rpt-all-2026-04-04",
  "period": {
    "key": "all",
    "timezone": "Asia/Seoul",
    "as_of_date": "2026-04-04",
    "start_date": "2026-01-05",
    "end_date": "2026-04-04",
    "effective_start_date": "2026-01-05",
    "effective_end_date": "2026-04-04",
    "is_partial": true
  },
  "summary": {
    "practiced_days": 0,
    "completed_count": 0,
    "evaluated_completed_count": 0,
    "evaluated_target_count": 84,
    "completion_rate": 0.0,
    "unrecorded_count": 84,
    "planned_count": 84,
    "participation_days": 84,
    "completed_cycles_count": 3
  },
  "cycles": {
    "items": [
      {
        "cycle_id": "4",
        "cycle_number": 3,
        "start_date": "2026-03-02",
        "end_date": "2026-03-29",
        "status": "completed",
        "selected_challenges": [
          {
            "challenge_code": "regular_meals_log",
            "title": "규칙적인 식사 횟수 기록하기"
          }
        ],
        "practiced_days": 0,
        "completed_count": 0,
        "evaluated_completed_count": 0,
        "evaluated_target_count": 28,
        "completion_rate": 0.0,
        "unrecorded_count": 28,
        "planned_count": 28
      },
      {
        "cycle_id": "3",
        "cycle_number": 2,
        "start_date": "2026-02-02",
        "end_date": "2026-03-01",
        "status": "completed",
        "selected_challenges": [
          {
            "challenge_code": "regular_meals_log",
            "title": "규칙적인 식사 횟수 기록하기"
          }
        ],
        "practiced_days": 0,
        "completed_count": 0,
        "evaluated_completed_count": 0,
        "evaluated_target_count": 28,
        "completion_rate": 0.0,
        "unrecorded_count": 28,
        "planned_count": 28
      },
      {
        "cycle_id": "2",
        "cycle_number": 1,
        "start_date": "2026-01-05",
        "end_date": "2026-02-01",
        "status": "completed",
        "selected_challenges": [
          {
            "challenge_code": "regular_meals_log",
            "title": "규칙적인 식사 횟수 기록하기"
          }
        ],
        "practiced_days": 0,
        "completed_count": 0,
        "evaluated_completed_count": 0,
        "evaluated_target_count": 28,
        "completion_rate": 0.0,
        "unrecorded_count": 28,
        "planned_count": 28
      }
    ],
    "next_cursor": null
  }
}
```

### `GET /api/v1/reports?period=week` (회차를 한 번도 시작하지 않은 사용자 — 빈 결과)

```json
{
  "data": {
    "contract_version": "report-v1.4-draft",
    "status": "empty",
    "empty_reason": "no_challenges",
    "report_id": "rpt-week-2026-04-04",
    "generated_at": "2026-09-08T13:24:46.248049+09:00",
    "period": {
      "key": "week",
      "timezone": "Asia/Seoul",
      "as_of_date": "2026-04-04",
      "start_date": null,
      "end_date": "2026-04-04",
      "effective_start_date": null,
      "effective_end_date": null,
      "is_partial": true
    },
    "summary": {
      "practiced_days": 0,
      "completed_count": 0,
      "evaluated_completed_count": 0,
      "evaluated_target_count": 0,
      "completion_rate": null,
      "unrecorded_count": 0,
      "planned_count": 0,
      "participation_days": 0,
      "completed_cycles_count": 0
    },
    "headline": "아직 기록이 없어요. 첫 실천을 기록해 보세요.",
    "challenges": [],
    "trend": {
      "unit": null,
      "buckets": []
    },
    "highlights": [],
    "needs_support": null,
    "next_adjustment": null,
    "barriers": {
      "total_count": 0,
      "items": []
    },
    "next_action": {
      "code": "start_cycle",
      "label": "챌린지 시작하기",
      "message": "생활습관 챌린지를 시작해 보세요."
    },
    "cycles": {
      "items": [],
      "next_cursor": null
    },
    "availability": {
      "wearable": "not_connected",
      "health_measurements": "not_in_scope"
    },
    "disclaimer": "기록 변화와 수행률은 질병 위험 감소, 진단 또는 치료 효과를 의미하지 않습니다."
  },
  "meta": {
    "request_id": "req_a4093421c1d943ef",
    "timestamp": "2026-09-08T04:24:46.248080Z"
  }
}
```

### 잘못된 `period` 파라미터

```json
{"status_code": 422, "body": {"detail": {"error_code": "INVALID_PERIOD", "message": "period는 week, four-week, all 중 하나여야 합니다.", "retryable": false}}}
```

**미완료 항목**: DB 마이그레이션은 코드로는 완성됐지만 실제 운영 MySQL에는 아직 적용하지 않았다 — Docker 환경에서 직접 실행해야 한다.
