const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const zlib = require('node:zlib');

// Read actual PNG pixels with Node's built-ins; no browser/native dependency.
function readRgbaPng(file) {
  const png = fs.readFileSync(file), chunks = [];
  const width = png.readUInt32BE(16), height = png.readUInt32BE(20);
  assert.equal(png[24], 8, 'fixture must use 8-bit channels');
  assert.equal(png[25], 6, 'fixture must use RGBA channels');
  assert.equal(png[28], 0, 'fixture must not be interlaced');
  for (let offset = 8; offset < png.length;) {
    const size = png.readUInt32BE(offset);
    if (png.toString('ascii', offset + 4, offset + 8) === 'IDAT') chunks.push(png.subarray(offset + 8, offset + 8 + size));
    offset += size + 12;
  }
  const packed = zlib.inflateSync(Buffer.concat(chunks));
  const pixels = new Uint8ClampedArray(width * height * 4), stride = width * 4;
  function paeth(a, b, c) {
    const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
    return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
  }
  for (let y = 0; y < height; y++) {
    const filter = packed[y * (stride + 1)];
    assert.ok(filter <= 4);
    for (let x = 0; x < stride; x++) {
      const i = y * stride + x, left = x >= 4 ? pixels[i - 4] : 0;
      const above = y ? pixels[i - stride] : 0, upperLeft = y && x >= 4 ? pixels[i - stride - 4] : 0;
      const prediction = [0, left, above, Math.floor((left + above) / 2), paeth(left, above, upperLeft)][filter];
      pixels[i] = (packed[y * (stride + 1) + 1 + x] + prediction) & 255;
    }
  }
  return { width, height, naturalWidth: width, naturalHeight: height, complete: true, pixels };
}

function setup() {
  const canvases = [];
  const document = { createElement(tag) {
    assert.equal(tag, 'canvas');
    const canvas = { width: 0, height: 0, calls: [] };
    canvas.getContext = () => {
      canvas.pixels ||= new Uint8ClampedArray(canvas.width * canvas.height * 4);
      return { drawImage(source, sx, sy, sw, sh, dx, dy, dw, dh) {
        canvas.calls.push([source, sx, sy, sw, sh, dx, dy, dw, dh]);
        if (!source.pixels) return;
        for (let y = 0; y < dh; y++) {
          const sourceY = sy + Math.floor(y * sh / dh);
          for (let x = 0; x < dw; x++) {
            const start = (sourceY * source.width + sx + Math.floor(x * sw / dw)) * 4;
            canvas.pixels.set(source.pixels.subarray(start, start + 4), ((dy + y) * canvas.width + dx + x) * 4);
          }
        }
      } };
    };
    canvases.push(canvas);
    return canvas;
  } };
  const window = {};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../src/frontend/forest-objects.js'), 'utf8'), { window, document });
  return { api: window.ForestObjects, canvases };
}

const source = readRgbaPng(path.join(__dirname, '../src/frontend/assets/carrot-forest-storage-atlas-v4.png'));
const alpha = (image, x, y) => image.pixels[(y * image.width + x) * 4 + 3];

test('shared crop map covers all twenty stable frames and preserves native coordinates', () => {
  const { api } = setup(), result = api.createStorageAtlas(source);
  assert.equal(api.STORAGE_CODES.length, 20);
  assert.equal(api.STORAGE_INDEX.campfire, 14);
  assert.deepEqual([result.width, result.height], [1280, 1024]);
  assert.equal(result.calls.length, 20);
  for (const [index, code] of Array.from(api.STORAGE_CODES).entries()) {
    assert.equal(api.STORAGE_INDEX[code], index);
    const [sx, sy, sw, sh] = api.SOURCE_RECTS[code];
    assert.ok(sx >= index % 5 * 256 && sx + sw <= (index % 5 + 1) * 256);
    assert.ok(sy >= Math.floor(index / 5) * 256 && sy + sh <= (Math.floor(index / 5) + 1) * 256);
    const call = result.calls[index];
    assert.deepEqual(call.slice(1, 5), call.slice(5, 9));
  }
});

