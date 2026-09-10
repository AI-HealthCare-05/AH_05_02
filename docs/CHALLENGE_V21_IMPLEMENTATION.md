# 챌린지 V2.1 구현 및 검증 기록

관련 이슈: https://github.com/AI-HealthCare-05/AH_05_02/issues/34

## 범위와 현재 상태

루트의 `CHALLENGE_SYSTEM_V2_20260903.md` v2.1 및 카탈로그 policy 2.1을 별도 일일 시스템으로 확장했다. 기존 4주 주기·ChallengeLog·당근 잔액·소유 아이템은 삭제하거나 소급 재해석하지 않는다. 템플릿의 `production_enabled: false`는 승인 전 상태 그대로 유지한다.

- 실제 서버 배정, 회차별 저장, T2 파일 검증, T3 자가 기록, T1 실제 수동 검토 API, 멱등 보상까지 구현.
- 일반 적격·촬영 동의·실제 담당자 가용 조건에서는 T1/T2/T3 각 1개, E/M/H 각 1개, 서로 다른 family 3개를 조합으로 선택한 후 모드·행동 우선순위로 평가.
- 균형: H01-E / D01-M / A01-H. 운동형: D01-E / A01-M / A02-H. 식단형: D03-E / H01-M / D01-H.
- H01 기회/제한 조건 미충족 시 같은 난이도 H02를 우선 대체. 물을 추가로 마시게 하지 않으며 0mL가 정상 기록.
- 실제 검토 담당자가 없는 기본 환경에서는 T1 추천을 비활성화하고 별도 `-C` T3 카드와 `proof_mix_exception_reason`을 표시한다. 임의의 사진을 AI 검증 성공으로 취급하지 않는다.
- A03은 항상 비활성. 치료식·연하·알레르기·운동 가능·수분 제한은 보수적으로 확인한다. 기진단·긴급증상·미확인 의료 안내·건강정보 동의 철회는 서버가 차단한다.
- 이전 주기가 있으면 신규 등록 다음 날부터 배정. 새로고침·다중 요청은 동일 KST 일일 계획을 반환. 선호 변경은 다음 배정부터, 안전/사진 제한은 즉시 적용. 대체 카드는 revision으로 추가하고 이전 회차 이력을 유지한다.

## 구현 파일과 데이터 계약

| 영역 | 파일 / 데이터 |
|---|---|
| 정책·안전 후보 | `app/services/challenge_v2_catalog.py`, 원본 카탈로그 27개 + 이름이 구분된 접근성 대안 |
| API | `app/apis/v1/challenge_v2_routers.py`, 모든 사용자 작업 Bearer 인증·활성 계정 확인 |
| 서버 배정/집계 | `app/services/challenge_v2.py`, `app/repositories/challenge_v2_repository.py` |
| 입력 계약 | `app/dtos/challenge_v2.py`, 추가 필드 금지·횟수/시간/단위 검증 |
| 저장 모델 | `app/models/challenge_v2.py`: Enrollment, Day, Assignment, Session, Evidence, Review, Reward |
| 마이그레이션 | `app/core/db/migrations/models/6_20260903140000_challenge_v21.py` — MySQL 추가 테이블, 기존 테이블 수정/삭제 없음 |
| 비공개 파일 | `app/services/challenge_v2_evidence.py`, `app/middleware/challenge_upload_limit.py`, `app/services/challenge_v2_retention.py` |
| 공통 화면 | `src/frontend/challenge-v2.js`, `.css`, `app.js/index.html`, `forest-game.js/forest.html` 연결 |
| 대시보드 | 기존 summary에 `daily_challenge_v2`, progress에 `challenge_v2` 추가. 기존 응답 필드 유지 |
| 구형 추천 | `app/services/challenges.py`의 ‘세 끼가 아님 → 불규칙’ 추천 제거 |

### API

접두사 `/api/v1/challenge-v2`:

