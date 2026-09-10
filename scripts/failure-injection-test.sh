#!/bin/bash
# 실패 케이스 주입 테스트: 모델 미설치 / Redis 장애 / 타임아웃
#
# 사용법 (docker compose up -d 로 로컬 서버가 떠 있어야 합니다):
#   bash scripts/failure-injection-test.sh model-today     # 오늘이 모델 파일 없음
#   bash scripts/failure-injection-test.sh model-tomorrow  # 내일이 모델 파일 없음
#   bash scripts/failure-injection-test.sh redis           # Redis 장애
#   bash scripts/failure-injection-test.sh timeout         # 타임아웃
#   bash scripts/failure-injection-test.sh all             # 전부 순서대로
#
# 각 시나리오는 끝나면 자동으로 원상복구합니다. 중간에 Ctrl-C로 끊어도
# trap이 최선을 다해 복구하지만, 끝나고 `docker compose ps`로 한 번
# 확인해 보시는 걸 권장합니다.

set -uo pipefail
BASE="${BASE_URL:-http://localhost:8001/api/v1}"

hr() { echo; echo "=================================================="; echo "$1"; echo "=================================================="; }

# ---------- 공통: 유저 하나 만들고 health-checkup까지 세팅 ----------
setup_user_and_checkup() {
  local tag="$1"
  local email="failtest_${tag}_$(date +%s)@example.com"
  curl -s -o /dev/null -X POST "$BASE/auth/signup" -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\",\"password\":\"Passw0rd!\",\"terms_agreed\":true}"
  TOKEN=$(curl -s -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\",\"password\":\"Passw0rd!\"}" | jq -r .access_token)
  AUTH="Authorization: Bearer $TOKEN"
  if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
    echo "  회원가입/로그인 실패 — 서버가 떠 있는지 확인하세요 (docker compose ps)"
    return 1
  fi
  curl -s -X PATCH "$BASE/users/me/profile" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"birthday":"1965-01-01","gender":"FEMALE","height_cm":160}' >/dev/null
  curl -s -X POST "$BASE/consents" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"consent_item":"health_data","version":"1.0","is_agreed":true}' >/dev/null
  curl -s -X POST "$BASE/eligibility-checks" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"has_diabetes_diagnosis":false,"has_urgent_warning_sign":false,"population_in_scope":true}' >/dev/null
  CHECKUP=$(curl -s -X POST "$BASE/health-checkups" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"checkup_type":"initial","checkup_date":"2026-09-08","height_cm":160,"weight_kg":68.5,"waist_cm":82,"systolic_bp":128,"diastolic_bp":82,"smoking_status":"never","regular_exercise":true,"current_drinker":false,"exercise_days_per_week":3,"exercise_minutes":40}')
  CHECKUP_ID=$(echo "$CHECKUP" | jq -r '.data.checkup_id // .checkup_id')
  if [[ -z "$CHECKUP_ID" || "$CHECKUP_ID" == "null" ]]; then
    echo "  health-checkup 생성 실패:"; echo "$CHECKUP" | jq .
    return 1
  fi
}

# job을 만들고 succeeded/failed까지 폴링해서 전체 응답을 찍는다
submit_and_poll() {
  local model_key="$1"
  JOB=$(curl -s -X POST "$BASE/prediction-jobs" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"checkup_id\":$CHECKUP_ID,\"model_key\":\"$model_key\"}")
  echo "  --- job 생성 응답 ---"
  echo "$JOB" | jq .
  JOB_ID=$(echo "$JOB" | jq -r '.data.job_id // .job_id // empty')
  if [[ -z "$JOB_ID" ]]; then
    echo "  (job_id 없음 — 위 응답이 큐 장애 등으로 즉시 실패한 것일 수 있습니다. 이게 기대값일 수도 있습니다)"
    return
  fi
  echo "  --- 폴링 결과 (queued -> succeeded/failed) ---"
  for _ in $(seq 1 20); do
    RESP=$(curl -s "$BASE/prediction-jobs/$JOB_ID" -H "$AUTH")
    STATUS=$(echo "$RESP" | jq -r '.data.status // .status // empty')
    if [[ "$STATUS" == "succeeded" || "$STATUS" == "failed" ]]; then
      echo "$RESP" | jq .
      return
    fi
    sleep 2
  done
  echo "  (20회 폴링 후에도 안 끝남 — docker compose logs ai-worker ai-worker-current 확인)"
}

