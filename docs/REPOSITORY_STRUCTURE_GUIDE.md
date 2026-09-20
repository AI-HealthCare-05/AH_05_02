# 저장소 구조 및 파일 저장 위치 가이드

## 1. 한 줄 원칙

팀원은 **자신의 작업 코드와 설정만 Git에 올리고**, 원본 의료 데이터·전처리 산출물·모델 바이너리·개인정보는 정해진 로컬 폴더에만 둡니다.

## 2. 실제 실행 기준 구조

```text
AH_05_02/
├─ app/                         # 정식 FastAPI 백엔드
│  ├─ apis/v1/                 # HTTP 라우터
│  ├─ dtos/                    # 요청·응답 스키마
│  ├─ services/                # 비즈니스 정책
│  ├─ repositories/            # DB 접근
│  ├─ models/                  # DB 엔터티
│  ├─ prediction/              # 웹과 모델 사이의 입력·출력 계약
│  └─ core/db/migrations/      # DB 마이그레이션
├─ ai_worker/                  # Redis 작업을 소비하는 비동기 AI Worker
├─ src/
│  ├─ frontend/                # 실제 웹 화면·CSS·JavaScript·이미지
│  ├─ ml/
│  │  ├─ preprocessing/        # KLoSA·KNHANES 전처리 코드
│  │  ├─ modeling/             # 공통 분리·특성·모델·임계값 코드
│  │  ├─ evaluation/           # 공통 평가·신뢰구간 코드
│  │  ├─ inference/            # 승인 모델 추론 어댑터
│  │  └─ experiments/          # 실험 manifest 조립기
│  ├─ rag/                     # 문서 검색·근거 생성·안전장치
│  └─ backend/                 # 과거 프로토타입 호환용; 신규 기능 작성 금지
├─ data/
│  ├─ raw/                     # 다운로드한 원본, Git 제외
│  ├─ interim/                 # 압축 해제·중간 전처리본, Git 제외
│  ├─ processed/official_v1/   # 공통 학습·평가 데이터, Git 제외
│  ├─ external/                # RAG 원문 등 외부 자료, Git 제외
│  └─ metadata/                # 변수·라벨·코호트·품질 기준, Git 공유
├─ experiments/
│  ├─ _template/               # 새 실험 생성 템플릿
│  └─ diabetes_incidence/
│     ├─ baselines/            # 기준 모델
│     ├─ candidates/           # 단일 후보 모델
│     ├─ ensembles/            # 앙상블
│     └─ leaderboard.csv       # Recall 중심 공통 리더보드
├─ models/
│  ├─ registry/                # 후보·운영 모델 manifest, Git 공유
│  └─ artifacts/               # 실제 모델 바이너리, Git 제외
├─ configs/                    # 재현 가능한 환경·모델·RAG 설정
├─ docs/                       # 요구사항·API·DB·회의·근거·보고서
├─ infra/                      # Docker·Nginx·배포 설정
├─ scripts/                    # 팀 공통 실행 명령
├─ tests/                      # 단위·통합·E2E·의료안전 테스트
└─ outputs/                    # 실행·렌더·모델 결과, Git 제외
```

`app/`가 정식 백엔드입니다. `src/backend/`는 초기 프로토타입 테스트가 남아 있어 당장 삭제하지 않지만 신규 API를 추가하지 않습니다.

## 3. 담당자별로 어디에 올리나요?

| 담당 | 작업 | 올릴 위치 | 같이 올릴 것 |
| --- | --- | --- | --- |
| 세준(PM·QA) | 요구사항·정책·결정 | `docs/` | 변경 이유와 완료 기준 |
| 세준(PM·QA) | 통합·의료안전 테스트 | `tests/` | 해당 요구사항 ID |
| 준혁(AI·데이터) | 전처리 코드 | `src/ml/preprocessing/` | `data/metadata/` 변경과 테스트 |
| 준혁(AI·데이터) | 공통 모델 코드 | `src/ml/modeling/`, `evaluation/` | 설정·재현 명령 |
| 준혁(AI·데이터) | 개별 모델 실험 | `experiments/diabetes_incidence/.../<experiment_id>/` | `experiment.json`, `pipeline.py`, `README.md` |
| 준혁(AI·데이터) | RAG 코드·근거 목록 | `src/rag/`, `docs/` | 출처 URL·확인일·안전 기준 |
| 빛샘(BE·DB·인프라) | API | `app/apis/v1/`, `app/dtos/` | 서비스 코드·API 문서·테스트 |
| 빛샘(BE·DB·인프라) | 정책·DB | `app/services/`, `repositories/`, `models/` | 마이그레이션·ERD·테스트 |
| 빛샘(BE·DB·인프라) | Redis·Worker·배포 | `ai_worker/`, `infra/`, `scripts/` | 환경변수명·장애/재시도 테스트 |
| 수인(FE·UI/UX) | 화면·스타일·API 연결 | `src/frontend/` | 상태별 화면과 접근성 확인 |
| 공통 | 테스트 | `tests/` | 정상·예외·권한·의료안전 시나리오 |

