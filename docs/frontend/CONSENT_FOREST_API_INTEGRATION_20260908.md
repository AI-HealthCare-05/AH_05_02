# 동의 철회·당근의 숲 API 연동 (2026-09-08)

## 적용 범위

- 마이페이지 `개인정보 설정`에서 건강정보 동의 상태 조회, 철회, 재동의 제공
- 철회 사용자는 계정과 일반 페이지를 계속 이용하고 신규 건강정보 저장·예측·4주 챌린지 생성만 차단
- 로그인 후 함께하기에서 활성 공동 챌린지 그룹을 선택해야 당근의 숲 진입 가능
- 숲·지갑·상점·보유 아이템·아바타·오브젝트를 서버 API에서 조회
- 퀘스트 기록, 그룹 보상, 아바타 기본 외형·닉네임, 구매·장착, 오브젝트 배치·회수를 API로 저장
- API 오류를 데모 `localStorage` 데이터로 대체하지 않음

## 사용 API

- `GET /api/v1/consents`
- `PATCH /api/v1/consents/{consent_id}/withdraw`
- `POST /api/v1/consents`
- `GET /api/v1/shared-challenge-groups`
- `GET|POST /api/v1/forest/spaces...`
- `GET /api/v1/forest/catalog`
- `PATCH /api/v1/forest/avatar`
- `GET /api/v1/wallet`
- `GET /api/v1/inventory-items`
- `GET /api/v1/inventory`
- `POST /api/v1/inventory/items/{item_id}/purchase`
- `GET /api/v1/avatar`
- `PUT /api/v1/avatar/equipment`
- `PUT /api/v1/user-challenges/{id}/logs/{date}`

## 인증 전달

현재 백엔드가 Bearer 인증을 사용하고 메인과 숲이 별도 문서이므로, 메인 화면에서 그룹을 선택할 때 토큰·사용자 ID·그룹 ID를 동일 탭의 `sessionStorage`에 최대 30분 저장한다. URL이나 `localStorage`에는 토큰을 넣지 않으며 로그아웃·401·만료 시 즉시 제거한다. HTTP-only 쿠키 기반 세션이 도입되면 이 임시 전달 방식을 쿠키로 교체한다.

## 서버 계약 대기

- `PATCH /api/v1/forest/spaces/{group_id}/slogan`은 현재 통합 코드에 없음. 프론트는 저장 성공으로 위장하지 않고 미연결 안내를 표시함.
- 게임 상점 장착 정보는 게임 API를 단일 기준으로 사용함. 숲 기본 헤어·의상·닉네임은 현재 Forest Avatar API 계약에 맞춰 저장함.
- 기존 건강정보·예측 결과의 보관·파기 세부 문구는 개인정보 처리방침 확정본과 함께 갱신 필요.

## 검증

- `node --test tests/frontend/*.test.cjs`: 71개 통과
- `tests/frontend/consent_forest_qa.cjs`: 철회·재동의, 그룹 선택, API 숲 진입, 새로고침, 다른 브라우저 복원, 401 만료, 무세션 접근 차단 통과
- `pytest -q tests/test_carrot_forest_lite.py tests/test_dual_model_integration.py tests/test_s2_api002_contract.py`: 8개 통과
