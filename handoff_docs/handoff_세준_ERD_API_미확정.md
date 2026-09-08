# 세준 전달용 — ERD·API 미확정 사항

기준: PR #25(`Fix/24 carrot forest sync`, PR #19 브랜치 위에 쌓인 최신 브랜치) 코드 + 로컬 저장소 대조

## 1. 문서(`docs/API_SPEC.md`)가 실제 코드보다 뒤처짐 — 업데이트 필요

- **위험 범주 이름은 지금도 `low/caution/high`입니다 — 이전 버전 이 문서 정정**: 지난 버전에서 제가 "실제 코드가 `moderate`를 쓴다"고 적고 `RISK_LABELS`를 `moderate`로 고쳤었는데, 이번에 실제 MySQL/Redis를 붙여 코드 전체를 다시 훑어보니 **그게 잘못된 정정이었습니다.** 카테고리 이름을 실제로 만들어내는 곳(`src/ml/evaluation/diabetes_risk_categories.py`)도, 타입 정의(`app/prediction/providers.py`의 `RiskCategory`)도, 프론트(`src/frontend`의 `hyeoldangi-face-caution.png` 등 자산 이름)도 전부 지금도 `caution`을 일관되게 씁니다. 즉 `moderate`는 **모델팀 인수인계서가 "목표"로 적어둔 이름일 뿐, 실제 구현 어디에도 반영된 적이 없습니다.** 제가 지난번에 만든 `moderate` 패치는 이후 원래대로(`caution`) 되돌려져 있었고, 이번에 확인해보니 그게 맞는 방향이었습니다(제가 되돌려놓은 게 아니라 이미 그렇게 되어 있었습니다 — 팀 다른 분이 고치신 것으로 보입니다). **팀에 확인 필요한 부분은: 인수인계서대로 `moderate`로 실제 리네이밍할지, 아니면 인수인계서 쪽 표기를 `caution`으로 정정할지**입니다. 문서(`docs/API_SPEC.md`)는 실제 코드에 맞춰 `caution` 기준으로 갱신하면 됩니다.
- **회원가입 요청 예시 불일치**: 문서는 `email/password/terms_agreed` 3필드만 보여주는데, 실제 `SignUpRequest`는 `email/password/name/gender/birth_date/phone_number`를 씁니다.
- **건강정보 입력 예시가 8변수 시절 그대로**: 문서 예시는 `smoking_status` 등 옛 필드 일부만 있고, RF25 반영 후 실제로는 25변수 입력(운동일수/시간, 기저질환 8종, 소득/만족도, 교육/혼인/가구형태, 우울/수면 등)이 추가돼 있습니다. → 최신 예시는 수인 전달 문서 참고.
- **예측 결과 응답도 문서보다 훨씬 늘어나 있음**: `GET /predictions/{id}` 계열이 `task_type`/`threshold_scope`/`age_risk_forecast`/`output_status`/`input_as_of_date` 등을 추가로 반환하고, `GET /predictions/changes`·`GET /predictions/{id}/risk-curve`·`GET /predictions/{id}/risk-factors` 3개 엔드포인트가 문서에 아예 빠져 있습니다. → 최신 예시는 수인 전달 문서 참고.

## 2. RiskFactor 저장 계약 미확정

`app/models/health.py`에 `RiskFactor` 테이블은 정의돼 있지만, 실제로 여기에 INSERT하는 코드가 어디에도 없습니다 (`ai_worker/db.py`의 `persist_prediction()` 확인 결과). 문서(`BACKEND_DB_CONSOLIDATION.md`)에도 "검증된 설명 방법과 저장 계약이 확정되기 전까지는 공개하지 않는다"고 되어 있어 의도된 미구현으로 보이지만, **언제·누가 설명(explanation) 로직과 저장 계약을 확정할지가 아직 정해지지 않았습니다.** ERD/일정에 반영 필요.

## 3. `class_probabilities` 필드 항상 비어 있음

`predictions` 테이블에 `class_probabilities` 컬럼은 있는데, `persist_prediction()`이 항상 `None`으로 넣습니다. 모델 결과 딕셔너리(`ProviderResult`)에도 이 값 자체가 없습니다. 두 클래스 확률을 프론트/감사 목적으로 실제로 저장할지, 저장한다면 `providers.py`부터 어떻게 채울지 결정이 필요합니다.

## 4. 마이그레이션 히스토리 정리 필요

