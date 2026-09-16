const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const zlib = require('node:zlib');
const animals = require('../src/frontend/forest-animals.js');

const moduleSource = fs.readFileSync(path.join(__dirname, '../src/frontend/forest-animals.js'), 'utf8');
const generatedVariants = () => animals.rabbitVariants.filter(variant => variant.generated);
const directions = ['up', 'down', 'left', 'right', 'up_left', 'up_right', 'down_left', 'down_right'];
const furColors = {
  bunbun: [0x6f6f6f, 0x8e8e8e, 0xa3a3a3, 0xb3b3b3, 0xdddddd],
  'last-tick': [0x414752, 0x626773, 0x868d9b, 0xb6b8c7],
};
const rgba = (rgb, alpha = 255) => [rgb >>> 16, (rgb >>> 8) & 255, rgb & 255, alpha];
const rgbAt = (pixels, index) => (pixels[index] << 16) | (pixels[index + 1] << 8) | pixels[index + 2];

test('coat palettes are immutable exact-color maps limited to verified original fur colors', () => {
  const signatures = new Set();
  for (const variant of generatedVariants()) {
    assert.ok(Object.isFrozen(variant.palette));
    assert.deepEqual(Object.keys(variant.palette).map(Number).sort((a, b) => a - b), furColors[variant.family]);
    for (const [original, replacement] of Object.entries(variant.palette)) {
      assert.ok(Number.isSafeInteger(replacement) && replacement >= 0 && replacement <= 0xffffff);
      assert.notEqual(Number(original), replacement, `${variant.id} changes every fur shade`);
    }
    const signature = Object.values(variant.palette).join(',');
    assert.equal(signatures.has(signature), false, `${variant.id} has a distinct coat palette`);
    signatures.add(signature);
  }
});

test('pure recoloring copies RGBA input and preserves transparency, partial alpha and protected colors', () => {
  // Unlisted colors represent dark eyes/outlines, pink inner ears, and orange /
  // green carrot pixels. Only exact known coat RGBs may ever be replaced.
  const protectedColors = [0x000000, 0x111111, 0x282e3b, 0xea9aaa, 0xffb3c7, 0xed792f, 0x76a446, 0x123456];
  for (const variant of generatedVariants()) {
    const input = new Uint8ClampedArray([
      ...furColors[variant.family].flatMap(rgb => [0, 1, 127, 255].flatMap(alpha => rgba(rgb, alpha))),
      ...protectedColors.flatMap(rgb => rgba(rgb)),
    ]);
    const before = new Uint8ClampedArray(input);
    const output = animals.recolorRabbitPixels(input, variant.id);
    assert.ok(output instanceof Uint8ClampedArray);
    assert.notEqual(output, input);
    assert.notEqual(output.buffer, input.buffer);
    assert.deepEqual(input, before);
    for (let index = 0; index < input.length; index += 4) {
      const replacement = variant.palette[rgbAt(input, index)];
      const expected = replacement !== undefined && input[index + 3]
        ? rgba(replacement, input[index + 3]) : Array.from(input.subarray(index, index + 4));
      assert.deepEqual(Array.from(output.subarray(index, index + 4)), expected, `${variant.id} pixel ${index / 4}`);
    }
  }
});

test('original and unknown colors return independent unchanged copies; invalid RGBA fails explicitly', () => {
  const input = new Uint8ClampedArray([...rgba(0xdddddd), ...rgba(0x868d9b, 127), ...rgba(0x123456, 0)]);
  for (const id of ['bunbun', 'last-tick', 'missing-color', undefined, null]) {
    const result = animals.recolorRabbitPixels(input, id);
    assert.ok(result instanceof Uint8ClampedArray);
    assert.deepEqual(result, input);
    assert.notEqual(result.buffer, input.buffer);
  }
  assert.deepEqual(animals.recolorRabbitPixels(new Uint8ClampedArray(), 'bunbun-cream'), new Uint8ClampedArray());
  for (const invalid of [undefined, null, new Uint8ClampedArray(1), new Uint8ClampedArray(3), new Uint8ClampedArray(5)]) {
    assert.throws(() => animals.recolorRabbitPixels(invalid, 'bunbun-cream'), /RGBA/);
  }
});

