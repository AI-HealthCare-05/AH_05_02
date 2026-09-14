# 이수인 게임 연계형 웹 화면 API 연결 위치와 응답 필드

작성일: 2026-09-10  
대상 화면: 메인 MVP, 챌린지, 보상 화면, RAG 건강교육·퀴즈, 당근의 숲

## 1. 전체 화면 흐름

완료 기준 흐름은 아래 순서로 연결한다.

```text
로그인 → 건강정보 → 예측 → 설명 → 챌린지 → 보상 → 당근의 숲
```

프론트 주요 위치:

- 메인 화면: `src/frontend/index.html`
- 메인 MVP 동작: `src/frontend/app.js`
- 당근의 숲 화면: `src/frontend/forest.html`
- 당근의 숲 동작: `src/frontend/forest-game.js`

## 2. 로그인

프론트 연결 위치:

- `src/frontend/app.js`
- 로그인 폼 제출 후 토큰을 저장하고 이후 API 요청의 `Authorization: Bearer {token}` 헤더에 사용한다.

API:

- `POST /api/v1/auth/login`

필요 요청 필드:

- `email`
- `password`

필요 응답 필드:

- `access_token`

## 3. 건강정보 입력 및 저장

프론트 연결 위치:

- `src/frontend/app.js`
- 건강정보 입력 폼에서 기본 건강정보와 상세 건강정보를 수집해 저장한다.

API:

- `POST /api/v1/health-checkups`
- `GET /api/v1/health-checkups`

필요 요청 필드:

- `checkup_date`
- `height_cm`
- `weight_kg`
- `waist_cm`
- `systolic_bp`
- `diastolic_bp`
- `self_rated_health`
- `meal_count_yesterday`
- `smoking_status`
- `regular_exercise`
- `current_drinker`
- `exercise_days_per_week`
- `exercise_minutes`
- `feature_schema_version`

필요 응답 필드:

- `checkup_id`
- `checkup_date`
- `height_cm`
- `weight_kg`
- `bmi`
- `waist_cm`
- `systolic_bp`
- `diastolic_bp`
- `created_at`

## 4. 예측 및 설명

프론트 연결 위치:

- `src/frontend/app.js`
- 예측 요청 후 작업 상태를 확인하고 결과 화면에 오늘이·내일이 결과를 나눠 표시한다.
- XAI 표시 영역은 현재 결과와 미래 결과 아래에 각각 준비되어 있다.

API:

- `POST /api/v1/prediction-jobs`
- `GET /api/v1/prediction-jobs/{job_id}`
- `GET /api/v1/predictions/{prediction_id}`
- `GET /api/v1/predictions/{prediction_id}/risk-factors`

필요 요청 필드:

- `checkup_id`
- `model_key`

필요 응답 필드:

- `job_id`
- `status`
- `prediction_id`
- `model_key`
- `risk_category`
- `raw_probability_exposed`
- `public_message`
- `result_status`
- `items`

XAI 응답의 `items` 권장 필드:

- `display_name`
- `factor_name`
- `message`
- `description`
- `direction`
- `modifiable`

## 5. 챌린지 추천 및 선택

프론트 연결 위치:

- `src/frontend/app.js`
- 예측 결과 이후 챌린지 추천을 불러오고 사용자가 선택한 항목으로 4주 챌린지 사이클을 생성한다.

API:

- `GET /api/v1/challenge-recommendations`
- `POST /api/v1/challenge-cycles`
- `GET /api/v1/challenge-cycles/current`

필요 요청 필드:

- `prediction_id`
- `start_date`
- `challenge_ids`
- `catalog_version`
- `focus`
- `difficulty`

필요 응답 필드:

- `cycle_id`
- `cycle_number`
- `start_date`
- `end_date`
- `status`
- `user_challenges`

`user_challenges` 필요 필드:

