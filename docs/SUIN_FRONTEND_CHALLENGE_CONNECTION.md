# 수인 프론트엔드와 숲 챌린지 연결

## 가져온 버전과 범위

- 원본: `AI-HealthCare-05/AH_05_02`, `codex/fe-ui-layout-polish`
- 확인한 커밋: `1c021e83e1cd1864f8f502809ab6c400a666e833`
- 작성자/일자: `in2su-code`, 2026-09-07
- 제목: `feat(fe): refresh service intro and harden account result flows`
- 원격 브랜치를 직접 확인하고 해당 커밋의 `index.html`, `app.js`, `styles.css`, 이미지 40개를 `src/frontend/suin/`에 분리했다. 기존 `/` 화면, 게임 파일, 의료 모델은 교체하지 않았다.

## 사용자 흐름

1. 같은 서버의 `/forest`에서 **로그인하고 챌린지 설정하기**를 누른다.
2. `/service?returnTo=forest-challenges`에서 수인님의 최신 로그인 화면이 열린다. 비밀번호는 사용자가 직접 입력한다.
3. 실제 계정 프로필과 건강정보 동의를 서버에서 읽는다. 미완료 동의와 이용 가능 확인은 사용자가 직접 진행한다.
4. `GET /api/v1/challenge-v2/today`로 현재 동의, 적합성, 미확인 의료 안내를 서버에서 다시 확인한다. 이 읽기 요청은 챌린지를 배정하거나 건강 기록을 만들지 않는다.
5. 허용된 경우 `/forest#daily-settings`로 돌아간다. 사용자가 제한 조건, 난이도, 사진 동의를 직접 확인한 뒤 설정을 저장한다.
6. 완료 기록은 실제 수행 후 사용자가 직접 입력한다. 숲 체험 당근과 계정 챌린지 보상은 별도로 표시한다.

로그인·설정·실제 수행 기록을 대신 생성하는 자동 가입이나 가짜 건강정보는 사용하지 않는다. 시험 로그인 계정도 자동 생성하지 않는다.

## 연결부 변경

- FastAPI `app.main`의 `/service`가 복사본을 제공한다. 모든 정적 경로는 `/static/suin/`, API는 기존 `/api/v1/`를 사용한다.
- 로그인과 숲이 같은 호스트·포트를 사용하므로 HttpOnly refresh cookie를 공유한다. `localhost`와 `127.0.0.1`를 섞거나 토큰을 URL/브라우저 저장소로 전달하지 않는다.
- `returnTo`는 정확히 `forest-challenges`만 허용한다. 외부 URL과 임의 경로는 무시한다.
- 원본의 `/users/me/profile`은 현재 서버가 실제 제공하는 `PATCH /users/me`에 연결했다. 생년월일·성별의 사용자 입력 payload는 동일하다.
- 복사본에서는 로컬 preview fixture를 비활성화했다. 로그인 후 건강검진/예측을 먼저 생성하지 않고 서버의 챌린지 이용 가능 여부만 확인한다.
- 현재 서버의 챌린지 연령 기준은 만 19세 이상이다. 가입 연령과 혼동하지 않도록 안내를 맞췄으며 서버 정책은 변경하지 않았다.
- 복사본의 하드코딩된 Kakao SDK 키 포함 스크립트는 제외했다. 지도 SDK를 활성화하지 않으며 기존 API·텍스트 의료기관 안내를 유지한다. 이 연결 작업은 별도의 지도 키 설정이나 의료기관 기능의 운영 승인을 포함하지 않는다.
- 토큰 만료 시 같은 호스트의 refresh cookie로 한 번 갱신한다. 인증 서버 장애를 로그아웃으로 오인하거나 저장 불가능한 설정 폼을 보여주지 않는다.
- 잘못된 refresh cookie의 명시적 `400 / Provided invalid token.`은 로그인 필요로 안내한다. 그 외 400·422·503 오류는 연결 장애로 유지하며 설정·플랜 요청을 진행하지 않는다.
- 숲 service worker는 `/forest`에 등록된다. 오프라인 shell은 정확히 `/forest` navigation의 성공·비redirect 응답만 저장한다. `/service` 등 다른 navigation이나 오류 응답은 숲 shell을 덮어쓰지 않는다. 조회·정리는 숲 자체 캐시에 한정하며 같은 origin의 다른 앱 캐시는 지우지 않는다.

