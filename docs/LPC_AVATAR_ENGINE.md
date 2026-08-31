# Universal LPC 기반 아바타·펫 엔진

## 적용 범위

`당근의 숲` 아바타는 Universal LPC Spritesheet Character Generator의 호환 레이어를 선별해 동일한 `64×64` 프레임 규격으로 합성한다. 완성형 캐릭터 이미지를 잘라 붙이지 않고 몸·하의·신발·상의·헤어·안경·모자를 매 프레임 같은 좌표에 그리므로, 코디를 바꿔도 인접 스프라이트나 원래 의상이 비치지 않는다.

- 성별 몸체: 남성형·여성형
- 헤어 5종, 상의 5종, 하의 4종, 신발 3종, 모자 3종, 안경 3종
- 피부·헤어·상의·하의·신발 색상 필터
- 표정 6종: 차분한 미소, 환한 미소, 윙크, 눈웃음, 살짝 걱정, 씩씩한 표정
- 기본·걷기·달리기·앉기·점프·감정표현·수확·낚시·문 열기·공격 동작
- 아우라·순간 이펙트·탈것·펫을 별도 레이어로 유지

## 입력과 동작

| 입력 | 동작 |
| --- | --- |
| 방향키 / WASD | 4방향 걷기 |
| R + 이동 | 달리기 |
| Q | 가까운 대상에 따라 당근 수확·낚시·문 열기 |
| Z | 공격 모션 |
| 0 | 아바타와 펫이 함께 춤추기 |
| X | 아바타와 펫이 함께 앉기·일어나기 |
| E | 탈것 승하차 |

펫은 아바타 컨테이너에 고정하지 않는다. 플레이어의 최근 이동 좌표를 짧은 경로로 보관하고 약 `330ms` 뒤의 지점을 따라가며, 좌우 방향·보행 바운스·정지 호흡을 따로 표현한다. 춤에서는 좌우 이동과 점프·기울기를 함께 적용하고, 앉기에서는 플레이어 가까이 이동해 낮은 자세를 유지한다.

## 재현

```powershell
.\.venv\Scripts\python.exe scripts/build_lpc_avatar_pack.py
node --check src/frontend/lpc-avatar-engine.js
node --check src/frontend/forest-phaser.js
.\.venv\Scripts\python.exe -m pytest -q tests/test_carrot_forest_pixel_game.py
```

생성 파일은 `src/frontend/assets/lpc-pack/`에 저장된다. `manifest.json`은 런타임 레이어·애니메이션 행을, `credits.json`은 각 원본 파일·저작자·라이선스를 기록한다. 새 아이템을 추가할 때는 빌드 스크립트의 카탈로그에 원본 레이어를 등록하고 pack을 다시 생성한다.

## 출처와 라이선스

- 원본 프로젝트: [Universal LPC Spritesheet Character Generator](https://github.com/liberatedpixelcup/Universal-LPC-Spritesheet-Character-Generator)
- LPC 에셋은 파일별로 CC0, CC-BY, CC-BY-SA, OGA-BY, GPL 등 조건이 다르다.
- 배포 전 `src/frontend/assets/lpc-pack/credits.json`의 저작자 표시와 라이선스 조건을 최종 확인해야 한다.
- 이 저장소의 자체 코드 라이선스가 개별 LPC 에셋의 라이선스 조건을 대체하지 않는다.

## 표정 디자인 기준

귀여운 얼굴 비율과 표정 일관성을 검토하기 위한 자체 콘셉트 시트는 `docs/assets/lpc-cute-face-expression-concept-v1.png`에 보관한다. 이 이미지는 기존 서비스 캐릭터를 복제하지 않고 표정 레이어 제작 방향만 정의한다.
