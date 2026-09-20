# 당근밭 6주차 레이아웃 이미지 프롬프트

생성 방식: 내장 image_gen. 기존 파일은 보존하고 새 파일로 적용합니다.

## 배경 편집

참조: `src/frontend/assets/carrot-forest-garden-v2.png`

```text
Use case: precise-object-edit.
Asset type: final 2D top-down oblique pixel-art game background, 1536x1024 landscape.
Input image 1 is the existing editable game garden.
Change ONLY the planted field interior and the closed gate, preserving the exact camera, framing, crisp detailed pixel/storybook style, warm brown soil and green forest palette, trees, fence perimeter, irrigation channels, bottom-left wooden bucket, bottom-right watering can and central walkway.
REMOVE EVERY carrot and every sprout/leaf inside the two brown cultivated soil plots. They will be rendered separately by the game, so leave both soil plots COMPLETELY EMPTY with NO vegetables.
Organize the empty soil as SIX subtle horizontal rows across each side of the center path, at image y approximately 248,328,408,488,568,648. Empty row furrows, no plants, no signs, no text.
REMOVE the two shut wooden gate leaves at the bottom center, including the center divider, handles and all crossbars within the opening. Keep the two sturdy outer gateposts at approximately x560 and950, but between them show an unobstructed dirt path continuous from the central farm path to the foreground. No door, no gate, no closed fence across the entrance. Do not add new props, people, animals, lettering or watermarks. Preserve the surrounding illustration and its crispness, do not blur or globally recolor.
```
## 당근 스프라이트

참조: `src/frontend/assets/carrot-forest-garden-v2.png` (스타일 참조)

```text
Use case: background-extraction and game sprite.
Input image 1 is STYLE REFERENCE, the garden from which to derive ONE matching carrot plant.
Create one isolated planted carrot sprite as seen in this exact top-down oblique storybook pixel art garden: a compact cluster of crisp green carrot leaves at the top and a short broad orange carrot root shoulder peeking above the ground at the bottom. Orange shoulder must be visible and readable. It is a growing carrot, NOT a full long harvested carrot. Use the same small blocky pixel clusters, brown/olive shading, golden gentle light, and sharp edges as the reference. Only ONE carrot plant, no other objects, no soil platform, no background, no pot, no UI or letters.
Genuinely transparent RGBA background with real alpha, no checkerboard drawn into the art. Tight centered sprite with modest transparent padding, full leaves and carrot shoulder visible uncropped. Square canvas. Do not add cast shadow outside the sprite.
```

## 적용 파일

- 배경: `src/frontend/assets/carrot-forest-garden-v3.png`
- 투명 당근: `src/frontend/assets/garden-carrot-v168.png`
- 표지판과 정확한 6 × 5 배치: `src/frontend/forest-garden.js`

원본 v2 배경은 보존했습니다. 메인 필드와 집 안 배경은 이번 변경에 포함하지 않습니다.