test('actual neighboring fragments and stray line disappear from all six affected frames', () => {
  const { api } = setup(), result = api.createStorageAtlas(source);
  const fragments = {
    lantern: [[240, 187, 246, 212]],
    flower_cart: [[115, 237, 179, 246], [116, 42, 130, 43]],
    flower_pot: [[81, 234, 147, 246]],
    mushroom: [[85, 232, 187, 246]],
    bench: [[241, 186, 246, 220]],
    watering_can: [[243, 211, 246, 229]],
  };
  for (const [code, regions] of Object.entries(fragments)) {
    const index = api.STORAGE_INDEX[code], ox = index % 5 * 256, oy = Math.floor(index / 5) * 256;
    for (const [left, top, right, bottom] of regions) {
      let oldVisible = 0;
      for (let y = top; y < bottom; y++) for (let x = left; x < right; x++) {
        if (alpha(source, ox + x, oy + y) > 12) oldVisible++;
        assert.equal(alpha(result, ox + x, oy + y), 0, `${code} fragment at ${x},${y}`);
      }
      assert.ok(oldVisible > 0, `${code} must exercise real pre-fix visible contamination`);
    }
  }
});

test('all twenty main silhouettes retain every visible pixel at exactly the same position', () => {
  const { api } = setup(), result = api.createStorageAtlas(source);
  for (const code of api.STORAGE_CODES) {
    const index = api.STORAGE_INDEX[code], ox = index % 5 * 256, oy = Math.floor(index / 5) * 256;
    const seen = new Uint8Array(256 * 256), components = [];
    for (let y = 0; y < 256; y++) for (let x = 0; x < 256; x++) {
      const point = y * 256 + x;
      if (seen[point] || alpha(source, ox + x, oy + y) <= 12) continue;
      const queue = [point]; seen[point] = 1;
      for (let current = 0; current < queue.length; current++) {
        const px = queue[current] % 256, py = Math.floor(queue[current] / 256);
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
          const nx = px + dx, ny = py + dy, next = ny * 256 + nx;
          if (nx < 0 || nx >= 256 || ny < 0 || ny >= 256 || seen[next] || alpha(source, ox + nx, oy + ny) <= 12) continue;
          seen[next] = 1; queue.push(next);
        }
      }
      components.push(queue);
    }
    const main = components.sort((a, b) => b.length - a.length)[0];
    assert.ok(main.length > 10000, `${code} must retain its complete main artwork`);
    for (const point of main) {
      const offset = ((oy + Math.floor(point / 256)) * source.width + ox + point % 256) * 4;
      for (let channel = 0; channel < 4; channel++) assert.equal(result.pixels[offset + channel], source.pixels[offset + channel], `${code} pixel ${point}`);
    }
  }
});

test('DOM drawing consumes the same cached atlas as Phaser, not the contaminated PNG', () => {
  const { api, canvases } = setup(), shared = api.createStorageAtlas(source), calls = [];
  const target = { drawImage(...args) { calls.push(args); } };
  assert.equal(api.drawStorageItem(target, source, 'flower_cart', 4, 5, 76, 76), true);
  assert.equal(calls[0][0], shared);
  assert.deepEqual(calls[0].slice(1), [0, 512, 256, 256, 4, 5, 76, 76]);
  assert.equal(canvases.length, 1);
  assert.equal(api.drawStorageItem(target, source, 'missing', 0, 0, 76, 76), false);
  assert.equal(api.createStorageAtlas({ complete: false }), null);
  assert.equal(api.createStorageAtlas({ naturalWidth: 0, naturalHeight: 0 }), null);
  assert.throws(() => api.createStorageAtlas({ width: 1280, height: 1000 }), /1280×1024/);
});

const animatedSource = readRgbaPng(path.join(__dirname, '../src/frontend/assets/carrot-forest-animated-objects-v2.png'));

