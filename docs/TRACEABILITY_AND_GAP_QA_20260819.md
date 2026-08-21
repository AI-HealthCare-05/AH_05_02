# Sprint 2 요구사항 추적성·누락 QA

| 항목 | 내용 |
|---|---|
| 점검일 | 2026-08-19 |
| 담당 | 정세준(PM·기획·QA) |
| 기준 문서 | 요구사항 v2.0, API 명세 v2.0, 서비스 대상·안전 문구 v1.0, Sprint 2 백로그 |
| 점검 범위 | 화면·API·DB·AI·테스트·의료 안전 문구 |
| 판정 의미 | `완료`: 계약과 검증 근거 있음, `구현중`: 계약은 확정됐으나 기능 구현 미완료, `후속`: Sprint 2 범위 밖 |

## 1. 확정 결정

1. 예측 작업 경로는 코드·프론트·테스트가 사용하는 `/api/v1/prediction-jobs`로 통일한다.
2. 작업 상태는 `queued/running/succeeded/failed`, 생성 시각은 `created_at`으로 통일한다.
3. `202` 접수 뒤의 시간초과는 상태 조회에서 HTTP `200`, `status=failed`, `error_code=TIMEOUT`으로 제공한다.
4. 위험 범주의 숫자 임계값은 검증·보정과 문구 검토를 통과한 `threshold_version`만 사용한다.
5. 동의 철회 즉시 신규 개인화 처리를 중단하며, 탈퇴한 사용자의 법적 보존 의무가 없는 식별 가능 건강정보는 30일 이내 삭제 또는 복구 불가능하게 익명화한다.

## 2. 핵심 요구사항 추적표

| 요구사항 | 화면 | API | DB·AI | 테스트·검수 | 상태 |
|---|---|---|---|---|---|
| REQ-USER-001 | 회원가입 | `POST /auth/signup` | `User` | 중복 이메일·해시 저장 | 구현중 |
| REQ-USER-002 | 로그인 | `/auth/login`, `/auth/refresh`, `/auth/logout` | `User`, 토큰 저장소 | 성공·실패·만료 | 구현중 |
| REQ-USER-003 | 건강정보 동의 | `/consents` | `Consent` | 미동의·철회 후 예측 차단 | 완료 |
| REQ-USER-004 | 적합성 확인 | `/eligibility-checks` | `EligibilityCheck`, 활성 모델 카드 | 미성년·기진단·경고·모델 범위 밖 | 완료 |
| REQ-HEALTH-001 | 프로필 | `/users/me/profile` | `UserProfile` | 생년월일 기반 만 나이 | 구현중 |
| REQ-HEALTH-002 | 건강정보 입력 | `POST /health-checkups` | `HealthCheckup`, 입력 계약 | 단위·필수값·누수 제외 | 완료 |
| REQ-HEALTH-003 | 검진 이력 | `/health-checkups` | `HealthCheckup` | 덮어쓰기 금지·신규 이력 | 완료 |
| REQ-HEALTH-004 | 입력 오류 | 입력 화면·필드 오류 | `422` 공통 오류 | 입력 스키마 | 누락·범위·형식 오류 | 완료 |
| REQ-PRED-001 | 예측 대기 | `/prediction-jobs` | `PredictionJob`, Redis Stream | `202`, 정책 차단, 중복 방지 | 개발 provider 완료 |
| REQ-PRED-002 | 위험 결과 | `/predictions/{id}` | `Prediction`, 모델·임계값 버전 | 승인 전 확률 비공개 | 어댑터 완료·모델 승인 대기 |
| REQ-PRED-003 | 예측 이력 | `/predictions` | `HealthCheckup 1:N Prediction` | 모델 버전별 재예측 | 완료 |
| REQ-PRED-004 | 최신 결과 | `/predictions/latest` | `Prediction` | `predicted_at`, `id` 정렬 | 완료 |
| REQ-PRED-005 | 위험·보호 요인 | `/predictions/{id}/risk-factors` | `RiskFactor` | 방향·중요도·수정 가능성 | 안전한 미제공 완료·설명 모델 후속 |
| REQ-PRED-006 | 의료기관 안내 | `/follow-up-actions` | `FollowUpAction` | 고위험 시 챌린지보다 우선 | 경고·기진단 완료, 승인 고위험 모델 E2E 후속 |
| REQ-CHAL-001 | 챌린지 후보 | `/challenge-recommendations` | 추천 규칙·문구 버전 | 치료·복약 표현 차단 | 완료 |
| REQ-CHAL-002~004 | 선택·사이클·기록 | `/challenge-cycles`, `/user-challenges/*/logs` | 챌린지 엔터티 | 최대 3개·일별 중복·미래일 | 완료 |
| REQ-CHAL-005 | 기진단 전환 | `/challenge-cycles/{id}/status` | `ChallengeCycle` | 신규 개인화 중단·과거 이력 보존 | 완료 |
| REQ-DASH-001~003 | 대시보드 | `/dashboard/*` | 예측·검진·챌린지 집계 | 원시 확률·개선율 비노출 | 기본 요약 완료·추이 화면 후속 |
| NFR-SAFE-001~003 | 소개·결과·고위험 안내 | 공통 문구·오류 | 문구·근거 버전 | 진단·처방·약물 변경 표현 0건 | 완료 |
| NFR-SEC-003 | 철회·탈퇴 | 동의 철회·회원 탈퇴 | 삭제 대기·감사로그 | 처리 차단·30일 정책 검증 | 구현중 |
| NFR-ML-001~003 | 모델 평가·이력 | 모델 메타데이터 | 파이프라인·모델 카드 | 분할 후 전처리·연령 평가·버전 | 구현중 |