- GET `/capabilities`: 활성 여부. 다른 API는 인증 필요.
- PUT `/preferences`: 설정·선택적 사진 동의·명시적 전환 동의. 필수 건강정보 동의/이용 가능 확인은 기존 API 사용.
- GET `/today`: 현재 배정 읽기. POST `/today`: 없는 경우만 오늘 배정 생성.
- GET `/history/{YYYY-MM-DD}`: 소유한 배정일의 기록·원배정일 보상 조회.
- PUT `/assignments/{id}/sessions/{index}`: 회차별 자기보고. 활동은 종료 시각+분, 식사는 시각+내용, H02는 오전/오후/저녁 구간의 실제 양, D02는 기준량·단위·당류 및 난이도별 추가값.
- PUT `/assignments/{id}/evidence/{index}`: multipart `photo`, 단일 이미지. URL 입력 불가.
- GET `/assignments/{id}/alternatives`, PATCH `/assignments/{id}/replacement`: 서버 안전/행동군/주간 횟수 재검사. 완료 카드 변경 불가. 일반 선호 변경은 유형·난이도 조합 유지.
- GET `/evidence/{id}`: 소유자 또는 지정 검토 담당자에게만 JPEG 스트리밍. 공개·서명 URL을 발급하지 않으며 응답은 no-store.
- GET `/reviews`, POST `/evidence/{id}/review`: 지정 담당자 API. evidence generation과 명시된 조건별 결과·사유·사진 열람 확인을 요구. 자기 사진 검토, 조건 불충족 통과, 오래된 사진 버전 판정은 거부. 프런트 사용자에게 판정 버튼을 제공하지 않는다.

### 보상 및 기존 숲과의 경계

`ChallengeV2Reward`는 그룹 공간 ID를 요구하는 기존 ForestReward에 가짜 공간을 넣지 않기 위한 **개인 일일 원장**이다. 지급은 기존 `ForestAvatar.carrot_balance`와 `ForestInventory`를 사용한다. 슬롯 완료 10개, 확정된 활성 슬롯 전체 완료 시 일일 50개+기존 무료 보상 목록의 미소유 아이템 1개(모두 소유하면 아이템 추가 없음). 슬롯/날짜 source key UNIQUE + 사용자 행 잠금 + 트랜잭션으로 중복을 차단한다. 사진·섭취량·추가 운동량에 따른 보너스는 없다. 늦은 수동 검토는 원배정일에 한 번 지급한다.

숲의 **퀘스트 카드/개인 완료 수는 같은 서버 배정**을 사용한다. 기존 브라우저 DemoForestAdapter의 꾸미기용 잔액·쥐 사냥·펫 먹이·인벤토리는 별도 체험 기록이므로 계정 지갑으로 임의 이관하지 않는다. UI에 ‘계정 당근’을 별도 표기하고 구형 로컬 퀘스트 보상 버튼은 차단한다. 기존 데모 공동목표를 실제 가족 수행률로 승격하지 않는다. 게임 전체 경제의 서버 이관은 이 변경으로 완료됐다고 주장하지 않는다.

## 사진·검토 운영 경계

- JPEG/PNG/WebP만 허용, 확장자와 실제 MIME 비교, 10MB/1,600만 픽셀 상한, 애니메이션 거부. multipart 파싱 전 전체 요청 11MB 상한.
- 로컬에서 디코딩·방향 정규화 후 metadata 없는 JPEG로 다시 저장. 원본 EXIF/GPS는 남기지 않는다. 사진 속 URL·QR·문장은 실행하지 않는다. 외부 AI 전송 없음.
- 파일럿 보관은 DB 비공개 Binary 필드. 업로드 기준 7일 만료, 만료 시 읽기 즉시 거부. 서버 실행 중 1분 간격으로 바이트 삭제, 사진 동의 철회 시 즉시 삭제. 재동의해도 삭제된 파일로 완료할 수 없다. 검토·보상 원장의 비이미지 이력은 유지한다.
- 서버 중지 시간·DB 백업본까지의 삭제 보장은 별도 운영 정책/작업이 필요하다. 상용 스토리지 암호화·백업 만료·모니터링·업로드 속도 제한은 출시 전 검토 대상이다.
- T1은 실제 사람이 사진의 명시된 시각 조건/라벨 입력만 확인한다. 실제 섭취, 걷기 진위, 혈당·예방 효과, 열량을 검증하지 않는다. AI 워커에는 자동 통과 핸들러를 추가하지 않았다.
- T1 만료/판단 어려움은 실패 확정이 아니다. 당일은 재제출/체크형 대체, 지난 날 기록은 보존하고 새 날의 대안을 이용한다. 과거 배정의 재개 UI는 제공하지 않는다.

