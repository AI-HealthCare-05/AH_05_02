# 챌린지별 frequency 분류 근거 (2026-09-08)

`report-handoff-20260907` 패키지는 챌린지가 4개(가볍게 걷기·식사 리듬 지키기·덜 달게 마시기·정기 점검하기)라고 가정했지만, 이 4개는 실제 운영 카탈로그가 아니라 `src/frontend/app.js::fallbackChallenges`(서버 연결 불가 시 프론트가 보여주는 오프라인 데모 목록)의 이름이었다. 실제 운영 카탈로그는 `app/services/challenges.py::CHALLENGE_CATALOG`의 29개이며, 각 항목은 `daily_goal`이 자유 문장이라 "매일 하는 목표"인지 "주 N회 목표"인지 구조화된 값이 없었다.

이 문서는 `app/core/db/migrations/models/21_20260908090000_report_goal_frequency_snapshot.py`가 각 챌린지에 부여한 `frequency`/`target_count`의 근거를 남긴다. **분류 원칙: 제목 또는 daily_goal 문장에 "하루"/"매일"/"오늘"/"주 N회"/"주 N일"처럼 빈도를 명시하는 표현이 있을 때만 분류하고, 그렇지 않으면 임의로 추정하지 않고 `frequency=null`(API에서는 `unconfirmed`)로 남긴다.** `activity_150m_weekly`처럼 "며칠 했는지"가 아니라 "누적 시간"을 목표로 하는 항목도, 이번 리포트의 일수 기반 평가 모델 자체와 맞지 않으므로 unconfirmed로 분류했다.

## daily, target_count=1 (6개)

| code | title | daily_goal | 근거 |
|---|---|---|---|
| regular_meals_log | 규칙적인 식사 횟수 기록하기 | 하루 1회 기록 | "하루 1회" 명시 |
| activity_check | 오늘의 신체활동 확인하기 | 하루 1회 확인 | "하루 1회" 명시 |
| two_minute_activity_break | 오래 앉아 있을 때 2분 움직이기 | 하루 1회 | "하루 1회" 명시 |
| reduce_processed_food | 가공식품 줄이기 | 가공식품을 먹지 않은 하루 만들기 | "하루" 명시 |
| daily_meal_review | 오늘 식사 돌아보기 | 하루 식사 습관 간단 기록 | "하루" 명시, code에도 daily |
| smoke_free_today | 오늘도 금연 | 담배와 전자담배 사용하지 않기 | title "오늘도"가 매일 반복을 명시(code도 today) |

## weekly (9개)

| code | title | daily_goal | frequency/target_count | 근거 |
|---|---|---|---|---|
| weekly_weight_log | 일주일에 한 번 체중 기록하기 | 주 1회 기록 | weekly / 1 | "주 1회" 명시 |
| strength_twice_weekly | 근력운동 주 2회 | 연속되지 않은 날에 주 2회 | weekly / 2 | "주 2회" 명시 |
| balance_flex_twice_weekly | 균형·유연성 운동 주 2회 | 스트레칭·의자운동·균형운동 주 2회 | weekly / 2 | "주 2회" 명시 |
| weekly_habit_review | 생활습관 돌아보기 | 운동·식사·수면 기록 주 1회 확인 | weekly / 1 | "주 1회" 명시 |
| walk_three_days_weekly | 주 3일 이상 걷기 | 걸은 날을 주 3일 이상 기록 | weekly / 3 | "주 3일" 명시 |
| unsweetened_drink_five_days | 무가당 음료 주 5일 | 물 또는 무가당 음료를 선택한 날 기록 | weekly / 5 | title의 "주 5일" 명시 |
| vegetables_five_days | 채소 먹기 주 5일 | 채소를 충분히 먹은 날 기록 | weekly / 5 | title의 "주 5일" 명시 |
| whole_grain_three_times | 통곡물 선택 주 3회 | 잡곡·통곡물·콩류를 선택한 횟수 기록 | weekly / 3 | title의 "주 3회" 명시 |
| weekly_weight_trend | 체중 추이 확인 | 주 1회 같은 조건에서 기록 확인 | weekly / 1 | "주 1회" 명시 |

