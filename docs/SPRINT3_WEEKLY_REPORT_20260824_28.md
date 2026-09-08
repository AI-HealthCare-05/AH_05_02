# Sprint 3 주간 결과 보고 — 2026-08-24~28

## 1. 목표 달성 현황

| 목표 | 결과 | 판정 |
| --- | --- | --- |
| 실행 가능한 MVP 기준선 확정 | 가입–예측–챌린지–대시보드와 안전 흐름 검증 | 완료 |
| 모델 실험 공통 구조 | 표준 폴더·계약·QA·3단계 RF 후보 확인 | 부분 완료 |
| API·DB·화면 통합 | 개발 Provider 기준 핵심 E2E 통과 | 부분 완료 |
| 의료 안전 유지 | 승인 전 비공개·기진단 분기·복약 차단 테스트 | 완료 |
| Docker·운영 배포 검증 | 현재 PC에 Docker CLI가 없어 증적 미확보 | 이월 |

## 2. 정세준 주간 과업

| 일자 | 계획 | 결과 |
| --- | --- | --- |
| 8/24 | MVP·의료 안전 흐름 검수 | 40개 테스트와 핵심 브라우저 흐름 확인 |
| 8/25 | 요구사항·백로그·폴더 책임 확정 | 요구사항 v2.1, 백로그, 저장소 가이드 작성 |
| 8/26 | 모델·API·DB·화면 계약 QA | 연동 계약·QA 체크리스트와 게임팩 범위 작성 |
| 8/27 | 멘토링·결정사항 준비 | 사전 보고·모델 결과·시연 질문 정리 |
| 8/28 예정 과업 | E2E·데모·릴리즈·취합 | 8/27 선행 완료: 47개 테스트, E2E 문서, 릴리즈 노트, 주간 보고 작성 |

## 3. 핵심 산출물

- [요구사항 정의서 v2.1](REQUIREMENTS.md)
- [Sprint 3 백로그](SPRINT3_BACKLOG.md)
- [모델–웹 연동 계약](MODEL_WEB_INTEGRATION_CONTRACT.md)
- [실제 모델 연동 QA](MODEL_INTEGRATION_QA_20260826.md)
- [저장소 구조 가이드](REPOSITORY_STRUCTURE_GUIDE.md)
- [멘토링 사전 보고](MENTORING_PRE_REPORT_20260827.md)
- [E2E·데모 시나리오](E2E_DEMO_SCENARIO_20260828.md)
- [릴리즈 노트](RELEASE_NOTES_20260828.md)
- [당근의 숲 Lite MVP](CARROT_FOREST_LITE_MVP.md)

## 4. 모델 결과

- 최대 Recall: 4단계 XGBoost 0.8103
- 균형 후보: 비가중 3단계 25개 변수 Random Forest
- Recall 0.8000, Specificity 0.4742, R/S 균형 0.6371
- 2단계 대비 Recall 2.56%p, Specificity 1.95%p 향상
- 독립 검증·확률 보정 전 개인 발병확률 비공개

## 5. 검증 결과

- 전체 pytest: 47 passed
- 핵심 E2E·게임: 25 passed
- Ruff: 통과
- Docker: 실행환경 부재로 미검증

## 6. 이월 항목

- 실제 모델 artifact·전처리기·checksum·롤백 후보 패키징
- Artifact Provider·Redis Worker·DB 실제 모델 E2E
- Docker·EC2 통합 실행 및 실패·재시도 증적
- 모바일·고령자 실사용성 테스트
- 멘토링 피드백의 요구사항·Issue 반영

## 7. 다음 Sprint 우선순위

1. 실제 모델 Provider 연결과 고정 입력 재현
2. Docker·EC2 배포 및 장애·롤백 검증
3. 사용자 테스트와 대시보드 정보 우선순위 조정
4. 당근의 숲 Beta의 DB 연동과 참여지표 수집
