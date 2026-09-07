/* One audited storage-atlas crop map for the world and every DOM thumbnail. */
(() => {
  "use strict";

  const STORAGE_TILE_SIZE = 256;
  const STORAGE_COLUMNS = 5;
  const STORAGE_ROWS = 4;
  const STORAGE_CODES = Object.freeze([
    "tent", "light_tent", "picnic_table", "bbq_table", "chair_green",
    "chair_red", "picnic_blanket", "pond", "lantern", "fence",
    "flower_cart", "flower_pot", "mushroom", "bench", "campfire",
    "mailbox", "scarecrow", "carrot_crate", "watering_can", "wheelbarrow",
  ]);
  const STORAGE_INDEX = Object.freeze(Object.fromEntries(STORAGE_CODES.map((code, index) => [code, index])));

  // The v4 PNG already contains neighbouring artwork INSIDE six logical cells.
  // These local [x, y, width, height] windows remove those fragments. They are
  // deliberately generous around the intended object, retaining antialiasing.
  // Do not stretch/recenter the crops: keep their original 256px tile positions,
  // so world scale, ground anchors and the campfire flame mask remain unchanged.
  const isolatedWindows = {
    lantern: [0, 0, 238, 256],             // fence fragment at x=240..245
    flower_cart: [0, 44, 256, 192],       // stray line y=42; mailbox at y=237..
    flower_pot: [0, 0, 256, 231],        // scarecrow hat at y=234..
    mushroom: [0, 0, 256, 230],          // carrot leaves at y=232..
    bench: [0, 0, 238, 256],             // campfire fragment at x=241..
    watering_can: [0, 0, 239, 256],      // wheelbarrow fragment at x=243..
  };
  const SOURCE_RECTS = Object.freeze(Object.fromEntries(STORAGE_CODES.map((code, index) => {
    const [x, y, width, height] = isolatedWindows[code] || [0, 0, 256, 256];
    return [code, Object.freeze([
      (index % STORAGE_COLUMNS) * STORAGE_TILE_SIZE + x,
      Math.floor(index / STORAGE_COLUMNS) * STORAGE_TILE_SIZE + y,
      width, height,
    ])];
  })));
  const atlasCache = new WeakMap();
  const ANIMATED_TILE_SIZE = 128;
  const ANIMATED_CODES = Object.freeze(["duck_float", "animated_fountain", "firefly_lantern", "garden_pinwheel"]);
  const ANIMATED_ROWS = Object.freeze(Object.fromEntries(ANIMATED_CODES.map((code, row) => [code, row])));
  // The generated v2 artwork crosses both nominal 128px row and column cuts.
  // Audited separation gaps are x=[0,132,256,378,512], y=[0,120,245,372,512].
  // Exact alpha bounds below retain complete tips, water jets and light motes.
  const animatedBounds = [
    [[10, 25, 129, 116], [136, 27, 255, 116], [259, 26, 377, 117], [380, 27, 500, 117]],
    [[13, 126, 127, 242], [136, 125, 250, 243], [260, 125, 374, 242], [380, 126, 494, 243]],
    [[21, 249, 118, 370], [147, 248, 243, 370], [266, 249, 370, 370], [390, 249, 493, 370]],
    [[29, 373, 109, 487], [154, 375, 235, 487], [275, 375, 355, 487], [395, 377, 475, 487]],
  ];
  const ANIMATED_FRAME_RECTS = Object.freeze(Object.fromEntries(ANIMATED_CODES.map((code, row) => [
    code, Object.freeze(animatedBounds[row].map(([left, top, right, bottom]) => Object.freeze([left, top, right - left, bottom - top]))),
  ])));
  const animatedAtlasCache = new WeakMap();

  function animatedFrameLayout(code, frame = 0) {
    const rectangles = ANIMATED_FRAME_RECTS[code];
    if (!rectangles) return null;
    const index = ((Math.trunc(Number(frame)) || 0) % 4 + 4) % 4;
    const source = rectangles[index];
    // One scale per animation row avoids frame-by-frame size pulsing.
    const maximum = Math.max(...rectangles.flatMap((rect) => [rect[2], rect[3]]));
    const scale = Math.min(1, 118 / maximum);
    const width = Math.round(source[2] * scale), height = Math.round(source[3] * scale);
    return { source, target: [Math.floor((128 - width) / 2), 124 - height, width, height], frame: index };
  }

  function createAnimatedAtlas(source) {
    if (!source || source.complete === false) return null;
    const width = source.naturalWidth ?? source.width, height = source.naturalHeight ?? source.height;
    if (!width || !height) return null;
    if (width !== 512 || height !== 512) throw new RangeError("Animated crop map requires the 512×512 v2 atlas");
    const sourceKey = source.currentSrc || source.src || "";
    const cached = animatedAtlasCache.get(source);
    if (cached?.sourceKey === sourceKey) return cached.canvas;
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 512;
    const context = canvas.getContext("2d");
    context.imageSmoothingEnabled = true;
    ANIMATED_CODES.forEach((code, row) => {
      for (let frame = 0; frame < 4; frame++) {
        const { source: rect, target } = animatedFrameLayout(code, frame);
        context.drawImage(source, ...rect, frame * 128 + target[0], row * 128 + target[1], target[2], target[3]);
      }
    });
    animatedAtlasCache.set(source, { sourceKey, canvas });
    return canvas;
  }

  function drawAnimatedItem(context, source, code, x, y, width, height, frame = 0) {
    const row = ANIMATED_ROWS[code], layout = animatedFrameLayout(code, frame);
    if (row == null || !layout) return false;
    const atlas = createAnimatedAtlas(source);
    if (!atlas) return false;
    context.drawImage(atlas, layout.frame * 128, row * 128, 128, 128, x, y, width, height);
    return true;
  }

  function createStorageAtlas(source) {
    if (!source || source.complete === false) return null;
    const width = source.naturalWidth ?? source.width;
    const height = source.naturalHeight ?? source.height;
    if (!width || !height) return null;
    if (width !== STORAGE_COLUMNS * STORAGE_TILE_SIZE || height !== STORAGE_ROWS * STORAGE_TILE_SIZE) {
      throw new RangeError("Storage crop map requires the 1280×1024 v4 atlas");
    }
    const sourceKey = source.currentSrc || source.src || "";
    const cached = atlasCache.get(source);
    if (cached?.sourceKey === sourceKey) return cached.canvas;
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    context.imageSmoothingEnabled = false;
    Object.values(SOURCE_RECTS).forEach(([x, y, cropWidth, cropHeight]) => {
      context.drawImage(source, x, y, cropWidth, cropHeight, x, y, cropWidth, cropHeight);
    });
    atlasCache.set(source, { sourceKey, canvas });
    return canvas;
  }

  function drawStorageItem(context, source, code, x, y, width, height) {
    const index = STORAGE_INDEX[code];
    if (index == null) return false;
    const atlas = createStorageAtlas(source);
    if (!atlas) return false;
    context.drawImage(atlas,
      (index % STORAGE_COLUMNS) * STORAGE_TILE_SIZE,
      Math.floor(index / STORAGE_COLUMNS) * STORAGE_TILE_SIZE,
      STORAGE_TILE_SIZE, STORAGE_TILE_SIZE, x, y, width, height);
    return true;
  }

  window.ForestObjects = Object.freeze({
    STORAGE_TILE_SIZE, STORAGE_COLUMNS, STORAGE_ROWS, STORAGE_CODES, STORAGE_INDEX,
    SOURCE_RECTS, createStorageAtlas, drawStorageItem,
    ANIMATED_TILE_SIZE, ANIMATED_CODES, ANIMATED_ROWS, ANIMATED_FRAME_RECTS,
    animatedFrameLayout, createAnimatedAtlas, drawAnimatedItem,
  });
})();
