# 당근의 숲 Lite MVP 구현

## 1. 목적

`당근의 숲`은 간당간당의 건강정보 입력·예측 기능과 분리된 선택형 참여 기능이다. 기존 공동 챌린지의 가족·친구 그룹을 이용해 일일 수행 현황, 아바타, 보상과 숲 장식을 제공한다.

## 2. MVP 범위

- 공동 챌린지 그룹당 숲 1개
- 그룹 구성원 최대 5명(기존 공동 챌린지 제한 재사용)
- 사용자별 아바타 헤어·상의·액세서리 저장
- 오늘 완료한 챌린지를 사용자당 최대 3개로 집계
- 모든 구성원이 3개씩 완료하면 일일 그룹 보상 활성화
- 일일 그룹 보상 중복 수령 차단
- 당근 재화로 숲 장식 배치
- 데스크톱·모바일 웹 화면

실시간 이동, 채팅, 결제, 아이템 거래, 자유형 맵 편집은 포함하지 않는다.

## 3. 데이터 구조

| 테이블 | 역할 |
| --- | --- |
| `forest_spaces` | 공동 챌린지 그룹의 숲 |
| `forest_avatars` | 사용자 코디와 당근 잔액 |
| `forest_inventories` | 획득한 아바타 아이템 |
| `forest_objects` | 숲에 배치한 장식과 위치 |
| `forest_rewards` | 날짜·사용자별 보상 이력과 중복 방지 |

그룹과 구성원은 기존 `shared_challenge_groups`, `shared_challenge_members`를 사용하고, 완료 수는 기존 `challenge_logs`에서 조회한다.

## 4. API

| Method | Path | 기능 |
| --- | --- | --- |
| `GET` | `/api/v1/forest/catalog` | 아바타·장식 카탈로그 조회 |
| `POST` | `/api/v1/forest/spaces` | 공동 챌린지 그룹의 숲 시작 |
| `GET` | `/api/v1/forest/spaces/{group_id}` | 숲·구성원·진행률·인벤토리 조회 |
| `PATCH` | `/api/v1/forest/avatar` | 내 아바타 코디 저장 |
| `POST` | `/api/v1/forest/spaces/{group_id}/rewards/group-daily` | 일일 그룹 보상 수령 |
| `POST` | `/api/v1/forest/spaces/{group_id}/objects` | 숲 장식 배치 |
| `DELETE` | `/api/v1/forest/spaces/{group_id}/objects/{object_id}` | 내가 배치한 장식 회수·당근 환급 |

모든 변경·조회 API는 로그인 사용자가 해당 공동 챌린지의 활성 구성원인지 확인한다.

## 5. 주요 규칙

- 개인 일일 완료 수는 3개를 상한으로 계산한다.
- 공동 목표는 `활성 구성원 수 × 3`이다.
- 그룹 보상은 사용자·그룹·날짜별 1회만 받을 수 있다.
- 액세서리는 기본 아이템 또는 획득한 인벤토리만 착용할 수 있다.
- 장식 구매 시 서버에서 당근 잔액을 확인하고 차감한다.
- 장식은 배치한 사용자만 회수할 수 있고 회수 시 사용한 당근을 돌려준다.
- 숲 응답에는 챌린지 완료 수, 아바타, 장식만 포함한다.

## 6. 실행과 확인

```powershell
$env:DEMO_MODE="true"
uv run --group app uvicorn app.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`에 접속한 뒤 다음 순서로 확인한다.

1. 가입·챌린지 시작
2. 함께하기에서 가족·친구 공동 챌린지 생성 및 수락
3. `당근의 숲` 탭에서 그룹 선택 후 숲 시작
4. 구성원별 오늘의 챌린지 3개 기록
5. 보상 상자 수령
6. 아바타 코디 저장과 숲 장식 배치

## 7. 수용 기준

- [x] 비구성원은 다른 그룹의 숲을 조회할 수 없다.
- [x] 숲이 없는 그룹은 명시적으로 시작할 수 있다.
- [x] 그룹 진행률은 `challenge_logs`와 일치한다.
- [x] 같은 날 같은 사용자의 그룹 보상은 중복 지급되지 않는다.
- [x] 미획득 액세서리는 착용할 수 없다.
- [x] 당근 부족 시 장식을 배치할 수 없다.
- [x] 데스크톱과 모바일에서 핵심 조작이 가능하다.

## 8. 관련 파일

- 모델: `app/models/forest.py`
- DTO: `app/dtos/forest.py`
- 저장소: `app/repositories/forest_repository.py`
- 서비스: `app/services/forest.py`
- 라우터: `app/apis/v1/forest_routers.py`
- 마이그레이션: `app/core/db/migrations/models/5_20260826143000_carrot_forest_lite.py`
- 프론트엔드: `src/frontend/index.html`, `src/frontend/app.js`, `src/frontend/styles.css`
- 통합 테스트: `tests/test_carrot_forest_lite.py`
