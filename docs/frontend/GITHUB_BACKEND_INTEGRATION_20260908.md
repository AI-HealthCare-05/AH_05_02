# GitHub 백엔드 로컬 연동 · 2026-09-08

기존 `AH_05_02-s2-api002` 프런트가 사용하는 `http://127.0.0.1:8022/`에 GitHub 백엔드 변경을 통합했다. 가입·건강정보 입력·비동기 분석·결과 조회·V3 카탈로그가 로컬 MySQL/Redis를 통해 동작한다.

## 반영 기준

- PR 41: https://github.com/AI-HealthCare-05/AH_05_02/pull/41 · `e2ceea11d991ebd5b8c0d8d2f65cdb8d376bc25f`
- 공통 기준: `origin/codex/e2e-integration` · `60b1ea4a4276fd383bcf3f2ca97cbb6b08386df4`
- 기존 V3 연동: PR 40 · `aaeea3b9b9979409fad4b3c8c92f527c70cf6fcb` 기반의 로컬 변경 유지.
- PR 41 변경 40개 파일을 공통 기준과 현재 작업 파일로 병합했다. 기존 프런트 수정은 이 작업에서 덮어쓰지 않았다. 원본과 비교 자료는 무시되는 `tmp/backend-integration-20260908/`에 보관했다.

## 동작 변경

회원가입 시 약관 동의 여부·시각을 저장한다. 건강정보의 주관적 건강 상태·어제 식사 횟수는 선택 입력이다. 현재 위험 선별과 향후 위험 선별을 별도 Redis 스트림/워커로 처리하고, 실패 응답의 코드와 재시도 가능 여부를 유지한다. v0.6.1의 입력 변환·아티팩트 계약 검증 코드도 반영했다.

현재 로컬 모델은 **shared7 현재 위험 선별 + RF25 다중 기간 향후 위험 선별**이다. `LOCAL_CURRENT_SCREENING_RUNTIME` 기본값을 `shared7`으로 명시했다. 최신 모델 실패 시 임의로 이전 모델로 대체하는 방식이 아니며, 실제 결과에는 사용한 모델 버전이 기록된다. 일반 서버 설정의 기본 현재 모델은 원격 PR과 같은 `v061`이다. 결과의 기존 연구용 미리보기 및 운영 승인 제한은 유지된다.

## DB와 실행

기존 로컬 17번 마이그레이션은 유지하고 `18_20260908233000_pr41_local_api_contract.py`를 추가했다. `scripts/apply_pr41_local_schema.py --apply`로 약관 컬럼 2개 추가와 건강정보 선택 필드의 NULL 허용을 적용했다. 기존 예측 provenance의 길이·NULL 허용과 기존 사용자 기록을 유지한다. 기존 사용자에게 약관 동의를 소급 생성하지 않는다. Aerich 이력은 변경하지 않았으며 추후 해당 마이그레이션이 실행되어도 기존 컬럼을 다시 추가하지 않는다.

저장소 루트에서 각 프로세스를 실행한다.

```sh
.venv/bin/python scripts/run_frontend_local_8022.py
.venv/bin/python scripts/run_worker_local_8022.py --model current
.venv/bin/python scripts/run_worker_local_8022.py --model future
```

현재/향후 스트림은 각각 `ai:jobs:local8022:pr41-current`, `ai:jobs:local8022:pr41-future`다. 기존 다른 워커의 스트림과 분리했다. 기존 비공개 DB 설정을 읽으며 자격 증명을 복사하거나 출력하지 않는다.

## 남은 조건

v0.6.1의 `models/artifacts/candidates/diabetes_current_screening/v061/model.joblib`은 로컬과 GitHub에 없다. 매니페스트 SHA-256 `ffc6743849973676308703dd6bd5af0f8d557d5f45a8886e6660f86c81b85178`과 일치하는 아티팩트 및 전용 scikit-learn 1.9.0 런타임이 필요하다. 이 파일이 없으면 명시적인 v061 선택은 시작 전 실패한다. 현재 로컬 Python의 scikit-learn 1.8.0을 임의로 업그레이드하지 않았다.

신규 `/reports?period=...` 및 별도 현재 선별 입력 API는 확인한 GitHub 브랜치에 없어 이번 반영 대상에 포함할 수 없었다. 기존 리포트의 현재 API 조합은 유지된다. 원격 PR 병합·GitHub push·운영 배포는 수행하지 않았다.

## 검증

- 관련 Python 회귀/통합 테스트 101개 통과. 테스트 DB는 메모리 SQLite다.
- 프런트 Node 회귀 테스트 92개 통과. Ruff 및 `git diff --check` 통과.
- 실제 로컬 HTTP: 합성 QA 계정 가입/로그인 → 프로필/건강정보 동의 → 이용 대상 확인 → 선택 필드 NULL인 건강정보 저장 → 두 모델 요청 → 각각 워커 추론 성공 → DB 결과 조회 확인.
- 현재 결과: `knhanes-shared7-sk180-research-v1`, 향후 결과: `rf25-first-interval-survival-ensemble-v1`, 향후 미리보기 3개 시점. 모두 `preview_only=true`, `display_allowed=false` 유지.
- V3 카탈로그 13개 응답, 브라우저의 8022 기본 페이지 로드 확인.
- 검증용으로 만든 합성 계정은 실행 후 비활성화했다. 실사용자 계정으로 테스트하지 않았다. 결과 요약은 `tmp/backend-integration-20260908/http-smoke-result.json`에 있다.

v0.6.1 실제 추론, 외부 병원/사진/RAG 서비스, 운영 배포 환경은 이번 실행 검증 범위에 포함하지 않는다.
