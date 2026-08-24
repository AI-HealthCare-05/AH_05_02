# 간당간당 서비스 확장 구현 보고서

## 1. 구현 결과

기존 핵심 사용자 흐름(가입·동의·적합성·건강정보·미래 위험 선별·챌린지·대시보드)을 유지하면서 다음 7개 영역을 정식 `app/` API와 웹 화면에 연결했다.

1. 핵심 흐름 오류 메시지 개선: 입력 검증 오류를 필드별로 표시
2. 웨어러블: 연결 어댑터, 일일 요약, 활동 확인 챌린지 자동 기록
3. RAG: 승인 문서 검색, 답변별 원문 링크, 근거 부족·복약 변경 안전 분기
4. 주간 리포트/NLP: 수행 기록만 사용하는 결정형 요약과 PDF 내보내기
5. 가족·친구: 초대·공동 챌린지에 연결 해제·차단·공유 범위 관리 추가
6. CV/OCR: 실제 모델 연동 전 교체 가능한 개발 어댑터와 사용자 확인 단계
7. 웹 알림: 종류별 설정, 조용한 시간, 챌린지·주간 리포트 안내

## 2. 구현 경계

- 웨어러블은 Google Health Connect·Apple Health·제조사 OAuth를 흉내 내지 않는다. 현재 제공자는 `development_mock`, `file_import`뿐이다.
- RAG v1은 외부 LLM 없이 승인 문서의 키워드 검색과 검토 문구를 사용한다. 답변에 없는 사실을 생성하지 않는다.
- CV는 파일명 기반 개발 어댑터이며 실제 이미지 픽셀을 분석하지 않는다. `provider=development_mock`과 확인 필요 상태를 반환한다.
- OCR은 전달된 개발용 추출 초안에서 허용 필드만 남긴다. 주민번호 등 미허용 항목은 버리고 자동 저장하지 않는다.
- 알림은 웹 내부 표시만 제공한다. 문자·이메일·모바일 푸시는 발송하지 않는다.

## 3. 데이터베이스

마이그레이션 `4_20260824170000_wellness_extensions.py`에 다음 엔터티를 추가했다.

- `wearable_connections`, `wearable_daily_summaries`
- `food_analyses`, `ocr_drafts`
- `notification_preferences`, `in_app_notifications`

가족·친구 공유는 기존 `connections.sharing_scope`를 사용하며 현재 허용 값은 `challenge_status`뿐이다.

## 4. 검증

- Ruff lint 및 format 검사
- Python 전체 테스트 30개
- RAG 출처·복약 변경 거절 테스트
- 웨어러블 입력 범위 및 저장 계약 테스트
- CV·OCR 확인 전 상태와 개인정보 필드 제외 테스트
- 알림 설정 및 유효 PDF 헤더 테스트
- JavaScript 문법 검사

재현 명령:

```powershell
.venv\Scripts\ruff.exe check app src tests
.venv\Scripts\ruff.exe format app src tests --check
.venv\Scripts\pytest.exe -q
node --check src/frontend/app.js
```

## 5. 다음 교체 지점

- 실제 웨어러블: 제공자별 OAuth/동의/토큰 갱신 어댑터
- RAG: 승인 문서 인덱싱·하이브리드 검색·인용 범위 검증·평가 세트
- CV: 검증된 음식 분류 모델과 사용자 교정 데이터 계약
- OCR: CLOVA OCR 등 실제 제공자와 원문 이미지 보관·삭제 정책
- 알림: 사용자 별도 동의를 전제로 한 푸시 제공자

실제 제공자를 연결할 때도 기존 API 응답의 `provider`, `status`, `requires_user_confirmation`, `citations` 계약은 유지한다.

## 6. 전체 기능 MVP 실행

Docker 없이도 전체 흐름을 확인할 수 있도록 SQLite와 인프로세스 안전 추론을 사용하는 명시적 `DEMO_MODE`를 추가했다. 실행과 검증 방법은 `MVP_DEMO_GUIDE_20260824.md`를 따른다. 운영 기본값은 `DEMO_MODE=false`이며 MySQL·Redis·별도 Worker 구조는 유지한다.
