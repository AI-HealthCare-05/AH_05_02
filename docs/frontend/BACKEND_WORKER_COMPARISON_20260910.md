# 프론트 푸시와 백엔드·Worker 통합 구분

확인일: 2026-09-10. 9/9 프론트 공유 메모의 후속 코드 비교입니다.

## 이번 프론트 반영

- 저장소: [AI-HealthCare-05/AH_05_02](https://github.com/AI-HealthCare-05/AH_05_02)
- 브랜치: `codex/fe-followup-20260909`
- PR: [#42](https://github.com/AI-HealthCare-05/AH_05_02/pull/42), 대상 `codex/e2e-integration`
- 포함: 확정한 프론트 화면·이미지, 관련 테스트, 공유 문서.
- 로컬 `codex/s2-api002`의 백엔드·Worker·DB 변경은 이번 프론트 커밋에 포함하지 않습니다.

## 비교 기준

| PR | 확인한 커밋 | 범위 |
|---|---|---|
| [#41](https://github.com/AI-HealthCare-05/AH_05_02/pull/41) | `e2ceea11d991ebd5b8c0d8d2f65cdb8d376bc25f` | 현재 선별 v0.6.1 API·Worker·DB |
| [#43](https://github.com/AI-HealthCare-05/AH_05_02/pull/43) | `ab27587b0a5678de33a897e1e85a67a9627ce593` | 모델·프론트·숲 통합 시연본 |
| [#44](https://github.com/AI-HealthCare-05/AH_05_02/pull/44) | `777b65ed7fb7ebea298981f1e6ed023cd178d2ba` | 빛샘님 Apple 정제·RAG·퀴즈·프로필 수정 |

파일 내용 비교 결과이며 실제 병합·DB 마이그레이션·Worker 실환경 검증 결과는 아닙니다.

## 이미 원격 PR에 들어 있는 로컬 수정

다음은 로컬 작업 파일과 해당 PR의 파일 전체 내용이 일치합니다. 같은 수정으로 다시 올릴 필요가 없습니다.

| 파일 | 일치하는 PR |
|---|---|
| `app/apis/responses.py` | #41, #43, #44 |
| `ai_worker/db.py`, `ai_worker/worker.py`, `ai_worker/Dockerfile.current-screening` | #41, #43 |
| `app/apis/v1/ai_job_routers.py`, `app/apis/v1/prediction_routers.py` | #41, #43 |
| `app/core/__init__.py`, `app/dtos/ai_jobs.py`, `app/services/health.py` | #41, #43 |
| `app/models/users.py`, `app/repositories/user_repository.py`, `app/services/auth.py` | #41, #43 |
| `app/apis/v1/challenge_routers.py`, `app/services/challenge_catalog.py`, `app/services/challenge_proofs.py`, `app/vision/food_vision.py` | #43, #44 |
| `app/dtos/health.py` | #43 |

가입 동의 여부·동의 시각 저장은 #44에는 없지만 #41·#43에는 이미 있습니다.

## 빛샘님 수정 중 보존할 부분

- `PATCH /users/me`를 `/users/me/profile`과 같은 처리로 연결한 수정.
- 프로필 이름 변경 시 기존 숲 아바타 이름 동기화.
- Apple Health 정제, 근거 기반 건강교육 답변, 퀴즈 API와 관련 테스트.
- 통합 브랜치의 챌린지 V2 설정 및 숲 기능. 로컬 구버전 설정 파일 전체로 덮어쓰지 않습니다.

로컬 8022 작업 폴더에는 위 일부 변경이 아직 없으므로, 그 폴더 전체가 #44를 포함한 최신 통합본이라는 뜻은 아닙니다.

## 추가 검토가 필요한 로컬 차이

| 차이 | 통합 시 처리 |
|---|---|
| `CURRENT_SCREENING_RUNTIME`으로 `v061`/`shared7`를 명시적으로 선택하고 입력값도 분기 | API와 Worker를 함께 반영할지 검토. 한쪽만 반영하면 입력 계약이 어긋날 수 있음 |
| `ai_worker/Dockerfile`에 원격의 `--group modeling`이 빠짐 | #43의 의존성 그룹을 유지. 로컬 Dockerfile로 덮어쓰지 않음 |
| `Prediction.task_type`이 nullable 80자이고 `threshold_scope`도 nullable | 기존 로컬 DB 호환 목적. #41의 필수 필드·마이그레이션과 일치 여부를 먼저 확인 |
| `18_20260908233000_pr41_local_api_contract.py` | 이미 적용된 로컬 마이그레이션 순서를 전제로 함. 정식 DB에 그대로 추가하지 않고 기존 마이그레이션 이력과 비교 |
| 식사 횟수가 3회가 아니면 식사 기록을 우선 추천하는 로컬 조건 | #43·#44는 식사 횟수만으로 불규칙 식사를 판단하지 않도록 제거했음. 원격의 수정 유지 |

## 다음 통합 순서

1. #42에 프론트 변경을 검증·푸시.
2. #43 통합 시연본에 최신 #42와 #44를 반영할 때 프로필·RAG·퀴즈 수정 보존.
3. 위 로컬 차이 중 필요한 모델 선택 기능만 별도 변경으로 검토.
4. 실제 DB·Worker 환경에서 가입 → 건강정보 저장 → 두 모델 요청 → 일부 실패 재시도 → 결과 확인.

현재 문서 작성 시점에는 2~4번을 완료하지 않았습니다. 8022의 기존 작업 파일과 로컬 DB는 이 비교 작업으로 변경하지 않았습니다.
