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