## 4. 데이터 파일 저장 위치

| 파일 | 위치 | Git |
| --- | --- | --- |
| KLoSA ZIP | `data/raw/klosa/` | 금지 |
| KLoSA `.sav` | `data/interim/source_extract/klosa/` | 금지 |
| KLoSA 원본 코드북 | `data/raw/klosa/codebooks/` | 금지 |
| KNHANES ZIP | `data/raw/knhanes/` | 금지 |
| KNHANES `.sav` | `data/interim/source_extract/knhanes/<연도>/` | 금지 |
| 작업 중 전처리본 | `data/interim/<작업명>/` | 금지 |
| 팀 공통 최종 전처리본 | `data/processed/official_v1/` | 금지 |
| 변수명·단위·결측·라벨·코호트 기준 | `data/metadata/` | 허용 |
| 원본을 재생성하는 전처리 코드 | `src/ml/preprocessing/` | 허용 |

KLoSA의 `w*`는 원자료, `str*`는 구조변환자료, `Lt*`는 라이트 버전입니다. 원본 파일명은 바꾸지 않습니다.

## 5. 모델을 갈아 끼워 조립하는 방법

### 5-0. 운영체제별 실행 원칙

팀 공통 기준은 `uv run python -m src.ml.experiments.runner`이며 Windows와 macOS에서 동일하게 사용할 수 있습니다.

| 환경 | 권장 실행 방식 |
| --- | --- |
| Windows PowerShell | `.\scripts\ml-experiment.ps1 <명령>` |
| macOS Terminal | `bash scripts/ml-experiment.sh <명령>` |
| Windows·macOS 공통 | `uv run python -m src.ml.experiments.runner <명령>` |

`.ps1`은 C++ 파일이 아니라 Windows PowerShell 스크립트입니다. macOS 사용자는 `.sh` 또는 공통 Python 명령을 사용합니다. 두 운영체제 모두 저장소 루트에서 실행합니다.

### 5-1. 새 실험 폴더 만들기

Windows PowerShell:

```powershell
.\scripts\ml-experiment.ps1 new rf_25features_v001 -Kind candidate -Owner "양준혁"
```

macOS Terminal:

```bash
bash scripts/ml-experiment.sh new rf_25features_v001 --kind candidate --owner "양준혁"
```

공통 명령:

```bash
uv run python -m src.ml.experiments.runner new rf_25features_v001 --kind candidate --owner "양준혁"
```

종류는 다음 중 하나입니다.

- `baseline`: Logistic Regression 등 비교 기준
- `candidate`: Random Forest·XGBoost 등 개별 후보
- `ensemble`: Soft Voting·Stacking 등 결합 모델

### 5-2. 팀원이 수정할 파일

```text
experiments/diabetes_incidence/candidates/rf_25features_v001/
├─ experiment.json     # 데이터·담당자·평가지표·스키마
├─ pipeline.py         # 학습·검증·테스트 및 artifact 생성
└─ README.md           # 가설·변수·결과·결론
```

### 5-3. 공통 조립·실행

Windows PowerShell:

```powershell
.\scripts\ml-experiment.ps1 validate
.\scripts\ml-experiment.ps1 run rf_25features_v001
.\scripts\ml-experiment.ps1 leaderboard
```

macOS Terminal:

```bash
bash scripts/ml-experiment.sh validate
bash scripts/ml-experiment.sh run rf_25features_v001
bash scripts/ml-experiment.sh leaderboard
```

운영체제와 관계없이 `uv run python -m src.ml.experiments.runner <명령>`으로도 동일하게 실행할 수 있습니다.

