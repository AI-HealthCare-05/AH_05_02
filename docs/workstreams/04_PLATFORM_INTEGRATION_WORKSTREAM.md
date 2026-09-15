# 작업 창구 4/5 — 기반·연동

## 목적

기획·AI·학습 데이터·고객 화면을 실제 서비스로 연결하고 운영 DB, 배포 및 품질 기준을 관리한다.

## 담당과 브랜치

- 담당: 박빛샘 (`qlctoa`)
- 브랜치: `codex/platform-rag-auth-followup-20260914`
- 병합 대상: `develop`
- 선행 작업: PR #61·PR #62

## API·인증과 운영 DB

- FastAPI REST API와 `/api/v1` 공통 경로
- JWT Access·Refresh Token, 인증·권한·본인 데이터 소유권
- 동의 상태 확인과 철회 이후 신규 처리 차단
- 요청·응답 DTO, 표준 성공·오류 응답
- 사용자·동의·건강정보·예측·챌린지·리포트·게임 운영 DB
- ORM·Repository·마이그레이션·무결성·중복 요청 방지

> 2번의 DB는 AI 학습용 원천·가공 데이터이고, 이 영역의 DB는 실제 서비스 이용 기록을 저장하는 운영 DB다.

## AI·비동기·외부 연동

- Redis Stream·AI Worker·비동기 예측
- Model Provider·Artifact·전처리기·모델별 작업 분기·결과 저장
- `queued·running·succeeded·failed`, 재시도·시간초과·중복 방지
- 승인 문서와 임베딩 검색 기반 RAG·교육·퀴즈·출처 응답
- OpenAI Vision·Clova OCR·의료기관 검색 등 외부 API
- Apple Health·Android Health Connect·건강검진 업로드
- 사용자·모델·XAI·챌린지·리포트·게임·당근의 숲 기능별 API

## 실행·배포·품질

- Docker·Docker Compose·Nginx
- AWS EC2·모델/파일 저장소·환경변수·Secret 관리
- Windows·macOS와 로컬·고객 재현 환경
- GitHub Actions·CI/CD
- 단위·통합·E2E·Smoke·장애 시나리오 테스트
- Worker 미작동·배포 실패 테스트
- 로깅·오류 추적·`/health`·`/ready`·민감정보 로그 차단
- 장애 안내와 모델·서비스 롤백 기준

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
