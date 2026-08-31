# Universal LPC 기반 아바타·펫 엔진

## 적용 범위

`당근의 숲` 아바타는 Universal LPC Spritesheet Character Generator의 호환 레이어를 선별해 동일한 `64×64` 프레임 규격으로 합성한다. 완성형 캐릭터 이미지를 잘라 붙이지 않고 몸·하의·신발·상의·헤어·안경·모자를 매 프레임 같은 좌표에 그리므로, 코디를 바꿔도 인접 스프라이트나 원래 의상이 비치지 않는다.

- 체형: 성인 남성·성인 여성·근육형·슬림형·아이. 선택 체형을 실제로 지원하는 레이어만 목록에 표시한다.
- 검증된 헤어·상의·하의·신발·모자·안경/눈 장식을 이미지 중심으로 제공한다. 개수보다 체형 호환성과 레이어 정렬을 우선한다.
- 피부·헤어·상의·하의·신발 색상 필터
- 공식 LPC 표정 16종과 눈썹·코·특수 눈·주름 레이어. 기존 임의 제작 표정 오버레이는 사용하지 않는다.
- 기본·걷기·달리기·앉기·점프·감정표현·수확·낚시·문 열기·공격 동작
- 공격 효과에 맞춰 검은 휘두르기, 화살은 사격, 마법은 주문 시전, 잎 칼날은 찌르기 동작을 사용
- 중립 얼굴을 기본 레이어로 유지하고 선택 표정을 겹쳐 부분 표정에서도 눈·코·입이 사라지지 않음
- 앉기는 반복 재생하지 않고 마지막 자세를 유지하며 `X`를 다시 누르면 해제
- 아우라·순간 이펙트·탈것·펫을 별도 레이어로 유지

## 입력과 동작

| 입력 | 동작 |
| --- | --- |
| 방향키 / WASD | 4방향 걷기 |
| R + 이동 | 달리기 |
| Q | 가까운 대상에 따라 당근 수확·낚시·문 열기 |
| Z | 공격 모션 |
| 0 | 댄스 |
| X | 아바타와 펫이 함께 앉기·일어나기 |
| F | 보유 당근 1개를 펫에게 먹이로 주고 하트 표시 |
| E | 탈것 승하차 |

펫은 아바타 컨테이너에 고정하지 않는다. 플레이어의 최근 이동 좌표를 짧은 경로로 보관하고 약 `330ms` 뒤의 지점을 따라가며, 좌우 방향·보행 바운스·정지 호흡을 따로 표현한다. 춤에서는 좌우 이동과 점프·기울기를 함께 적용하고, 앉기에서는 플레이어 가까이 이동해 낮은 자세를 유지한다.

LPC 합성 캔버스의 실제 발바닥 좌표를 Phaser 컨테이너 원점에 맞춰 캐릭터 발과 그림자가 붙도록 한다. 몸 레이어 전체에 선택한 피부 필터를 적용하고 코·주름 같은 얼굴 피부 레이어에도 같은 색상 키를 전달한다. 표정·눈썹·코는 별도 레이어이므로 기본 캐릭터에서도 얼굴이 비어 보이지 않는다.

## 재현

```powershell
.\.venv\Scripts\python.exe scripts/build_lpc_avatar_pack.py `
  --source "<Universal-LPC-Spritesheet-Character-Generator 경로>" `
  --output src/frontend/assets/lpc-pack
.\.venv\Scripts\python.exe scripts/build_lpc_pet_pack.py
node --check src/frontend/lpc-avatar-engine.js
node --check src/frontend/forest-phaser.js
.\.venv\Scripts\python.exe -m pytest -q tests/test_carrot_forest_pixel_game.py
```

생성 파일은 `src/frontend/assets/lpc-pack/`에 저장된다. `manifest.json`은 런타임 레이어·애니메이션 행을, `credits.json`은 각 원본 파일·저작자·라이선스를 기록한다. 새 아이템을 추가할 때는 빌드 스크립트의 카탈로그에 원본 레이어를 등록하고 pack을 다시 생성한다.

아이템 카드는 그림과 선택 상태만 시각적으로 노출하고 이름은 접근성용 `aria-label`에 유지한다. 동작 탭은 보유 여부와 단축키만 확인하는 읽기 전용이며, 대량 레이어는 선택 시점에 지연 로딩한다.

## 출처와 라이선스

- 원본 프로젝트: [Universal LPC Spritesheet Character Generator](https://github.com/liberatedpixelcup/Universal-LPC-Spritesheet-Character-Generator)
- LPC 에셋은 파일별로 CC0, CC-BY, CC-BY-SA, OGA-BY, GPL 등 조건이 다르다.
- 배포 전 `src/frontend/assets/lpc-pack/credits.json`의 저작자 표시와 라이선스 조건을 최종 확인해야 한다.
- 이 저장소의 자체 코드 라이선스가 개별 LPC 에셋의 라이선스 조건을 대체하지 않는다.

## 표정 디자인 기준

귀여운 얼굴 비율과 표정 일관성을 검토하기 위한 자체 콘셉트 시트는 `docs/assets/lpc-cute-face-expression-concept-v1.png`에 보관한다. 이 이미지는 기존 서비스 캐릭터를 복제하지 않고 표정 레이어 제작 방향만 정의한다.
