# 데일리 뭐하징 Daily Task (8월 25일) — 세준

## 📝 목표 💻

- 전날 완성한 MVP를 Sprint 3 공통 개발 기준선으로 확정한다.
- 필수·확장·개발용·제외 기능의 범위를 명확히 한다.
- 실제 모델 연동에 필요한 모델·API·DB·화면 계약과 QA 기준을 완성한다.
- Git Flow와 Draft PR의 병합 순서를 정리한다.

## 뭐 했지⁉️

- 요구사항 정의서를 v2.1로 갱신하고 현재 MVP·확장 기능·개발용 기능·제외 범위를 다시 구분했다.
- Sprint 3 기능 구현 백로그와 P0·P1 우선순위 및 완료 정의를 작성했다.
- 모델 입력 8개 특성, `/api/v1/prediction-jobs`, 비동기 상태, DB 저장 필드, 화면 표시와 오류 처리를 하나의 계약으로 통일했다.
- 승인 전 개인 발병확률·위험 범주·위험요인 비공개 원칙과 기진단자 예측 차단 기준을 반영했다.
- Draft PR #2·#4·#8·#11을 병합 가능·수정 필요·중복 검토·보류로 판정하고 권장 병합 순서를 정리했다.
- 통합 PR #2의 기준 브랜치를 `develop`으로 변경했다.
- 실제 모델 Artifact Provider와 E2E 통합 작업을 GitHub Issue #12로 분리했다.
- 저장소 구조와 팀원별 파일 제출 위치를 확정했다.
- 8월 26일 실제 모델 연동 QA 체크리스트를 작성했다.
- 전체 테스트 40건과 Ruff 검사를 통과했다.

## 산출물

- [요구사항 정의서 v2.1](REQUIREMENTS.md)
- [Sprint 3 기능 구현 백로그](SPRINT3_BACKLOG.md)
- [모델–API–DB–화면 공통 입출력 계약](MODEL_WEB_INTEGRATION_CONTRACT.md)
- [Draft PR 점검 결과](PR_AUDIT_20260825.md)
- [실제 모델 연동 QA 체크리스트](MODEL_INTEGRATION_QA_20260826.md)
- [저장소 구조 및 파일 제출 가이드](REPOSITORY_STRUCTURE_GUIDE.md)
- [GitHub Issue #12](https://github.com/AI-HealthCare-05/AH_05_02/issues/12)

## 다음 작업

- 팀원 리뷰를 받아 PR #2를 `develop`에 병합한다.
- 공통 분할로 재현된 모델 artifact와 전처리기를 전달받는다.
- Artifact Provider·Redis Worker·DB·화면의 실제 모델 E2E를 검증한다.

