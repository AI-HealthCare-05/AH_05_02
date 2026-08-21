# SHARE DOCUMENTS 반영 점검 — 2026-08-21

## 기준 산출물

- [요구사항 정의서 v2.0](https://drive.google.com/drive/u/0/folders/124dzMvTaU4oejNn9H7GxvYDJjtKzHFti)
- [와이어프레임](https://www.figma.com/design/GgsFZ60n8nwxkmIdTRcyHf/%EB%A7%8C%EC%84%B1%EC%A7%88%ED%99%98-%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C-%EC%98%88%EC%8B%9C?node-id=45-2&p=f)
- [API 명세서 v2](https://drive.google.com/drive/u/0/folders/11SEANDSx0kPvITSX-xp_vuidpPNDU6xM)
- [ERD V6](https://dbdiagram.io/d/%EB%A7%8C%EC%84%B1%EC%A7%88%ED%99%98_ERD_V6-6a8505586440800f5299de3f)
- 이번 주 Notion 페이지는 현재 연결 계정에서 열리지 않아, 위 SHARE DOCUMENTS와 저장소 주간 점검 문서를 기준으로 대조했다.

## 이번 반영 내용

| 영역 | 반영 내용 | 구현 위치 |
| --- | --- | --- |
| 개인정보 최소수집 | 이름·전화번호를 신규 가입 필수 항목에서 제거하고 선택값으로 변경 | `app/dtos/auth.py`, `app/models/users.py`, 가입 화면 |
| 대상 구분 | 만 19세 이상 서비스, 40세 이상 주 타깃, 활성 모델 연령 범위를 각각 분리 | 적합성 응답의 `service_eligible`, `target_segment`, `model_eligible` |
| 건강정보 이력 | 검진 이력 조회와 예측 전 정정 API 제공, 예측에 사용된 기록은 덮어쓰기 금지 | `PATCH /api/v1/health-checkups/{id}` |
| 비동기 분석 UX | 입력 보존, 실패 안내, 입력 확인, 동일 검진 재시도 상태 구현 | Figma 실패 화면을 반영한 결과 화면 |
| 사용자 피드백 | 예측·추천·서비스 맥락별 별도 피드백 엔터티 및 API 추가 | `feedbacks`, `POST/GET /api/v1/feedback` |
| 의료 안전 | 검증 전 확률·개선율 비공개, 기진단·경고증상 차단, 고위험 안내 우선 | 예측·적합성·챌린지 API 및 화면 |
| 접근성 | 18px 이상 기본 글자, 44px 조작 영역, 키보드 포커스, 색 외 텍스트 병행 | `src/frontend` |

## API·ERD 정합성

- `HealthCheckup 1:N Prediction`을 허용하고 최신 결과는 `predicted_at`, `id` 역순으로 판별한다.
- 위험도 변화값은 저장 컬럼을 만들지 않고 필요 시 조회 계산한다. 검증 전에는 사용자에게 개선율로 노출하지 않는다.
- 4주 챌린지는 `ChallengeCycle`로 분리하고 최대 3개 챌린지를 묶는다.
- 의료기관 안내는 `FollowUpAction.trigger_source`와 `trigger_entity_id`로 발생 위치를 기록한다.
- 피드백은 운영 데이터와 분리된 `Feedback` 엔터티에 저장해 모델 정답이나 학습 라벨로 자동 사용하지 않는다.

## 후속 작업

다음 항목은 이번 Sprint의 안전한 핵심 사용자 흐름 완료 후 별도 Issue로 진행한다.

- 비밀번호 재설정과 계정 탈퇴 후 30일 삭제 배치
- 승인된 모델의 임계값·성능·설명 가능성 검증 및 Model Registry 연동
- 위험 추이/변화 API와 검증된 대시보드 시각화
- EC2 TLS, 운영 부하시험, P95 성능 기준 검증
- 근거 문서가 확정된 뒤 RAG 답변과 인용 출처 표시