function imageFor(asset, overrides = {}) {
  const width = asset.columns * 32, height = asset.frameCount / asset.columns * 32;
  const pixels = new Uint8ClampedArray(width * height * 4);
  const family = asset.key.endsWith('bunbun') ? 'bunbun' : 'last-tick';
  pixels.set(furColors[family].flatMap(color => rgba(color)));
  return { width, height, naturalWidth: width, naturalHeight: height, pixels, ...overrides };
}

function browserFixture() {
  const canvases = [];
  const document = { createElement(tag) {
    assert.equal(tag, 'canvas');
    const canvas = { width: 0, height: 0, draws: [], reads: [], writes: [] };
    canvas.getContext = (kind) => {
      assert.equal(kind, '2d');
      return {
        drawImage(image, ...args) {
          canvas.draws.push([image, ...args]);
          if (image.drawError) throw new Error('source image cannot be drawn');
          canvas.pixels = new Uint8ClampedArray(image.pixels);
          canvas.tainted = image.tainted;
        },
        getImageData(...args) {
          canvas.reads.push(args);
          if (canvas.tainted) throw new Error('canvas cannot be read');
          return { data: new Uint8ClampedArray(canvas.pixels) };
        },
        putImageData(imageData, ...args) {
          canvas.writes.push(args);
          canvas.pixels = new Uint8ClampedArray(imageData.data);
        },
      };
    };
    canvases.push(canvas);
    return canvas;
  } };
  const context = vm.createContext({ module: { exports: {} }, document, Uint8ClampedArray });
  vm.runInContext(moduleSource, context);
  return { api: context.module.exports, canvases };
}

function sceneFixture(sourceImages, { failedKey } = {}) {
  const textures = new Map(sourceImages), registrations = [], lookups = [];
  const scene = { textures: {
    exists: key => textures.has(key),
    get(key) {
      lookups.push(key);
      assert.ok(textures.has(key), 'missing sources are not read');
      return { getSourceImage: () => textures.get(key) };
    },
    addSpriteSheet(key, image, config) {
      if (key === failedKey) throw new Error('texture registration failed');
      assert.equal(textures.has(key), false, 'textures are never overwritten');
      registrations.push({ key, image, config });
      textures.set(key, image);
      return { key };
    },
  } };
  return { scene, textures, registrations, lookups };
}

test('canvas skins preserve original dimensions and grid without scaling, cropping or source mutation', () => {
  const { api, canvases } = browserFixture();
  for (const variant of animals.rabbitVariants) {
    const asset = animals.rabbitAssets.find(item => item.key === variant.sourceKey);
    const image = imageFor(asset), before = new Uint8ClampedArray(image.pixels);
    const canvas = api.createRabbitSkinCanvas(image, variant.id);
    assert.equal(canvas, canvases.at(-1));
    assert.deepEqual([canvas.width, canvas.height], [image.naturalWidth, image.naturalHeight]);
    assert.deepEqual(canvas.draws, [[image, 0, 0]], 'source is copied at 1:1 size');
    assert.deepEqual(canvas.reads, variant.generated ? [[0, 0, image.width, image.height]] : []);
    assert.deepEqual(canvas.writes, variant.generated ? [[0, 0]] : []);
    assert.deepEqual(canvas.pixels, animals.recolorRabbitPixels(image.pixels, variant.id));
    assert.deepEqual(image.pixels, before);
  }
});

test('canvas preparation accepts canvas dimensions but rejects missing, unknown or malformed source sheets', () => {
  const { api, canvases } = browserFixture();
  const image = imageFor(animals.rabbitAssets[0]);
  assert.ok(api.createRabbitSkinCanvas({ ...image, naturalWidth: undefined, naturalHeight: undefined }, 'bunbun-cream'));
  const count = canvases.length;
  for (const source of [undefined, null, {}, { ...image, naturalWidth: 127 }, { ...image, naturalHeight: 255 }]) {
    assert.equal(api.createRabbitSkinCanvas(source, 'bunbun-cream'), null);
  }
  assert.equal(api.createRabbitSkinCanvas(image, 'last-tick-white'), null, 'wrong source-family dimensions cannot corrupt frame indexing');
  assert.equal(api.createRabbitSkinCanvas(image, 'missing-color'), null);
  assert.equal(canvases.length, count, 'invalid source sheets allocate no canvas');
});

