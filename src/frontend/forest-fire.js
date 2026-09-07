/* Runtime flame ripple: reuse the original art; never distort the stone/log base. */
(() => {
  "use strict";
  const SIZE = 256, FRAMES = 16, ROOT_Y = 170, FLAME_BOTTOM = 184;
  const BASE_BOUNDS = Object.freeze({ x: 10, y: 103, width: 236, height: 143 });
  const offTiles = new WeakMap();
  const flameSources = new WeakMap(), burningTiles = new WeakMap();

  function flameMask(pixels) {
    const mask = new Uint8Array(SIZE * SIZE);
    // Above the rear stones, retain every flame pixel, including its neutral
    // antialias/outline. Below them, select only the hot central flame footprint.
    // The source stone ring and crossed logs are never used as a moving layer.
    for (let y = 24; y < FLAME_BOTTOM; y++) {
      for (let x = 80; x < 180; x++) {
        const i = (y * SIZE + x) * 4;
        const [r, g, b, a] = pixels.subarray(i, i + 4);
        if (!a) continue;
        const inBody = y < 120 ? x >= 98 && x <= 169
          : y < 145 ? x >= 86 && x <= 174
          : y < ROOT_Y ? x >= 100 && x <= 159
          : x >= 110 && x <= 147;
        const hot = r > 215 && r - b > 110 && (r - g > 30 || g > 150);
        const warmEdge = y < 151 && r > 110 && r - g > 35 && r - b > 65;
        if (y < 103 || (inBody && (hot || warmEdge))) mask[y * SIZE + x] = 1;
      }
    }
    return mask;
  }

  function rippleFrame(pixels, mask, frame, basePixels) {
    if (frame === 0 && !basePixels) return new Uint8ClampedArray(pixels);
    const output = new Uint8ClampedArray(basePixels || pixels);
    if (!basePixels) for (let i = 0; i < mask.length; i++) if (mask[i]) output.fill(0, i * 4, i * 4 + 4);
    const composite = (from, to) => {
      const alpha = pixels[from + 3] / 255, baseAlpha = output[to + 3] / 255;
      const combined = alpha + baseAlpha * (1 - alpha);
      if (!combined) return;
      for (let channel = 0; channel < 3; channel++) {
        output[to + channel] = (pixels[from + channel] * alpha + output[to + channel] * baseAlpha * (1 - alpha)) / combined;
      }
      output[to + 3] = combined * 255;
    };
    // The low flame root stays anchored over the shared ash center.
    for (let y = ROOT_Y; y < FLAME_BOTTOM; y++) for (let x = 80; x < 180; x++) {
      const index = y * SIZE + x;
      if (mask[index]) composite(index * 4, index * 4);
    }
    const phase = frame / FRAMES * Math.PI * 2;
    const stretch = 1 + Math.sin(phase) * .045;
    for (let y = 16; y < ROOT_Y; y++) {
      const sourceY = Math.round(ROOT_Y - (ROOT_Y - y) / stretch);
      if (sourceY < 0 || sourceY >= ROOT_Y) continue;
      const lift = Math.max(0, (ROOT_Y - y) / (ROOT_Y - 24));
      const dx = Math.round(lift * (7 * (Math.sin(phase + y / 23) - Math.sin(y / 23))
        + 3 * (Math.sin(phase * 2 + y / 11) - Math.sin(y / 11))));
      for (let x = 60; x < 200; x++) {
        const sourceX = x - dx;
        if (sourceX < 0 || sourceX >= SIZE || !mask[sourceY * SIZE + sourceX]) continue;
        composite((sourceY * SIZE + sourceX) * 4, (y * SIZE + x) * 4);
      }
    }
    return output;
  }

  function alphaBounds(pixels, width, height, threshold = 200) {
    let left = width, top = height, right = -1, bottom = -1;
    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
      if (pixels[(y * width + x) * 4 + 3] < threshold) continue;
      left = Math.min(left, x); right = Math.max(right, x);
      top = Math.min(top, y); bottom = Math.max(bottom, y);
    }
    return right < left ? null : { x: left, y: top, width: right - left + 1, height: bottom - top + 1 };
  }

  function fitBase(bounds) {
    const scale = Math.min(BASE_BOUNDS.width / bounds.width, BASE_BOUNDS.height / bounds.height);
    const width = Math.round(bounds.width * scale), height = Math.round(bounds.height * scale);
    return { x: Math.round(BASE_BOUNDS.x + (BASE_BOUNDS.width - width) / 2), y: BASE_BOUNDS.y + BASE_BOUNDS.height - height, width, height };
  }

  function offTile(atlas, baseSource) {
    // The same intact imagegen base is used for OFF and under every ON frame.
    // Do not cut a replacement ring out of the lit tile: its hidden stones cannot
    // be recovered by clearing pixels, and doing so leaves holes and old outlines.
    if (!baseSource) throw new Error("Campfire base artwork is required");
    if (offTiles.has(baseSource)) return offTiles.get(baseSource);
    const source = document.createElement("canvas");
    source.width = baseSource.naturalWidth || baseSource.width;
    source.height = baseSource.naturalHeight || baseSource.height;
    const sourceContext = source.getContext("2d", { willReadFrequently: true });
    sourceContext.drawImage(baseSource, 0, 0);
    const bounds = alphaBounds(sourceContext.getImageData(0, 0, source.width, source.height).data, source.width, source.height);
    if (!bounds) throw new Error("Campfire base artwork is empty");
    const target = fitBase(bounds);
    const tile = document.createElement("canvas");
    tile.width = tile.height = SIZE;
    const context = tile.getContext("2d", { willReadFrequently: true });
    context.imageSmoothingEnabled = false;
    // Measure the solid art, not the faint halo. Still draw the entire source so
    // its feathered alpha is not sliced into a visible rectangular edge.
    const scale = Math.min(BASE_BOUNDS.width / bounds.width, BASE_BOUNDS.height / bounds.height);
    context.drawImage(source, 0, 0, source.width, source.height,
      target.x - bounds.x * scale, target.y - bounds.y * scale, source.width * scale, source.height * scale);
    offTiles.set(baseSource, tile);
    return tile;
  }

  function burningTile(atlas, baseSource, frame = 0) {
    const index = ((Math.round(frame) % FRAMES) + FRAMES) % FRAMES;
    let baseCache = burningTiles.get(atlas);
    if (!baseCache) { baseCache = new WeakMap(); burningTiles.set(atlas, baseCache); }
    let frames = baseCache.get(baseSource);
    if (!frames) { frames = []; baseCache.set(baseSource, frames); }
    if (frames[index]) return frames[index];
    let flame = flameSources.get(atlas);
    if (!flame) {
      const source = document.createElement("canvas");
      source.width = source.height = SIZE;
      const context = source.getContext("2d", { willReadFrequently: true });
      context.drawImage(atlas, SIZE * 4, SIZE * 2, SIZE, SIZE, 0, 0, SIZE, SIZE);
      const pixels = context.getImageData(0, 0, SIZE, SIZE).data;
      flame = { pixels, mask: flameMask(pixels) };
      flameSources.set(atlas, flame);
    }
    const base = offTile(atlas, baseSource).getContext("2d").getImageData(0, 0, SIZE, SIZE).data;
    const tile = document.createElement("canvas");
    tile.width = tile.height = SIZE;
    tile.getContext("2d").putImageData(new ImageData(rippleFrame(flame.pixels, flame.mask, index, base), SIZE, SIZE), 0, 0);
    frames[index] = tile;
    return tile;
  }

  function install(scene, { flameAtlasKey = "storage-objects" } = {}) {
    const key = "campfire-ripple";
    // The visible furniture atlas now contains independently authored OFF art.
    // Keep the isolated legacy flame source explicit instead of reading its ring.
    const frame = scene.textures.getFrame(flameAtlasKey, 14);
    const baseSource = scene.textures.get("campfire-base-source").getSourceImage();
    const base = offTile(frame.source.image, baseSource);
    if (!scene.textures.exists("campfire-off")) {
      scene.textures.addCanvas("campfire-off", base);
    }
    if (!scene.textures.exists(key)) {
      const sheet = document.createElement("canvas");
      sheet.width = SIZE * FRAMES; sheet.height = SIZE;
      const target = sheet.getContext("2d");
      for (let index = 0; index < FRAMES; index++) {
        target.drawImage(burningTile(frame.source.image, baseSource, index), index * SIZE, 0);
      }
      scene.textures.addSpriteSheet(key, sheet, { frameWidth: SIZE, frameHeight: SIZE });
    }
    if (!scene.anims.exists("forest-campfire-burn")) {
      scene.anims.create({ key: "forest-campfire-burn", frames: scene.anims.generateFrameNumbers(key, { start: 0, end: FRAMES - 1 }), frameRate: 12, repeat: -1 });
    }
  }

  window.ForestFire = { install, flameMask, rippleFrame, offTile, burningTile, alphaBounds, fitBase, BASE_BOUNDS, SIZE, FRAMES };
})();
