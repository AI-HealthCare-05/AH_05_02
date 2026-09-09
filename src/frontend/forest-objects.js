/* Individually authored furniture: complete alpha silhouettes, shared world/thumbnail atlases. */
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
  const RESTORED_CODES = Object.freeze(["lantern", "mailbox", "scarecrow", "carrot_crate", "wheelbarrow"]);

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
  const INDIVIDUAL_ASSETS = Object.freeze([...STORAGE_CODES, ...ANIMATED_CODES].map(code => Object.freeze({
    code, key: `furniture-${code}`,
    // Restore the complete pre-carrot-house furniture set. Campfire and
    // fountain already used these exact protected originals; cow and
    // riverduck are loaded from their dedicated manifests elsewhere.
    url: RESTORED_CODES.includes(code)
      ? `/static/assets/carrot-forest-storage-atlas-v3.png?v=20260909-${code}`
      : `/static/assets/furniture-v153/${code}.png?v=20260907-1`,
    kind: Object.hasOwn(STORAGE_INDEX, code) ? "storage" : "animated",
  })));
  const individualAtlasCache = new WeakMap(), hybridStorageCache = new WeakMap(), alphaBoundsCache = new WeakMap(), individualImageSources = new WeakMap();
  let individualImages = null, individualLoadRequired = false, individualLoadPromise = null;

  function imageDimensions(image) {
    if (!image || image.complete === false) return null;
    const width = image.naturalWidth ?? image.width, height = image.naturalHeight ?? image.height;
    return width > 0 && height > 0 ? { width, height } : null;
  }

  function alphaBounds(pixels, width, height, minimumAlpha = 1) {
    const threshold = Number.isFinite(minimumAlpha) ? Math.max(1, Math.min(255, Math.round(minimumAlpha))) : 1;
    let left = width, top = height, right = -1, bottom = -1;
    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
      if (pixels[(y * width + x) * 4 + 3] < threshold) continue;
      left = Math.min(left, x); right = Math.max(right, x);
      top = Math.min(top, y); bottom = Math.max(bottom, y);
    }
    return right < left ? null : { x: left, y: top, width: right - left + 1, height: bottom - top + 1 };
  }

  function individualFrameLayout(bounds, tileSize = STORAGE_TILE_SIZE) {
    if (!bounds || bounds.width <= 0 || bounds.height <= 0) return null;
    const padding = Math.round(tileSize * 12 / STORAGE_TILE_SIZE);
    const scale = Math.min((tileSize - padding * 2) / bounds.width, (tileSize - padding * 2) / bounds.height);
    const width = Math.round(bounds.width * scale), height = Math.round(bounds.height * scale);
    return {
      source: [bounds.x, bounds.y, bounds.width, bounds.height],
      target: [Math.floor((tileSize - width) / 2), tileSize - padding - height, width, height],
      scale, padding,
    };
  }

  function measuredImageBounds(image) {
    const size = imageDimensions(image);
    if (!size) throw new Error("Individual furniture image is not loaded");
    const source = String(image.currentSrc || image.src || "");
    // Phaser's XHR image loader replaces original URLs with blob: URLs. Keep
    // the trusted manifest identity separately rather than relying on .src.
    const manifestSource = individualImageSources.get(image) || "";
    // v156 generators may leave nearly invisible alpha-1 halos far from the
    // object. Only those new files use a visible-alpha fitting threshold;
    // v153 fire/fountain and every existing caller retain their original fit.
    const minimumAlpha = 1;
    const sourceKey = `${manifestSource}:${source}:${size.width}:${size.height}:${minimumAlpha}`;
    const cached = alphaBoundsCache.get(image);
    if (cached?.sourceKey === sourceKey) return cached.bounds;
    const canvas = document.createElement("canvas");
    canvas.width = size.width; canvas.height = size.height;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(image, 0, 0, size.width, size.height, 0, 0, size.width, size.height);
    const bounds = alphaBounds(context.getImageData(0, 0, size.width, size.height).data, size.width, size.height, minimumAlpha);
    if (!bounds) throw new Error("Individual furniture image is fully transparent");
    alphaBoundsCache.set(image, { sourceKey, bounds });
    return bounds;
  }

  function createIndividualTile(image, tileSize = STORAGE_TILE_SIZE) {
    const layout = individualFrameLayout(measuredImageBounds(image), tileSize);
    const tile = document.createElement("canvas");
    tile.width = tile.height = tileSize;
    const context = tile.getContext("2d");
    context.imageSmoothingEnabled = true;
    context.drawImage(image, ...layout.source, ...layout.target);
    return tile;
  }

  function createIndividualAtlas(images, kind) {
    const codes = kind === "storage" ? STORAGE_CODES : ANIMATED_CODES;
    if (!images || codes.some(code => !imageDimensions(images[code]))) throw new Error(`Missing required ${kind} furniture PNG`);
    const sourceKey = codes.map(code => {
      const image = images[code], size = imageDimensions(image);
      return `${code}:${individualImageSources.get(image) || ""}:${image.currentSrc || image.src || ""}:${size.width}:${size.height}`;
    }).join("|");
    let cached = individualAtlasCache.get(images);
    if (cached?.[kind]?.sourceKey === sourceKey) return cached[kind].canvas;
    if (!cached) { cached = {}; individualAtlasCache.set(images, cached); }
    const tileSize = kind === "storage" ? STORAGE_TILE_SIZE : ANIMATED_TILE_SIZE;
    const columns = kind === "storage" ? STORAGE_COLUMNS : 4;
    const canvas = document.createElement("canvas");
    canvas.width = columns * tileSize;
    canvas.height = kind === "storage" ? STORAGE_ROWS * tileSize : ANIMATED_CODES.length * tileSize;
    const context = canvas.getContext("2d");
    context.imageSmoothingEnabled = true;
    codes.forEach((code, index) => {
      const image = images[code];
      // Normalize in a dedicated tile first. No draw can ever read pixels from
      // another object's source PNG or spill visible artwork into its neighbor.
      const tile = createFurnitureTile(image, code, tileSize);
      const copies = kind === "storage" ? 1 : 4;
      for (let frame = 0; frame < copies; frame++) {
        const column = kind === "storage" ? index % columns : frame;
        const row = kind === "storage" ? Math.floor(index / columns) : index;
        context.drawImage(tile, 0, 0, tileSize, tileSize, column * tileSize, row * tileSize, tileSize, tileSize);
      }
    });
    cached[kind] = { sourceKey, canvas };
    return canvas;
  }

  function createFurnitureTile(image, code, tileSize = STORAGE_TILE_SIZE) {
    const size = imageDimensions(image);
    if (!RESTORED_CODES.includes(code) || size?.width !== 1280 || size?.height !== 1024) return createIndividualTile(image, tileSize);
    // The older safe-cell source contains the complete hat, post and handles.
    // Isolate before measuring alpha so neighbouring furniture never affects fit.
    const index = STORAGE_INDEX[code];
    const isolated = document.createElement("canvas");
    isolated.width = isolated.height = 256;
    isolated.getContext("2d").drawImage(image, (index % 5) * 256, Math.floor(index / 5) * 256, 256, 256, 0, 0, 256, 256);
    const fitted = createIndividualTile(isolated, tileSize);
    // Match the field's pixel cadence without recolouring the original palette.
    const pixels = document.createElement("canvas");
    pixels.width = pixels.height = tileSize / 2;
    const sample = pixels.getContext("2d");
    sample.imageSmoothingEnabled = false;
    sample.drawImage(fitted, 0, 0, tileSize, tileSize, 0, 0, pixels.width, pixels.height);
    const tile = document.createElement("canvas");
    tile.width = tile.height = tileSize;
    const context = tile.getContext("2d");
    context.imageSmoothingEnabled = false;
    context.drawImage(pixels, 0, 0, pixels.width, pixels.height, 0, 0, tileSize, tileSize);
    return tile;
  }

  function createStorageAtlasFromImages(images, legacySource = null) {
    if (!legacySource) return createIndividualAtlas(images, "storage");
    const cached = hybridStorageCache.get(legacySource);
    if (cached?.images === images) return cached.canvas;
    const legacy = createLegacyStorageAtlas(legacySource);
    const canvas = document.createElement("canvas");
    canvas.width = STORAGE_COLUMNS * STORAGE_TILE_SIZE;
    canvas.height = STORAGE_ROWS * STORAGE_TILE_SIZE;
    const context = canvas.getContext("2d");
    context.imageSmoothingEnabled = false;
    STORAGE_CODES.forEach((code, index) => {
      const x = (index % STORAGE_COLUMNS) * STORAGE_TILE_SIZE;
      const y = Math.floor(index / STORAGE_COLUMNS) * STORAGE_TILE_SIZE;
      if (code === "campfire" || RESTORED_CODES.includes(code)) {
        // The current animated campfire is intentionally retained.
        context.drawImage(createFurnitureTile(images[code], code), 0, 0, STORAGE_TILE_SIZE, STORAGE_TILE_SIZE, x, y, STORAGE_TILE_SIZE, STORAGE_TILE_SIZE);
      } else {
        // Every ordinary furniture item comes from the pre-carrot-house v4
        // atlas, not from the later individually generated illustration pack.
        context.drawImage(legacy, x, y, STORAGE_TILE_SIZE, STORAGE_TILE_SIZE, x, y, STORAGE_TILE_SIZE, STORAGE_TILE_SIZE);
      }
    });
    hybridStorageCache.set(legacySource, { images, canvas });
    return canvas;
  }
  function createAnimatedAtlasFromImages(images) { return createIndividualAtlas(images, "animated"); }

  function registerIndividualImages(images) {
    if (INDIVIDUAL_ASSETS.some(asset => !imageDimensions(images?.[asset.code]))) throw new Error("All 24 individual furniture PNGs must be loaded before registration");
    INDIVIDUAL_ASSETS.forEach(asset => individualImageSources.set(images[asset.code], asset.url));
    individualImages = Object.freeze(Object.fromEntries(INDIVIDUAL_ASSETS.map(asset => [asset.code, images[asset.code]])));
    individualLoadRequired = true;
    return individualImages;
  }

  function loadIndividualAssets() {
    individualLoadRequired = true; // Suppress legacy-art flashes from this point onward.
    if (individualImages) return Promise.resolve(individualImages);
    if (individualLoadPromise) return individualLoadPromise;
    individualLoadPromise = Promise.all(INDIVIDUAL_ASSETS.map(asset => new Promise((resolve, reject) => {
      const image = new window.Image();
      image.onload = () => resolve([asset.code, image]);
      image.onerror = () => reject(new Error(`Unable to load furniture artwork: ${asset.code}`));
      image.src = asset.url;
    }))).then(entries => registerIndividualImages(Object.fromEntries(entries)));
    return individualLoadPromise;
  }

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

  function createLegacyAnimatedAtlas(source) {
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

  function createAnimatedAtlas(source) {
    if (individualImages) return createAnimatedAtlasFromImages(individualImages);
    return individualLoadRequired ? null : createLegacyAnimatedAtlas(source);
  }

  function drawAnimatedItem(context, source, code, x, y, width, height, frame = 0) {
    const row = ANIMATED_ROWS[code], layout = animatedFrameLayout(code, frame);
    if (row == null || !layout) return false;
    const atlas = createAnimatedAtlas(source);
    if (!atlas) return false;
    context.drawImage(atlas, layout.frame * 128, row * 128, 128, 128, x, y, width, height);
    return true;
  }

  function createLegacyStorageAtlas(source) {
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

  function createStorageAtlas(source) {
    if (individualImages) return createStorageAtlasFromImages(individualImages, source);
    return individualLoadRequired ? null : createLegacyStorageAtlas(source);
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
    SOURCE_RECTS, RESTORED_CODES, createStorageAtlas, drawStorageItem,
    ANIMATED_TILE_SIZE, ANIMATED_CODES, ANIMATED_ROWS, ANIMATED_FRAME_RECTS,
    animatedFrameLayout, createAnimatedAtlas, drawAnimatedItem,
    INDIVIDUAL_ASSETS, alphaBounds, individualFrameLayout, createIndividualTile,
    createStorageAtlasFromImages, createAnimatedAtlasFromImages,
    registerIndividualImages, loadIndividualAssets, createLegacyStorageAtlas, createLegacyAnimatedAtlas,
    get individualReady() { return Boolean(individualImages); },
  });
})();
