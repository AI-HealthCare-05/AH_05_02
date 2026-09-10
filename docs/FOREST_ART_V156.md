# 메인 필드 그림체 가구 교체 — v156

2026-09-08. Built-in `image_gen` 모드로 기존 물건의 정체성과 시점을 유지하는 style-transfer 후, 필요한 이미지에 background-extraction을 수행했다. CLI/API 전환 또는 코드 기반 이미지 편집을 사용하지 않았다. 생성 결과를 파일 그대로 복사했다.

생성 원본 경로는 개인 Windows 계정 경로를 남기지 않도록 `${CODEX_HOME}` 기준으로 기록한다.

## 범위와 보존

- 메인 필드 `carrot-forest-world-v6.png`의 올리브·이끼색, 따뜻한 목재색, 계단형 픽셀 질감에 맞춘 가구 22개.
- 모닥불·분수 2개는 기존 v153 PNG와 기존 효과를 유지한다.
- 기존 24개 PNG는 `art-archive/furniture-before-v156/`에 원본 그대로 복사했으며 `furniture-v153/`도 유지했다.
- 그림은 각각 별도 파일로 생성한다. 전체 alpha 범위를 종횡비 유지해 정규화하므로 다른 물건의 파편이나 시트 경계가 끼지 않는다.
- 현재 배치·인벤토리 코드·캐릭터·저장된 코디·상호작용·동물은 변경하지 않았다.

## Root 8개: 최종 프롬프트와 파일

스타일 입력: Image1=`src/frontend/assets/carrot-forest-world-v6.png` (스타일만), Image2=`src/frontend/assets/furniture-v153/{code}.png` (변경 대상). 알파 추출 입력은 해당 첫 생성 결과 1장이다. 모든 입력은 사용 전 시각 검수했다.

### 공통 스타일 프롬프트

```
Use case: style-transfer. Asset type: one placeable 2D cozy forest game prop, isolated real transparent RGBA PNG. Image 1 is ONLY the art-style/perspective/palette reference, the current main field. Image 2 is the target object to restyle. Keep target subject identity, layout, relative proportions, facing direction and whole silhouette, but REPAINT to match Image 1: crisp visibly squared pixel clusters and stepped pixel edges, restrained matte warm-ochre/olive/moss palette, soft upper-left daylight, simple readable highlights like the wooden gate and pond in Image 1. Current target is too smooth shiny high-detail painted art. Replace that rendering with the field's coarser game pixel-art style, no glossy 3D shading, no soft airbrush gradients, no thick black outlines, no high-res painting microtexture. One complete object centered with 10 percent empty transparent margins on every side. True alpha transparency outside silhouette, NOT black background, NOT checkerboard painted pixels, NOT white background. No additional furniture, scene backdrop, grass island, label, text, frame, cast shadow or watermark. Output only the standalone replacement asset, not a scene mockup.
```

### pond

최종: `src/frontend/assets/furniture-v156/pond.png`

스타일 프롬프트 추가:

```
Primary request: Restyle the small oval decorative pond in Image 2. Preserve mossy grey rock ring, contained teal water, lily pads and a few white daisies; match exactly the main field pond stones and water color. It is NOT a fountain. Retain all water inside rock rim.
```

첫 출력: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-b82e1b6b-173b-4e06-8129-4c92925ca99d.png`

최종 알파 추출 프롬프트:

```
Use case: background-extraction. Image 1 is the edit target: a pixel-art small decorative pond sprite. Change ONLY the background: remove the currently baked gray-and-white checkerboard completely, both outside the object and from all openings between its parts. Deliver a genuinely TRANSPARENT PNG with an alpha channel (RGBA), with background alpha=0, NOT a picture of a transparency checkerboard, NOT white, NOT black, NOT any opaque color. Preserve the object's current pixels, style, colors, viewpoint, exact shape and composition. Keep all existing decorative vines and flowers attached to it. Do not add any object or shadow. Whole object visible with clear empty margin. It must composite cleanly over the game's meadow, without any gray or white boxes.
```

최종 생성 원본: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-458905cb-8788-492b-8f0a-41456a24922d.png`

