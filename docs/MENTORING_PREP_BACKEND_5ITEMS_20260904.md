# 멘토링 준비자료 — 오늘이·내일이 5개 항목 (백엔드 박빛샘)

다음 5개 항목에 대한 답변 초안이다. 모든 수치는 실제 리포지토리의 모델 카드·Registry
Manifest·테스트 파일에서 직접 확인한 값이며, 추정치는 없다. 출처 파일 경로를 각 항목에 표기했다.

## 0. 먼저 정리할 전제 — "최종" 모델은 없다

오늘이(현재 위험 신호, `diabetes_current_screening`)와 내일이(약 2년 후 신규 발병,
`diabetes_incidence`) 둘 다 **`candidate_only` 상태이며 운영 승인된 단일 최종 모델이
없다.** 각각 여러 후보 버전이 존재한다. 멘토님께는 "최종 1개"가 아니라 "현재 가장
앞선 후보들"로 답하는 것이 정확하다.

| 모델 | 후보 버전 | promotion_status | 비고 |
| --- | --- | --- | --- |
| 오늘이 | `knhanes-current-screening-v050` | `candidate_internal_not_for_diagnosis_or_personal_probability_display` | 최초 후보 |
| 오늘이 | `knhanes-current-diabetes-recall-v0.6.1` | `challenger_requires_external_validation` | v0.5 대비 소폭 개선 |
| 오늘이(엣지) | `knhanes-shared7-sk180-research-v1` | `research_candidate_only` | 입력 7개로 축소한 PR #36 연구용 모델 |
| 내일이 | `rf25-tuned-spec40-v1` | **`approved`** (단, `operational_model_activated: false`) | 현재 유일하게 registry상 `approved`로 표기된 후보 |
| 내일이(모레노, 2~18년) | `rf25-first-interval-survival-ensemble-v1` | `constraint_failed` / `research_..._not_operationally_approved` | 18년 구간 specificity 미달로 연구단계에서 이미 탈락 |

출처: `models/registry/diabetes_current_screening/candidates/*.json`,
`models/registry/diabetes_incidence/candidates/*.json`

---

## 1. 오늘이·내일이 최종 confusion matrix

### 내일이 — `rf25-tuned-spec40-v1` (Test, N=7,903)

| | 예측 양성 | 예측 음성 |
| --- | ---: | ---: |
| 실제 양성 (195건) | TP 164 | FN 31 |
| 실제 음성 (7,708건) | FP 4,606 | TN 3,102 |

출처: `models/registry/diabetes_incidence/candidates/rf25-tuned-spec40-v1.json` (`metrics.confusion_matrix`),
`docs/model/MODEL_CARD_RF25_DIABETES_INCIDENCE.md`

### 오늘이 — 후보별 Test confusion matrix (Test 연도 2023–2024, N=9,691, 양성 390건)

| 후보 | TP | FN | TN | FP |
| --- | ---: | ---: | ---: | ---: |
| v0.5 | 363 | 27 | 3,783 | 5,518 |
| v0.6.1 | 366 | 24 | 3,783* | 5,518* |
| shared7-sk180(엣지) | 364 | 26 | 3,901 | 5,400 |

\* v0.6.1 registry manifest는 TP/FN만 명시(`true_positive: 366`, `false_negative: 24`)하고
TN/FP는 직접 기록하지 않는다. 위 표의 TN/FP는 `specificity = TN/(TN+FP) = 0.40662...`와
음성 전체 9,301건으로 역산한 값이며, 반올림 오차가 있을 수 있다 — 멘토님께 원값 그대로
말하되 "TN/FP는 specificity로부터 역산했다"고 밝히는 것이 정직하다.

출처: `docs/model/MODEL_CARD_KNHANES_CURRENT_SCREENING_V0_5.md`,
`models/registry/diabetes_current_screening/candidates/knhanes-current-screening-v061.json`,
`models/registry/diabetes_current_screening/candidates/knhanes-shared7-sk180-v1.json`

---

