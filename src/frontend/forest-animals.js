/* Downloaded LPC animal frames. See assets/animals/ATTRIBUTION.md for source licenses. */
((root) => {
  "use strict";
  const directory = "/static/assets/animals/";
  const assets = Object.freeze([
    Object.freeze({ key: "forest-cow-eat", url: `${directory}lpc-cow-eat.png`, frameWidth: 128, frameHeight: 128 }),
    Object.freeze({ key: "forest-cow-walk", url: `${directory}lpc-cow-walk.png`, frameWidth: 128, frameHeight: 128 }),
    Object.freeze({ key: "forest-rabbit", url: `${directory}lpc-rabbit.png`, frameWidth: 72, frameHeight: 72 }),
  ]);
  const rows = Object.freeze({ up: 0, left: 1, down: 2, right: 3 });
  const cowFootY = Object.freeze([110 / 128, 88 / 128, 102 / 128, 88 / 128]);
  const reactionColumns = Object.freeze([0, 1, 2, 3, 3, 2, 1, 0]);
  const cowReactionFrameMs = 170;
  const cowReactionDurationMs = reactionColumns.length * cowReactionFrameMs;
  const mooUrl = `${directory}cow-moo-joseph-sardin-cc0.mp3`;

  function directionRow(direction, fallback = "down") {
    return Object.hasOwn(rows, direction) ? rows[direction] : rows[fallback];
  }

  // A negative/missing elapsed time is a genuinely still animal. It never advances
  // frames on its own. A finite touch reaction returns to exactly the same pose.
  function cowFrame(elapsedMs = -1, { direction = "left", reducedMotion = false } = {}) {
    const row = directionRow(direction, "left");
    const reacting = Number.isFinite(elapsedMs) && elapsedMs >= 0 && elapsedMs < cowReactionDurationMs;
    const column = reacting && !reducedMotion ? reactionColumns[Math.floor(elapsedMs / cowReactionFrameMs)] : 0;
    return {
      key: "forest-cow-eat", frame: row * 4 + column, done: !reacting,
      originX: 0.5, originY: cowFootY[row],
    };
  }

  // The sheet contains the natural hop displacement already. Do not add a sine
  // bounce or stretch the body. Lower rows are the source's grazing poses.
  function rabbitFrame(direction = "down", moving = false, elapsedMs = 0, reducedMotion = false) {
    const row = directionRow(direction);
    const time = Number.isFinite(elapsedMs) ? Math.max(0, elapsedMs) : 0;
    const column = reducedMotion ? 0 : Math.floor(time / (moving ? 140 : 330)) % 4;
    return {
      key: "forest-rabbit", frame: (moving ? row : row + 4) * 4 + column,
      originX: 0.5, originY: 51 / 72,
    };
  }

  function frameRect(key, frame) {
    const asset = assets.find(item => item.key === key);
    const frameCount = key === "forest-rabbit" ? 32 : 16;
    if (!asset || !Number.isInteger(frame) || frame < 0 || frame >= frameCount) return null;
    return {
      x: (frame % 4) * asset.frameWidth, y: Math.floor(frame / 4) * asset.frameHeight,
      width: asset.frameWidth, height: asset.frameHeight,
    };
  }

  let moo = null;
  let lastMooAt = -Infinity;
  function playMoo({ enabled = true, volume = 0.32, nowMs = Date.now() } = {}) {
    if (!enabled || typeof root.Audio !== "function" || nowMs - lastMooAt < 1400) return false;
    lastMooAt = nowMs;
    if (!moo) {
      moo = new root.Audio(mooUrl);
      moo.preload = "none";
    }
    const safeVolume = Number.isFinite(volume) ? Math.max(0, Math.min(1, volume)) : 0.32;
    moo.pause();
    moo.currentTime = 0;
    moo.volume = safeVolume;
    try {
      const playing = moo.play();
      if (playing && typeof playing.catch === "function") playing.catch(() => {});
    } catch {
      return false;
    }
    return true;
  }

  const api = Object.freeze({ assets, cowFrame, rabbitFrame, frameRect, mooUrl, playMoo, cowReactionDurationMs });
  root.ForestAnimals = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window === "object" ? window : globalThis);
