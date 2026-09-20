# 와이어프레임 정합화 ver.5.6

| 항목 | 내용 |
|---|---|
| 기준일 | 2026-09-14 |
| 기준 요구사항 | 요구사항 정의서 ver.5.6 |
| 기준 API | API 명세서 ver.5.6, `/api/v1` |
| 기준 ERD | `03_ERD_ver.5.6.dbml` |
| 표현 원칙 | 위험 신호 선별·건강교육이며 진단·처방이 아님 |

## 1. 전체 사용자 흐름

`서비스 소개 → 회원가입·로그인 → 필수 동의 → 적합성·응급증상 확인 → 건강정보 입력·불러오기 → 오늘이·내일이 결과 → 대시보드 → 4주 챌린지 → 일일 인증 → 보상·리포트`

- 기진단자는 예측을 실행하지 않고 의료기관 안내와 일반 건강관리 기능으로 이동한다.
- 만 19~44세 사용자는 현재 위험 신호와 건강 챌린지를 이용한다.
- 만 45세 이상 적합 사용자는 현재 위험 신호와 미래 위험 전망을 함께 확인할 수 있다.
- 긴급증상 응답은 일반 응급안내와 119 연결을 우선하며 예측·챌린지를 진행하지 않는다.

## 2. 화면별 계약

| 순서 | 화면 | 핵심 입력·표시 | 연결 API | 필수 상태 |
|---:|---|---|---|---|
| 1 | 소개·진입 | 서비스 목적, 시작하기, 로그인 | 없음 | 기본 |
| 2 | 회원가입·로그인 | 이메일, 비밀번호, 필수 약관 | `/auth/signup`, `/auth/login`, `/auth/refresh`, `/auth/logout` | 입력 오류, 중복, 잠금 |
| 3 | 동의 | 필수·선택 동의, 철회 | `/consents`, `/consents/{consent_id}/withdraw` | 동의, 철회, 재동의 |
| 4 | 적합성·응급증상 | 연령, 기진단, 긴급증상 | `/eligibility-checks`, `/eligibility-checks/latest` | 이용 가능, 기진단, 응급 |
| 5 | 건강정보 | 직접 입력, OCR 초안, 웨어러블 | `/health-checkups`, `/ocr-drafts/*`, `/wearables/*` | 로딩, 검증 실패, 사용자 확인 |
| 6 | 예측 대기 | 비동기 작업 상태 | `/prediction-jobs`, `/prediction-jobs/{job_id}` | queued, running, failed, succeeded |
| 7 | 오늘이·내일이 결과 | 낮음·주의·높음, 위험·보호요인, 안전 문구 | `/predictions/*`, `/research/models/*` | 결과 없음, 부분 결과, 모델 미준비 |
| 8 | 대시보드 | 최신 결과, 오늘 챌린지, 보상, 다음 행동 | `/dashboard/*`, `/follow-up-actions` | 첫 이용, 진행 중, 오류 |
| 9 | 4주 챌린지 | 사이클, 음료·식단·운동 3영역 | `/challenge-cycles/*`, `/challenge-v2/today` | 생성 전, 진행, 완료 |
| 10 | 일일 인증 | 물컵 체크, 사진, 웨어러블 | `/challenge-v2/assignments/*`, `/challenge-v2/evidence/{evidence_id}` | 목표 전, 검토 중, 승인, 반려 |
| 11 | 교육·리포트 | 근거 교육, 퀴즈, 주간·4주·전체 결과 | `/health-education/*`, `/weekly-reports/*` | 근거 없음, 로드 실패, 완료 |
| 12 | 당근의 숲 | 지갑, 인벤토리, 아바타, 숲 배치 | `/wallet`, `/inventory*`, `/avatar*`, `/forest/*` | 그룹 없음, 권한 없음, 보상 완료 |
| 13 | 의료기관 안내 | 가까운 의료·응급시설, 지도 | `/medical-facilities/map-config`, `/medical-facilities/nearby`, `/emergency-facilities/nearby` | 위치 허용, 위치 거부, 검색 실패 |

## 3. 챌린지·보상 화면 기준

