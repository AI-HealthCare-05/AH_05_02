/* The garden artwork is an empty base; these six weeks own all 30 carrots. */
((root) => {
  "use strict";

  const assets = Object.freeze({
    background: Object.freeze({ key: "garden-bg", url: "/static/assets/carrot-forest-garden-v3.png?v=20260908-1" }),
    carrot: Object.freeze({ key: "garden-carrot", url: "/static/assets/garden-carrot-v168.png?v=20260908-1" }),
  });
  const columns = Object.freeze([255, 320, 440, 500, 560]);
  const rows = Object.freeze([124, 164, 204, 244, 284, 324].map((y, index) => Object.freeze({
    week: index + 1,
    label: `${index + 1}주차`,
    y,
    // Both signs and carrots use a bottom-center anchor in world coordinates.
    sign: Object.freeze({ x: 207, y, width: 43, height: 20, postHeight: 8 }),
    carrots: Object.freeze(columns.map(x => Object.freeze({ x, y, width: 36, height: 40 }))),
  })));
  const layout = Object.freeze({ width: 768, height: 512, weeks: 6, carrotsPerWeek: 5, totalCarrots: 30, rows });
  const measuredBounds = new WeakMap();

  function alphaBounds(pixels, width, height, threshold = 16) {
    if (!Number.isInteger(width) || !Number.isInteger(height) || width <= 0 || height <= 0
      || !pixels || pixels.length !== width * height * 4) return null;
    const minimum = Number.isFinite(threshold) ? Math.max(1, Math.min(255, threshold)) : 16;
    let left = width, top = height, right = -1, bottom = -1;
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        if (pixels[(y * width + x) * 4 + 3] < minimum) continue;
        left = Math.min(left, x); top = Math.min(top, y);
        right = Math.max(right, x); bottom = Math.max(bottom, y);
      }
    }
    return right < left ? null : Object.freeze({ x: left, y: top, width: right - left + 1, height: bottom - top + 1 });
  }

  function imageBounds(source) {
    const width = source?.naturalWidth || source?.width;
    const height = source?.naturalHeight || source?.height;
    if (!source || source.complete === false || !width || !height) return null;
    const cached = measuredBounds.get(source);
    if (cached && cached.width === width && cached.height === height) return cached.bounds;
    let bounds = Object.freeze({ x: 0, y: 0, width, height });
    if (root.document?.createElement) {
      const canvas = root.document.createElement("canvas");
      canvas.width = width; canvas.height = height;
      try {
        const context = canvas.getContext("2d", { willReadFrequently: true });
        context.drawImage(source, 0, 0);
        bounds = alphaBounds(context.getImageData(0, 0, width, height).data, width, height);
      } catch { /* Keep the source rectangle if a canvas cannot expose pixels. */ }
    }
    measuredBounds.set(source, { width, height, bounds });
    return bounds;
  }

  function drawSign(context, row) {
    const { x, y, width, height, postHeight } = row.sign;
    const left = Math.round(x - width / 2), top = y - height - postHeight;
    context.fillStyle = "rgba(54, 35, 19, .18)";
    context.fillRect(left + 2, top + 2, width, height);
    context.fillStyle = "#76502e";
    context.fillRect(x - 3, top + height, 6, postHeight);
    context.fillStyle = "#a67a43";
    context.fillRect(x - 2, top + height, 2, postHeight - 1);
    context.fillStyle = "#664127";
    context.fillRect(left, top, width, height);
    context.fillStyle = "#c9914e";
    context.fillRect(left + 1, top + 1, width - 2, height - 2);
    context.fillStyle = "#edc17d";
    context.fillRect(left + 2, top + 2, width - 4, 2);
    context.fillStyle = "#a46c39";
    context.fillRect(left + 2, top + height - 3, width - 4, 1);
    context.fillStyle = "#3f2a1b";
    context.font = '700 12px "Noto Sans KR", Pretendard, system-ui, sans-serif';
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(row.label, x, top + height / 2 + .5);
  }

  function draw(context, carrotImage, options = {}) {
    if (!context) return 0;
    const bounds = options.bounds || imageBounds(carrotImage);
    const ready = carrotImage && carrotImage.complete !== false && bounds?.width > 0 && bounds?.height > 0;
    let count = 0;
    context.save();
    context.imageSmoothingEnabled = false;
    for (const row of rows) {
      drawSign(context, row);
      if (!ready) continue;
      for (const carrot of row.carrots) {
        // Generated sprites may have large transparent borders. Trim to alpha
        // and uniformly fit the live silhouette; never squash the square file.
        const scale = Math.min(carrot.width / bounds.width, carrot.height / bounds.height);
        const width = bounds.width * scale, height = bounds.height * scale;
        context.drawImage(carrotImage, bounds.x, bounds.y, bounds.width, bounds.height,
          carrot.x - width / 2, carrot.y - height, width, height);
        count += 1;
      }
    }
    context.restore();
    return count;
  }

  function createLayerCanvas(carrotImage, { resolution = 4 } = {}) {
    if (!root.document?.createElement) return null;
    const density = Number.isFinite(resolution) ? Math.max(1, Math.min(8, resolution)) : 4;
    const canvas = root.document.createElement("canvas");
    canvas.width = Math.round(layout.width * density);
    canvas.height = Math.round(layout.height * density);
    const context = canvas.getContext("2d");
    if (!context) return null;
    context.scale(density, density);
    draw(context, carrotImage);
    return canvas;
  }

  const api = Object.freeze({ assets, layout, alphaBounds, draw, createLayerCanvas });
  root.ForestGarden = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window === "object" ? window : globalThis);
