# Sprint 2 정식 앱 핵심 사용자 흐름(End-to-End) 구현 보고

| 항목 | 내용 |
|---|---|
| 구현 이슈 | [#5 SP2-WEB-004](https://github.com/AI-HealthCare-05/AH_05_02/issues/5) |
| 작업 브랜치 | `feature/5-sprint2-vertical-flow` |
| 실행 기준 | `app/main.py` |
| 구현일 | 2026-08-21 |
| 모델 연결 | 교체 가능한 `PredictionProvider`, 기본값 `development` |

## 1. 구현 결과

- 정식 FastAPI 앱에 `가입·로그인 → 동의 → 적합성 확인 → 건강정보 입력 → 비동기 예측 → 안전 결과 → 챌린지 → 일일 기록 → 대시보드` 흐름을 연결했다.
- 사용자 예측 API를 `/api/v1/prediction-jobs`로 통일하고 상태를 `queued/running/succeeded/failed`, 생성 시각을 `created_at`으로 고정했다.
- Redis Stream은 작업 전달·단기 상태에 사용하고 처리한 메시지는 `XACK` 후 `XDEL`한다. MySQL 작업 요청에는 입력값이 아닌 스키마 버전·필드명만 저장하고, 완료·실패와 모델·입력·임계값 버전 및 결과 이력을 남긴다.
- 개발 provider는 모델 연결 상태만 검증한다. 승인된 임계값이 없으므로 개인 위험 범주, 내부 점수, 확률, 개선율을 공개하지 않는다.
- 경고 증상·기진단은 서버에서 예측을 차단하고 의료기관 안내를 만들며, 진행 중 챌린지는 종료 상태로 보존한다.
- 검토된 일반 건강 챌린지 템플릿에 출처와 안전 문구를 함께 제공한다.
- Sprint 1 프로토타입의 독립 실행 경로를 제거했다. `src.backend.main:app`도 정식 `app.main:app`을 사용한다.
- Nginx의 `/`와 정적 파일 요청을 정식 FastAPI 앱으로 전달해 실제 웹 화면을 제공한다.

## 2. 단일 모델 입력 계약

PR #4의 KLoSA 미래 발병 입력 계약과 웹 입력을 `klosa-diabetes-incident-v1`로 맞췄다.

| 모델 변수 | 웹·서버 처리 |
|---|---|
| `age` | 회원 생년월일로 서버 계산 |
| `bmi` | 키·몸무게로 서버 계산 |
| `self_rated_health` | 5단계 필수 입력 |
| `meal_count_yesterday` | 0~10회 필수 입력 |
| `sex` | 회원 프로필에서 변환 |
| `regular_exercise` | Boolean 필수 입력 |
| `current_smoker` | Boolean 필수 입력 |
| `current_drinker` | Boolean 필수 입력 |

다음 차수 당뇨 진단, 다음 차수 약물, 미래 측정값 등 정답을 직접 결정하는 변수는 계약에서 제외하며 추가 필드는 서버가 거부한다.

## 3. 주요 구현 위치

| 영역 | 파일 |
|---|---|
| 모델 입력·활성 모델 계약 | `app/prediction/contracts.py` |
| 교체 가능한 provider | `app/prediction/providers.py` |
| 동의·적합성·건강정보 | `app/services/health.py`, `app/apis/v1/health_routers.py` |
| 비동기 예측 | `app/services/ai_jobs.py`, `app/apis/v1/prediction_routers.py` |
| Worker·DB 결과 저장 | `ai_worker/handlers.py`, `ai_worker/worker.py`, `ai_worker/db.py` |
| 챌린지·일일 기록 | `app/services/challenges.py`, `app/apis/v1/challenge_routers.py` |
| 대시보드·후속조치 | `app/apis/v1/dashboard_routers.py` |
| 정식 프론트 | `src/frontend/index.html`, `src/frontend/app.js` |
| DB 마이그레이션 | `app/core/db/migrations/models/1_20260821170000_sprint2_vertical_flow.py` |
| Docker E2E | `scripts/test-sprint2-flow.ps1` |

## 4. 의료·개인정보 안전

- 결과는 진단·처방이 아니라 약 2년 뒤 신규 당뇨 진단 위험 선별·건강교육으로 표현한다.
- 개발 provider에서는 `risk_category=null`, `internal_score=null`이며 화면에는 `범주 검토 중`을 표시한다.
- 내부 점수가 DB에 존재하더라도 공개 응답의 `prediction_payload`에는 포함하지 않는다.
- 검증된 설명 방법이 없으므로 위험요인 API는 빈 목록과 `not_available` 상태를 반환한다. 휴리스틱을 SHAP으로 표시하지 않는다.
- 기진단·경고 증상·미동의·만 19세 미만·모델 연령 밖·검증 모집단 밖은 표준 사유 코드로 차단한다.
- 의료기관 안내가 필요한 동안 새 챌린지 사이클 생성을 거부한다.
- 동의 철회 시 신규 개인화 처리를 중지하고 진행 중 사이클을 종료한다. 탈퇴 후 30일 삭제·익명화 자동화는 후속 구현이다.
- 원본 의료 데이터, 개인 단위 행 데이터, 비밀번호, API 키, 모델 파일을 반입하지 않았다.

## 5. 검증 결과

### 정적·단위 테스트

```text
uv run ruff check .                 PASS
uv run ruff format . --check        PASS
uv run pytest -q                    18 passed
```

검증 범위에는 입력 계약 추가 필드 거부, 개발 provider의 확률·범주 미생성, 미성년·미동의·기진단·경고·모델 범위 차단, 미승인 결과 비공개, Worker 시간초과가 포함된다.

### Docker 통합 스모크

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-sprint2-flow.ps1
```

실제 `FastAPI + MySQL + Redis + AI Worker 3개 + Nginx` 환경에서 다음을 확인했다.

- 정상 흐름의 작업 상태 `succeeded`와 `Prediction` 저장
- 개발 결과 `development_only`, 공개 위험 범주 없음
- 4주 사이클·일일 로그·대시보드 연결
- 기진단자 예측 차단과 후속 안내
- 미동의 사유 코드
- 경고 증상의 의료 안내 우선
- 다른 사용자의 예측 결과 접근 `404`

### 브라우저 화면 점검

- Nginx `http://localhost/`에서 첫 화면과 가입·동의 화면 연결 확인
- 390×844 모바일 화면에서 가로 넘침 없음(`scrollWidth == clientWidth`)
- 표시된 주요 버튼 높이 44px 이상 확인
- 기본 화면과 모바일 화면의 큰 글씨·의료 안전 문구·단계 안내 확인
- 브라우저 오류·경고 로그 없음

Windows 한글 저장소 경로에서 BuildKit gRPC 오류가 발생할 수 있어, 같은 저장소를 가리키는 임시 영문 junction에서 `docker build`하면 재현된다. 소스 사본은 만들지 않는다.

## 6. PR #4 모델 이식 방법

1. PR #4가 기준 브랜치에 병합되면 artifact 로더를 `ArtifactPredictionProvider`에 연결한다.
2. `PREDICTION_PROVIDER=artifact`, `MODEL_URI`, 모델·입력·임계값 버전을 환경변수로 설정한다.
3. artifact의 `feature_columns`가 `klosa-diabetes-incident-v1`의 8개 변수와 정확히 같은지 시작 시 검증한다.
4. 검증 전 내부 점수는 계속 비공개로 유지한다.
5. AUROC·AUPRC·민감도·특이도·Brier·Calibration과 고위험 누락 비용 검토 후 승인된 `threshold_version`만 운영 범주에 사용한다.
6. 승인 모델의 낮음·주의·높음 및 고위험 후속조치 E2E를 추가한 뒤 `promotion_status=approved`로 전환한다.

## 7. 의도적으로 제외한 항목

- 이미지 식단 분석: 모델·영양 안전 검토와 범위가 부족해 제외
- 웹 알림: OT 선택 기능이며 Sprint 2 필수 핵심 사용자 흐름보다 우선순위가 낮아 제외
- 생성형 개인 의료 조언·RAG: 근거 검색·출처·안전 필터가 완성되기 전 제외
- 고혈압·비만·관절염 모델: 당뇨병 단일 목적 계약 검증 전 확장하지 않음
- 개인 위험요인·SHAP: 검증 설명 pipeline 준비 전 미제공

## 8. 남은 완료 게이트

- PR #4의 모델 artifact와 입력 계약 리뷰·병합
- 승인 임계값과 모델 카드 확정 후 범주 공개 E2E
- 개인정보 탈퇴·30일 삭제 또는 복구 불가능한 익명화 자동화
- CI 통과 및 최소 1명 리뷰
- 통합 브랜치에 Squash merge

## 9. PR #6 사용자 흐름 리뷰 반영

- 적합성 제외 사유를 한 문구로 합치지 않고 화면 코드와 다음 행동으로 구분한다: 미성년 `E02`, 급한 경고 증상 `E03`, 당뇨병 기진단 `D01`, 활성 모델 범위 밖 `E05`.
- 높은 위험 범주는 `결과 설명 보기` 대신 `검사·의료기관 안내 보기`를 우선 행동으로 제공한다. 높은 위험 범주는 진단이 아니며 챌린지보다 검사·상담 안내를 먼저 노출한다.
- 비동기 일반 실패와 `failed + TIMEOUT`을 구분하고 `입력정보 확인하기`, `다시 시도하기`를 제공한다. 실패가 높은 위험을 의미하지 않는다는 문구를 함께 표시한다.
- 모델 버전과 입력 스키마 버전은 DB·API에서 운영·감사 목적으로 추적하되 일반 사용자 화면에는 표시하지 않는다.
- 예측 기간은 모델 계약과 운영 문서에 보존하되 일반 사용자 첫 화면의 핵심 문구에서는 제외한다.
- 서비스 이용 연령 만 19세 이상과 KLoSA 활성 모델 적용 연령 만 45세 이상을 별도 문구로 안내한다.
