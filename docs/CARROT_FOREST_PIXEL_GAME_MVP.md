# 당근의 숲 (Beta) 웹 픽셀 게임 MVP

## 1. 한 줄 정의

`당근의 숲`은 간당간당의 의료·예측 흐름과 분리된 선택형 확장 패키지로, 기존 생활습관 챌린지 기록을 다섯 명의 공동 퀘스트·픽셀 아바타·숲 꾸미기로 연결한다.

독립 실행 경로는 `/forest`이며 메인 서비스의 `당근의 숲 (Beta)` 메뉴에서도 진입한다.

## 2. 오늘 구현한 범위

- Canvas 기반 24×16 타일 픽셀 맵: 숲, 당근밭, 공동 나무, 집, 산책길
- 여성형·남성형·중립형 성별 표현과 외형 프리셋 4종
- 아바타 표시 이름과 맵 위 이름표
- 키보드 방향키·WASD 및 모바일용 큰 방향 버튼
- 개인 일일 퀘스트 3개와 다섯 명 공동 목표 15개
- 구성원별 `0/3`~`3/3`, 공동 진행률과 접근 가능한 progressbar
- 공동 목표 달성 후 날짜별 1회 무료 보물상자
- 아바타 액세서리 장착·해제
- 숲 오브젝트 선택·Canvas 위치 배치·창고 회수
- 큰 글자 전환, 48px 이상 주요 조작 영역, 사진 인증 없는 체크 방식
- 유료 상품·현금 결제·아이템 거래·건강정보 공개 기능 제외
- 게임 제작 도구를 닮은 월드 스튜디오 UI: 좌측 작업 도구, 중앙 Canvas, 우측 퀘스트 인스펙터, 하단 에셋 라이브러리
- 작업 영역 바로가기, 월드 확대·화면 맞춤, 위치 초기화, 실시간 좌표 HUD
- 저작권 음원을 복제하지 않은 Web Audio 기반 오리지널 숲 배경음악과 재생·정지
- 집·공동 당근밭 클릭 및 근접 `Q` 상호작용, 물주기·휴식·옷장 연결
- `R` 달리기, `C` 채팅, `X` 앉기, `E` 숲 스쿠터 승하차
- 옷장(아바타 액세서리)과 창고(숲 오브젝트)를 분리한 에셋 관리
- 기존 퀘스트 화면의 연속 참여·퀘스트별 당근 보상 정보를 월드 스튜디오에 통합
- 1536×1024 내부 Canvas를 768×512 월드 좌표에 2배 렌더링하는 고해상도 픽셀 파이프라인
- 집·공동 당근밭·공동 나무·연못·울타리·꽃·스쿠터를 독립 레이어 함수로 세분화
- 지붕 타일, 창문 반사, 나뭇결, 흙 고랑, 잎 명암, 그림자와 캐릭터 표정·의상·신발 디테일 추가
- 모션 감소 설정을 존중하는 저주파 잎 흔들림·수면 반사·아바타 호흡 애니메이션
- 전용 `아바타 꾸미기` 작업실: 좌측 카테고리, 중앙 아이템 카드, 우측 2배 픽셀 미리보기
- 꾸미기 카테고리: 피부·의상·헤어·얼굴·액세서리·아우라·이펙트·탈것·펫·말풍선
- 아우라는 지속 장식, 이펙트는 순간 표현으로 구분하며 선택·실행 취소·무작위 코디·저장을 지원
- 저장한 피부색·의상·헤어·표정·액세서리·아우라·이펙트·펫·말풍선을 월드 아바타에 즉시 반영
- PWA 설치: 지원 브라우저에서 바탕화면·홈 화면 앱으로 추가하고 독립 창으로 실행
- 오프라인 앱 셸: 화면·스크립트·스타일·아이콘만 캐시하며 `/api/` 건강·사용자 데이터는 캐시하지 않음

## 3. 실행 방법

```powershell
$env:DEMO_MODE="true"
$env:DB_GENERATE_SCHEMAS="true"
$env:DATABASE_URL="sqlite://storage/gandang_mvp.sqlite3"
$env:SECRET_KEY="local-demo-only-change-before-deployment"
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

- 메인 MVP: `http://127.0.0.1:8000/`
- 당근의 숲: `http://127.0.0.1:8000/forest`
- API 문서: `http://127.0.0.1:8000/api/docs`