test('all animated frames include the complete alpha silhouette inside separated source regions', () => {
  const { api } = setup();
  const xs = [0, 132, 256, 378, 512], ys = [0, 120, 245, 372, 512];
  for (const [row, code] of Array.from(api.ANIMATED_CODES).entries()) for (let frame = 0; frame < 4; frame++) {
    const [left, top, width, height] = api.ANIMATED_FRAME_RECTS[code][frame];
    let actualPixels = 0;
    for (let y = ys[row]; y < ys[row + 1]; y++) for (let x = xs[frame]; x < xs[frame + 1]; x++) {
      if (!alpha(animatedSource, x, y)) continue;
      actualPixels++;
      assert.ok(x >= left && x < left + width && y >= top && y < top + height, `${code}:${frame} pixel ${x},${y} must not be cropped`);
    }
    assert.ok(actualPixels > 5000);
    assert.ok(left >= xs[frame] && left + width <= xs[frame + 1]);
    assert.ok(top >= ys[row] && top + height <= ys[row + 1]);
    const { target } = api.animatedFrameLayout(code, frame);
    assert.ok(target[0] >= 4 && target[1] >= 6);
    assert.equal(target[1] + target[3], 124, 'all objects share a padded ground baseline');
    assert.ok(target[2] <= 118 && target[3] <= 118);
  }
});

test('normalized animated frames remove next-row fragments and recover cropped fountain/lantern/pinwheel tops', () => {
  const { api } = setup(), result = api.createAnimatedAtlas(animatedSource);
  assert.equal(result.calls.length, 16);
  const recovered = [];
  for (const code of ['animated_fountain', 'firefly_lantern', 'garden_pinwheel']) {
    const row = api.ANIMATED_ROWS[code];
    for (let frame = 0; frame < 4; frame++) {
      const layout = api.animatedFrameLayout(code, frame);
      const [sx, sy, sw, sh] = layout.source;
      let formerlyMissing = 0;
      for (let y = sy; y < Math.min(sy + sh, row * 128); y++) for (let x = sx; x < sx + sw; x++) {
        if (alpha(animatedSource, x, y) > 12) formerlyMissing++;
      }
      if (formerlyMissing) recovered.push(`${code}:${frame}`);
      // Everything below the intended base is truly empty in the shared atlas.
      for (let y = 124; y < 128; y++) for (let x = 0; x < 128; x++) {
        assert.equal(alpha(result, frame * 128 + x, row * 128 + y), 0);
      }
    }
  }
  assert.ok(recovered.includes('animated_fountain:1'));
  assert.ok(recovered.includes('animated_fountain:2'));
  for (const code of ['firefly_lantern', 'garden_pinwheel']) for (let frame = 0; frame < 4; frame++) assert.ok(recovered.includes(`${code}:${frame}`));
  // 4th duck and fountain start before x=384; their left edges must be retained.
  assert.ok(api.ANIMATED_FRAME_RECTS.duck_float[3][0] < 384);
  assert.ok(api.ANIMATED_FRAME_RECTS.animated_fountain[3][0] < 384);
});

test('animated DOM thumbnails and Phaser reuse one atlas with a stable first pinwheel pivot', () => {
  const { api, canvases } = setup(), shared = api.createAnimatedAtlas(animatedSource), calls = [];
  const target = { drawImage(...args) { calls.push(args); } };
  assert.equal(api.drawAnimatedItem(target, animatedSource, 'animated_fountain', 0, 0, 96, 96, 3), true);
  assert.equal(calls[0][0], shared);
  assert.deepEqual(calls[0].slice(1), [384, 128, 128, 128, 0, 0, 96, 96]);
  assert.equal(canvases.length, 1);
  assert.equal(api.drawAnimatedItem(target, animatedSource, 'missing', 0, 0, 96, 96), false);
  assert.deepEqual(Array.from(api.animatedFrameLayout('garden_pinwheel', 0).target), [24, 10, 80, 114]);
  assert.equal(api.createAnimatedAtlas({ complete: false }), null);
  assert.throws(() => api.createAnimatedAtlas({ width: 512, height: 500 }), /512×512/);
});
