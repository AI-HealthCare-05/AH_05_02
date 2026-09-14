# 실내 그림체에 맞춘 LP 가구

- 생성 방식: 내장 이미지 생성 도구, 이미지 생성 스킬 사용. CLI/API 방식은 사용하지 않음.
- 참고 이미지: `src/frontend/assets/carrot-forest-home-v1.png`.
- 최종 실행 자산: `src/frontend/assets/home-record-player-cottage-v1.png` (RGBA, 256×363).
- 스타일: 꿀빛 원목, 올리브색 패널, 황동 톤암, 부드러운 픽셀 명암. 기존 단색 도형 LP는 제거.
- 후처리: 실제 알파 채널 검증 후 투명 여백만 잘라내고 비율을 유지해 축소. 배경 이미지에는 변경 없음.
- 배치: `(452, 320)` 바닥 기준, 76×108 표시. 원탁이 아닌 책장 아래 빈 바닥 사용.
- 재생 중에는 작은 음표로 상태 표시. 가구 전체를 회전·변형하지 않음.

## 생성 프롬프트

```text
Use case: stylized-concept
Asset type: single transparent-background game furniture sprite, wooden vinyl LP record player on a small matching wooden console cabinet.
Input image role: STYLE AND CAMERA REFERENCE ONLY, the existing cozy wooden cottage interior. Do not reproduce the room.
Primary request: create one isolated record-player furniture piece that looks like it belongs to the same illustrated pixel-art asset set as the provided room. Match the honey-oak wood grain, softly shaded edges, dark brown outlines, warm golden highlights, olive-green accent panel, and fine painterly pixel texture of its bookshelf and cabinets. Above-front 3/4 RPG room camera, front face horizontal and visible top surface, NOT a flat UI icon and NOT photorealistic. Compact wooden console with two short feet, a woven speaker grille on the front, a vinyl record and brass tonearm on the top, hinged lid open behind the turntable. The record should be clearly visible. Muted cream record label. No modern neon light.
Composition: one centered furniture object fully visible with generous transparent padding. Entire floor/background must be real alpha transparency, no baked checkerboard, no room, no floor tile, no ground patch, no large drop shadow, no text, no logo, no extra objects. High-quality cohesive cozy pixel-painted game sprite with clearly defined silhouette readable when scaled down to about 90x100 screen pixels.
```

## 투명 배경 수정 프롬프트

첫 결과가 RGB 체크무늬 배경이어서 아래 편집으로 RGBA 투명 배경을 확보했다.

```text
Use case: background-extraction. Edit target is the supplied wooden record player sprite. Keep the entire furniture exactly unchanged in shape, colors, pixel-painted texture, camera, and framing. Remove the entire white/light gray checkerboard background outside the furniture silhouette AND the space between its feet. Deliver an RGBA PNG with genuine alpha=0 transparency outside the furniture, not a drawing of a checkerboard, not white. No added floor or shadows. Only change the background to real transparency. Preserve the golden honey wood, olive panel, brass tonearm, cream vinyl label, and warm pixel-art details.
```