test('registration installs six independent sprite sheets once and reuses cached colors without their originals', () => {
  const { api, canvases } = browserFixture();
  const sources = animals.rabbitAssets.map(asset => [asset.key, imageFor(asset)]);
  const { scene, textures, registrations, lookups } = sceneFixture(sources);
  const expected = generatedVariants().map(item => item.key);
  assert.deepEqual(Array.from(api.registerRabbitSkins(scene)), expected);
  assert.equal(registrations.length, 6);
  assert.equal(canvases.length, 6);
  for (const registration of registrations) {
    const variant = generatedVariants().find(item => item.key === registration.key);
    const source = textures.get(variant.sourceKey);
    assert.deepEqual([registration.config.frameWidth, registration.config.frameHeight], [32, 32]);
    assert.deepEqual([registration.image.width, registration.image.height], [source.width, source.height]);
    assert.notEqual(registration.image, source);
  }
  for (const [key, image] of sources) assert.equal(textures.get(key), image, 'original textures are never replaced');
  const reads = lookups.length;
  assert.deepEqual(Array.from(api.registerRabbitSkins(scene)), expected);
  for (const [key] of sources) textures.delete(key);
  assert.deepEqual(Array.from(api.registerRabbitSkins(scene)), expected);
  assert.equal(registrations.length, 6);
  assert.equal(canvases.length, 6);
  assert.equal(lookups.length, reads, 'cached colors never reread or recolor original image data');
});

test('missing, malformed or unreadable optional sources leave original fallback textures usable', () => {
  for (const mode of ['missing', 'malformed', 'unreadable']) {
    const { api } = browserFixture();
    const sources = animals.rabbitAssets.map(asset => [asset.key, imageFor(asset)]);
    const originalBunbun = sources[0][1];
    if (mode === 'missing') sources.shift();
    if (mode === 'malformed') originalBunbun.naturalWidth = 1;
    if (mode === 'unreadable') originalBunbun.tainted = true;
    const { scene, textures, registrations } = sceneFixture(sources);
    const expected = generatedVariants().filter(item => item.family === 'last-tick').map(item => item.key);
    assert.deepEqual(Array.from(api.registerRabbitSkins(scene)), expected, mode);
    assert.equal(registrations.length, 3);
    for (const [key, image] of sources) assert.equal(textures.get(key), image);
    if (mode !== 'missing') assert.equal(textures.get('forest-rabbit-bunbun'), originalBunbun);
  }
  const { api, canvases } = browserFixture();
  const { scene } = sceneFixture([]);
  assert.deepEqual(Array.from(api.registerRabbitSkins(scene)), []);
  assert.equal(canvases.length, 0);
});

test('a single generated texture failure does not abort other colors or touch the source fallback', () => {
  const { api } = browserFixture();
  const failedKey = generatedVariants()[0].key;
  const sources = animals.rabbitAssets.map(asset => [asset.key, imageFor(asset)]);
  const { scene, textures } = sceneFixture(sources, { failedKey });
  assert.deepEqual(Array.from(api.registerRabbitSkins(scene)), generatedVariants().map(item => item.key).filter(key => key !== failedKey));
  assert.equal(textures.has(failedKey), false);
  for (const [key, image] of sources) assert.equal(textures.get(key), image);
});

test('all generated rabbit colors retain every original action, timing, direction and source rectangle', () => {
  assert.equal(generatedVariants().length, 6);
  for (const variant of generatedVariants()) {
    const original = animals.rabbitVariants.find(item => item.id === variant.family);
    assert.ok(original && !original.generated);
    assert.equal(variant.sourceKey, original.key);
    for (const name of original.actions) {
      const action = animals.rabbitAction(variant.id, name);
      assert.deepEqual(action, animals.rabbitAction(original.id, name));
      for (const direction of directions) for (const reducedMotion of [false, true]) {
        for (const elapsedMs of [0, action.frameMs, action.durationMs - 1, action.durationMs]) {
          const options = { action: name, direction, elapsedMs, reducedMotion };
          const pose = animals.rabbitPose(variant.id, options);
          const sourcePose = animals.rabbitPose(original.id, options);
          assert.deepEqual(pose, { ...sourcePose, key: variant.key }, `${variant.id}/${name}/${direction}/${elapsedMs}`);
          assert.deepEqual(animals.frameRect(pose.key, pose.frame), animals.frameRect(original.key, pose.frame));
        }
      }
    }
  }
});