- 하루 배정은 음료·식단·운동 영역에서 각 1개를 제공한다.
- 물 섭취는 컵 단위로 체크하며 목표 달성 전 인증 버튼을 비활성화한다.
- 식단 사진과 웨어러블 결과는 자동 확정하지 않고 사용자의 확인 또는 검토 상태를 표시한다.
- 챌린지 완료 보상은 지갑 거래와 함께 한 번만 반영한다.
- 건강정보와 예측 결과는 가족·친구 그룹에 기본 공유하지 않는다.

## 4. 공통 UI·접근성 기준

- 위험 단계는 색상뿐 아니라 `낮음·주의·높음` 텍스트와 아이콘을 함께 표시한다.
- 버튼 이름은 행동이 드러나게 작성하고 다음 단계는 한 화면에 하나의 주 행동으로 제시한다.
- 고령 사용자를 위해 본문 크기, 명암비, 터치 영역과 키보드 포커스를 점검한다.
- API 지연 중에는 중복 제출을 막고 진행 상태와 재시도 방법을 제공한다.
- 예시 데이터와 연구용 결과는 실제 사용자 결과처럼 표시하지 않는다.

## 5. 구현 정합성 점검 결과

2026-09-14 `develop`의 OpenAPI와 API 명세서 ver.5.6을 `HTTP Method + 정규화된 URI`로 비교했다.

- API 명세서에는 100개 작업이 정의되어 있고, 현재 OpenAPI에는 `/api/v1` 기준 118개 작업이 노출된다.
- 기능 자체가 없는 경우보다 식별자 위치와 복수형, 하위 리소스 경로가 달라 정확히 일치하지 않는 경우가 많다.
- 대표 불일치는 동의 철회, 건강검진 입력 스키마, 위험요인·위험곡선, 웨어러블, 퀴즈, 인벤토리 구매, 숲 오브젝트 경로다.
- 화면 구현은 현재 OpenAPI 경로를 사용한다. API 명세서 경로를 목표 계약으로 확정할 경우 별도 구현 PR에서 라우트와 계약 테스트를 함께 변경한다.
- 기존 경로를 즉시 삭제하지 않고 호환 경로 제공 여부를 먼저 결정해 프론트엔드 회귀를 방지한다.

| 영역 | API 명세서 ver.5.6 | 현재 OpenAPI | 처리 기준 |
|---|---|---|---|
| 동의 철회 | `PATCH /consents/withdrawal` | `PATCH /consents/{consent_id}/withdraw` | 현재 경로 사용, 목표 계약 확정 후 호환 처리 |
| 입력 스키마 | `GET /health-checkup-input-schema` | `GET /health-checkups/input-schema` | 현재 경로 사용 |
| 위험 설명 | `GET /predictions/risk-factors` | `GET /predictions/{prediction_id}/risk-factors` | 결과 식별자를 유지 |
| 위험 곡선 | `GET /predictions/risk-curve` | `GET /predictions/{prediction_id}/risk-curve` | 결과 식별자를 유지 |
| 웨어러블 | `/wearable-*` | `/wearables/*` | 현재 복수형 경로 사용 |
| 근거 퀴즈 | `/quizzes*` | `/health-education/quizzes*` | 근거 교육 네임스페이스 유지 |
| 아이템 구매 | `POST /inventory/purchase` | `POST /inventory/items/{item_id}/purchase` | 아이템 식별자를 유지 |
| 숲 배치 | `/forest/objects*` | `/forest/spaces/{group_id}/objects*` | 그룹 권한 범위를 유지 |

## 6. 완료 확인

- [ ] 요구사항 ID와 화면이 연결되어 있다.
- [ ] 화면의 API 경로와 API 명세서 ver.5.6이 일치한다.
- [ ] 화면에 필요한 엔터티가 ERD ver.5.6에 존재한다.
- [ ] 정상·빈 상태·부분 실패·권한 오류·모델 미준비 화면이 준비되어 있다.
- [ ] 의료 안전 문구와 응급 우선 흐름이 모든 관련 화면에서 유지된다.
- [ ] 모바일·고령층 접근성과 E2E 핵심 흐름을 확인했다.
