# 공통 7변수 판정·첫 구간 앙상블 서비스 연동

## 제공 범위

`codex/e2e-integration` 기반의 **관리자 전용 내부 검증 API**다. 기존 공개 예측
API, Redis 작업, 활성 모델 Registry, 프론트엔드, DB 스키마는 교체하지 않는다.
API 호출과 실제 모델 실행은 가능하지만 운영 승인이나 일반 사용자 노출을 뜻하지 않는다.
관리자도 동의·권한이 확인된 입력 또는 합성 입력만 사용한다. 요청 건강정보를 저장하지 않는다.

| API (POST) | 모델 | 결과 |
|---|---|---|
| `/api/v1/research/models/shared7/predict` | `knhanes-shared7-sk180-research-v1` | 현재 위험 신호, 현재 선별 임계값 |
| `/api/v1/research/models/first-interval/predict` | `rf25-first-interval-survival-ensemble-v1` | 첫 2년 stacking + 이후 Logistic hazard, 2~18년 내부 누적 신호 |

공통 입력은 `diabetes-incidence-api-25features-v1` 원래 요청 형식이다. RF25 특성으로
변환한 DataFrame에는 키·체중이 없으므로 그 DataFrame을 공통 입력으로 사용하지 않는다.
서비스는 만 45~105세 미진단자만 지원한다. KNHANES 학습 대상은 19세 이상이나 이
공통 서비스에서는 별도 검증 없이 연령 범위를 넓히지 않는다. 모든 연령별 성능을
입증했다는 뜻은 아니다. 앙상블의 projected_age는 미래 표시값이며 입력 지원 연령과 다르다.

## 서버 준비

- 두 Artifact 모두 **scikit-learn 1.8.0**. 런타임 버전 불일치를 거부한다.
- 로컬: `uv sync --group app --group modeling --group dev --frozen`.
- Docker: `docker build -f app/Dockerfile --build-arg ML_RESEARCH_RUNTIME=true -t ah05-research .`.
  Docker 빌드는 이 PR 작업에서 실행하지 않았다. 저장소 lock에 고정된 modeling 환경을 사용한다.
- 모델 바이너리는 Git이나 이미지에 넣지 않고 신뢰된 내부 전달 채널로 아래 경로에
  공급하거나 읽기 전용 볼륨으로 연결한다. 원본 의료 데이터는 추론 서버에 필요하지 않다.
- `ML_RESEARCH_ENDPOINTS_ENABLED=true`를 명시적으로 설정해야 한다. 기본값 false.
- `ML_SHARED7_MODEL_URI`, `ML_FIRST_INTERVAL_MODEL_URI`로 서버 내 파일 경로를
  지정할 수 있다. 클라이언트가 파일 경로나 Manifest를 지정할 수는 없다.
- 관리자 계정의 기존 Bearer access token을 사용한다. 비관리자·비활성 계정은 403.
- 캐시된 로딩 결과를 사용하므로 모델 파일/설정을 변경하거나 롤백하면 프로세스를 재시작한다.

| 모델 | 기본 파일 경로 | SHA-256 |
|---|---|---|
| shared7 | `models/artifacts/candidates/diabetes_current_screening/knhanes-shared7-sk180-v1/model.joblib` | `6946553dd321189caa6fda207edd3f7a190b8fe1ed007b9a152958ea1cf2e86f` |
| 첫 구간 | `models/artifacts/candidates/diabetes_incidence/rf25-first-interval-survival-ensemble-v1/model.joblib` | `36323bad1ba2c115f8c52c4c6460220b960a5bae43787be5b029e2d90d3d488f` |

SHA 검증 후에만 joblib 역직렬화한다. 다른 경로를 설정해도 이 체크섬 계약은 유지된다.
새 체크섬/임계값을 임의로 갱신하지 않는다. raw score를 클라이언트에서 threshold와
다시 비교하지 말고 서버 판정값을 사용한다(응답 점수는 표시 재현성을 위해 반올림됨).

## 공통 요청 예시

```json
{
  "as_of_date": "2026-08-31",
  "input": {
    "birth_date": "1970-02-14",
    "sex": "female",
    "height_cm": 162.0,
    "weight_kg": 68.0,
    "smoking_status": "never",
    "current_drinker": false,
    "regular_exercise": true,
    "exercise_days_per_week": 3,
    "exercise_minutes": 40,
    "previously_diagnosed_diabetes": false
  }
}
```

`as_of_date`는 건강정보 측정 기준일이며 같은 기준일·입력이면 같은 결과를 반환한다.
필수 필드 누락/null은 거부한다. 전체 선택 필드는 기존 RF25 입력 규격을 따른다.
키 120~220cm, 체중 25~250kg, 파생 BMI 10~70, 운동일 0~7, 회당 운동 0~720분.
교육은 `code_1~code_4` 또는 null만 허용하며 `code_97`은 거부한다.

