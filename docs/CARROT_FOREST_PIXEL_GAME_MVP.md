# 당근의 숲 (Beta) 웹 픽셀 게임 MVP

## 1. 한 줄 정의

`당근의 숲`은 간당간당의 의료·예측 흐름과 분리된 선택형 확장 패키지로, 기존 생활습관 챌린지 기록을 다섯 명의 공동 퀘스트·픽셀 아바타·숲 꾸미기로 연결한다.

독립 실행 경로는 `/forest`이며 메인 서비스의 `당근의 숲 (Beta)` 메뉴에서도 진입한다.

## 2. 오늘 구현한 범위

- Phaser 3.90 기반 24×16 월드: 숲, 당근밭, 공동 나무, 집, 산책길
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
- 숲 월드·집 내부 홈피·공동 당근밭을 서로 분리한 장면 전환
- 집·당근밭·연못 클릭 및 근접 `Q` 상호작용, 소파 휴식·옷장·물주기·낚시 연결
- `R` 달리기, `C` 채팅, `X` 앉기, `E` 숲 스쿠터 승하차
- 옷장(아바타 액세서리)과 창고(숲 오브젝트)를 분리한 에셋 관리
- 기존 퀘스트 화면의 연속 참여·퀘스트별 당근 보상 정보를 월드 스튜디오에 통합
- 1536×1024 내부 Canvas를 768×512 월드 좌표에 2배 렌더링하는 고해상도 픽셀 파이프라인
- 집·공동 당근밭·공동 나무·연못·울타리·꽃·스쿠터를 독립 레이어 함수로 세분화
- 지붕 타일, 창문 반사, 나뭇결, 흙 고랑, 잎 명암, 그림자와 캐릭터 표정·의상·신발 디테일 추가
- 모션 감소 설정을 존중하는 저주파 잎 흔들림·수면 반사·아바타 호흡 애니메이션
- 전용 `아바타 꾸미기` 작업실: 좌측 카테고리, 중앙 아이템 카드, 우측 2배 픽셀 미리보기
- 꾸미기 카테고리: 피부·의상·하의·신발·헤어·얼굴·모자·안경·액세서리·아우라·찌르기 이펙트·탈것·펫·말풍선. 각 탭에는 의미에 맞는 전용 아이콘을 표시한다.
- 아우라는 지속 장식, 이펙트는 순간 표현으로 구분하며 선택·실행 취소·무작위 코디·저장을 지원
- 저장한 피부색·의상·헤어·표정·액세서리·아우라·이펙트·펫·말풍선을 월드 아바타에 즉시 반영하며, 커스텀 조합은 서로 덮어쓰지 않는 레이어형 렌더러를 사용한다.
- 기본 `새싹 정원사`와 추가 프리셋 5종은 앞·뒤·좌·우 4방향 보행과 방향별 프레임 애니메이션을 제공한다. 프리셋에 없는 개별 조합은 레이어 합성 미리보기로 제공한다.
- 기본 프리셋의 스쿠터는 캐릭터와 탈것을 따로 겹치지 않고, 손·발·발판을 하나로 그린 방향별 정지·이동 프레임을 사용한다.
- 리본 정원사·음메 목장지기·한밤 숲지기·파란 모자 농부·미소 정원사 5개 프리셋을 추가했다. 각 프리셋은 고유 헤어·모자·안경·의상과 4방향 보행·통합 스쿠터 자세를 가진다.
- 프리셋에서 안경·모자·가방·아우라를 덧입힐 수 있고, 개별 피부·헤어·의상·얼굴을 선택하면 `나만의 조합`으로 전환되어 선택 결과가 미리보기와 월드에 반영된다.
- 프리셋은 꾸미기 작업실의 첫 번째 카테고리와 왼쪽 기본 정보 선택기에서 고를 수 있으며, 목도리·새싹 모자·안경·가방은 이동 프레임 위에 별도 장착 레이어로 유지된다.
- 꾸미기 카드 썸네일은 CSS 배경 위치 대신 독립 Canvas 셀 크롭을 사용해 인접 스프라이트의 위·아래가 노출되지 않도록 했다.
- 오리지널 투명 PNG 아틀라스 기반의 정교한 32-bit 치비 캐릭터 12종과 꾸미기 아이콘 20종 적용
- 카드 썸네일은 원본 아틀라스를 안전하게 크롭하고, 미리보기·커스텀 월드는 레이어형 렌더러로 선택 조합을 정확히 표현한다.
- 파란 눈의 흰 고양이와 노란 눈의 주황갈색 고양이를 전용 펫 아틀라스로 추가
- 창고에서는 오브젝트 이름·설명을 감추고 그림만으로 고르되, 스크린리더용 이름과 툴팁은 유지
- PWA 설치: 지원 브라우저에서 바탕화면·홈 화면 앱으로 추가하고 독립 창으로 실행
- 초기 CSS·JavaScript가 준비되기 전에는 원시 HTML 대신 전용 로딩 화면을 표시
- 오프라인 앱 셸: 화면·스크립트·스타일·아이콘을 먼저 원자적으로 캐시하고 대용량 미디어는 보조 캐시하며 `/api/` 건강·사용자 데이터는 캐시하지 않음
- `127.0.0.1`·`localhost` 개발 실행에서는 오래된 설치형 PWA 캐시를 자동 해제하며, 실제 배포 호스트에서만 서비스워커를 등록