## 2. Threshold 비교 (PPV/NPV/Positive Rate 포함)

Positive Rate = (TP+FP) / 전체. PPV = TP/(TP+FP). NPV = TN/(TN+FN). 아래는 각 후보의
Test confusion matrix로부터 직접 계산한 값이다.

| 모델 | 후보 | Threshold | Recall | Specificity | PPV | NPV | Positive Rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 내일이 | rf25-tuned-spec40-v1 | 0.021154 | 84.10% | 40.24% | 3.44% | 99.01% | 60.36% |
| 오늘이 | v0.5 | 0.023227 | 93.08% | 40.67% | 6.17% | 99.29% | 60.68% |
| 오늘이 | v0.6.1 | 0.023231 | 93.85% | 40.66% | 6.22% | 99.37% | 60.72% |
| 오늘이(엣지) | shared7-sk180 | 0.026160 | 93.33% | 41.94% | 6.32% | 99.34% | 59.47% |

**해석 포인트 (멘토님이 물어볼 만한 것):**
- 두 모델 모두 Recall(민감도)을 최우선으로 튜닝했기 때문에 PPV(정밀도)가 3~7% 수준으로
  매우 낮다. 즉 "양성"으로 뜬 사람 100명 중 실제 위험군은 3~7명뿐이라는 뜻이다.
- 반대로 NPV는 99% 이상이므로, "낮음/음성"으로 나온 결과는 신뢰도가 높다. 이 모델의
  실질적 가치는 "위험 아님을 걸러내는 것"에 가깝고, "위험 확정"에는 약하다.
- 내일이(RF25)는 오늘이 계열보다 PPV가 특히 낮다(3.44%) — 2년 뒤 발생을 예측하는 문제라
  기저 사건률(2.5%)이 더 낮기 때문. 이건 모델 결함이 아니라 문제 자체의 난이도 차이로
  설명하면 된다.
- 내일이 Threshold는 low/caution/high 3단계(`0.0 / 0.017113 / 0.021154`)이고, 오늘이
  계열은 단일 이진 threshold다. 두 점수는 서로 다른 축이라 합산·평균하지 않는다
  (`docs/model/MODEL_CARD_KNHANES_CURRENT_SCREENING_V0_5.md` 6절).

---

## 3. Model Release Gate — 오늘이·내일이 결과화면

배포 게이트는 두 층으로 나뉜다. 이 구분을 명확히 말하는 게 핵심이다.

**① Registry 게이트 (팀 공식 승인 상태, `models/registry/*/active.json`)**
- 코드 조건(`ActiveModel.threshold_is_approved`): `threshold_version`이 빈 값/`unapproved`가
  아니고, `promotion_status == "approved"`일 때만 공개 화면에 risk_category를 노출한다.
- 실제 리포지토리에는 `active.json`이 없고 `active.example.json` 템플릿만 있다. 내일이
  템플릿은 `model_version: "replace-after-review"`, `artifact_sha256: "replace-after-review"`
  같은 placeholder 그대로다 → **아직 아무도 진짜 active.json을 채워 넣지 않았다는 뜻이므로,
  팀 공식 게이트는 두 모델 다 "닫힘"이다.**
- 오늘이 `active.example.json`은 `operational_model_activated: false`이고
  `activation_requires`에 `team_review`, `external_or_unused_period_validation`,
  `medical_safety_review`, `backend_contract_test` 4가지가 명시되어 있다 — 이 4개 중 아직
  통과한 게 없다는 게 정직한 현황이다.

**② 로컬 데모 게이트 (내 개발 환경 `.env`)**
- 지난주 라이브 디버깅 때 내가 `.env`에서 `PREDICTION_PROVIDER=artifact`,
  `PREDICTION_PROMOTION_STATUS=approved`로 바꿔서 로컬 화면에 위험 카테고리가 뜨게 만든
  것 — 이건 **개인 개발 환경의 데모용 override**이지, 팀 공식 승인(①)을 대체하는 게
  아니다. 멘토님께는 "로컬에서 실제 아티팩트가 연결되어 화면까지 나오는 건 확인했지만,
  이건 팀 공식 릴리즈 게이트를 통과한 게 아니라 개발자 개인 데모 설정"이라고 구분해서
  답하는 게 맞다.