shared7 변환: 생년월일→만 나이; BMI=kg/(cm/100)^2; male=1/female=2;
current=1/former·never=0; 교육 code_1~4→1~4. 추가 의료·생활 변수를 쓰지 않는다.
교육 미입력은 학습 최빈값 4로 대치(실제 학력으로 해석 금지). 숫자 대치·범주 처리기는
Artifact에 포함된 Train-only 전처리기를 그대로 사용한다. 첫 구간 모델도 Train 통계만 사용한다.

## 실제 합성 입력 응답 요약

위 요청을 실제 Artifact로 실행한 내부 신호이며 진단·검증된 발병확률이 아니다.

- shared7: `risk_score_internal=0.047658176973160`, `screening_signal_detected=true`,
  `screening_decision_threshold=0.02615995276723876`,
  `threshold_version=shared7-sk180-validation-spec042-v1`, `display_allowed=false`.
- 첫 구간: 2년 `0.024914381803585`, 4년 `0.053716045185859`, 6년 `0.078011944743102`.
  `threshold_version=validation-spec043-by-horizon-first-interval-stack-v1`.
  2~18년 전체 응답은 `docs/api/examples/first_interval_survival_ensemble_response.actual.json`.
  `risk_curve_status=unavailable`, `display_allowed=false`, 확률·신뢰구간 필드는 null.

프론트엔드는 연구 결과를 일반 사용자 화면·퍼센트 발병확률·생활습관 개선 효과로 표시하지
않는다. 현재 선별과 미래 발생의 임계값은 별개이며 점수를 합산하지 않는다.

## 오류 계약

| 조건 | HTTP | 코드 |
|---|---:|---|
| 비활성화 | 404 | Research endpoints disabled |
| 인증 없음 / 비관리자 | 401 또는 403 / 403 | 기존 인증 계약 |
| 필수값 누락 | 422 | ML_INPUT_MISSING |
| 연령 범위 밖 | 422 | ML_POPULATION_UNSUPPORTED |
| 기존 당뇨 진단 | 422 | ML_POPULATION_INELIGIBLE |
| 범위·자료형·교육 코드 오류 | 422 | ML_INPUT_OUT_OF_RANGE |
| 모델 미탑재 | 503 | ML_MODEL_UNAVAILABLE |
| SHA·모델 계약·런타임 불일치 | 503 | ML_MODEL_CONTRACT_ERROR |

Pydantic 요청 형태 오류는 기본 422 validation 응답이다. 요청/응답 본문을 수집하는
미들웨어·프록시 로깅은 비활성화해야 한다. 성공 응답은 Cache-Control: no-store.

## 성능·한계와 롤백

- shared7: Validation R/S 0.93735/0.42538; Test R/S 0.93333/0.41942;
  Precision 0.06315, AUROC 0.76023, AUPRC 0.10614. 상세: KNHANES_SHARED7_SK180_REPRODUCTION.md.
- 첫 구간: 2/4/6년 Test R/S 0.7778/0.4793, 0.8163/0.4421, 0.8235/0.4203.
  14/16/18년 Specificity<0.40로 전체 기간 constraint_failed이며 장기 운영 후보가 아니다.
- KNHANES 연도 분할과 KLoSA PID 분할·최초 적격 코호트는 다르다. 직접 성능 순위를 매기지 않는다.
- 동일 historical Test 반복 조회, 자기보고·탈락 편향, 연령별 검증·확률 보정 불확실성 한계.
- 오류/성능 회귀/승인 철회 시 `ML_RESEARCH_ENDPOINTS_ENABLED=false` 후 재시작.
  기존 공개 서비스와 활성 모델은 그대로 유지된다. 자동 fallback 점수는 생성하지 않는다.

## 검증과 재현

기본 테스트는 합성 모델로 인증·입력·오류·단조성·반복 추론을 확인한다. 실제 Artifact
테스트는 파일 공급 후 환경변수를 지정하며 CI에는 바이너리가 없다.

신규 관련 테스트 58개(실제 모델 테스트 포함)가 통과했고, 실제 두 Artifact를 연결한
FastAPI TestClient 경로에서 HTTP 200 및 동일 요청 반복 응답 일치를 확인했다.
TestClient의 인증은 관리자 테스트 계정으로 대체했다. 실서버 JWT/DB·Docker 배포까지
검증한 결과는 아니며 배포 환경에서 추가 점검해야 한다.

```bash
TEST_SHARED7_ARTIFACT=/trusted/shared7/model.joblib \
TEST_FIRST_INTERVAL_ARTIFACT=/trusted/first-interval/model.joblib \
uv run pytest --noconftest -q tests/ml/test_research_models.py \
  tests/ml/test_diabetes_first_interval_survival_ensemble_inference.py tests/test_research_model_api.py
```

shared7 재학습: `python -m src.ml.evaluation.reproduce_knhanes_shared7_sk180 --handoff-dir /trusted/today_v061_team --output-dir outputs/ml/shared7/new_run`.
첫 구간 재학습: `./scripts/ml-experiment.sh run rf25_first_interval_survival_ensemble_v001`.
과거 실험 의존 코드도 포함하지만 원자료·전처리 데이터와 팀 전달 패키지는 별도 공급한다.