# ---------- 시나리오 1: 오늘이 모델 파일 없음 ----------
scenario_model_today() {
  hr "모델 미설치 - 오늘이 (MODEL_UNAVAILABLE 기대)"
  local model="models/artifacts/candidates/diabetes_current_screening/v061/model.joblib"
  if [[ ! -f "$model" ]]; then echo "  모델 파일이 이미 없습니다: $model"; return 1; fi
  mv "$model" "$model.bak"
  echo "  모델 파일 임시로 치움: $model"
  # 오늘이 로더는 캐시가 없어서 워커 재시작 없이 바로 다음 요청부터 반영됩니다.
  setup_user_and_checkup "today" && submit_and_poll "diabetes_current_screening"
  mv "$model.bak" "$model"
  echo "  모델 파일 복원 완료"
}

# ---------- 시나리오 2: 내일이 모델 파일 없음 ----------
scenario_model_tomorrow() {
  hr "모델 미설치 - 내일이 (ML_MODEL_UNAVAILABLE 기대)"
  local model="models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib"
  if [[ ! -f "$model" ]]; then echo "  모델 파일이 이미 없습니다: $model"; return 1; fi
  mv "$model" "$model.bak"
  echo "  모델 파일 임시로 치움: $model"
  echo "  내일이 로더는 lru_cache로 메모리에 캐싱되므로, 이미 한 번 성공한 적이 있다면"
  echo "  워커를 재시작해서 캐시를 비워야 실제로 실패가 재현됩니다."
  docker compose restart ai-worker
  echo "  ai-worker 재시작 완료, 기동 대기 중..."
  sleep 8
  setup_user_and_checkup "tomorrow" && submit_and_poll "diabetes_incidence"
  mv "$model.bak" "$model"
  echo "  모델 파일 복원, ai-worker 다시 재시작..."
  docker compose restart ai-worker
  sleep 8
  echo "  복원 완료"
}

# ---------- 시나리오 3: Redis 장애 ----------
scenario_redis() {
  hr "Redis 장애 (QUEUE_UNAVAILABLE, HTTP 503 기대)"
  setup_user_and_checkup "redis" || { echo "  사전 세팅 실패 (Redis가 이미 내려가 있으면 여기서부터 실패할 수 있습니다)"; }
  docker compose stop redis
  echo "  redis 컨테이너 중지 완료"
  echo "  --- 이 상태에서 prediction-jobs 생성 시도 ---"
  RESP=$(curl -s -w "\nHTTP:%{http_code}\n" -X POST "$BASE/prediction-jobs" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"checkup_id\":$CHECKUP_ID,\"model_key\":\"diabetes_incidence\"}")
  echo "$RESP"
  docker compose start redis
  echo "  redis 재기동 중, healthy 대기..."
  for _ in $(seq 1 15); do
    STATE=$(docker compose ps redis --format json 2>/dev/null | jq -r '.Health // empty' 2>/dev/null)
    [[ "$STATE" == "healthy" ]] && break
    sleep 2
  done
  echo "  redis 복구 완료"
}

# ---------- 시나리오 4: 타임아웃 ----------
scenario_timeout() {
  hr "타임아웃 (TIMEOUT, retryable=true, retry_after_seconds=30 기대)"
  cp .env .env.bak.failtest
  if grep -q '^PREDICTION_TIMEOUT_SECONDS=' .env; then
    sed -i.bak2 's/^PREDICTION_TIMEOUT_SECONDS=.*/PREDICTION_TIMEOUT_SECONDS=1/' .env
  else
    echo 'PREDICTION_TIMEOUT_SECONDS=1' >> .env
  fi
  rm -f .env.bak2
  echo "  PREDICTION_TIMEOUT_SECONDS=1로 임시 변경, 컨테이너 재생성..."
  # restart는 .env를 다시 읽지 않고 컨테이너 생성 시점 환경변수를 그대로 씁니다.
  # up -d로 재생성해야 바뀐 .env가 실제로 반영됩니다.
  docker compose up -d --force-recreate ai-worker ai-worker-current
  sleep 8
  setup_user_and_checkup "timeout" && submit_and_poll "diabetes_incidence"
  mv .env.bak.failtest .env
  echo "  .env 원복, 컨테이너 다시 재생성..."
  docker compose up -d --force-recreate ai-worker ai-worker-current
  sleep 8
  echo "  복원 완료 (1초는 너무 짧아서 다음 정상 요청까지 몇 초 걸릴 수 있습니다)"
}

case "${1:-}" in
  model-today) scenario_model_today ;;
  model-tomorrow) scenario_model_tomorrow ;;
  redis) scenario_redis ;;
  timeout) scenario_timeout ;;
  all)
    scenario_model_today
    scenario_model_tomorrow
    scenario_redis
    scenario_timeout
    ;;
  *)
    echo "사용법: bash scripts/failure-injection-test.sh [model-today|model-tomorrow|redis|timeout|all]"
    exit 1
    ;;
esac

hr "완료"