## unconfirmed — frequency null (14개)

기록(record_count/record_dates)만 표시하고 목표·평가·달성률은 null로 반환한다. 매일/주 몇 회인지 문장에 명시가 없거나(예: "10분", "몸 상태에 맞춰 최대 30분"), 하루 여러 끼 단위 표현("한 끼 이상")이라 날짜 단위 목표로 바로 못 바꾸거나, 날짜수가 아닌 누적 시간 목표라서 이번 일수 기반 모델과 맞지 않는 경우다.

| code | title | daily_goal | 미분류 사유 |
|---|---|---|---|
| walk_after_meal_10m | 식후 10분 천천히 걷기 | 10분 | 빈도 표현 없음 |
| brisk_walk_30m | 빠르게 걷기 | 몸 상태에 맞춰 최대 30분 | 빈도 표현 없음 |
| activity_break_30m | 30분마다 일어나기 | 3~5분 가볍게 움직이기 | 빈도 표현 없음 |
| water_instead_sugary_drink | 단 음료 대신 물 | 물이나 무가당 음료 선택 | 빈도 표현 없음 |
| vegetables_first | 채소 먼저 먹기 | 한 끼 이상 채소 먼저 먹기 | 끼니 단위, 날짜 목표 아님 |
| half_plate_vegetables | 접시 절반 채소 | 한 끼의 약 절반을 채소로 구성 | 끼니 단위, 날짜 목표 아님 |
| whole_grain_choice | 통곡물·잡곡 선택 | 한 끼를 잡곡·통곡물·콩류로 바꾸기 | 끼니 단위, 날짜 목표 아님 |
| whole_fruit_choice | 과일은 통째로 | 과일주스 대신 생과일 선택 | 빈도 표현 없음 |
| healthy_snack_swap | 달콤한 간식 바꾸기 | 견과류·무가당 유제품·과일 중 선택 | 빈도 표현 없음 |
| slow_meal_15m | 천천히 식사하기 | 한 끼를 15분 이상 먹기 | 끼니 단위, 날짜 목표 아님 |
| sleep_7_8h | 7~8시간 수면 기록 | 기상 후 수면시간 입력 | 빈도 표현 없음 |
| healthy_grocery_list | 건강한 장보기 | 건강한 식재료 3종 이상 준비 | 빈도 표현 없음 |
| postmeal_light_activity | 식후 10분 가볍게 움직이기 | 걷기 또는 가벼운 집안일 10분 | 빈도 표현 없음 |
| activity_150m_weekly | 주 150분 움직이기 | 중강도 활동시간을 주간 누적으로 기록 | 날짜수가 아닌 누적 시간 목표 — 일수 기반 모델과 불일치 |

## 이 분류의 한계 (제품·기획팀 검토 필요)

- 이 분류는 순수 텍스트 판단이며 실제 건강행동 전문가 검토를 거치지 않았다. 특히 unconfirmed 14개 중 상당수는 실제로는 "매일 실천이 맞다"고 봐도 이상하지 않은 항목들(예: 물 마시기, 채소 먼저 먹기)이라 제품팀이 "매일"로 확정해 주면 즉시 weekly/daily로 옮길 수 있다.
- `user_challenges`의 과거(이 마이그레이션 이전) 선택 기록은 "선택 당시의 정의"가 원래 저장되어 있지 않았으므로, 마이그레이션이 현재 카탈로그 값을 그대로 복사해 넣었다. 즉 과거 회차의 스냅샷은 실제 "그 당시" 정의가 아니라 "이 마이그레이션 시점의" 정의다.
- 이 문서와 마이그레이션은 새 회차 선택부터는 정확한 스냅샷(선택 시점의 frequency/target_count/title)을 남긴다(`app/services/challenges.py::create_cycle`).
