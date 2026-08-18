# 프로젝트 기술 스택 가이드

## 1. 문서 목적

이 문서는 AI 헬스케어 파이널 프로젝트의 기술 선택 기준과 팀 적용 후보를 정리한 문서다.

- 모든 기술을 의무적으로 사용하는 것은 아니다.
- 같은 역할을 하는 기술은 하나를 선택해 사용한다.
- 최종 선택은 구현 난이도, 팀 숙련도, 배포 환경을 고려해 결정한다.
- 공식 배포 세션과 다른 구성을 선택할 경우 멘토와 사전에 협의한다.

---

## 2. 프로젝트 적용안 요약

| 영역 | 우선 적용 기술 | 비고 |
|---|---|---|
| 버전 관리 | Git, GitHub | Issue·feature 브랜치·PR 사용 |
| CI/CD | GitHub Actions | Lint·Test·Build 자동화 |
| Python 품질 | Ruff, Mypy | 포맷·정적 검사 |
| 테스트 | pytest, pytest-asyncio, Coverage | 단위·비동기·커버리지 테스트 |
| 데이터 처리 | NumPy, Pandas, Parquet | 전처리 데이터는 Parquet 권장 |
| 예측 모델 | scikit-learn | 표 형식 만성질환 데이터 분류에 우선 적용 |
| 모델 설명 | SHAP | 주요 영향요인 설명에 활용 |
| 실험 관리 | MLflow | 필요 시 실험 조건·결과 기록 |
| 백엔드 | FastAPI, Uvicorn | AI 추론 및 REST API 제공 |
| 데이터베이스 | PostgreSQL | 사용자·건강기록·예측·챌린지 저장 |
| ORM | SQLAlchemy | Tortoise ORM과 중복 사용하지 않음 |
| DB 드라이버 | asyncpg | PostgreSQL 비동기 연결 |
| 마이그레이션 | Alembic | SQLAlchemy 스키마 버전 관리 |
| 프론트엔드 | React, TypeScript, Vite | SPA 기반 사용자 화면 |
| 서버 상태 | TanStack Query | API 데이터 조회·캐싱 |
| 클라이언트 상태 | Zustand | 필요한 경우에만 사용 |
| API 통신 | Axios | 백엔드 API 호출 |
| 입력 검증 | Zod | 건강 설문 폼 검증 |
| UI | Tailwind CSS, shadcn/ui | 빠르고 일관된 화면 구성 |
| 컨테이너 | Docker, Docker Compose | 개발·배포 환경 통일 |
| 백엔드 배포 | AWS EC2 | 기업 안내 배포 환경 |
| 프록시 | Nginx | 운영 배포 시 HTTPS·리버스 프록시 |
| 프론트 배포 | Vercel 또는 EC2 | 공식 배포 방식 확인 후 하나로 결정 |

---

## 3. 공통 개발 도구

| 기술 | 용도 | 적용 기준 |
|---|---|---|
| Git | 변경 이력과 브랜치 관리 | 필수 |
| GitHub | 저장소·Issue·PR·리뷰 | 필수 |
| GitHub Actions | CI/CD 자동화 | 필수 |
| Ruff | Python 포맷 및 Lint | 필수 |
| Mypy | Python 정적 타입 검사 | 권장 |
| pytest | Python 테스트 | 필수 |
| pytest-asyncio | 비동기 API 테스트 | 비동기 기능에 적용 |
| Coverage | 테스트 커버리지 측정 | 권장 |

### 협업 원칙

- `main`과 `develop`에 직접 Push하지 않는다.
- 기능은 Issue와 feature 브랜치에서 작업한다.
- Pull Request에서 테스트와 리뷰를 거쳐 병합한다.
- 기능 변경 시 관련 테스트와 문서를 함께 수정한다.

---

## 4. AI·데이터 기술

### 4-1. MVP 적용 기술

| 기술 | 용도 |
|---|---|
| NumPy | 수치 연산 |
| Pandas | 표 형식 데이터 전처리·분석 |
| Parquet | 전처리 데이터의 효율적인 저장 |
| scikit-learn | 분류 모델 학습·평가·전처리 파이프라인 |
| SHAP | 예측 주요 영향요인 설명 |
| MLflow | 실험 조건·성능·모델 버전 기록 |

### 4-2. 모델 후보

- Logistic Regression: 설명 가능한 기준 모델
- Random Forest: 비선형 관계를 반영하는 비교 모델
- XGBoost 또는 LightGBM: 표 형식 데이터의 주요 성능 모델

최소 두 개 이상의 모델을 동일한 데이터 분할과 평가지표로 비교한다.

### 4-3. RAG·LLM 선택 구현

| 기술 | 용도 | 적용 판단 |
|---|---|---|
| LangChain | 문서 검색과 LLM 응답 흐름 구성 | 선택 |
| sentence-transformers | 문서 임베딩 | 선택 |
| FAISS | 로컬 벡터 검색 | ChromaDB와 하나 선택 |
| ChromaDB | 문서·메타데이터 기반 벡터 저장 | FAISS와 하나 선택 |

RAG를 구현할 경우 답변에 검색 근거와 원문 출처를 함께 제공한다.

### 4-4. MVP 우선 제외 기술

다음 기술은 이미지 기반 식단 분석 또는 대규모 딥러닝이 확정될 때 검토한다.

- OpenCV, Pillow
- PyTorch
- YOLO
- ResNet, EfficientNet
- ONNX Runtime, TensorRT, NVIDIA APEX
- Vertex AI