**결과화면 요약 문장 (멘토링용):**
> "오늘이·내일이 둘 다 Registry의 `active.json`이 아직 placeholder이고, 오늘이는
> 4개 활성화 조건 중 통과한 게 없어서 팀 공식 게이트는 닫혀 있습니다. 제 로컬에서는
> `.env` override로 실제 아티팩트 기반 화면을 데모로 띄워봤지만, 이건 개발 데모지
> 운영 승인은 아닙니다."

출처: `app/prediction/providers.py` (`ActiveModel.threshold_is_approved`),
`models/registry/diabetes_current_screening/active.example.json`,
`models/registry/diabetes_incidence/active.example.json`, `app/core/config.py`

---

## 4. 실제 Model Artifact E2E 시연

두 갈래로 준비하면 된다. 둘 다 진짜 `.joblib` 아티팩트를 로드해서 실제로 추론까지
도는 경로다(가짜 stub 아님).

### (A) 공개 예측 파이프라인 — 내일이(RF25) 아티팩트

이미 `.env`에 `PREDICTION_PROVIDER=artifact`, `MODEL_URI`, `MODEL_MANIFEST_URI`가
설정되어 있으므로, 스택을 띄운 상태에서:

```bash
# 1) 회원가입/로그인 후 건강정보 입력 → PredictionJob 생성
curl -X POST http://localhost:8001/api/v1/prediction-jobs \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{ ... 건강체크업 payload ... }'

# 2) Job 상태 폴링 (ai-worker가 Redis Stream에서 소비 → 실제 model.joblib 추론)
curl http://localhost:8001/api/v1/prediction-jobs/<job_id> \
  -H "Authorization: Bearer <access_token>"

# 3) 완료되면 실제 결과 조회
curl http://localhost:8001/api/v1/predictions/latest \
  -H "Authorization: Bearer <access_token>"
```

시연 포인트: 화면에 뜨는 `risk_category`, `model_version: rf25-tuned-spec40-v1`,
`threshold_version`이 실제 `.joblib`이 계산한 값이라는 것을 `docker compose logs ai-worker`
로 같이 보여주면 "진짜 모델이 돌았다"는 증거가 된다.

### (B) 관리자 전용 연구 API — 오늘이 엣지 + 모레노(PR #36)

`ML_RESEARCH_ENDPOINTS_ENABLED=true`, `ML_SHARED7_MODEL_URI`,
`ML_FIRST_INTERVAL_MODEL_URI`를 설정한 뒤 관리자 계정 토큰으로:

```bash
curl -X POST http://localhost:8001/api/v1/research/models/shared7/predict \
  -H "Authorization: Bearer <admin_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "as_of_date": "2026-08-31",
    "input": {
      "birth_date": "1970-02-14", "sex": "female",
      "height_cm": 162.0, "weight_kg": 68.0,
      "smoking_status": "never", "current_drinker": false,
      "regular_exercise": true, "exercise_days_per_week": 3,
      "exercise_minutes": 40, "previously_diagnosed_diabetes": false
    }
  }'
```

동일 요청을 `/research/models/first-interval/predict`로도 호출하면 2~18년 구간별
내부 점수가 나온다. 두 모델 다 SHA-256 체크섬 검증 후에만 역직렬화하므로, 응답이
정상 200이면 "체크섬 검증 + 실제 로드 + 실제 추론"이 모두 성공했다는 뜻이다.

이미 실행된 실증 결과(문서 기준, 재현 가능):
- shared7: `risk_score_internal=0.047658`, `screening_signal_detected=true`, `display_allowed=false`
- 첫 구간: 2년 `0.024914`, 4년 `0.053716`, 6년 `0.078012`, `display_allowed=false`