## 활성화·배포

- `DEMO_MODE`에서는 파일럿 제공. 일반 환경은 `CHALLENGE_V2_ENABLED`와 `CHALLENGE_V2_CONTENT_APPROVED`가 모두 참이어야 활성화한다. 승인값을 임의 설정하지 않는다.
- `CHALLENGE_V2_REVIEWER_IDS`는 실제 담당자 User ID 목록. `is_admin`, `is_active`가 모두 참인 지정 계정이 존재할 때만 T1을 배정한다. 기본값 빈 목록. 담당자 지정은 개인정보 고지·실제 업무 배정 후 운영자가 수행한다.
- 앱 의존성 그룹에 Pillow 추가, 기존 잠금된 Pillow 패키지 재사용. 호스트 한정 쿠키를 기본값으로 사용해 localhost/127.0.0.1 간 잘못된 Domain 설정을 피한다. 명시한 배포 COOKIE_DOMAIN은 유지된다.
- PWA v138. 신규 모듈은 캐시에 포함하고 개인 API는 no-store. 로그인/기기 간 동기화에는 온라인 연결이 필요하다.
- MySQL 배포 전 마이그레이션·다중 워커 동시성 시험 필요. SQLite 인메모리/격리 DB 검증과 MySQL 실배포 검증은 동일하지 않다. 파괴적 downgrade는 금지하도록 명시적으로 실패시킨다.

## 검증

- Python 관련 회귀: **88 passed** (V2.1 신규 23개 + 기존 웹·숲·의료 안전·AI 워커).
- 숲 JavaScript 동작 테스트: **19 passed**. 신규 공통 JS, app/game/service worker `node --check` 통과.
- 변경 Python 파일 Ruff 통과. `uv lock --check --offline` 통과(기존 잠금 Pillow 재사용).
- MySQL 실서버 마이그레이션/다중 프로세스 동시성은 미검증. 정적 계약·SQLite 검증만으로 출시 완료 처리하지 않는다.

`tests/test_challenge_v21.py`는 다음을 확인한다:

1. 세 모드의 인증·난이도·행동군 조합 및 유형별 난이도 변화.
2. 당 음료 비섭취/제한 시 H02 대체, 사진/검토 미가용 예외, A03 비활성, 주간 빈도 상한.
3. A01-M 한 회차로 완료 불가, 두 회차와 T2 제출 후 완료, 활동 겹침 차단.
4. T1 pending/불확실/조건 불충족 보상 차단, 실제 수동 검토와 익일 원배정일 보상, 판정 재시도 멱등성.
5. H02 0mL/구간별 합산/양에 따른 추가 보상 없음, 중복 동시 완료 요청.
6. 사용자 소유권, URL/MIME 위장/과대파일/과대 픽셀 거부, EXIF 제거, 만료·철회 삭제, 재동의 우회 차단.
7. 새로고침 안정성, 자정 신규 배정/과거 로그 차단, 기진단·긴급·의료 안내 차단, 기존 주기/지갑 보존.
8. 대시보드와 동일 API 내용, 클라이언트 완료 플래그 주입 거부, 대체 revision/과거 회차 보존.

실제 브라우저: 별도 포트 8013의 격리 테스트 DB/가상 계정에서 로그인 → 촬영 미동의 안전 설정 → 대체 사유 표시 → 수분 0mL 기록 → 1/3, 계정 당근 110개 확인 → 다른 카드로 대체 → 새로고침 후 동일 배정/잔액 유지 확인. 실제 사용자 사진이나 계정은 사용하지 않았다.

이 검증은 사진 AI 정확도·임상 예방 효과·고령자 사용성 검증이나 출시 승인이 아니다. 수동 검토 운영자 화면, 전체 게임 경제의 서버 이관, 실제 MySQL·스토리지 운영 검증은 후속 범위다.