현재 MVP가 표 형식 건강데이터 예측 중심이라면 위 기술을 선행 도입하지 않는다.

---

## 5. 백엔드·DB 기술

| 구분 | 기술 | 역할 |
|---|---|---|
| API 프레임워크 | FastAPI | 인증·건강기록·예측·챌린지 API |
| ASGI 서버 | Uvicorn | FastAPI 실행 |
| 데이터 검증 | Pydantic | 요청·응답 스키마 검증 |
| 데이터베이스 | PostgreSQL | 관계형 서비스 데이터 저장 |
| ORM | SQLAlchemy | Python 객체 기반 DB 접근 |
| 비동기 드라이버 | asyncpg | PostgreSQL 비동기 연결 |
| 마이그레이션 | Alembic | DB 스키마 변경 이력 관리 |
| 캐시·메시지 브로커 | Redis | 성능 또는 비동기 작업이 필요할 때 선택 |
| 리버스 프록시 | Nginx | 운영 트래픽 전달·HTTPS 구성 |

### 중복 선택 주의

- PostgreSQL과 MySQL 중 하나를 선택한다.
- SQLAlchemy와 Tortoise ORM 중 하나를 선택한다.
- SQLAlchemy를 사용하면 Alembic을 사용한다.
- Tortoise ORM을 사용하면 Aerich를 사용한다.
- PostgreSQL 비동기 구성에서는 `asyncpg`를 사용한다.
- MySQL 비동기 구성에서는 `asyncmy`를 사용한다.

### 현재 프로젝트 권장 조합

> FastAPI + PostgreSQL + SQLAlchemy + asyncpg + Alembic

---

## 6. 프론트엔드 기술

| 구분 | 기술 | 역할 |
|---|---|---|
| 언어 | TypeScript | 타입 안전한 UI 개발 |
| UI 라이브러리 | React | 컴포넌트 기반 화면 구현 |
| 빌드 도구 | Vite | 개발 서버와 프로덕션 빌드 |
| 패키지 관리 | npm | 의존성·스크립트 관리 |
| 서버 상태 | TanStack Query | API 조회·캐싱·동기화 |
| 클라이언트 상태 | Zustand | 로그인·화면 상태 등 필요 시 사용 |
| API 클라이언트 | Axios | HTTP 요청·오류 처리 |
| 폼 검증 | Zod | 건강정보 입력값 검증 |
| 스타일 | Tailwind CSS | 반응형 UI와 디자인 규칙 |
| UI 컴포넌트 | shadcn/ui | 접근성을 고려한 기본 컴포넌트 |
| 코드 품질 | ESLint, Prettier | 오류 검사·코드 형식 통일 |

### 상태 관리 기준

- 서버에서 가져오는 데이터는 TanStack Query로 관리한다.
- 화면 전역에서 공유해야 하는 클라이언트 상태만 Zustand로 관리한다.
- 한 화면 내부에서만 쓰는 값은 React 로컬 상태를 사용한다.

---

## 7. 인프라·배포 기술

| 기술 | 용도 | 적용 기준 |
|---|---|---|
| Docker | 애플리케이션 실행환경 패키징 | 필수 |
| Docker Compose | API·DB 등 다중 컨테이너 실행 | 필수 |
| AWS EC2 | 백엔드·모델 운영 서버 | 필수 후보 |
| AWS S3 | 대용량 파일·모델 아티팩트 저장 | 필요 시 적용 |
| Nginx | HTTPS·리버스 프록시 | 운영 배포 시 적용 |
| Vercel | 프론트엔드 자동 배포 | 공식 배포 방식과 협의 후 결정 |

### 권장 배포 구조

```text
사용자
  └─ React 프론트엔드
       └─ Nginx 또는 Vercel
            └─ FastAPI API
                 ├─ 예측 모델
                 ├─ PostgreSQL
                 └─ RAG·LLM(선택)
```

---

## 8. 기술 선택 체크리스트

- [ ] 공식 배포 세션과 호환되는가?
- [ ] 팀원이 학습하고 구현할 수 있는 난이도인가?
- [ ] 같은 역할의 기술을 중복으로 선택하지 않았는가?
- [ ] MVP 필수 기능에 실제로 필요한 기술인가?
- [ ] 테스트와 배포 방법을 설명할 수 있는가?
- [ ] 기술 선택 이유와 대안을 문서화했는가?
- [ ] API 키와 비밀번호를 환경변수로 관리하는가?
- [ ] 원본 의료 데이터와 개인정보를 Git에서 제외했는가?
- [ ] 예측 결과를 진단·처방으로 표현하지 않는가?

---

## 9. 최종 결정이 필요한 항목

| 항목 | 선택지 | 팀 결정 |
|---|---|---|
| 1차 예측 프레임워크 | scikit-learn / PyTorch |  |
| 데이터베이스 | PostgreSQL / MySQL |  |
| ORM·마이그레이션 | SQLAlchemy·Alembic / Tortoise·Aerich |  |
| 벡터 검색 | FAISS / ChromaDB / 미구현 |  |
| 실험 관리 | MLflow / 파일 기반 기록 |  |
| Redis | 적용 / 미적용 |  |
| 프론트 배포 | Vercel / EC2 |  |
| 이미지 분석 | MVP 포함 / 제외 |  |

---

## 10. 기술 선택 기록 양식

| 기술 | 선택 여부 | 선택 이유 | 대안 | 담당자 | 결정일 |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

