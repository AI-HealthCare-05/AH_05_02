# API 상태 정리 (9/7)

범례: **완료(라이브)** = 실제 요청 보내서 응답 확인함 / **완료(코드)** = 구현은 확인했으나 오늘 라이브 테스트는 안 함 / **부분구현** / **범위 제외** = 팀 결정으로 이번 MVP 제외 / **미점검** = 오늘 점검 범위 밖(전혀 안 봄)

## 회원가입 / 인증
| API | 상태 |
|---|---|
| `POST /auth/signup` | 완료(라이브) — `terms_agreed` 저장 버그 수정 |
| `POST /auth/login` | 완료(라이브) |
| `POST /auth/refresh` | 미점검 |
| `POST /auth/logout` | 미점검 |

## 사용자 / 건강정보
| API | 상태 |
|---|---|
| `GET /users/me` | 완료(라이브) |
| `PATCH /users/me/profile` | 완료(라이브) |
| `DELETE /users/me` | 미점검 |
| `GET`/`POST /consents` | 완료(라이브) |
| `PATCH /consents/{id}/withdraw` | 완료(코드) |
| `POST /eligibility-checks` | 완료(라이브) — 프로필 미입력 시 422 가드 확인 |
| `GET /eligibility-checks/latest` | 완료(코드) |
| `GET /health-checkups/input-schema` | 완료(코드) |
| `POST`/`GET`/`GET{id}`/`PATCH /health-checkups` | 완료(라이브 생성만, 나머지는 코드 확인) |

## 예측 (오늘이·내일이·모레노)
| API | 상태 |
|---|---|
| `GET /models/active` | 미점검 |
| `POST /prediction-jobs` | 완료(라이브) |
| `GET /prediction-jobs/{id}` | 완료(라이브) |
| `GET /predictions/latest` | 완료(라이브) — `signal_level` 확인 |
| `GET /predictions`, `/predictions/changes`, `/predictions/{id}` | 완료(코드) |
| `GET /predictions/{id}/risk-curve` (모레노) | 범위 제외(팀 결정) — 승인 모델 없어 503 유지 정상 |
| `GET /predictions/{id}/risk-factors` | 부분구현 — 설명 기능 항상 빈 배열 |
| `POST /ai-jobs`, `GET /ai-jobs/{id}` | 완료(라이브) — 오늘 라우터 미등록 버그 발견·수정 |
| `GET /ai-jobs/{id}/events` (SSE) | 미점검 |
| `POST /research/models/{model}/predict` | 미점검 |

## 챌린지 / 대시보드
| API | 상태 |
|---|---|
| `GET /challenges` | 완료(라이브) |
| `GET /challenge-recommendations` | 완료(라이브) — 규칙기반, 팀 결정과 일치 확인 |
| `POST /challenge-cycles` 외 사이클/기록 API 5종 | 완료(코드) — 미래날짜·사이클상태 검증 로직 확인, 라이브 미검증 |
| `GET /dashboard/summary` | 완료(라이브) |
| `GET /dashboard/challenge-progress`, `/lifetime-risk`, `/follow-up-actions`, `/recommendations` | 완료(코드) |

## 병원 검색 / 응급 안내
| API | 상태 |
|---|---|
| `GET /medical-facilities/nearby` | 완료(라이브) — 카카오 실키 |
| `GET /emergency-facilities/nearby` | 완료(라이브) — NEMC 실키 |

## 건강교육 RAG / 웰니스
| API | 상태 |
|---|---|
| `POST /health-education/questions` | 완료(라이브) — 출처 있는 답변 + 의료 안전 거절 확인 |
| 웨어러블·식단분석·OCR·알림·주간리포트 PDF (`/wearables/*`, `/food-analyses/*`, `/ocr-drafts/*`, `/notifications*`, `/weekly-reports/current/pdf`) | 미점검 |

## 오늘 범위 밖 (전혀 점검 안 함)
- `/feedback` (피드백)
- `/forest/*` (당근숲 게임)
- 게임(`/wallet`, `/inventory*`, `/avatar*`)
- `/user-challenges/{id}/barriers`, `/invitations`, `/connections`, `/shared-challenge-groups` 등 소셜·초대 기능(engagement)

자세한 근거·요청/응답 예시는 `docs/BACKEND_STATUS_20260907.md`, 흐름별 요약은 `docs/INTEGRATION_TABLE_20260907.md` 참고.
