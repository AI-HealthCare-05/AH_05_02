# 9월 8일 통합·배포 준비 QA

## 1. 오늘 결론

- 통합 브랜치는 PR #33, #36, #23을 반영한 `60b1ea4`까지 최신화했다.
- PR #28의 기준 브랜치를 과거 기능 브랜치에서 `develop`로 변경했다.
- PR #28은 충돌이 없고 CI가 통과했으나, 기준 변경으로 기존 승인이 초기화되어 재승인 1건이 필요하다.
- 오늘이·내일이 분석 실패는 모델 성능 문제가 아니라 비동기 실행시간과 Worker 상태를 먼저 확인해야 하는 운영 이슈다.
- 배포 전 E2E와 배포 직후 Smoke Test를 필수 Release Gate로 지정한다.

## 2. 통합 현황

| 항목 | 상태 | 확인 내용 |
| --- | --- | --- |
| PR #33 | 완료 | 회원가입 `terms_agreed`와 Worker 의존성 복구 |
| PR #36 | 완료 | 오늘이·내일이 연구 모델 런타임 연결 |
| PR #23 | 완료 | 가입·설문·결과·챌린지 프론트 흐름 반영 |
| 통합 브랜치 | 완료 | `codex/e2e-integration` → `60b1ea4` |
| PR #28 | 승인 대기 | base=`develop`, 충돌 없음, CI 통과, 재승인 1건 필요 |
| PR #35 | 분리 유지 | 당근의 숲 확장팩 Draft, 의료 핵심 MVP와 별도 관리 |

## 3. FE–BE–모델 계약 확인

| 구간 | 확정 계약 | 검수 기준 |
| --- | --- | --- |
| 회원가입 | `email`, `password`, `terms_agreed` | `POST /api/v1/auth/signup`에서 422가 발생하지 않는다. |
| 기본정보 | 성별·생년월일 별도 저장 | 가입 후 `PATCH /api/v1/users/me/profile`을 사용한다. |
| 예측 생성 | `checkup_id`, `model_key` | HTTP 202와 `job_id`를 받는다. |
| 작업 상태 | `queued/running/succeeded/failed` | 프론트와 API 상태명이 일치한다. |
| 결과 노출 | 승인 여부 확인 | `display_allowed=false`인 수치·위험 범주는 공개하지 않는다. |
| 오류 처리 | 실패 원인 보존 | `error_code`, `retryable`, `retry_after_seconds`를 화면에서 구분한다. |

## 4. 분석 시간초과 점검 결과

현재 코드의 시간 제한은 다음과 같다.

- API가 작업을 생성한 시점부터 `PREDICTION_TIMEOUT_SECONDS=30`을 적용한다.
- AI Worker의 개별 추론도 30초로 제한한다.
- 프론트는 모델별 상태를 최대 35초 동안 확인한다.
- 오늘이와 내일이는 순차 요청하므로 사용자 총 대기시간은 최대 약 70초가 될 수 있다.
- 모델 최초 요청에는 파일 검증, 역직렬화, 라이브러리 초기화가 포함될 수 있다.

### 상태별 원인 판정

| 마지막 상태 | 우선 확인할 원인 |
| --- | --- |
| `queued` 유지 | AI Worker 미기동, Redis 연결 또는 Consumer Group 문제 |
| `running` 후 약 30초에 `TIMEOUT` | 모델 콜드스타트 또는 추론이 Worker 제한 초과 |
| `ML_MODEL_UNAVAILABLE` | Artifact 경로·볼륨 마운트 누락 |
| `ML_MODEL_CONTRACT_ERROR` | SHA-256, 스키마 또는 라이브러리 버전 불일치 |
| 프론트만 시간초과 | 서버 작업은 계속되지만 프론트 35초 Polling이 먼저 종료 |

### 조치안

1. `queued_at`, `started_at`, `completed_at`, `worker_name`, `attempts`, `error_code`를 같은 작업 ID로 수집한다.
2. 모델 로딩시간과 순수 추론시간을 분리해 기록한다.
3. 시연 환경에서는 검증 후 API·Worker 제한을 90~120초로 조정하고 프론트 대기시간을 그보다 길게 맞춘다.
4. Worker 시작 시 모델을 사전 로딩하고 준비 완료 후 Health Check를 통과시킨다.
5. 오늘이·내일이 병렬 요청은 서버 자원과 부분 성공 UX를 검증한 뒤 적용한다.
6. 큐 대기 제한과 실제 추론 제한을 장기적으로 분리한다.

단순히 제한시간만 늘리고 원인을 숨기지 않는다. Worker 미기동이나 모델 계약 오류는 해당 오류 코드로 바로 종료해야 한다.

## 5. 오늘의 Release Gate

- [x] 통합 브랜치의 PR #33·#36·#23 반영 확인
- [x] PR #28을 `develop` 기준으로 변경
- [x] PR #28 충돌 없음 및 CI 통과 확인
- [ ] 팀원 1명 재승인 후 PR #28 병합
- [ ] 실제 Docker 환경에서 FastAPI·MySQL·Redis·AI Worker 기동
- [ ] 실제 Artifact 기반 오늘이·내일이 작업 완료시간 측정
- [ ] 정상·결측·기진단·Worker 중단·시간초과 E2E 증적 저장
- [ ] 배포 직후 Smoke Test 통과
- [ ] `develop → main` Release PR 검토

## 6. 담당자 확인 요청

| 담당 | 확인할 내용 |
| --- | --- |
| 박빛샘 | Docker·Redis·Worker 로그와 PredictionJob 상태 전환, 시간 측정 |
| 양준혁 | Artifact 로딩·추론시간, 모델 파일·Manifest·의존성 재현 |
| 이수인 | 35초 Polling·부분 성공·재시도 화면, 가입 계약 회귀 확인 |
| 정세준 | PR #28 통합, E2E·Smoke Release Gate, 의료 안전 문구 최종 QA |

