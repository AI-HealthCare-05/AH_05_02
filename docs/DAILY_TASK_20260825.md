# 오늘의 할일(Daily Task) — 8월 25일

## 오늘의 공통 목표

- 어제 완성한 MVP를 공통 개발 기준선으로 확정한다.
- 새 저장소 구조에 기존 작업을 배치하고 팀원별 파일 위치를 통일한다.
- 모델 실험·웹서비스·DB·화면의 연결 계약을 확정해 수요일 실제 연동을 준비한다.
- 진행 중인 Draft PR과 로컬 산출물을 중복 없이 정리한다.

---

## 박빛샘 — 정식 백엔드·DB 기준 정리

### 오늘 할 일

- 신규 백엔드 작업 위치를 정식 `app/` 기준으로 통일
- `PredictionJob`, `Prediction`, `RiskFactor`와 최신 마이그레이션 재점검
- AI Worker 결과에서 DB에 지속 보관할 최소 이력 확정
- 모델 버전·특성 스키마·임계값 버전 저장 위치 확인
- 기존 API·ERD 작업 파일을 새 폴더 가이드에 맞춰 정리

### 완료 기준

- 수정 또는 확인한 파일 경로 공유
- 모델 연동에 필요한 DB 필드와 미정 항목 목록 작성
- 수요일 Artifact Provider 연결을 위한 체크리스트 작성

---

## 양준혁 — 모델 실험 표준 구조 이관

### 오늘 할 일

- 기존 Logistic·RF·XGBoost·앙상블 실험을 `baseline/candidates/ensembles`로 분류
- 우선 이관할 RF 25개 변수 실험의 표준 폴더 생성
- `experiment.json`, `pipeline.py`, `README.md` 작성
- 참여자 단위 공통 분할과 데이터 누수 제외 기준 재확인
- 기존 점수와 공통 분할 재실행 점수를 구분해 기록

### 시작 명령

```powershell
.\scripts\ml-experiment.ps1 new rf_25features_v001 -Kind candidate -Owner "양준혁"
.\scripts\ml-experiment.ps1 validate
```

### 완료 기준

- 표준 실험 폴더 또는 PR 링크 공유
- 입력 변수·라벨·분할·임계값 선택 방법 기록
- 원본 데이터와 모델 바이너리가 PR에서 제외된 상태 확인

---

## 이수인 — MVP 화면과 정식 API 계약 대조

### 오늘 할 일

- 실제 화면 파일을 `src/frontend/` 기준으로 정리
- 가입·적합성·건강정보·예측·결과·챌린지·대시보드 화면별 API 확인
- 예측 상태값 `queued/running/succeeded/failed` 표시 방식 점검
- 승인 전 확률 비공개와 의료기관 안내 문구 확인
- 모바일·키보드·큰 글씨·명암 대비 보완 항목 정리

### 완료 기준

- 화면별 API·상태·오류 처리 체크표 공유
- 수요일 보완할 화면을 우선순위로 구분
- 프론트 작업 파일이 `src/frontend/` 밖에 남아 있지 않은지 확인

---

## 정세준 — 요구사항·백로그·통합 기준 확정

### 오늘 할 일

- 어제 구현한 MVP 기능을 요구사항과 Sprint 3 백로그에 반영
- 필수 기능·확장 기능·개발용 기능을 다시 구분
- 팀원별 폴더 책임과 제출 위치를 공지
- 모델·API·DB·화면의 공통 입출력 항목 작성
- Draft PR별 `병합 가능/수정 필요/중복/보류` 판정
- 수요일 실제 모델 연동 QA 체크리스트 작성

### 완료 기준

- 변경된 주간 계획과 오늘 과업 공유
- 저장소 구조 가이드 공유
- 각 팀원의 산출물 위치와 다음 담당자 전달 항목 확정
- 미정 사항을 GitHub Issue 또는 회의 안건으로 분리

---

## 오늘 확인할 공통 계약

- 모델 목적: KLoSA 다음 조사 신규 당뇨 진단 위험 선별
- 1차 지표: Recall, 단 Specificity 제약 함께 확인
- 데이터 분리: 참여자 단위 Train·Validation·Test
- 임계값: Validation에서만 선택
- 예측 상태: `queued/running/succeeded/failed`
- 모델 추적: 모델·특성 스키마·임계값 버전 저장
- 사용자 표시: 승인 전 개인 발병확률·위험 범주 비공개
- 기진단 사용자: 예측 제외 후 일반 건강 챌린지·의료 상담 안내
- 의료 안전: 진단·처방·복약 변경 추천 금지

## 제출 위치

| 산출물 | 위치 |
| --- | --- |
| 요구사항·결정·회의 결과 | `docs/` |
| 전처리 코드 | `src/ml/preprocessing/` |
| 변수·라벨·품질 기준 | `data/metadata/` |
| 모델 실험 | `experiments/diabetes_incidence/` |
| 백엔드·DB | `app/` |
| 비동기 추론 | `ai_worker/` |
| 프론트엔드 | `src/frontend/` |
| 테스트 | `tests/` |
| 실행 결과·모델 파일 | `outputs/` — Git 제외 |

## 회의 안건

- 실제 연동 후보 모델과 공통 재현 일정
- 모델 입력 스키마와 사용자 입력 화면의 차이
- Artifact Provider·Redis Worker·DB 저장 경계
- 수요일 실제 모델 연동 완료 기준

## 추가 논의사항

- Draft PR 간 중복 코드 정리 방식
- 승인 전 모델 결과의 화면 노출 범위
- 목요일 멘토링에서 시연할 안정적인 데모 범위

---

## 뭐 했지⁉️ — 정세준

- 요구사항 정의서를 v2.1로 갱신하고 MVP·확장·개발용·제외 기능을 다시 구분했다.
- Sprint 3 기능 구현 백로그와 완료 정의를 작성했다.
- 모델–API–DB–화면의 8개 입력 특성, 비동기 상태, 버전, 공개 범위, 오류 계약을 통일했다.
- Draft PR #2·#4·#8·#11의 병합 가능성·충돌·중복·선행조건과 권장 병합 순서를 정리했다.
- 수요일 실제 모델 Artifact Provider 연동 QA 체크리스트를 작성했다.
- 저장소 구조 가이드와 팀원별 제출 위치를 확정했다.
- 통합 PR #2의 기준 브랜치를 `develop`으로 변경하고, 실제 모델 연동 과업을 [GitHub Issue #12](https://github.com/AI-HealthCare-05/AH_05_02/issues/12)로 분리했다.

## 오늘 산출물

- [요구사항 정의서 v2.1](REQUIREMENTS.md)
- [Sprint 3 기능 구현 백로그](SPRINT3_BACKLOG.md)
- [모델–API–DB–화면 공통 입출력 계약](MODEL_WEB_INTEGRATION_CONTRACT.md)
- [Draft PR 점검 결과](PR_AUDIT_20260825.md)
- [실제 모델 연동 QA 체크리스트](MODEL_INTEGRATION_QA_20260826.md)
- [저장소 구조 및 파일 제출 가이드](REPOSITORY_STRUCTURE_GUIDE.md)
