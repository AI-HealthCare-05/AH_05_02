# 당근밭 6주차 배치 · v168

## 변경 범위

- 당근밭 내부를 1주차부터 6주차까지 위에서 아래로 여섯 줄로 표시합니다.
- 한 줄은 가운데 길 왼쪽 2개와 오른쪽 3개를 합쳐 당근 5개, 전체 30개입니다.
- 각 줄 왼쪽에 해당 주차의 나무 팻말을 둡니다.
- 배경에 그려져 있던 닫힌 입구 문짝을 지워 흙길을 열었습니다. 주변 울타리·수로·물통·물뿌리개는 유지합니다.
- 출구 상호작용 제목은 `숲으로 가는 길`입니다.

이번 변경은 밭의 배치와 그림 변경입니다. 주차별 완료 여부나 성장 규칙을 새로 부여하지 않으며, 누적 챌린지 수확량·물주기·중복 보상 방지·저장 코디·가구 배치는 변경하지 않습니다. 메인 필드와 집 안 배경도 유지합니다.

## 구현

- `forest-garden.js`: 동결된 6 × 5 좌표와 주차 팻말을 Phaser/Canvas에서 공유합니다.
- 이미지의 투명 여백을 측정해 당근의 가로세로 비율을 유지합니다.
- Phaser는 4배 크기의 투명 레이어를 월드 크기로 표시합니다. 정원에서만 보이며 플레이어 아래에 있습니다.
- 당근밭 배경: `src/frontend/assets/carrot-forest-garden-v3.png` (1536 × 1024).
- 당근 스프라이트: `src/frontend/assets/garden-carrot-v168.png` (1254 × 1254, 실제 RGBA 투명도).
- 두 이미지는 내장 image_gen으로 생성/편집했습니다. [프롬프트 기록](art/garden-v168-prompts.md)에 정확한 입력을 보관합니다. 기존 v2 파일과 생성 원본은 삭제하지 않았습니다.
- PWA 캐시 `gandang-carrot-forest-pwa-v168-1`에 새 모듈과 이미지를 포함합니다.

## 검증

- 신규 정원 테스트 10개: 6개 팻말, 30개 독립 좌표, 입구 공간, 비율 유지, 투명 여백, 두 렌더러의 일치, 캐시 연결, 수확 회귀.
- 기존 Phaser preload 테스트 fixture에 새 정원 모듈 의존성만 추가했습니다.
- 브라우저: 밭 입장, 새 당근 레이어, 열린 길의 상호작용 창, 숲 복귀 확인. 브라우저 오류/경고 없음.
- 전체 배치 미리보기에서 `1주차`~`6주차`, 줄마다 5개, 열린 중앙 입구를 육안 확인했습니다.

```powershell
$forestTests = Get-ChildItem tests/forest-*.test.cjs | ForEach-Object { $_.FullName }
node --test $forestTests tests/challenge-settings.test.cjs
.\.venv\Scripts\python.exe -m pytest tests/test_carrot_forest_pixel_game.py tests/test_challenge_v21.py -q
git diff --check
```

게임: `/forest?garden=v168` · 배치 미리보기: `/static/forest-garden-review-v168.html`