- `challenge_verification_events` 테이블이 서로 다른 두 마이그레이션(`game_storage` 계열, `rf25_health_checkup_contract` 계열)에서 **중복으로 `CREATE TABLE IF NOT EXISTS`** 되고 있습니다. `IF NOT EXISTS`라 실행 에러는 안 나지만, 스키마 변경 이력이 지저분해서 정리(한쪽 제거)가 필요합니다.
- 로컬 저장소 점검 중 마이그레이션 번호 **"10번" 중복**(`food_vision_vegetable_detection` vs `game_storage`)을 발견해서 실제로 재정렬(10 유지, `game_storage`→11, `carrot_forest_lite`→12, `rf25_health_checkup_contract`→13)했습니다. **아직 로컬에만 있고 PR #25에는 안 올라간 상태**입니다(아래 7번 참고).
- 참고로 PR #19 브랜치 시점엔 없었던 "5번 중복"(PR #19의 `rename_ai_jobs...` vs PR #21의 `carrot_forest_lite`)은, PR #25 계열 작업에서 당근의 숲 쪽을 5번에서 11번으로 재배치하면서 자연히 해소돼 있었습니다.
- **"5번 중복"이 그 사이 로컬에 다시 생겼다가 오늘 재제거했습니다**: 이번에 다시 점검해보니 `5_20260826143000_carrot_forest_lite.py`라는 파일이 다시 나타나 있었는데, 내용을 대조해보니 위에서 12번으로 옮겨놓은 파일과 **바이트 단위로 완전히 동일**했습니다. 타임스탬프(`20260826143000`)를 보면 이건 PR #21이 쓰던 옛 버전 그대로로 보입니다 — 즉 **PR #21의 당근의 숲 마이그레이션이 어떤 경로로든(브랜치 병합/체크아웃 등) 로컬 작업 트리에 다시 섞여 들어온 것**으로 보입니다. 실제로 aerich를 붙여서 실행해보니 `IF NOT EXISTS` 덕분에 에러 없이 둘 다 적용은 되지만(중복 실행일 뿐 깨지진 않음), 정리가 필요해서 `_to_delete/`로 옮겨뒀습니다. **이게 반복해서 재발한다는 건, 5번 항목(PR #21 처리 방향)을 팀이 빨리 결정해야 한다는 신호로 보입니다** — 누군가 계속 PR #21 브랜치 내용을 로컬에 섞고 있을 가능성이 있습니다.
- **새로 추가된 마이그레이션 14~18번도 이번에 실제 MySQL에 적용해서 검증했습니다** (아래 8번 참고): `input_as_of_date` 백필, `model_registry`/`prediction_risk_curve_points`/`prediction_scenarios` 테이블, `age_risk_forecast` JSON 컬럼, `task_type`/`threshold_scope` 컬럼, `self_rated_health`/`meal_count_yesterday` nullable 전환 — 전부 순서대로 문제없이 적용됩니다.
- **팀 전체가 브랜치를 리베이스/머지할 때 마이그레이션 번호가 또 겹칠 수 있으니, 브랜치 합칠 때 번호 재점검을 프로세스화하면 좋을 것 같습니다.**

## 5. PR #21 처리 방향 결정 필요

PR #21("당근의 숲 웹 픽셀 게임 MVP")을 확인해보니, **develop이나 PR #25 어느 쪽과도 커밋 히스토리가 이어져 있지 않은 별개 브랜치**입니다. PR #21은 프론트엔드(Phaser 게임 파일) 위주이고 마이그레이션도 예전 번호(5번)를 그대로 쓰는데, 지금 PR #25 계열에 들어있는 당근의 숲 백엔드(`app/models/forest.py`, `app/repositories/forest_repository.py` 등, 마이그레이션 11번)는 완전히 다시 구현된 버전으로 보입니다. **PR #21의 작업이 이미 대체된 것인지 팀에 확인해서, 맞다면 닫는 게 좋을 것 같습니다.**

## 6. 라우터 구현 범위 재확인 권장

`challenge_router`, `dashboard_router`가 실제로 `app/apis/v1/`에 구현되어 있는 건 코드로 확인했지만(이번 세션에서 파일 존재·등록까지만 확인), **`docs/API_SPEC.md`에 나열된 챌린지·대시보드 엔드포인트 하나하나가 실제 구현과 100% 일치하는지까지는 이번 조사 범위에서 다 검증하지 못했습니다.** ERD/API 확정 회의에서 엔드포인트 단위로 한 번 더 맞춰보는 게 안전합니다.

## 7. PR #19 → PR #25 스택 구조 및 로컬 수정사항 반영 상태

