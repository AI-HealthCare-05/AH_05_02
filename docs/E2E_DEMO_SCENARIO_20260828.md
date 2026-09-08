# Sprint 3 E2E·데모 시나리오 — 2026-08-28

## 1. 검증 결과

| 검증 | 결과 |
| --- | --- |
| 전체 pytest | 47 passed |
| 핵심 E2E·게임 테스트 | 25 passed |
| Ruff | All checks passed |
| Docker 통합 | 현재 PC에 Docker CLI가 없어 미검증 |
| 실제 승인 모델 artifact | Provider 병합 후 검증 필요 |

실행 명령:

```powershell
$env:UV_CACHE_DIR="$PWD\.uv-cache"
uv run pytest -q
uv run pytest tests/test_mvp_demo_flow.py tests/test_sprint2_vertical_contract.py tests/test_engagement_integration.py tests/test_carrot_forest_lite.py tests/test_carrot_forest_pixel_game.py -q
uv run ruff check app ai_worker src tests
```

## 2. 핵심 MVP 데모

1. 서비스 소개에서 회원가입을 시작한다.
2. 건강정보 이용 동의와 적합성 확인을 완료한다.
3. 기진단·경고 증상 사용자가 예측에서 차단되는지 보여준다.
4. 건강검진·생활습관 정보를 입력한다.
5. 비동기 예측 작업의 대기·실행·완료 상태를 보여준다.
6. 승인 전 모델에서 확률·위험 범주가 공개되지 않는지 확인한다.
7. 검토된 결과 안내 후 챌린지를 선택한다.
8. 일일 기록을 입력하고 대시보드 수행률 변화를 확인한다.

## 3. 당근의 숲 Beta 데모

1. `/forest` 독립 화면으로 이동한다.
2. 픽셀 아바타와 모바일·키보드 이동을 보여준다.
3. 개인 퀘스트 3개를 수행한다.
4. 5인 공동 목표가 12/15에서 15/15로 변경되는지 확인한다.
5. 무료 보물상자를 열어 아이템을 획득한다.
6. 옷장에서 아이템을 장착하고 숲 오브젝트를 배치한다.
7. 건강정보가 공동 공간에 공유되지 않는다는 계약을 설명한다.

## 4. 예외·의료 안전 확인

- 미성년자·기진단자·경고 증상·모델 범위 밖 사용자는 예측 작업을 만들지 않는다.
- 개발 Provider는 임의 확률이나 위험 범주를 생성하지 않는다.
- 승인 전 내부 점수를 사용자에게 노출하지 않는다.
- 약물 시작·중단·용량 변경 질문을 차단한다.
- 실패·시간초과는 상태와 복구 안내를 글자와 아이콘으로 표시한다.
- 사진 인증이 어려운 챌린지는 간편 체크를 허용한다.

## 5. 배포 전 차단조건

- 실제 artifact·전처리기·checksum·롤백 후보 확보
- 고정 입력의 로컬 모델과 Provider 결과 일치
- Docker에서 FastAPI·DB·Redis·Worker 통합 실행
- `develop` 통합 CI와 팀 리뷰 통과
- `develop → main` Release PR 승인