// Optional local-byte audit. Only metadata and the decoder are checked in; the
// creator's PNGs remain private local installs and are never test fixtures.
function readRgbaPng(file) {
  const png = fs.readFileSync(file), chunks = [];
  const width = png.readUInt32BE(16), height = png.readUInt32BE(20);
  assert.equal(png.toString('ascii', 1, 4), 'PNG');
  assert.equal(png[24], 8, 'source has 8-bit channels');
  assert.equal(png[25], 6, 'source has RGBA channels');
  assert.equal(png[28], 0, 'source is not interlaced');
  for (let offset = 8; offset < png.length;) {
    const length = png.readUInt32BE(offset);
    if (png.toString('ascii', offset + 4, offset + 8) === 'IDAT') {
      chunks.push(png.subarray(offset + 8, offset + 8 + length));
    }
    offset += length + 12;
  }
  const packed = zlib.inflateSync(Buffer.concat(chunks)), stride = width * 4;
  const pixels = new Uint8ClampedArray(stride * height);
  const paeth = (a, b, c) => {
    const p = a + b - c, x = Math.abs(p - a), y = Math.abs(p - b), z = Math.abs(p - c);
    return x <= y && x <= z ? a : y <= z ? b : c;
  };
  assert.equal(packed.length, height * (stride + 1));
  for (let y = 0; y < height; y++) {
    const filter = packed[y * (stride + 1)];
    assert.ok(filter <= 4, 'known PNG filter');
    for (let x = 0; x < stride; x++) {
      const index = y * stride + x, left = x >= 4 ? pixels[index - 4] : 0;
      const up = y ? pixels[index - stride] : 0;
      const diagonal = x >= 4 && y ? pixels[index - stride - 4] : 0;
      const prediction = [0, left, up, Math.floor((left + up) / 2), paeth(left, up, diagonal)][filter];
      pixels[index] = (packed[y * (stride + 1) + x + 1] + prediction) & 255;
    }
  }
  return { width, height, pixels };
}

for (const asset of animals.rabbitAssets) {
  const file = path.join(__dirname, '../src/frontend', asset.url.split('?')[0].replace('/static/', ''));
  test(`installed ${asset.key} colors preserve every authored frame and all alpha bytes`, {
    skip: !fs.existsSync(file) ? 'Install the optional creator pack locally; PNGs are not redistributed.' : false,
  }, () => {
    const { width, height, pixels } = readRgbaPng(file);
    assert.deepEqual([width, height], [asset.columns * 32, asset.frameCount / asset.columns * 32]);
    const before = new Uint8ClampedArray(pixels);
    for (const variant of generatedVariants().filter(item => item.sourceKey === asset.key)) {
      const colored = animals.recolorRabbitPixels(pixels, variant.id);
      assert.equal(colored.length, pixels.length);
      const frames = new Set(variant.actions.flatMap(name => animals.rabbitAction(variant.id, name).frames));
      let totalChanged = 0;
      for (let i = 0; i < pixels.length; i += 4) {
        assert.equal(colored[i + 3], pixels[i + 3], `${variant.id} alpha ${i / 4}`);
        if (!pixels[i + 3] || !furColors[variant.family].includes(rgbAt(pixels, i))) {
          assert.deepEqual(colored.subarray(i, i + 4), pixels.subarray(i, i + 4), 'eyes, ears, carrots and non-coat pixels stay untouched');
        }
        totalChanged += colored[i] !== pixels[i] || colored[i + 1] !== pixels[i + 1] || colored[i + 2] !== pixels[i + 2];
      }
      assert.ok(totalChanged > 0, `${variant.id} changes the coat palette`);
      for (const frame of frames) {
        const rect = animals.frameRect(variant.key, frame);
        let visible = 0, changed = 0;
        for (let y = rect.y; y < rect.y + 32; y++) for (let x = rect.x; x < rect.x + 32; x++) {
          const i = (y * width + x) * 4;
          visible += colored[i + 3] > 0;
          changed += colored[i] !== pixels[i] || colored[i + 1] !== pixels[i + 1] || colored[i + 2] !== pixels[i + 2];
        }
        assert.ok(visible > 0, `${variant.id} frame ${frame} retains a visible original silhouette`);
        assert.ok(changed > 0, `${variant.id} frame ${frame} has the selected coat color`);
      }
      assert.deepEqual(pixels, before, 'source image bytes are never mutated');
    }
  });
}