두 모델 다 `display_allowed=false`인 이유는 관리자 내부 검증용이라 일반 사용자 화면에
노출하지 않기 때문 — 이 자체가 "게이트가 아직 안 열렸다"는 3번 항목과 같은 맥락이다.

출처: `app/apis/v1/research_model_routers.py`, `docs/model/SHARED7_FIRST_INTERVAL_SERVICE_HANDOFF.md`

---

## 5. 배포 실패 Scenario Test 결과

자동 테스트로 이미 확인된 것과, 아직 자동화되지 않아 정직하게 "설계는 되어 있으나
테스트 커버리지 없음"이라고 말해야 하는 것을 구분했다.

### 자동 테스트로 확인됨

| 실패 시나리오 | 처리/에러 코드 | 확인된 테스트 |
| --- | --- | --- |
| 모델 파일 없음/손상 | 503 `ML_MODEL_UNAVAILABLE` | `tests/ml/test_research_models.py::test_missing_and_corrupt_shared_artifact` |
| scikit-learn 런타임 버전 불일치 | 503 `ML_MODEL_CONTRACT_ERROR` | `tests/ml/test_research_models.py::test_runtime_mismatch` |
| 연구 API 기본 비활성화 | 404 | `tests/test_research_model_api.py::test_disabled_endpoint` |
| 비관리자/비인증 접근 | 401/403 | `test_requires_admin`, `test_requires_authentication` |
| 필수 입력 누락/범위 오류 | 422 | `test_invalid_input_rejected_before_model_load`, `test_missing_input_rejected` |
| 미승인 모델의 내부 점수가 공개 확률로 새는지 | 차단 확인 | `tests/test_sprint2_vertical_contract.py::test_unapproved_prediction_never_exposes_internal_score_as_public_probability` |
| 개발 stub이 확률/카테고리를 임의로 만들어내는지 | 차단 확인 | `test_development_provider_does_not_fabricate_probability_or_category` |

### 설계는 되어 있으나 자동 테스트 커버리지가 없음 (정직하게 밝힐 항목)

| 실패 시나리오 | 코드상 처리 위치 | 상태 |
| --- | --- | --- |
| 아티팩트 SHA-256 불일치(digest mismatch) | `ai_worker/worker.py` — `RuntimeError("MODEL_DIGEST_MISMATCH")` → 즉시 terminal failure | 코드 경로는 있으나 전용 자동 테스트를 찾지 못함 |
| Redis 완전 장애(연결 자체 실패) | `app/services/ai_jobs.py` — `error_code="QUEUE_UNAVAILABLE"`, 503 | 전용 자동 테스트 없음 |
| Worker 처리 타임아웃 | `ai_worker/worker.py` — `TimeoutError` → `TIMEOUT`(재시도 가능) | 전용 자동 테스트 없음, 수동 확인만 |
| Worker 크래시 후 `xautoclaim` 재수령 중 중복 발생 가능성 | `reclaim_pending()`, DB `job_id UNIQUE` 제약이 최종 방어선 | 좁은 시간창의 중복 가능성 있음(이전 멘토링 답변에서 이미 인정한 내용과 동일) |

**답변 요령:** 5번은 "테스트 다 통과했습니다"라고 뭉뚱그리지 말고, 표 두 개를 그대로
보여주면서 "입력 검증·인증·아티팩트 손상 계열은 테스트로 커버되어 있고, Redis/타임아웃/
digest mismatch 계열은 코드 방어는 있지만 자동 테스트가 아직 없다"고 말하는 게 훨씬
신뢰를 준다. 다음 주까지 시간이 되면 이 3개(digest mismatch, QUEUE_UNAVAILABLE, TIMEOUT)
중 하나라도 pytest로 추가해서 "이번 주에 이 갭을 메웠다"고 보고하면 좋은 인상을 줄 수 있다.

출처: `ai_worker/worker.py`, `app/services/ai_jobs.py`, 위 표에 명시한 테스트 파일들