`localhost` 또는 HTTPS 환경에서 `/forest`를 연 뒤 브라우저의 **앱 설치** 또는 **홈 화면에 추가**를 선택한다. 설치 이벤트를 지원하는 브라우저에서는 상단에 `앱으로 설치` 버튼이 표시된다.

## 4. 프론트엔드 상태와 어댑터 경계

### Demo Adapter

`src/frontend/forest-game.js`의 `DemoForestAdapter`가 브라우저 `localStorage`에 아래 상태를 저장한다.

- 아바타 이름·성별 표현·외형·위치·장착 액세서리
- 개인 퀘스트 체크 상태
- 다섯 명 구성원의 오늘 진행률
- 획득 아이템·배치 오브젝트·당근·보상 수령 여부

날짜가 바뀌면 일일 퀘스트와 보상 상태가 새로 시작된다. 이 어댑터는 실제 건강정보나 예측 결과를 읽지 않는다.

### 실제 API Adapter

같은 파일의 `ApiForestAdapter`가 교체 지점이다. UI와 Canvas 로직은 유지하고 다음 계약으로 상태 저장만 바꾼다.

| Method | Path | 연결 목적 |
| --- | --- | --- |
| `GET` | `/api/v1/challenge-cycles/current` | 내 일일 퀘스트 3개 조회 |
| `PUT` | `/api/v1/user-challenges/{id}/logs/{date}` | 체크 결과를 기존 챌린지 기록에 저장 |
| `GET` | `/api/v1/forest/catalog` | 아바타·오브젝트 카탈로그 |
| `POST` | `/api/v1/forest/spaces` | 공동 챌린지 그룹의 숲 생성 |
| `GET` | `/api/v1/forest/spaces/{group_id}` | 숲·5명 진행률·인벤토리·배치 상태 |
| `PATCH` | `/api/v1/forest/avatar` | 표시 이름과 코디 저장 |
| `POST` | `/api/v1/forest/spaces/{group_id}/rewards/group-daily` | 공동 목표 보상 수령 |
| `POST` | `/api/v1/forest/spaces/{group_id}/objects` | 숲 오브젝트 배치 |

현재 정식 API는 공동 챌린지 로그로 구성원별 완료 수를 계산하며, 사용자당 일일 3개를 상한으로 적용한다. 독립 게임 화면은 시연 안정성을 위해 Demo Adapter가 기본이고, 인증 세션과 그룹 선택 UX가 확정되면 `ApiForestAdapter`로 전환한다.

## 5. 주요 코드

| 책임 | 파일 |
| --- | --- |
| 독립 게임 화면 | `src/frontend/forest.html` |
| 픽셀 게임·상태·어댑터 | `src/frontend/forest-game.js` |
| 반응형·접근성 스타일 | `src/frontend/forest-game.css` |
| PWA 설치 정보 | `src/frontend/forest.webmanifest` |
| 오프라인 앱 셸 | `src/frontend/forest-sw.js` |
| 앱 아이콘 | `src/frontend/icons/forest-icon-192.png`, `forest-icon-512.png` |
| FastAPI 독립 경로 | `app/main.py` |
| 숲 API | `app/apis/v1/forest_routers.py` |
| 서비스 규칙 | `app/services/forest.py` |
| DB 모델 | `app/models/forest.py` |
| 통합 테스트 | `tests/test_carrot_forest_lite.py` |
| 화면·게임 계약 테스트 | `tests/test_carrot_forest_pixel_game.py` |

## 6. Unity를 나중에 연결할 때의 경계

오늘 구현은 Canvas 렌더러와 상태 어댑터를 분리했다. Unity WebGL을 도입하더라도 인증·퀘스트·보상·인벤토리·오브젝트 API는 그대로 사용하고, `forest-game.js`의 맵 렌더링과 입력 처리만 Unity 빌드로 교체한다. Unity가 건강정보나 예측 결과를 직접 조회하지 않고 서버가 승인한 게임 상태만 받도록 유지한다.

월드 스튜디오 레이아웃 역시 렌더러와 분리되어 있다. 향후 Unity 화면은 중앙 `world-stage`만 교체하고, 좌측 아바타 편집기·우측 퀘스트 인스펙터·하단 에셋 라이브러리는 웹 UI로 계속 사용할 수 있다.

## 7. 검증 명령

```powershell
node --check src/frontend/forest-game.js
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pytest -q
```
