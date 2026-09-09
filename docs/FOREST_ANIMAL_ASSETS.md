# 숲 동물 스프라이트 계약

`src/frontend/forest-animals.js`는 게임 상태를 직접 수정하지 않는 공유 모듈이다. `forest-game.js`와 `forest-phaser.js`보다 먼저 로드한다. 자료 출처와 이용 조건은 [`ATTRIBUTION.md`](../src/frontend/assets/animals/ATTRIBUTION.md)에 기록했으며 사용자 화면에서도 이 파일에 연결한다.

## 젖소

- `ForestAnimals.assets`의 `forest-cow-eat`와 `forest-cow-walk`를 128 × 128 프레임으로 로드한다.
- `cowFrame()`은 왼쪽을 바라보는 정지 프레임 4를 반환한다. 시간이 지나도 스스로 움직이지 않는다.
- 클릭·터치·명시적 상호작용 후 기록한 시작 시각으로 `cowFrame(now - startedAt)`을 호출한다. 1,360ms 동안 프레임 `[4,5,6,7,7,6,5,4]`를 순서대로 사용하고 원래 정지 자세로 돌아온다.
- 위치·크기·몸통 회전 tween을 추가하지 않는다. 원본 프레임에 있는 고개와 주둥이 움직임만 사용한다. 잔디 받침이나 별도 몸통 이미지는 필요 없다.
- `{ reducedMotion: true }`일 때는 상호작용 중에도 원래 프레임을 유지한다.
- 반환한 `originX`, `originY`는 알파 영역의 발 위치에 맞춘 값이다. 왼쪽/오른쪽 젖소는 `(0.5, 0.6875)`, 1.25배 표시 시 실제 몸체는 약 89 × 55px이다.
- 상호작용 순간 `playMoo({ enabled: soundEnabled, volume: 0.32 })`를 호출한다. 실제 소 녹음이며 1.4초 이내 반복 호출은 무시한다. 기본 대기 상태에서는 소리를 재생하지 않는다.

## 토끼

- `forest-rabbit`을 72 × 72 프레임으로 로드한다.
- `rabbitFrame(direction, moving, elapsedMs, reducedMotion)`을 사용한다. 방향은 `up`, `left`, `down`, `right`이다.
- 이동 시 원본 도약 프레임을 140ms 간격으로 사용한다. 대기 시 별도의 먹이 먹는 자세를 330ms 간격으로 사용한다.
- 원본에 도약 동작이 포함돼 있으므로 추가 사인파 점프나 몸통 늘이기를 넣지 않는다.
- 발 기준점 `(0.5, 51/72)`, 추천 배율 1.35이다. 기존 쥐 이벤트와 별도 동물 유형으로 다루며 기존 쥐 자산은 교체하지 않는다.

Canvas 폴백은 반환된 `key`, `frame`을 `frameRect(key, frame)`로 변환해 원본 이미지에서 잘라 그릴 수 있다. 잘못된 프레임은 `null`을 반환한다.

## 게임 연결과 배치·야간 동작

- 게임의 창고·보관함 썸네일과 Canvas 폴백도 실제 젖소 스프라이트를 사용한다. 과거 잔디 받침이 붙은 젖소 이미지는 이 코드에서 참조하지 않는다.
- 젖소 쓰다듬기와 Q 상호작용은 저장된 `active` 값을 토글하지 않는다. 일시적인 반응 시작 시각만 메모리에 기록하고 기존 효과음 음소거·볼륨을 사용한다.
- 야생 토끼/쥐 종류는 등장 이벤트의 `species`와 `eventId`로 받는다. 게임 UI가 종류를 다시 추첨하지 않으며 토끼 보상 안내를 쥐로 표시하지 않는다.
- 분수는 육지 장식이다. 연못 전용 배치는 `duck_float`에만 적용한다. 빈 풀밭의 배치는 월드 경계·집·당근밭·연못·이미 점유한 중심점만 확인하며 이동 충돌이나 배경 장식의 그림으로 추가 영역을 막지 않는다. 32px 인접 격자 배치가 가능하도록 서로 다른 오브젝트 중심 간 최소 간격은 28px이다.
- 한국 시각 19:00부터 밤 음악과 야간 안내를 적용한다. 밤 어둠은 `.78`, 05시 `.44`, 06시/18시 `.22`이며 낮은 0이다.
- Canvas 폴백은 배경과 캐릭터·가구를 그린 뒤 한 번만 어둠을 덮는다. 켜진 모닥불·등불 주변만 마스크를 열며, Phaser가 활성화된 경우에는 이 폴백 패스를 실행하지 않는다. 분위기 OFF는 음악과 어둠에 모두 적용한다.

## 검증

```powershell
node --test tests/forest-animals.test.cjs
node --test tests/forest-game-animal-integration.test.cjs tests/forest-placement.test.cjs tests/forest-atmosphere.test.cjs
```

2026-09-07: 7개 테스트와 JavaScript 구문 검사 통과. PNG 크기·투명 RGBA·그리드, 젖소 정지/유한 반응, reduced-motion, 토끼 방향/행, 프레임 경계, 음소거/자동재생 방지/반복 제한, 저작자·라이선스 포함을 확인했다. 다운로드 원본 4개는 합계 114,099바이트다.

추가 게임 연결 검증: 동물 모듈·게임 연결·배치·분위기를 합쳐 20개 테스트 통과. 젖소의 과거 받침 자산 미참조, 실제 프레임 렌더링, 상태 토글 없이 쓰다듬기, 종류를 유지한 토끼 안내, 분수 육지 배치, 인접 격자 사용, 19시 밤 음악, 폴백의 단일 어둠 패스와 켜진 등불 범위를 확인했다.

| 파일 | SHA-256 |
|---|---|
| `lpc-cow-eat.png` | `61bf45f6a448a9bda98d5f92e4263d821f2f8860e1a6438e70c745708275145f` |
| `lpc-cow-walk.png` | `f338ac144fcafdbbdb5c67ce674365b919b87c2a6ef757af60ec7e4abf23796b` |
| `lpc-rabbit.png` | `89da7327cb5662ac1f8ef14ec7c00d38218827582bc0f273e1cea873ce570ae1` |
| `cow-moo-joseph-sardin-cc0.mp3` | `574aa9bb61ca52c951340e93e898ae5b1cb211ce6fbcf1eadda2f5f28dfb7be7` |