- `user_challenge_id`
- `challenge_id`
- `title`
- `category`
- `daily_goal`
- `description`
- `safety`
- `catalog_version`
- `verification_type`
- `domain`

## 6. 챌린지 기록 완료

프론트 연결 위치:

- `src/frontend/app.js`
- `completeDailyRecord()`에서 오늘 실천 기록을 저장한다.
- 마지막 남은 챌린지를 완료하면 보상 수령 흐름으로 이어진다.

API:

- `PUT /api/v1/user-challenges/{user_challenge_id}/logs/{log_date}`
- `GET /api/v1/user-challenges/{user_challenge_id}/logs`

필요 요청 필드:

- `is_completed`
- `source`
- `note`
- `value`

필요 응답 필드:

- `log_id`
- `user_challenge_id`
- `log_date`
- `is_completed`
- `value`
- `source`
- `note`
- `updated_at`

## 7. 챌린지 완료 보상

프론트 연결 위치:

- `src/frontend/index.html`
- `src/frontend/app.js`
- 보상 다이얼로그 ID: `challenge-reward-dialog`
- 오늘 선택한 챌린지를 모두 완료하면 개인 일일 보상 API를 호출하고 보상 화면을 표시한다.
- 보상 화면의 `당근의 숲으로 가기` 버튼은 숲 진입 선택창으로 연결된다.

API:

- `GET /api/v1/challenge-rewards/daily`
- `GET /api/v1/challenge-rewards/daily/{reward_date}`
- `POST /api/v1/challenge-rewards/daily`
- `POST /api/v1/challenge-rewards/daily/{reward_date}`

필요 응답 필드:

- `reward_id`
- `reward_date`
- `completed`
- `required`
- `eligible`
- `claimed`
- `already_claimed`
- `credited`
- `carrot_amount`
- `carrot_balance`

의료 안전 문구:

- 보상 화면에는 “보상은 생활습관 기록에 대한 응원이며 질병 위험 감소나 치료 효과를 의미하지 않습니다.” 문구를 유지한다.

## 8. 당근의 숲 진입

프론트 연결 위치:

- `src/frontend/index.html`
- `src/frontend/app.js`
- `src/frontend/forest.html`
- `src/frontend/forest-game.js`
- 메인 MVP의 함께하기 영역과 보상 화면에서 당근의 숲 진입 흐름을 제공한다.

API:

- `GET /api/v1/shared-challenge-groups`
- `GET /api/v1/forest/spaces/{group_id}`
- `POST /api/v1/forest/spaces`
- `GET /api/v1/forest/catalog`

필요 응답 필드:

- `group_id`
- `title`
- `common_goal`
- `members`
- `today`
- `me`
- `catalog`

`today` 필요 필드:

- `completed_count`
- `target_count`
- `group_reward_ready`
- `group_reward_claimed`

`me` 필요 필드:

- `avatar_name`
- `carrot_balance`
- `accessory_code`

## 9. 당근의 숲 그룹 보상

프론트 연결 위치:

- `src/frontend/forest-game.js`
- 당근의 숲 내부 `일일 보상 받기` 버튼에서 그룹 일일 보상 API를 호출한다.

API:

- `POST /api/v1/forest/spaces/{group_id}/rewards/group-daily`

필요 응답 필드:

- `reward_id`
- `reward_date`
- `carrot_amount`
- `item_code`
- `carrot_balance`
- `already_claimed`

## 10. RAG 건강교육 질문

프론트 연결 위치:

- `src/frontend/index.html`
- `src/frontend/app.js`
- 건강도구 화면의 생활습관 도움말 폼 `rag-form`에서 질문을 보낸다.

API:

- `POST /api/v1/health-education/questions`

필요 요청 필드:

- `question`

필요 응답 필드:

- `answer_status`
- `answer`
- `citations`
- `medical_notice`
- `retrieval_method`

`citations` 필요 필드:

- `title`
- `url`

처리 상태:

