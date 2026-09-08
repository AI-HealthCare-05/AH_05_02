/* Unmodified CC0 Ulti frames; share one pose contract across every renderer. */
((root) => {
  "use strict";
  const names = ["riverduck", "idle-2", "swim-1", "swim-2", "flee-1", "flee-2"];
  const assets = Object.freeze(names.map((name, index) => Object.freeze({
    key: index ? `forest-riverduck-${name}` : "forest-riverduck",
    url: `/static/assets/animals/riverduck-v160/${name}.png?v=20260908-1`,
    frameWidth: 96, frameHeight: 96,
  })));
  const loaded = new Map();
  let loading;
  // The original 96px frames have wide transparent padding. All poses use
  // the same authored contact line, never resize individual animation frames.
  const SCALE = .75;
  const WATERLINE = 87;
  const ORIGIN = Object.freeze({ x: .5, y: WATERLINE / 96 });
  function pose(state = {}, timeMs = 0) {
    const time = Number.isFinite(timeMs) ? Math.max(0, timeMs) : 0;
    const phase = state.moving ? Math.floor(time / (state.fleeing ? 120 : 320)) % 2 : Math.floor(time / 900) % 2;
    const index = (state.moving ? state.fleeing ? 4 : 2 : 0) + phase;
    return { key: assets[index].key, frame: 0, index, originX: ORIGIN.x, originY: ORIGIN.y,
      scale: SCALE, flipX: state.direction === "left" || (state.direction === "up" && state.headingX < 0) };
  }
  function loadImages() {
    if (!loading) loading = Promise.all(assets.map(asset => new Promise((resolve, reject) => {
      const image = new root.Image();
      image.onload = () => { loaded.set(asset.key, image); resolve(image); };
      image.onerror = () => reject(new Error(`리버덕 그림을 불러오지 못했습니다: ${asset.key}`));
      image.src = asset.url;
    }))).catch(error => { loading = null; throw error; });
    return loading;
  }
  function draw(context, firstImage, state, x = 0, y = 0, timeMs = 0) {
    const frame = pose(state, timeMs), image = loaded.get(frame.key) || firstImage;
    if (!image || image.complete === false || image.naturalWidth === 0) return;
    context.save(); context.imageSmoothingEnabled = false;
    context.translate(x, y); context.scale(frame.flipX ? -SCALE : SCALE, SCALE);
    // The source is a walking duck. Its submerged feet stay below the common
    // waterline; animate the original body/wing frames, not land legs on water.
    context.drawImage(image, 0, 0, 96, WATERLINE, -96 * ORIGIN.x, -WATERLINE, 96, WATERLINE);
    context.restore();
  }
  function thumbnail(context, image, width, height) {
    if (!image || image.complete === false || image.naturalWidth === 0) return;
    // Fit only the duck's visible extent, not 96px of transparent author padding.
    const source = { x: 15, y: 45, w: 51, h: WATERLINE - 45 };
    const scale = Math.min(width * .72 / source.w, height * .72 / source.h);
    context.imageSmoothingEnabled = false;
    context.drawImage(image, source.x, source.y, source.w, source.h,
      (width - source.w * scale) / 2, (height - source.h * scale) / 2, source.w * scale, source.h * scale);
  }
  function hitTest(state, x, y) {
    return Number.isFinite(x) && Number.isFinite(y) && x >= state.x - 24 && x <= state.x + 24
      && y >= state.y - 33 && y <= state.y + 3;
  }
  const api = Object.freeze({ asset: assets[0], assets, pose, draw, thumbnail, hitTest, loadImages, SCALE, ORIGIN, WATERLINE });
  root.ForestRiverDuckArt = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window === "object" ? window : globalThis);
