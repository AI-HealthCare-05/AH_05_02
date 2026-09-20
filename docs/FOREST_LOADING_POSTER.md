# 당근의 숲 로딩 포스터 v147

## 적용 (2026-09-07)

- 현재 승인된 포스터의 당근집·네 농부·숲 색감을 바탕으로 로딩 전용 16:9 일러스트를 새로 구성했습니다.
- 산출물: `src/frontend/assets/carrot-forest-loading-v2.png` (1672 × 941, 약 2.25 MiB).
- 참조: `src/frontend/assets/carrot-forest-social-preview-v2.png`.
- 모드: 이미지 생성 도구의 **참조 이미지 기반 편집/재구성**. 일러스트만 생성하고 제목·슬로건·진행 표시는 HTML로 유지합니다.
- 슬로건: **함께 실천하고, 같이 성장하는 모두의 건강 숲**.
- 가로 화면에서는 왼쪽 여백에 제목을 배치하고, 세로 화면에서는 당근집을 중심으로 크롭한 뒤 하단 그라데이션 위에 텍스트를 배치합니다.
- 로딩 이미지를 우선 다운로드하며, 기존 CSS/스크립트 준비 조건을 유지합니다. 포스터를 보여주기 위한 인위적인 진입 지연은 추가하지 않았습니다.
- 서비스 워커 캐시를 v147로 변경해 기존 로딩 포스터와 분리했습니다. 이전 이미지는 과거 링크 보존을 위해 삭제하지 않습니다.

## 생성 프롬프트

```text
Use case: illustration-story
Asset type: full-screen loading screen background for the Korean cozy pixel-art game "당근의 숲".
Input image 1 is the CURRENT APPROVED POSTER, a strict visual reference for the carrot house, forest palette, chibi farmers, plants and deliberate pixel-block illustration.
Primary request: create a newly composed polished widescreen 16:9 loading illustration based on this exact poster. Preserve its recognizably carrot-shaped orange house with tall green leaves, round wooden window, arched door, warm brass lanterns, deep forest canopy and cheerful tiny farmers watering and harvesting carrots. Use exactly four little farmers in matching green/cream clothing, one small white rabbit, flowers, carrot beds, baskets and a winding stone path as implied in the reference.
Composition: landscape game splash, house in the right half with its entire leafy crown visible; farmers around the lower-right carrot patch. Preserve a calm luminous misty forest clearing on the left 45% for live HTML title, slogan and loading indicator; keep important faces, house and props out of that copy zone. Frame with deep green leaves around top corners. Keep recognizable subjects in safe interior margins and the rich foreground near the bottom.
Style: high-quality nostalgic pixel storybook illustration matching the reference, crisp intentionally blocky pixel clusters, warm outlines, tactile wooden objects, lush but controlled forest green, natural carrot orange, cream-green sunlight. Cozy tranquil daylight, gentle forest sunbeams, no glossy 3D mobile-game rendering, no photorealism, no yellow sepia wash.
Constraints: artwork only: NO text, NO letters, NO title, NO slogan, NO UI boxes, NO loading bar, NO watermark. Left space should be naturally integrated forest mist, not a blank rectangular panel. New coherent 16:9 composition, ideally 2048x1152 or larger.
```

## 검증

- 실제 /forest 문서를 스크립트 차단 임시 iframe에서 열어 1280×720 가로·390×844 세로 로딩 배치를 확인했습니다. 검증용 임시 HTML은 제거했습니다.
- 새 이미지 HTTP 200 / image/png 및 서버·DB 상태 정상 응답을 확인했습니다.
- `/forest?loading=v147` 일반 실행에서 `forest-style-ready`, `forest-script-ready`, `phaser-world-ready` 상태와 로딩 화면 해제(`display:none`), 게임 캔버스 렌더링을 확인했습니다.
- `tests/test_carrot_forest_pixel_game.py`: 55개 통과. 새 이미지 규격·캐시 등록·preload·승인 슬로건 회귀 검증을 포함합니다.
- `node --check src/frontend/forest-sw.js`: 통과.
