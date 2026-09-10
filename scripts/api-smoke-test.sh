#!/bin/bash
# 공동 연동표 기준 API 점검 스크립트
# 사용법: BASE_URL을 실제 서버에 맞게 바꾼 뒤 실행하세요.
#   docker compose up -d 로 로컬 서버가 떠 있어야 합니다 (기본 포트 8001).
#   brew install jq (jq 없으면 설치 필요)
set -uo pipefail

BASE="${BASE_URL:-http://localhost:8001/api/v1}"
STAMP=$(date +%s)
LAT=37.5665
LON=126.9780

hr() { echo; echo "=================================================="; echo "$1"; echo "=================================================="; }

signup_and_login() {
  local email="$1"
  curl -s -o /dev/null -w "  signup HTTP:%{http_code}\n" -X POST "$BASE/auth/signup" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\",\"password\":\"Passw0rd!\",\"terms_agreed\":true}" >&2

  curl -s -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\",\"password\":\"Passw0rd!\"}" | jq -r .access_token
}

poll_job() {
  local job_id="$1" auth="$2"
  for _ in $(seq 1 20); do
    resp=$(curl -s "$BASE/prediction-jobs/$job_id" -H "$auth")
    status=$(echo "$resp" | jq -r '.data.status // .status // empty')
    if [[ "$status" == "succeeded" || "$status" == "failed" ]]; then
      echo "$resp" | jq .
      return
    fi
    sleep 2
  done
  echo "  (20회 폴링 후에도 완료 안 됨 — ai-worker가 떠 있는지 확인하세요)"
}

# ---------- User A: 정상 흐름 (오늘이/내일이/모레노/챌린지/대시보드) ----------
hr "1. 회원가입 (User A)"
EMAIL_A="apitest_a_${STAMP}@example.com"
TOKEN_A=$(signup_and_login "$EMAIL_A")
AUTH_A="Authorization: Bearer $TOKEN_A"
echo "  token: ${TOKEN_A:0:24}..."

hr "2. 사용자 정보 (프로필 입력)"
curl -s -X PATCH "$BASE/users/me/profile" -H "$AUTH_A" -H "Content-Type: application/json" \
  -d '{"birthday":"1965-01-01","gender":"FEMALE","height_cm":160}' | jq .
curl -s "$BASE/users/me" -H "$AUTH_A" | jq .

hr "3. 동의"
curl -s -X POST "$BASE/consents" -H "$AUTH_A" -H "Content-Type: application/json" \
  -d '{"consent_item":"health_data","version":"1.0","is_agreed":true}' | jq .

hr "4. 적합성 확인 (정상 케이스, 응급 아님)"
curl -s -X POST "$BASE/eligibility-checks" -H "$AUTH_A" -H "Content-Type: application/json" \
  -d '{"has_diabetes_diagnosis":false,"has_urgent_warning_sign":false,"population_in_scope":true}' | jq .

hr "5. 건강정보 입력 (health-checkups)"
CHECKUP=$(curl -s -X POST "$BASE/health-checkups" -H "$AUTH_A" -H "Content-Type: application/json" \
  -d '{
    "checkup_type":"initial",
    "checkup_date":"2026-09-07",
    "height_cm":160,
    "weight_kg":68.5,
    "waist_cm":82,
    "systolic_bp":128,
    "diastolic_bp":82,
    "smoking_status":"never",
    "regular_exercise":true,
    "current_drinker":false,
    "exercise_days_per_week":3,
    "exercise_minutes":40
  }')
echo "$CHECKUP" | jq .
CHECKUP_ID=$(echo "$CHECKUP" | jq -r '.data.checkup_id // .checkup_id')
echo "  checkup_id: $CHECKUP_ID"

hr "6. 오늘이 (현재 위험 신호 선별, diabetes_current_screening)"
JOB1=$(curl -s -X POST "$BASE/prediction-jobs" -H "$AUTH_A" -H "Content-Type: application/json" \
  -d "{\"checkup_id\":$CHECKUP_ID,\"model_key\":\"diabetes_current_screening\"}")
echo "$JOB1" | jq .
JOB1_ID=$(echo "$JOB1" | jq -r '.data.job_id // .job_id')
poll_job "$JOB1_ID" "$AUTH_A"

hr "7. 내일이 (약 2년 후 위험, diabetes_incidence) — signal_level 확인"
JOB2=$(curl -s -X POST "$BASE/prediction-jobs" -H "$AUTH_A" -H "Content-Type: application/json" \
  -d "{\"checkup_id\":$CHECKUP_ID,\"model_key\":\"diabetes_incidence\"}")
echo "$JOB2" | jq .
JOB2_ID=$(echo "$JOB2" | jq -r '.data.job_id // .job_id')
poll_job "$JOB2_ID" "$AUTH_A"
echo "  --- predictions/latest (age_risk_forecast.signal_level 확인) ---"
curl -s "$BASE/predictions/latest" -H "$AUTH_A" | jq '.data.age_risk_forecast // .age_risk_forecast'

hr "8. [참고용, 이번 MVP 범위 제외] 모레노 (생존모델 전망) — 승인된 모델 없어서 503 나오는 게 정상입니다"
curl -s -w "\n  HTTP:%{http_code}\n" -X POST "$BASE/prediction-jobs" -H "$AUTH_A" -H "Content-Type: application/json" \
  -d "{\"checkup_id\":$CHECKUP_ID,\"model_key\":\"diabetes_lifetime_risk\",\"prediction_type\":\"survival_curve\"}"

hr "9. 고위험 안내 (병원 검색, 카카오 연동)"
curl -s "$BASE/medical-facilities/nearby?lat=$LAT&lon=$LON&radius=5000" -H "$AUTH_A" | jq .
echo "  --- data_source가 kakao_local_api_keyword_diabetes 인지 확인하세요 (development_mock이면 문제) ---"

hr "10. 챌린지"
curl -s "$BASE/challenges" -H "$AUTH_A" | jq .
curl -s "$BASE/challenge-recommendations" -H "$AUTH_A" | jq .

hr "11. 대시보드"
curl -s "$BASE/dashboard/summary" -H "$AUTH_A" | jq .

# ---------- User B: 응급 안내 (네/아니오 문진 팝업 - 응급 케이스) ----------
hr "12. 응급 안내 (User B, 응급 신호 있음 케이스)"
EMAIL_B="apitest_b_${STAMP}@example.com"
TOKEN_B=$(signup_and_login "$EMAIL_B")
AUTH_B="Authorization: Bearer $TOKEN_B"
curl -s -X PATCH "$BASE/users/me/profile" -H "$AUTH_B" -H "Content-Type: application/json" \
  -d '{"birthday":"1965-01-01","gender":"FEMALE","height_cm":160}' > /dev/null
curl -s -X POST "$BASE/consents" -H "$AUTH_B" -H "Content-Type: application/json" \
  -d '{"consent_item":"health_data","version":"1.0","is_agreed":true}' > /dev/null

echo "  --- 응급 신호 '예' 문진 제출 → next_action이 urgent_medical_guidance 인지 확인 ---"
curl -s -X POST "$BASE/eligibility-checks" -H "$AUTH_B" -H "Content-Type: application/json" \
  -d '{"has_diabetes_diagnosis":false,"has_urgent_warning_sign":true,"population_in_scope":true}' | jq .

echo "  --- 응급실 검색 (NEMC 연동) ---"
curl -s "$BASE/emergency-facilities/nearby?lat=$LAT&lon=$LON&radius=10000" -H "$AUTH_B" | jq .

hr "완료"