### lantern

최종: `src/frontend/assets/furniture-v156/lantern.png`

스타일 프롬프트 추가:

```
Primary request: Restyle the standing rustic wood post and hanging brass lantern from Image 2. Preserve full post, small stone footing, vines, hook and entire hanging lamp. Muted aged brass rather than shiny gold, matching the lantern on the carrot house in Image1. Keep warm amber lamp center positioned as original for ON/OFF light effect.
```

첫 출력: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-a1d559c4-0b20-480b-bc34-e288b25c8474.png`

최종 알파 추출 프롬프트:

```
Use case: background-extraction. Image 1 is the edit target: a pixel-art standing lantern sprite. Change ONLY the background: remove the currently baked gray-and-white checkerboard completely, both outside the object and from all openings between its parts. Deliver a genuinely TRANSPARENT PNG with an alpha channel (RGBA), with background alpha=0, NOT a picture of a transparency checkerboard, NOT white, NOT black, NOT any opaque color. Preserve the object's current pixels, style, colors, viewpoint, exact shape and composition. Keep all existing decorative vines and flowers attached to it. Do not add any object or shadow. Whole object visible with clear empty margin. It must composite cleanly over the game's meadow, without any gray or white boxes.
```

최종 생성 원본: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-d82b7b88-edd0-436e-964e-460dea8467e5.png`

### flower_cart

최종: `src/frontend/assets/furniture-v156/flower_cart.png`

스타일 프롬프트 추가:

```
Primary request: Restyle the two-wheel wooden flower cart from Image2 with white daisies, a few warm orange flowers, handles and hanging cloth intact. Timber shading exactly like field's garden gate, foliage rendered as coarse olive pixel clusters. All handles/wheels fully visible.
Must return actual RGBA transparency, transparent-background cutout output.
```

첫 출력: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-4b109142-27ac-4acc-95ba-0cdc9fe58dcd.png`

최종 알파 추출 프롬프트:

```
Use case: background-extraction. Image 1 is the edit target: a pixel-art flower cart sprite. Change ONLY the background: remove the currently baked gray-and-white checkerboard completely, both outside the object and from all openings between its parts. Deliver a genuinely TRANSPARENT PNG with an alpha channel (RGBA), with background alpha=0, NOT a picture of a transparency checkerboard, NOT white, NOT black, NOT any opaque color. Preserve the object's current pixels, style, colors, viewpoint, exact shape and composition. Keep all existing decorative vines and flowers attached to it. Do not add any object or shadow. Whole object visible with clear empty margin. It must composite cleanly over the game's meadow, without any gray or white boxes.
```

최종 생성 원본: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-d2b84c33-72b6-42da-ba2f-c39f5efadc79.png`

### flower_pot

최종: `src/frontend/assets/furniture-v156/flower_pot.png`

스타일 프롬프트 추가:

```
Primary request: Restyle the terracotta flowerpot from Image2 with orange tulips and white daisies intact. More natural muted terracotta, small readable pixel blossoms like field flowers, no glossy sheen. Preserve pot, complete leaves and every top petal.
Must return actual RGBA transparency, transparent-background cutout output.
```

첫 출력: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-ffef7cfa-1846-42b0-ba88-34aca4b6864a.png`

최종 알파 추출 프롬프트:

```
Use case: background-extraction. Image 1 is the edit target: a pixel-art flower pot sprite. Change ONLY the background: remove the currently baked gray-and-white checkerboard completely, both outside the object and from all openings between its parts. Deliver a genuinely TRANSPARENT PNG with an alpha channel (RGBA), with background alpha=0, NOT a picture of a transparency checkerboard, NOT white, NOT black, NOT any opaque color. Preserve the object's current pixels, style, colors, viewpoint, exact shape and composition. Keep all existing decorative vines and flowers attached to it. Do not add any object or shadow. Whole object visible with clear empty margin. It must composite cleanly over the game's meadow, without any gray or white boxes.
```

최종 생성 원본: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-3bc0a7a8-0f0e-4973-8def-cf93eabcb01c.png`