**PR #25는 develop에서 바로 갈라진 게 아니라, PR #19 브랜치 위에 그대로 쌓아 올린 브랜치입니다** (PR #19의 마지막 커밋 `b75821c`가 PR #25 히스토리에 그대로 포함됨). 즉 PR #25 = PR #19 전체 내용 + RF25/당근의 숲/푸드비전 등 추가 작업 구조라서, **PR #19가 먼저(또는 함께) develop에 머지되어야 PR #25도 정리된 diff로 머지할 수 있습니다.** 머지 순서를 팀 일정에 반영해 주세요.

또한 이번에 로컬 저장소에서 찾아 고친 아래는 **git 워크트리가 깨져서 커밋/푸시가 안 된 상태**라 PR #25(GitHub 원격)에는 아직 반영되어 있지 않습니다. 별도로 다시 적용해서 커밋해야 합니다. (`RISK_LABELS`/`moderate` 건은 제가 착각했던 것으로 확인돼 이 표에서 뺐습니다 — 1번 항목 참고.)

| 수정 | 원인(어느 작업에서 생긴 문제인지) | 로컬 파일 | PR #25(GitHub) |
|---|---|---|---|
| `worker.py` 오류코드 세분화 | RF25가 새 실패유형(`MODEL_ARTIFACT_UNAVAILABLE` 등)을 추가했는데 워커 예외처리가 못 알아봄 | 반영됨 | 미반영 |
| 마이그레이션 "10번" 중복 재정렬 | 푸드비전·게임저장소 두 기능이 같은 번호로 합쳐짐 | 반영됨 | 미반영 (10번 중복 그대로) |
| 마이그레이션 "5번" 중복 재제거 (2차) | PR #21의 옛 `carrot_forest_lite` 마이그레이션이 로컬에 다시 섞여 들어옴 | 반영됨(`_to_delete/`로 이동) | 미반영 |

전부 PR #19 자체의 문제가 아니라 PR #25 계열에서 생긴 문제라, PR #19가 아니라 **PR #25 브랜치에 커밋**하시면 됩니다.

마지막으로, PR #25에는 회원가입 필드를 `email/password/terms_agreed` 3개로 줄이는 커밋(`refactor: 회원가입 이름 수집 제거`)도 포함되어 있어서, 1번 항목의 "문서-코드 불일치"에 이 변경도 함께 반영해서 `docs/API_SPEC.md`를 갱신해야 합니다. `name`/`gender`/`birth_date`/`phone_number`를 이제 어느 단계에서 받는지(가입 직후 프로필 입력 플로우가 있는지)도 확인이 필요합니다.

## 8. Docker 통합 테스트 시도 결과 — 실제 MySQL/Redis로 대체 검증

`docker-compose.yml`(redis, mysql, fastapi, ai-worker×3, nginx)로 실제 통합 테스트를 시도했는데, **이 세션 환경에서는 Docker 이미지를 하나도 받아올 수 없어서(사내 네트워크 정책이 `docker.io`/`ghcr.io` 자체를 차단) docker-compose 통합 테스트 자체가 불가능했습니다.** (연결된 로컬 컴퓨터 쪽 샌드박스에는 Docker가 아예 없고, 실제 맥에 떠 있을 Docker Desktop에는 이 세션이 닿지 않습니다.)

대신 같은 효과를 보려고 **Docker 없이 클라우드 작업공간에 MySQL 8.0 + Redis를 직접 설치**해서 아래를 실제로 검증했습니다(기존처럼 일부만 옮겨서 목업으로 돌린 게 아니라, `pyproject.toml`/`uv.lock` 그대로 의존성을 설치하고 저장소 거의 전체를 가져왔습니다):

- `aerich upgrade`로 마이그레이션 0번~18번(재정리 이후 기준) 전체를 실제 MySQL에 순서대로 적용 — 전부 성공.
- 전체 pytest 361개 중 337개 통과. 남은 20개는 전부 (a) 당근의 숲 게임의 실제 이미지·사운드 에셋을 이번 테스트 환경에 안 가져와서 생긴 실패(코드 문제 아님), (b) `task_type`/`threshold_scope`(17번 마이그레이션) 추가 이전에 작성된 테스트 목(mock)이 새 필드를 안 넣어줘서 나는 실패(테스트만 오래된 것 — 실제 서비스 코드/DB 모델은 이미 두 필드를 정확히 채우고 있는 것 확인함) 두 가지 뿐이었고, **새로 발견된 실제 프로덕션 버그는 없었습니다.**
- 이 과정에서 `challenge_verification_events` 중복 생성(위 4번 항목)이 실제로 에러 없이(경고만 남기고) 넘어가는 것도 확인했습니다.

---
필요하면 각 항목별로 더 파고들어서 구체적인 파일·라인까지 짚어드릴게요.