## 3. 누락·충돌 점검 결과

| 점검 항목 | 이전 상태 | 조치 | 결과 |
|---|---|---|---|
| 예측 작업 API 경로 | `/ai-jobs`와 `/prediction-jobs` 논의 | 구현 기준 `/prediction-jobs` 확정 | 해결 |
| 비동기 시간초과 | 접수 후 `504`로 오해 가능 | 상태 조회의 `failed + TIMEOUT` 명시 | 해결 |
| 작업 상태·생성 시각 | 문서별 이름 차이 가능 | 상태 4종과 `created_at` 확정 | 해결 |
| 위험 범주 임계값 | 숫자 미확정 | 모델 카드 승인 절차와 비노출 게이트 확정 | 정책 해결·숫자는 모델 검증 후 입력 |
| 건강정보 철회·탈퇴 | 처리 방식 TBD | 즉시 처리 중단·30일 삭제/익명화 정책 확정 | 해결 |
| 19~44세 결과 의미 | KLoSA 미래 예측으로 오인 가능 | KLoSA 적용 차단, KNHANES는 현재 위험 신호만 | 해결 |
| 기진단 사용자 | 위험 100% 또는 예측 진입 우려 | 예측·개인화 추천 차단, 의료진 안내 | 해결 |
| 원시 확률·변화율 | 발병확률·개선율로 오인 가능 | 내부 감사용, 사용자 비노출 | 해결 |

## 4. 의료 안전 문구 QA

- 사용자 화면·API 예시는 `진단이나 처방이 아님`을 명시한다.
- 기진단자에게 미래 발병 예측을 제공하지 않는다.
- 고위험·경고 증상에서는 챌린지보다 검사·의료기관 안내가 먼저다.
- 약물 시작·중단·용량 변경을 권고하지 않는다.
- `SERVICE_SCOPE_AND_SAFETY_COPY.md`의 금지 표현 표에 실린 문장은 교육용 반례이므로 실제 사용자 문구 검사에서는 제외한다.
- 자동 계약 테스트는 API 경로, 비동기 시간초과, 개인정보 처리 기준이 문서와 코드에서 이탈하지 않는지 확인한다.

## 5. 남은 구현 작업

이 문서의 QA 과업은 완료됐지만 `구현중` 항목은 각 담당자의 기능 PR에서 완료해야 한다. 특히 모델 입력 계약·실제 임계값, 적합성 API/DB, 프론트 화면 연결, 전체 세로 흐름 통합 테스트는 Sprint 2 완료 조건으로 유지한다.
