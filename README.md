# 만성질환 생활습관 챌린지 웹서비스

공공 의료 데이터를 활용해 만성질환 위험을 예측하고, 건강지표 추적과 생활습관 챌린지를 제공하는 AI 헬스케어 웹서비스입니다.

> 본 서비스는 건강교육 및 위험 선별을 위한 프로젝트이며 의료진의 진단·처방을 대체하지 않습니다.

## 핵심 기능

### 필수 구현

- 만성질환 위험 예측 모델링
- 건강지표 추적 대시보드
- 생활습관 챌린지 생성·인증·달성률 관리

### 선택 구현

- 공식 건강지침 RAG 기반 예방 행동 추천
- CLOVA OCR 또는 이미지 모델을 활용한 식단 분석
- 챌린지 및 건강기록 알림
- sLLM과 vLLM 기반 자체 추론 서버 실험

## 역할 분담

| 역할 | 주요 책임 |
| --- | --- |
| PM·기획·문서·QA | 일정, 요구사항, 회의, 발표, 통합 테스트 |
| AI·데이터·RAG | 데이터 전처리, 예측 모델, SHAP, RAG, sLLM 실험 |
| 백엔드·DB·인프라 | FastAPI, 인증, DB, 모델 연동, Docker, EC2 |
| 프론트엔드·UI/UX | 건강정보 입력, 대시보드, 챌린지, 결과 시각화 |

## 프로젝트 구조

```text
.
├── .github/          # CI, Issue/PR 템플릿
├── configs/          # 모델·서비스 설정
├── data/             # 데이터 위치와 사용 안내
├── docs/             # 팀 룰, 회의록, API·설계 문서
├── experiments/      # 모델·RAG 실험 기록
├── models/           # 모델 메타데이터와 저장 위치 안내
├── notebooks/        # EDA와 빠른 검증
├── src/
│   ├── backend/      # FastAPI 애플리케이션
│   ├── frontend/     # 프론트엔드 애플리케이션
│   ├── ml/           # 예측 모델 학습·평가·추론
│   └── rag/          # 검색 증강 생성
└── tests/            # 자동 테스트
```

## 협업 문서

- [팀 룰](docs/TEAM_RULES.md)
- [기여 및 Git Flow](CONTRIBUTING.md)
- [프로젝트 작업 규칙](AGENTS.md)
- [요구사항 정의서 v2.0](docs/REQUIREMENTS.md)
- [서비스 대상·제외 범위 및 의료 안전 문구](docs/SERVICE_SCOPE_AND_SAFETY_COPY.md)
- [Sprint 2 요구사항 추적성·누락 QA](docs/TRACEABILITY_AND_GAP_QA_20260819.md)
- [Sprint 2 기능 구현 백로그](docs/SPRINT2_BACKLOG.md)

## 로컬 실행

```bash
uv python install 3.13
uv sync --all-groups --frozen
uv run uvicorn app.main:app --reload
```

API 문서 확인: `GET http://localhost:8000/api/docs`

## 환경변수

`.env.example`을 `.env`로 복사하고 필요한 값을 입력합니다. 실제 키가 들어 있는 `.env`는 커밋하지 않습니다.

## 배포 방향

- 애플리케이션: Docker
- 서버: Amazon EC2
- 생성형 AI: OpenAI API
- OCR: CLOVA OCR
- CI: GitHub Actions