## 개인정보 닉네임과 숲 연결

- 닉네임의 원본은 `GET /api/v1/users/me`의 `name`이다. 메인 MVP `/service`의 마이페이지 → 개인정보 수정에서만 닉네임을 입력하며, 기존 `PATCH /api/v1/users/me` 계약(선택 입력, 2~20자)을 사용한다. 실명 입력은 요구하지 않는다. 처음부터 이름이 없으면 빈 값을 유지할 수 있지만, 이미 저장한 이름의 삭제는 현재 서버 계약에서 지원하지 않는다. 닉네임만 수정한 경우 기존 생년월일·성별 값은 그대로 유지한다.
- 숲의 이름 수정 안내는 고정 경로 `/service?account=profile`을 연다. 이 경로는 동일 출처 HttpOnly refresh cookie로 세션을 확인한 뒤 계정 프로필만 읽고 편집창을 연다. 비로그인은 사용자가 직접 로그인한 뒤 연다. 건강정보 동의·적합성·챌린지 상태를 생성하거나 허용하지 않으며, 이름 수정 때문에 건강정보를 입력하도록 요구하지 않는다.
- 저장이 성공하면 다른 탭의 재조회를 위해 `gandang-account-profile-revision` localStorage 키에 현재 시각만 기록한다. 이름·생년월일·계정 번호·토큰은 브라우저 저장소나 URL에 전달하지 않는다. 저장소 접근이 차단되어도 실제 계정 저장 성공을 실패로 바꾸지 않는다.
- 기존 `/`의 숲 아바타 편집에서도 별도 이름 입력을 제거하고 메인 개인정보 링크로 통일했다. 아바타 코디 저장은 이름 없이 헤어·상의·액세서리만 전송한다. 숲으로 돌아가기는 고정 `/forest` 경로이며 챌린지 이용 허용을 의미하지 않는다.
- `node --test tests/suin-profile.test.cjs`는 실제 계정·DB·네트워크 쓰기 없이 메모리 내 UI 모의 객체로 로그인 복원, 비로그인/서버 장애, 이름 저장·길이 검증, 저장 실패, 개인정보 없는 탭 갱신, 구형 화면 중복 입력 제거를 검사한다.

## 실행 및 검증

저장소 루트에서 기존 DB/Redis 설정을 유지하고 `app.main:app` 서버를 실행한다. 이미 실행 중인 서버가 자동 재시작 모드가 아니라면 `/service` 추가 후 서버 재시작이 필요하다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
node --test tests/challenge-settings.test.cjs tests/suin-forest-auth.test.cjs
node --test tests/forest-service-worker.test.cjs
.\.venv\Scripts\python.exe -m unittest tests.test_suin_frontend_route -v
```

브라우저에서는 해당 서버와 같은 호스트·포트의 `/service?returnTo=forest-challenges`를 연다. 실제 실행 포트가 8000이 아니면 기존 숲 주소의 호스트·포트를 그대로 사용한다. 승인되지 않은 운영 챌린지는 capabilities 설정에 따라 계속 비활성 상태로 유지한다.

회귀 검증 범위: 고정 복귀 경로, 비로그인 화면, 현재 서버 프로필 계약, 누락 동의·적합성, 기진단·긴급/당일 증상·연령 차단, 서버 401/403/503 차단, 토큰 만료의 단일 재시도, 정적 자산 경로와 임베디드 지도 키 미포함. 실제 사용자 로그인·건강 동의·챌린지 저장은 사용자의 직접 입력 후 확인해야 한다.

2026-09-07 확인: Node 회귀 테스트 16개와 실제 ASGI 경로 테스트 2개 통과. ASGI 검증은 lifespan/DB 초기화를 실행하지 않고 `/service`·정적 자산 200, 비로그인 refresh·챌린지 조회 401을 확인했다. Python Ruff 검사·포맷 검사와 두 JavaScript 구문 검사도 통과했다.