### mushroom

최종: `src/frontend/assets/furniture-v156/mushroom.png`

스타일 프롬프트 추가:

```
Primary request: Restyle the cluster of three red-orange spotted mushrooms from Image2, preserving relative sizes, stems, and silhouette. Make shapes appear viewed from the field's top-down 3/4 camera (less view up under gills), matte low-contrast ochre stems and subdued caps. No ground base, no other objects.
Must return actual RGBA transparency, transparent-background cutout output.
```

첫 출력: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-785c7b1e-b5e3-44a4-b3ad-d7d1917d7597.png`

최종 알파 추출 프롬프트:

```
Remove the gray-and-white checkerboard background of this mushroom sprite. Make the background fully transparent. Keep the three mushrooms exactly unchanged. Output a clean transparent-background PNG cutout with no backdrop.
```

최종 생성 원본: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-5cedf678-5399-4df5-b457-950b3cc61727.png`

### duck_float

최종: `src/frontend/assets/furniture-v156/duck_float.png`

스타일 프롬프트 추가:

```
Primary request: Restyle the single cute yellow duck body from Image2 to fit the field's chunky top-down pixel art. Preserve compact rounded duck facing left with orange beak, small dark eyes, folded wings and tail. Natural pale golden yellow, no glossy toy highlights. Duck ONLY, no water/ripple/blue pixels/no float ring/no feet platform.
Must return actual RGBA transparency, transparent-background cutout output.
```

첫 출력: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-3cca6fe3-c750-4ada-9f42-fd11aa492327.png`

최종 알파 추출 프롬프트:

```
Use case: background-extraction. Image 1 is the edit target: a pixel-art yellow duck sprite. Change ONLY the background: remove the currently baked gray-and-white checkerboard completely, both outside the object and from all openings between its parts. Deliver a genuinely TRANSPARENT PNG with an alpha channel (RGBA), with background alpha=0, NOT a picture of a transparency checkerboard, NOT white, NOT black, NOT any opaque color. Preserve the object's current pixels, style, colors, viewpoint, exact shape and composition. Keep all existing decorative vines and flowers attached to it. Do not add any object or shadow. Whole object visible with clear empty margin. It must composite cleanly over the game's meadow, without any gray or white boxes.
```

최종 생성 원본: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-5f9f4f50-3f2a-408d-9444-f137ca24ed89.png`

### firefly_lantern

최종: `src/frontend/assets/furniture-v156/firefly_lantern.png`

스타일 프롬프트 추가:

```
Primary request: Restyle the portable brass/glass firefly lantern from Image2. Preserve handle, glass chamber, solid base, and a few tiny yellow-gold points inside the glass. Match matte brass pixel lamp in main field, NOT shiny 3D gold. Full lamp isolated, no external glow dots; points stay inside glass to preserve subtle runtime light animation.
Must return actual RGBA transparency, transparent-background cutout output.
```

첫 출력: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-7125bdc5-6eab-4258-8fbb-f0cc431910c1.png`

최종 알파 추출 프롬프트:

```
Use case: background-extraction. Image 1 is the edit target: a pixel-art firefly lantern sprite. Change ONLY the background: remove the currently baked gray-and-white checkerboard completely, both outside the object and from all openings between its parts. Deliver a genuinely TRANSPARENT PNG with an alpha channel (RGBA), with background alpha=0, NOT a picture of a transparency checkerboard, NOT white, NOT black, NOT any opaque color. Preserve the object's current pixels, style, colors, viewpoint, exact shape and composition. Keep all existing decorative vines and flowers attached to it. Do not add any object or shadow. Whole object visible with clear empty margin. It must composite cleanly over the game's meadow, without any gray or white boxes.
```

최종 생성 원본: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-dbd55d7d-64f3-41d7-9360-cbab71626105.png`

### garden_pinwheel

최종: `src/frontend/assets/furniture-v156/garden_pinwheel.png`

스타일 프롬프트 추가:

