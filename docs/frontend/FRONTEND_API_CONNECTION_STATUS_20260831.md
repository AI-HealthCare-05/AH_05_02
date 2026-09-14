# 프론트엔드 API 연결 상태 — 2026-08-31

## 기준

- 통합 대상: `develop`
- 프론트엔드: [PR #23](https://github.com/AI-HealthCare-05/AH_05_02/pull/23) (`codex/fe-ui-layout-polish`, Draft)
- 백엔드 계약: [PR #19](https://github.com/AI-HealthCare-05/AH_05_02/pull/19)
- 당근의 숲: [PR #21](https://github.com/AI-HealthCare-05/AH_05_02/pull/21), 핵심 MVP와 분리

API 경로는 사용자 화면에 노출하지 않고 개발·QA용 문서에서 관리한다.

## 핵심 화면별 연결 상태

| 화면 | API | 상태 | 확인 사항 |
|---|---|---|---|
| 가입 | `POST /api/v1/auth/signup` | 반영 | `email`, `password`, `gender`, `birth_date` 전송, 이름은 수집하지 않음 |
| 로그인 | `POST /api/v1/auth/login` | 반영 | 실패 시 데모로 자동 전환하지 않음 |
| 건강정보 동의 | `POST /api/v1/consents` | 반영 | 로그인 후 `health_data` 동의 저장 |
| 기본 프로필 | `GET/PATCH /api/v1/users/me` | 반영 | 성별·생년월일 조회 및 수정 |
| 이용 가능 확인 | `POST /api/v1/eligibility-checks` | 반영 | 14~18세 챌린지, 19~44세 현재 건강 신호, 45세 이상 미래 발병 위험 분기 |
| 건강정보 입력 | `POST /api/v1/health-checkups` | 연결됨·재대조 필요 | 19세 이상 저장 허용, 운영 8개 계약과 연구 후보 25개 재대조 필요 |
| 현재 건강 신호 | 백엔드 구현 중 | 화면 연결 준비 | 백엔드 응답만 표시하며 결과가 없으면 임의 범주를 만들지 않음 |
| 예측 요청 | `POST /api/v1/prediction-jobs` | 연결됨 | `checkup_id`, `model_key` 전송 |
| 예측 상태 | `GET /api/v1/prediction-jobs/{job_id}` | 반영 | `queued/running/succeeded/failed`만 작업 상태로 사용 |
| 결과 | `GET /api/v1/predictions/{prediction_id}` | 연결됨 | 승인된 위험 범주만 사용자에게 표시 |
| 위험·보호요인 | `GET /api/v1/predictions/{prediction_id}/risk-factors` | 연결됨 | 검증된 설명만 표시 |
| 챌린지 추천 | `GET /api/v1/challenge-recommendations` | 정비 | API 실패 시 기본 예시로 자동 대체하지 않음 |
| 챌린지 시작 | `POST /api/v1/challenge-cycles` | 연결됨 | 최대 선택 수와 오류 응답 재확인 필요 |
| 일일 기록 | `PUT /api/v1/user-challenges/{id}/logs/{date}` | 연결됨 | 중복 요청 대신 날짜별 갱신 |
| 대시보드 | `GET /api/v1/dashboard` 외 | 연결됨 | PR #19의 최종 엔드포인트·응답 예시와 재대조 필요 |
| 주간 리포트 | `GET /api/v1/weekly-reports/current` | 반영 | 기간·요약·`challenge_details` 표시, 고정 예시 데이터 제거 |
| 4주·전체 리포트 | 미확정 | 연결 대기 | 실제 API 전에는 준비 상태를 표시하며 예시 수치를 표시하지 않음 |
| 4주 건강교육 | `GET /api/v1/education-contents` | 반영 | 로딩·빈 데이터·오류·사용자별 완료 상태 표시 |
| 건강교육 완료 | `PUT /api/v1/education-contents/{id}/progress` | 반영 | 처리 중 중복 요청 방지 |

## 오류·상태 처리 원칙

- 네트워크 단절은 `NETWORK_ERROR`로 구분하고 재시도를 안내한다.
- HTTP 5xx는 서버 오류로 표시하고 로컬 예시 데이터로 바꾸지 않는다.
- `503`은 `MODEL_NOT_READY`, `504`는 `TIMEOUT`으로 해석한다.
- 작업 상태는 `queued`, `running`, `succeeded`, `failed` 네 값만 사용한다.
- 시간초과는 별도 작업 상태가 아니라 `status: failed`, `error_code: TIMEOUT`으로 표시한다.
- 로컬 예시는 `localhost`, `127.0.0.1`, `::1`에서 명시적으로 진입한 미리보기 흐름에만 허용한다.

## 팀 인계 대기 항목

### 박빛샘

- 정상·오류 공통 응답의 최종 JSON 예시
- 회원가입 중복, 토큰 만료, 모델 미탑재, 예측 실패의 확정 오류 코드
- 챌린지·일일 기록·대시보드 최종 엔드포인트
- PR #19와 PR #21의 마이그레이션 적용 순서
- 현재 건강 신호의 최종 엔드포인트와 `category/message/items` 응답 구조

### 양준혁

- 실제 모델 입력 25개와 필수·선택 구분
- 필드별 자료형·허용 범위·결측 처리
- 사용자 결과 화면에 공개 가능한 범주·모델 버전·위험요인 범위
- 적용 연령과 운영 미승인 상태 문구

### 정세준

- 모델–API–DB–화면 필드 대응표
- Sprint 4 핵심 MVP·확장·제외 기능 확정본
- 정상·기진단·긴급 증상·연령 외·예측 실패 E2E 완료 조건
- PR #19 → #21 → #22 → #23 병합 순서 확정

## 남은 프론트엔드 확인

- PR #19 병합 기준으로 회원가입 → 프로필 → 적합성 실제 응답 통합 테스트
- 25개 모델 입력 계약 수령 후 건강정보 폼 필드·단위·필수값 재대조
- 401·409·422·500·503·TIMEOUT 화면별 문구 확인
- 빈 챌린지·빈 대시보드·결과 없음 화면 확인
- 요일별 기록·4주 집계·전체 회차 이력 API 계약 수령 후 리포트 연결
- 4주 건강교육의 주차별 공개 규칙 확인
- 변경 내용을 PR #23에 반영하고 CI 재확인
