# 작업 창구 4/5 — 서비스 기반·연동

## 목적

화면·AI·데이터를 실제 서비스로 연결하는 기반, 배포 및 운영 변경을 한 곳에서 추적한다.

## 담당과 브랜치

- 담당: 박빛샘 (`qlctoa`)
- 브랜치: `codex/platform-rag-auth-followup-20260914`
- 병합 대상: `develop`
- 선행 작업: PR #61·PR #62

## 포함 범위

- FastAPI REST API
- JWT 인증·권한·개인정보 동의 관리
- 서비스 DB·ORM·마이그레이션
- Redis Stream·AI Worker·비동기 예측
- Model Provider·Artifact 로딩·결과 저장
- RAG·LLM·근거 문서·건강교육·퀴즈
- OpenAI Vision·Clova OCR·의료기관 검색 등 외부 API
- 웨어러블·건강검진 업로드 API
- 챌린지·리포트·게임·당근의 숲 API
- Docker·Docker Compose·Nginx
- AWS EC2·환경변수·Secret 관리
- GitHub Actions·CI/CD
- 단위·통합·E2E·Smoke·장애 시나리오 테스트
- 로깅·상태 확인·오류 응답·모니터링

## 작업 규칙

- API 키와 비밀번호는 환경변수로 관리한다.
- `.env.example`에는 변수명만 기록한다.
- RAG 답변은 검색 근거와 원문 출처를 함께 제공한다.
- API 변경 시 OpenAPI·호출 화면·계약 테스트를 함께 수정한다.
- 외부 API 실패를 데모 성공으로 자동 위장하지 않는다.

## 완료 체크리스트

- [ ] 인증·동의·권한 계약 확인
- [ ] RAG 의미 검색·퀴즈·출처 응답 검증
- [ ] Redis·Worker·Artifact 실패 시나리오
- [ ] 외부 API 오류·재시도·안전 응답
- [ ] AWS Secret·Artifact 공급 방식 확인
- [ ] Health·Ready·로그·모니터링 확인
- [ ] 통합·E2E·Smoke·CI 테스트 통과