- 실행 결과: `outputs/ml/<experiment_id>/<run_id>/`
- 리더보드: `experiments/diabetes_incidence/leaderboard.csv`
- 통과 후보 등록: `.\scripts\ml-experiment.ps1 register-candidate <run_dir>`
- 후보 manifest: `models/registry/diabetes_incidence/candidates/`

후보 등록은 운영 활성화가 아닙니다. 승인된 모델만 `models/registry/diabetes_incidence/active.json`과 웹 환경변수에 연결합니다.

## 6. 모델 공통 판정 기준

- 문제: KLoSA 다음 인접 조사에서의 신규 당뇨 진단 이진분류
- 동일 참여자가 Train·Validation·Test에 중복되지 않게 분리
- 전처리 통계와 임계값은 Train·Validation에서만 결정
- Test는 마지막 평가에만 사용
- 1차 비교지표: Recall
- 운영 제약: 실험 manifest의 `minimum_specificity` 확인
- 함께 보고: Specificity, AUROC, AUPRC, F1, Brier, 혼동행렬
- 서로 다른 분할·입력 스키마의 점수는 같은 리더보드 순위로 단정하지 않음
- 승인 전 결과는 사용자에게 개인 발병확률·진단으로 표시하지 않음

## 7. 기능별 작업 조립 규칙

| 기능 | 팀원이 넣는 곳 | 자동·공통 확인 |
| --- | --- | --- |
| API | `app/apis/v1` + `dtos` | OpenAPI·API 테스트 |
| DB | `app/models` + migrations | 마이그레이션·repository 테스트 |
| 서비스 정책 | `app/services` | 단위·의료안전 테스트 |
| 비동기 AI | `ai_worker` | Redis 상태·실패·재시도 테스트 |
| 화면 | `src/frontend` | API 계약·접근성·E2E 테스트 |
| 전처리 | `src/ml/preprocessing` | 메타데이터·누수·분리 검사 |
| 모델 | `experiments/.../<id>` | manifest·공통 리더보드 |
| 운영 모델 | `models/registry` | checksum·버전·승인 게이트 |
| RAG | `src/rag` | 출처 반환·복약/진단 차단 테스트 |
| 배포 | `infra`, `docker-compose.yml` | Docker 상태·환경변수 검사 |

## 8. 올리면 안 되는 것

- KLoSA·KNHANES·KoGES·AIHub 원본 또는 가공된 개인 단위 데이터
- `.env`, API 키, 비밀번호, 개인정보
- `.joblib`, `.pkl`, `.pt`, `.onnx` 모델 바이너리
- `outputs/`, `tmp/`, 로컬 DB와 로그
- 노트북의 대용량 셀 출력과 재현되지 않는 수동 결과

PR에는 코드·설정·메타데이터·테스트·README만 포함하고, 데이터와 모델은 재생성 또는 외부 저장 위치를 기록합니다.

## 9. 최근 작업을 새 구조에 넣는 위치

| 최근 작업 | 새 표준 위치 | 처리 기준 |
| --- | --- | --- |
| KLoSA·KNHANES 공식 전처리 코드 | `src/ml/preprocessing/` | 메타데이터 변경과 함께 PR |
| 공식 전처리 CSV | `data/processed/official_v1/` | 로컬 공유, Git 금지 |
| 변수 레지스트리·코호트·품질 규칙 | `data/metadata/` | Git 공유 |
| KLoSA 기본 8개 XGBoost 실험 | `experiments/diabetes_incidence/candidates/<id>/` | 공통 manifest로 변환 후 실행 |
| KLoSA 25개 변수 Random Forest 실험 | `experiments/diabetes_incidence/candidates/<id>/` | 동일 공통 분할 재검증 후 비교 |
| Soft Voting·Stacking 실험 | `experiments/diabetes_incidence/ensembles/<id>/` | 단일 후보와 같은 스키마 사용 |
| 개발용 예측 Provider | `app/prediction/` | 승인 전 결과 비공개 유지 |
| 실제 모델 비동기 추론 | `ai_worker/` + `src/ml/inference/` | Redis 최소 상태·DB 지속 이력 |
| 실제 웹 MVP | `app/` + `src/frontend/` | `src/backend/`에 신규 기능 추가 금지 |

Draft PR이나 `tmp/worktrees/` 안에서 진행 중인 실험 파일은 임의 복사하지 않습니다. 해당 PR을 정리할 때 코드·설정·README만 위 표준 위치로 옮기고, 생성 결과와 모델 바이너리는 `outputs/`에 남깁니다.