```
Primary request: Restyle the orange/olive four-bladed pinwheel from Image2. Preserve PRECISE upright structure/proportions: blade hub at horizontal 50%, 36% down the opaque silhouette; four blades reach to about 60% silhouette height, thin wooden pole continues to 85% and squat base occupies bottom15%. No new dangling parts. Blades orange and green with tiny cream marks; unadorned wooden pole and base. Crisp coarse pixel contours, matte colors. This is one static pose: not motion blur and not a rotated image. Full pole/base unchanged position for runtime blade-only hue effect.
Must return actual RGBA transparency, transparent-background cutout output.
```

첫 출력: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-d738e547-b227-4a09-8985-abdd1a27623e.png`

최종 알파 추출 프롬프트:

```
Use case: background-extraction. Image 1 is the edit target: a pixel-art garden pinwheel sprite. Change ONLY the background: remove the currently baked gray-and-white checkerboard completely, both outside the object and from all openings between its parts. Deliver a genuinely TRANSPARENT PNG with an alpha channel (RGBA), with background alpha=0, NOT a picture of a transparency checkerboard, NOT white, NOT black, NOT any opaque color. Preserve the object's current pixels, style, colors, viewpoint, exact shape and composition. Keep all existing decorative vines and flowers attached to it. Do not add any object or shadow. Whole object visible with clear empty margin. It must composite cleanly over the game's meadow, without any gray or white boxes.
```

최종 생성 원본: `${CODEX_HOME}\generated_images\019ff98f-395e-77e2-9645-c840802cef5e\exec-8a387664-0547-4481-9258-b2863db35515.png`

## 검수

- 새 이미지에 한해 거의 보이지 않는 alpha 1~15의 생성 잔여 여백을 크기 측정에서 제외한다. 원본 PNG는 수정하지 않는다. v153 모닥불·분수는 기존 alpha 1 기준을 그대로 유지한다. Phaser가 이미지를 blob URL로 불러오는 경우도 매니페스트의 이미지 식별 정보를 사용한다.
- 비파괴 시각 검수 페이지: `/static/forest-art-review-v156.html`. 게임에서 사용하는 실제 정규화 코드로 24개 물건을 메인 필드 잔디 위에 합성한다. 게임 상태·배치·코디를 저장하지 않는다.
- 초기 출력의 체크무늬는 실제 알파가 아닌 RGB 배경이어서 사용하지 않았다. 최종 RGBA, 투명 모서리, 불투명 본체를 확인한 파일만 연결했다.
- 버섯 첫 알파 재시도 `exec-cdd6ba47-e506-4029-86d2-b679b0003430.png`는 RGB라 제외했고 최종 단순한 배경 추출 프롬프트로 재시도했다.
- 나머지 14개 생성 과정: `FOREST_ART_V156_A.md`, `FOREST_ART_V156_B.md`.
- UI 변경 및 브라우저 검수: `FOREST_CONTROLS_ATTACK_V156.md`.

## 최종 연결 검증

- Node 숲 관련 테스트 143개, Python 숲 관련 테스트 56개: 총 199개 통과.
- 원본 모닥불·분수·메인 필드의 SHA-256, 화염 코드 무변경, 보관본 24개 바이트 동일성 검사 통과.
- 새 22개 실제 RGBA의 alpha 16 이상 실루엣이 원본 캔버스의 상하좌우 경계에 닿지 않는지 검사 통과.
- 최종 캐시: 신규 PNG/objects `20260908-2`, game/Phaser `20260908-3`, PWA `v156-2`. 보호 대상 두 PNG는 `20260907-1` 유지.
- 브라우저에서 검수 페이지 24/24 로딩, 실제 잔디 배경 합성으로 모든 물건의 실루엣·투명 배경·색감 확인. 최종 텐트 두 개를 새로고침하여 다시 확인했다.
- `/forest?furniture=v156` 재접속 시 로딩 포스터가 닫히고 게임 캔버스가 정상 생성된다. 8/9/0 버튼의 Y 위치·36px 높이·동일 3열 너비를 확인했으며 브라우저 경고/오류는 없었다.
- 저장된 코디와 배치한 분수 1개를 유지했으며 검수 과정에서 새 배치나 코디를 저장하지 않았다.
