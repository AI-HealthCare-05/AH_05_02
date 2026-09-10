const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const zlib = require('node:zlib');
const { createHash } = require('node:crypto');

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
  return { width, height, naturalWidth: width, naturalHeight: height, complete: true, pixels, src: file.replace(/\\/g, '/') };
}

function setup({ ImageClass } = {}) {
  const canvases = [];
  const document = { createElement(tag) {
    assert.equal(tag, 'canvas');
    const canvas = { width: 0, height: 0, calls: [] };
    canvas.getContext = () => {
      canvas.pixels ||= new Uint8ClampedArray(canvas.width * canvas.height * 4);
      return { getImageData() { return { data: canvas.pixels }; }, drawImage(source, sx, sy, sw, sh, dx, dy, dw, dh) {
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
  const window = { Image: ImageClass };
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

function individualImages(api) {
  return Object.fromEntries(Array.from(api.INDIVIDUAL_ASSETS, (asset, index) => {
    const width = 40, height = 80, pixels = new Uint8ClampedArray(width * height * 4);
    for (let y = 1; y < 79; y++) for (let x = 2; x < 38; x++) pixels.set([index + 10, 70, 140, 255], (y * width + x) * 4);
    return [asset.code, { width, height, naturalWidth: width, naturalHeight: height, complete: true, src: asset.url, pixels }];
  }));
}

test('manifest restores five complete safe cells and retains other furniture sources', () => {
  const { api } = setup();
  assert.equal(api.INDIVIDUAL_ASSETS.length, 24);
  assert.equal(new Set(api.INDIVIDUAL_ASSETS.map(asset => asset.url)).size, 24);
  assert.equal(api.INDIVIDUAL_ASSETS.filter(asset => asset.url.includes('/furniture-v153/')).length, 19);
  for (const asset of api.INDIVIDUAL_ASSETS) {
    assert.equal(asset.key, `furniture-${asset.code}`);
    assert.equal(asset.url, api.RESTORED_CODES.includes(asset.code)
      ? `/static/assets/carrot-forest-storage-atlas-v3.png?v=20260909-${asset.code}`
      : `/static/assets/furniture-v153/${asset.code}.png?v=20260907-1`);
  }
});

function independentAssetFile(asset) {
  return path.join(__dirname, '../src/frontend', asset.url.split('?')[0].replace(/^\/static\//, ''));
}

test('v156 preserves the exact fire, fountain and world art and the unchanged flame effect implementation', () => {
  const protectedHashes = {
    'assets/furniture-v153/campfire.png': 'C12D05D4958585ED27641A5BED191F3CA5511AB73BAD94261EB34EF6DB71F0D4',
    'assets/furniture-v153/animated_fountain.png': 'BF06DE2C7951B2B026A6AB656DD5009CE4326D5DE68F5B70296CF60B21C56120',
    'assets/carrot-forest-world-v6.png': 'AAD5F6243CD398FD37638AD6BE105E0D64D84B8649720611D0BF5A87B4B19A42',
    'forest-fire.js': '0A5E0BF030F5541BC5DEAA937F31262937841CCA2A19933F407FA809C70911DA',
  };
  for (const [relative, expected] of Object.entries(protectedHashes)) {
    const bytes = fs.readFileSync(path.join(__dirname, '../src/frontend', relative));
    // Text checkout line endings are not effect-code changes; PNG bytes are exact.
    const content = relative.endsWith('.js') ? bytes.toString('utf8').replace(/\r\n/g, '\n') : bytes;
    assert.equal(createHash('sha256').update(content).digest('hex').toUpperCase(), expected, relative);
  }
});

test('the archived 24 pre-v156 originals are byte-for-byte identical to the retained v153 sources', () => {
  const { api } = setup();
  const archive = path.join(__dirname, '../art-archive/furniture-before-v156');
  const files = fs.readdirSync(archive).filter(name => name.endsWith('.png')).sort();
  assert.deepEqual(files, Array.from(api.INDIVIDUAL_ASSETS, asset => `${asset.code}.png`).sort());
  for (const file of files) {
    const original = fs.readFileSync(path.join(__dirname, '../src/frontend/assets/furniture-v153', file));
    const archived = fs.readFileSync(path.join(archive, file));
    assert.equal(archived.equals(original), true, `${file}: never overwrite or transform archived art`);
  }
});

test('individual alpha bounds include faint edge pixels and aspect-fit the complete body with padding', () => {
  const { api } = setup(), pixels = new Uint8ClampedArray(80 * 40 * 4);
  pixels[(2 * 80 + 3) * 4 + 3] = 1;
  pixels[(37 * 80 + 77) * 4 + 3] = 255;
  const bounds = api.alphaBounds(pixels, 80, 40);
  assert.deepEqual({ ...bounds }, { x: 3, y: 2, width: 75, height: 36 });
  for (const tileSize of [128, 256]) {
    const layout = api.individualFrameLayout(bounds, tileSize), [x, y, width, height] = layout.target;
    assert.deepEqual(Array.from(layout.source), [3, 2, 75, 36]);
    assert.ok(x >= layout.padding && y >= layout.padding);
    assert.ok(x + width <= tileSize - layout.padding);
    assert.equal(y + height, tileSize - layout.padding);
    assert.ok(Math.abs(width / 75 - height / 36) < 1 / 36, 'rounding may differ by less than one pixel; body must not stretch');
  }
  assert.equal(api.alphaBounds(new Uint8ClampedArray(16), 2, 2), null);
});

test('restored v153 furniture retains every non-transparent edge pixel', () => {
  const { api } = setup(), width = 80, height = 80;
  const pixels = new Uint8ClampedArray(width * height * 4);
  pixels[(1 * width + 1) * 4 + 3] = 1;
  pixels[(78 * width + 78) * 4 + 3] = 15;
  for (let y = 20; y < 60; y++) for (let x = 25; x < 55; x++) pixels.set([120, 70, 50, 255], (y * width + x) * 4);
  pixels[(19 * width + 24) * 4 + 3] = 16;
  assert.deepEqual({ ...api.alphaBounds(pixels, width, height) }, { x: 1, y: 1, width: 78, height: 78 });
  assert.deepEqual({ ...api.alphaBounds(pixels, width, height, 16) }, { x: 24, y: 19, width: 31, height: 41 });
  const images = ['/static/assets/furniture-v153/tent.png?v=20260907-1',
    '/static/assets/furniture-v153/campfire.png?v=20260907-1',
    '/static/assets/furniture-v153/animated_fountain.png?v=20260907-1', ''].map(src => ({
    width, height, naturalWidth: width, naturalHeight: height, complete: true, pixels, src,
  }));
  const original = new Uint8ClampedArray(pixels);
  for (const [index, image] of images.entries()) {
    const tile = api.createIndividualTile(image, 128);
    assert.deepEqual(tile.calls[0].slice(1, 5), [1, 1, 78, 78]);
    assert.deepEqual(pixels, original, 'fitting may not alter PNG source alpha or RGB pixels');
  }
  images[1].currentSrc = images[0].src;
  assert.deepEqual(api.createIndividualTile(images[1], 128).calls[0].slice(1, 5), [1, 1, 78, 78], 'currentSrc change invalidates cached v153 bounds');
});

test('Phaser blob images inherit restored v153 fitting from the manifest and invalidate prior caches', () => {
  const { api } = setup(), images = individualImages(api);
  for (const [code, image] of Object.entries(images)) {
    image.src = `blob:https://forest.test/${code}`;
    image.pixels[3] = 1;
    image.pixels[image.pixels.length - 1] = 15;
  }
  const before = api.createStorageAtlasFromImages(images);
  assert.deepEqual(before.calls[0][0].calls[0].slice(1, 5), [0, 0, 40, 80]);
  api.registerIndividualImages(images);
  const after = api.createStorageAtlasFromImages(images);
  assert.notEqual(after, before, 'registering manifest identity invalidates blob-only atlas cache');
  assert.deepEqual(after.calls[0][0].calls[0].slice(1, 5), [0, 0, 40, 80]);
  for (const asset of api.INDIVIDUAL_ASSETS) {
    const tile = api.createIndividualTile(images[asset.code], 128);
    assert.deepEqual(tile.calls[0].slice(1, 5), [0, 0, 40, 80], asset.code);
  }
});

test('independent normalized tiles cannot inherit neighbors and retain padded top and bottom edges', () => {
  const { api } = setup(), images = individualImages(api), result = api.createStorageAtlasFromImages(images);
  assert.deepEqual([result.width, result.height], [1280, 1024]);
  assert.equal(result.calls.length, 20);
  for (let index = 0; index < 20; index++) {
    const tile = result.calls[index][0], ox = index % 5 * 256, oy = Math.floor(index / 5) * 256;
    assert.equal(tile.calls.length, 1);
    assert.equal(tile.calls[0][0], images[api.STORAGE_CODES[index]], 'tile reads only its own standalone PNG');
    assert.deepEqual(tile.calls[0].slice(1, 5), [2, 1, 36, 78]);
    let visible = 0;
    for (let y = 0; y < 256; y++) for (let x = 0; x < 256; x++) {
      if (!alpha(result, ox + x, oy + y)) continue;
      visible++;
      assert.ok(x >= 12 && x < 244 && y >= 12 && y < 244);
      assert.equal(result.pixels[((oy + y) * result.width + ox + x) * 4], index + 10, 'no foreign source color can enter a tile');
    }
    assert.ok(visible > 10000);
    assert.equal(alpha(result, ox + 128, oy + 12), 255, 'the full top edge survives normalization');
    assert.equal(alpha(result, ox + 128, oy + 243), 255, 'the full bottom edge survives normalization');
  }
  assert.equal(api.createStorageAtlasFromImages(images), result, 'unchanged source maps reuse the exact atlas');
  assert.throws(() => api.createStorageAtlasFromImages({ ...images, chair_green: null }), /Missing required/);
});

test('individual animated tiles repeat one identical fixture so only isolated runtime parts can move', () => {
  const { api } = setup(), images = individualImages(api), atlas = api.createAnimatedAtlasFromImages(images);
  assert.deepEqual([atlas.width, atlas.height], [512, 512]);
  assert.equal(atlas.calls.length, 16);
  for (let row = 0; row < 4; row++) {
    for (let frame = 1; frame < 4; frame++) assert.equal(atlas.calls[row * 4 + frame][0], atlas.calls[row * 4][0]);
    for (let x = 0; x < 128; x++) for (const y of [0, 5, 122, 127]) {
      assert.equal(alpha(atlas, x, row * 128 + y), 0);
    }
  }
});

test('registered images are shared by normal DOM drawing while explicit legacy flame access remains intact', () => {
  const { api } = setup(), images = individualImages(api), calls = [];
  api.registerIndividualImages(images);
  assert.equal(api.individualReady, true);
  const storage = api.createStorageAtlas(source), animated = api.createAnimatedAtlas(animatedSource);
  api.drawStorageItem({ drawImage: (...args) => calls.push(args) }, source, 'bench', 0, 0, 80, 80);
  api.drawAnimatedItem({ drawImage: (...args) => calls.push(args) }, animatedSource, 'garden_pinwheel', 0, 0, 80, 80);
  assert.equal(calls[0][0], storage); assert.equal(calls[1][0], animated);
  const flame = api.createLegacyStorageAtlas(source);
  assert.notEqual(flame, storage);
  assert.equal(flame.calls[14][0], source, 'the original flame pixels never come from new OFF-only artwork');
  assert.throws(() => api.registerIndividualImages({}), /All 24/);
});

test('ordinary furniture uses the pre-carrot-house atlas while campfire keeps its current art', () => {
  const { api } = setup(), images = individualImages(api);
  api.registerIndividualImages(images);
  const legacy = api.createLegacyStorageAtlas(source);
  const restored = api.createStorageAtlas(source);
  assert.equal(restored.calls[13][0], legacy, 'bench is copied from the old furniture atlas');
  assert.notEqual(restored.calls[14][0], legacy, 'campfire remains the approved current illustration');
});

test('five repaired objects retain complete silhouettes with centered padded bounds in the live atlas', () => {
  const { api } = setup(), images = individualImages(api);
  const safe = readRgbaPng(path.join(__dirname, '../src/frontend/assets/carrot-forest-storage-atlas-v3.png'));
  for (const code of api.RESTORED_CODES) images[code] = safe;
  const result = api.createStorageAtlasFromImages(images, source);
  for (const code of api.RESTORED_CODES) {
    const index = api.STORAGE_INDEX[code], tile = result.calls[index][0];
    const bounds = api.alphaBounds(tile.pixels, 256, 256, 12);
    assert.ok(bounds, code);
    assert.ok(bounds.x >= 10 && bounds.y >= 10, `${code}: complete top and left padding`);
    assert.ok(bounds.x + bounds.width <= 246 && bounds.y + bounds.height <= 246, `${code}: complete bottom/right padding`);
    assert.ok(Math.abs(bounds.x + bounds.width / 2 - 128) <= 3, `${code}: centered silhouette`);
    const small = tile.calls[0][0], fitted = small.calls[0][0], isolated = fitted.calls[0][0];
    assert.equal(isolated.calls[0][0], safe);
    assert.deepEqual(isolated.calls[0].slice(1, 5), [index % 5 * 256, Math.floor(index / 5) * 256, 256, 256]);
    assert.ok(bounds.height > 170, `${code}: restore a full-size object instead of hiding cropped edges`);
  }
});

test('async art boot blocks legacy flashes and registers nothing until every required PNG is ready', async () => {
  const pending = [];
  class ImageClass {
    constructor() { this.complete = false; pending.push(this); }
    set src(value) { this.url = value; }
    get src() { return this.url; }
  }
  const { api } = setup({ ImageClass }), loading = api.loadIndividualAssets();
  assert.equal(api.loadIndividualAssets(), loading);
  assert.equal(pending.length, 24);
  assert.equal(api.createStorageAtlas(source), null);
  assert.equal(api.createAnimatedAtlas(animatedSource), null);
  const fixtures = individualImages(api);
  for (let index = 0; index < 23; index++) {
    Object.assign(pending[index], fixtures[api.INDIVIDUAL_ASSETS[index].code]); pending[index].onload();
  }
  await Promise.resolve(); assert.equal(api.individualReady, false);
  Object.assign(pending[23], fixtures[api.INDIVIDUAL_ASSETS[23].code]); pending[23].onload();
  await loading; assert.equal(api.individualReady, true);
  assert.ok(api.createStorageAtlas(source));
});

test('every shipped standalone PNG is nonempty RGBA and normalizes its version-specific visible alpha extent', () => {
  const { api } = setup();
  for (const asset of api.INDIVIDUAL_ASSETS) {
    const image = readRgbaPng(independentAssetFile(asset));
    const tile = api.createIndividualTile(image, 128);
    const bounds = api.alphaBounds(image.pixels, image.width, image.height, asset.url.includes('/furniture-v156/') ? 16 : 1);
    assert.ok(bounds.width > 0 && bounds.height > 0, asset.code);
    assert.deepEqual(tile.calls[0].slice(1, 5), [bounds.x, bounds.y, bounds.width, bounds.height]);
    for (let x = 0; x < 128; x++) for (const y of [0, 5, 122, 127]) assert.equal(alpha(tile, x, y), 0, `${asset.code} padding`);
  }
});

function phaserSceneForPixels() {
  const Phaser = { Scene: class {}, AUTO: 0, Scale: { FIT: 1, CENTER_BOTH: 1 }, Game: class { constructor(config) { this.config = config; } } };
  const window = { Phaser };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../src/frontend/forest-phaser.js'), 'utf8'), {
    window, Phaser, localStorage: { getItem: () => null }, document: { getElementById: () => ({}) },
  });
  return new window.carrotForestPhaserGame.config.scene();
}

test('v156 visible silhouettes retain source margins before runtime normalization', () => {
  const { api } = setup();
  for (const asset of api.INDIVIDUAL_ASSETS.filter(item => item.url.includes('/furniture-v156/'))) {
    const image = readRgbaPng(independentAssetFile(asset));
    const bounds = api.alphaBounds(image.pixels, image.width, image.height, 16);
    assert.ok(bounds.x > 0 && bounds.y > 0, `${asset.code}: complete top/left edge`);
    assert.ok(bounds.x + bounds.width < image.width, `${asset.code}: complete right edge`);
    assert.ok(bounds.y + bounds.height < image.height, `${asset.code}: complete feet or lower edge`);
  }
});

test('new pinwheel art partitions without fabricated stem pixels or changes to its whole lower base', () => {
  const { api } = setup(), scene = phaserSceneForPixels();
  const image = readRgbaPng(independentAssetFile(api.INDIVIDUAL_ASSETS.find(asset => asset.code === 'garden_pinwheel')));
  const tile = api.createIndividualTile(image, 128), { base, blades } = scene.splitStaticPinwheelPixels(tile.pixels);
  let coloredBladePixels = 0;
  for (let i = 0; i < tile.pixels.length; i += 4) {
    if (blades[i + 3]) coloredBladePixels++;
    assert.ok(!base[i + 3] || !blades[i + 3], 'a source pixel belongs to exactly one layer');
    for (let channel = 0; channel < 4; channel++) assert.equal(base[i + channel] + blades[i + channel], tile.pixels[i + channel]);
    if (Math.floor(i / 4 / 128) >= 79) assert.equal(blades[i + 3], 0, 'entire pot and exposed lower stem remain static');
  }
  assert.ok(coloredBladePixels > 500);
});

test('new fountain animation changes only original cyan water pixels, never stone, moss, alpha, or position', () => {
  const { api } = setup(), scene = phaserSceneForPixels();
  const image = readRgbaPng(independentAssetFile(api.INDIVIDUAL_ASSETS.find(asset => asset.code === 'animated_fountain')));
  const tile = api.createIndividualTile(image, 128), original = new Uint8ClampedArray(tile.pixels);
  for (let frame = 1; frame < 8; frame++) {
    const output = scene.fountainFlowPixels(original, frame);
    let changed = 0;
    for (let i = 0; i < original.length; i += 4) {
      const [r, g, b, a] = original.subarray(i, i + 4);
      assert.equal(output[i + 3], a);
      const water = a && b - r > 28 && g - r > 18 && b >= g * .92;
      for (let channel = 0; channel < 3; channel++) {
        if (!water) assert.equal(output[i + channel], original[i + channel]);
        else if (output[i + channel] !== original[i + channel]) changed++;
      }
    }
    assert.ok(changed > 500, 'flow must visibly animate the real water surface');
  }
  assert.deepEqual(tile.pixels, original, 'the static source art is never modified');
});