## 픽셀 에셋 출처와 재현

- 실행 월드는 `Phaser 3.90.0`을 저장소 내부 정적 파일로 제공하며 MIT 라이선스 전문은 `src/frontend/vendor/PHASER_LICENSE.txt`에 보관한다.
- 투자자 데모의 월드 아바타와 꾸미기 미리보기는 프로젝트에서 제작한 동일한 고해상도 치비 프리셋 아틀라스를 사용한다. 각 프리셋은 앞·뒤·좌·우 보행과 스쿠터 방향 장면을 포함하며, 월드와 선택 카드의 화풍이 달라지지 않도록 완성형 코디 단위로 제공한다.
- 현재 투자자 데모는 `리본 정원사`, `음메 목장지기`, `한밤 숲지기`, `파란 모자 농부`, `미소 정원사`의 5개 완성형 코디를 제공한다. 개별 헤어·의상 조합은 같은 화풍의 레이어 아틀라스를 별도로 제작한 뒤 확장한다.

- `src/frontend/assets/carrot-forest-avatar-atlas-v1.png`: 프로젝트용으로 생성한 오리지널 4×3 투명 캐릭터 아틀라스
- `src/frontend/assets/carrot-forest-basic-walk-atlas-v1.png`: 새싹 정원사 기본 의상용 앞·뒤·좌·우 4×4 보행 아틀라스
- `src/frontend/assets/carrot-forest-basic-scooter-atlas-v1.png`: 같은 기본 의상용 4방향 × 정지·이동 4×2 통합 탑승 아틀라스
- `src/frontend/assets/carrot-forest-preset-red-bow-v1.png`: 리본 정원사 보행·탑승 아틀라스
- `src/frontend/assets/carrot-forest-preset-cow-hood-v1.png`: 음메 목장지기 보행·탑승 아틀라스
- `src/frontend/assets/carrot-forest-preset-midnight-v1.png`: 한밤 숲지기 보행·탑승 아틀라스
- `src/frontend/assets/carrot-forest-preset-blue-cap-v1.png`: 파란 모자 농부 보행·탑승 아틀라스
- `src/frontend/assets/carrot-forest-preset-teal-bob-v1.png`: 미소 정원사 보행·탑승 아틀라스
- `src/frontend/assets/carrot-forest-cosmetics-atlas-v1.png`: 프로젝트용으로 생성한 오리지널 5×4 투명 꾸미기 아이콘 아틀라스
- `src/frontend/assets/carrot-forest-cat-pets-v1.png`: 파란 눈 흰 고양이·노란 눈 주황갈색 고양이 2×1 투명 펫 아틀라스
- `src/frontend/assets/carrot-forest-storage-atlas-v1.png`: 꽃밭·등불·바르게 선 버섯·벤치 4×1 투명 창고 오브젝트 아틀라스
- `src/frontend/assets/carrot-forest-world-v2.png`: 집·당근밭·연못·산책길이 있는 고해상도 숲 월드
- `src/frontend/assets/carrot-forest-home-v1.png`: 소파·옷장·출구가 있는 집 내부 홈피
- `src/frontend/assets/carrot-forest-garden-v1.png`: 당근 고랑·물뿌리개·출구가 있는 공동 당근밭
- 첨부 화면은 픽셀 밀도·치비 비율·카드 가독성의 참고 자료로만 사용했으며 기존 캐릭터·아이템·로고·UI 이미지는 복제하지 않았다.
- 스프라이트 셀 좌표는 `drawAtlasCell()`에서 계산하며, 같은 에셋을 카드 CSS와 Canvas 미리보기·월드 렌더러가 함께 사용한다.

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
| Phaser 월드·고해상도 프리셋 아바타·4방향 이동 | `src/frontend/forest-phaser.js` |
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

오늘 구현은 Phaser 렌더러와 상태 어댑터를 분리했다. Unity WebGL을 도입하더라도 인증·퀘스트·보상·인벤토리·오브젝트 API는 그대로 사용하고, `forest-phaser.js`의 월드 렌더링과 입력 처리만 Unity 빌드로 교체한다. Unity가 건강정보나 예측 결과를 직접 조회하지 않고 서버가 승인한 게임 상태만 받도록 유지한다.

월드 스튜디오 레이아웃 역시 렌더러와 분리되어 있다. 향후 Unity 화면은 중앙 `world-stage`만 교체하고, 좌측 아바타 편집기·우측 퀘스트 인스펙터·하단 에셋 라이브러리는 웹 UI로 계속 사용할 수 있다.

## 7. 검증 명령

```powershell
node --check src/frontend/forest-game.js
node --check src/frontend/forest-phaser.js
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pytest -q
```