- `grounded`
- `insufficient_evidence`
- `medical_safety_refusal`

의료 안전 문구:

- `medical_notice`가 없을 경우 프론트 기본 문구 “일반 건강교육 정보이며 개인 진단·처방을 대신하지 않습니다.”를 표시한다.

## 11. RAG 건강교육·퀴즈

프론트 연결 위치:

- `src/frontend/index.html`
- `src/frontend/app.js`
- 4주 건강교육·퀴즈 카드는 `/health-education/quizzes` 응답을 4주 카드 형태로 매핑해 표시한다.

API:

- `GET /api/v1/health-education/quizzes`

필요 응답 필드:

- `quiz_id`
- `document_id`
- `quiz_type`
- `question`
- `options`
- `source_title`
- `source_url`
- `checked_at`

프론트 매핑 규칙:

- 최대 12개 문항을 사용한다.
- 4개 주차 카드에 순서대로 분배한다.
- `quiz_type`이 `ox`이면 선택지를 `참`, `거짓`으로 표시한다.
- `quiz_type`이 `fill_in_blank`이면 API의 `options`를 그대로 표시한다.
- API가 정답과 해설을 숨겨 내려주므로, 프론트는 정답을 노출하지 않고 확인형 피드백을 표시한다.

## 12. CV 식단 인증

프론트 연결 위치:

- `src/frontend/index.html`
- `src/frontend/app.js`
- 사진 인증 모달에서 업로드, 분석 중, 실패, 재시도, 완료 상태를 표시한다.

API:

- `POST /api/v1/user-challenges/{user_challenge_id}/photo-verifications`
- `POST /api/v1/food-analyses`
- `PATCH /api/v1/food-analyses/{analysis_id}/confirm`

필요 요청 필드:

- `verification_date`
- `actual_value`
- `file`
- `image_name`
- `confirmed_category`

필요 응답 필드:

- `verification_id`
- `challenge_completed`
- `review_status`
- `notice`
- `analysis_id`
- `provider`
- `status`
- `requires_user_confirmation`
- `detected_category`
- `confidence`

## 13. 로딩·실패·시간초과·재시도 상태

프론트 연결 위치:

- `src/frontend/app.js`

주요 상태:

- 예측 작업 접수, 진행 중, 완료, 실패, 시간초과
- RAG 질문 검색 중, 근거 부족, 의료 안전 거절, 실패
- 사진 인증 업로드, 분석 중, 실패, 재촬영, 간편 체크 fallback, 완료
- 챌린지 기록 저장 실패 및 재시도
- 당근의 숲 그룹 목록 로딩, 실패, 재시도

공통 응답 필드 권장:

- `status`
- `message`
- `error_code`
- `retryable`
- `retry_after_seconds`

## 14. 2026-09-10 확인 결과

8023 프리뷰 서버에서 확인한 항목:

- `/health` 200
- `/api/v1/health-education/quizzes` 노출 확인
- `/api/v1/challenge-rewards/daily` 노출 확인
- `/api/v1/challenge-rewards/daily/{reward_date}` 노출 확인
- 메인 HTML에 `challenge-reward-dialog` 포함 확인
- 메인 JS에 `/challenge-rewards/daily/{today}` 호출 포함 확인
- 메인 JS에 `/health-education/quizzes` 호출 포함 확인

실행한 테스트:

- `node --check src/frontend/app.js`
- `node tests/frontend/completed_record.test.cjs`
- `node tests/frontend/education_carousel.test.cjs`
- `node tests/frontend/health_education_result.test.cjs`
- `uv run pytest -q tests/test_wellness_extensions.py tests/test_quiz_generator.py`
- `uv run pytest -q tests/test_mvp_demo_flow.py::test_demo_mode_completes_core_user_flow_without_redis tests/test_carrot_forest_lite.py::test_carrot_forest_lite_group_reward_avatar_and_object_flow`

