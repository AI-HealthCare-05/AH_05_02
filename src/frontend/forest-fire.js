/* Runtime flame ripple: reuse the original art; never distort the stone/log base. */
(() => {
  "use strict";
  const SIZE = 256, FRAMES = 16, ROOT_Y = 170;

  function flameMask(pixels) {
    const mask = new Uint8Array(SIZE * SIZE);
    // This rectangle encloses only the flame in the normalized campfire tile.
    // Warm, luminous pixels are selected; grey stones and lower logs stay fixed.
    for (let y = 24; y < ROOT_Y; y++) {
      for (let x = 80; x < 180; x++) {
        const i = (y * SIZE + x) * 4;
        const [r, g, b, a] = pixels.subarray(i, i + 4);
        if (a && r > 150 && g > 24 && r - b > 55 && g > b * 1.1 && r >= g * .9) mask[y * SIZE + x] = 1;
      }
    }
    return mask;
  }

  function rippleFrame(pixels, mask, frame) {
    if (frame === 0) return new Uint8ClampedArray(pixels);
    const output = new Uint8ClampedArray(pixels);
    for (let i = 0; i < mask.length; i++) if (mask[i]) output.fill(0, i * 4, i * 4 + 4);
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
        const from = (sourceY * SIZE + sourceX) * 4, to = (y * SIZE + x) * 4;
        const alpha = pixels[from + 3] / 255, baseAlpha = output[to + 3] / 255;
        const combined = alpha + baseAlpha * (1 - alpha);
        for (let channel = 0; channel < 3; channel++) {
          output[to + channel] = (pixels[from + channel] * alpha + output[to + channel] * baseAlpha * (1 - alpha)) / combined;
        }
        output[to + 3] = combined * 255;
      }
    }
    return output;
  }

  function install(scene) {
    const key = "campfire-ripple";
    if (!scene.textures.exists(key)) {
      const frame = scene.textures.getFrame("storage-objects", 14);
      const tile = document.createElement("canvas");
      tile.width = tile.height = SIZE;
      const ctx = tile.getContext("2d", { willReadFrequently: true });
      ctx.drawImage(frame.source.image, frame.cutX, frame.cutY, SIZE, SIZE, 0, 0, SIZE, SIZE);
      const original = ctx.getImageData(0, 0, SIZE, SIZE).data;
      const mask = flameMask(original);
      const sheet = document.createElement("canvas");
      sheet.width = SIZE * FRAMES; sheet.height = SIZE;
      const target = sheet.getContext("2d");
      for (let index = 0; index < FRAMES; index++) {
        target.putImageData(new ImageData(rippleFrame(original, mask, index), SIZE, SIZE), index * SIZE, 0);
      }
      scene.textures.addSpriteSheet(key, sheet, { frameWidth: SIZE, frameHeight: SIZE });
    }
    if (!scene.anims.exists("forest-campfire-burn")) {
      scene.anims.create({ key: "forest-campfire-burn", frames: scene.anims.generateFrameNumbers(key, { start: 0, end: FRAMES - 1 }), frameRate: 12, repeat: -1 });
    }
  }

  window.ForestFire = { install, flameMask, rippleFrame, SIZE, FRAMES };
})();
