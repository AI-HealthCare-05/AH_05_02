const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../src/frontend/forest-sw.js'), 'utf8');
const origin = 'https://forest.test';
const response = (body, { status = 200, redirected = false } = {}) => ({
  body, status, redirected, ok: status >= 200 && status < 300,
  clone() { return response(body, { status, redirected }); },
});
const keyOf = request => typeof request === 'string' ? request : request.url;

test('offline shell versions match every HTML script, stylesheet, and restored furniture asset', () => {
  const context = { self: { addEventListener() {} } };
  vm.runInNewContext(source + ';globalThis.shell = CORE_SHELL;globalThis.media = MEDIA_ASSETS;', context);
  const html = fs.readFileSync(path.join(__dirname, '../src/frontend/forest.html'), 'utf8');
  const htmlSources = [...html.matchAll(/\b(?:href|src)="(\/static\/[^"\s]+\.(?:js|css)(?:\?[^"\s]*)?)"/g)].map(match => match[1]);
  const cachedSources = Array.from(context.shell).filter(url => /\.(?:js|css)(?:\?|$)/.test(url));
  assert.ok(htmlSources.length >= 12, 'inspect the full shell rather than a handpicked script');
  assert.deepEqual(cachedSources.sort(), htmlSources.sort(), 'no old script or CSS query may remain in the offline shell');
  const objects = { window: {} };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../src/frontend/forest-objects.js'), 'utf8'), objects);
  const manifest = Array.from(objects.window.ForestObjects.INDIVIDUAL_ASSETS, asset => asset.url).sort();
  const cachedFurniture = Array.from(context.media).filter(url => /\/furniture-v\d+\//.test(url)).sort();
  assert.deepEqual(cachedFurniture, manifest);
  assert.equal(cachedFurniture.filter(url => url.includes('/furniture-v153/')).length, 24);
  assert.equal(cachedFurniture.some(url => url.includes('/furniture-v156/')), false);
  const animals = require('../src/frontend/forest-animals.js');
  assert.deepEqual(Array.from(context.media).filter(url => url.includes('/licensed-rabbits/')).sort(),
    animals.rabbitAssets.map(asset => asset.url).sort(), 'both optional packs use the same URLs in preload and offline cache');
  const pets = require('../src/frontend/forest-pets.js');
  assert.deepEqual(Array.from(context.media).filter(url => url.includes('/licensed-kittens/')).sort(),
    pets.assets.map(asset => asset.url).sort(), 'all four optional kitten sheets share exact cache URLs');
});

function worker({ network = async () => response('fresh forest'), failPut = false } = {}) {
  const handlers = {}, stores = new Map(), fetches = [], deleted = [], writes = [];
  let claims = 0;
  const caches = {
    async keys() { return [...stores.keys()]; },
    async delete(name) { deleted.push(name); return stores.delete(name); },
    async open(name) {
      if (!stores.has(name)) stores.set(name, new Map());
      const store = stores.get(name);
      return {
        async match(request) { return store.get(keyOf(request)); },
        async put(request, value) {
          if (failPut) throw new Error('cache quota unavailable');
          writes.push({ name, key: keyOf(request), value });
          store.set(keyOf(request), value);
        },
      };
    },
  };
  const context = {
    URL, caches,
    fetch: async request => { fetches.push(request.url); return network(request); },
    self: {
      location: { origin }, addEventListener: (name, handler) => { handlers[name] = handler; },
      skipWaiting() {}, clients: { claim() { claims += 1; } },
    },
  };
  vm.runInNewContext(source + ';globalThis.cacheName = CACHE_NAME;', context);
  async function dispatch(url, { method = 'GET', mode = 'navigate' } = {}) {
    let result, intercepted = false;
    const pending = [];
    handlers.fetch({
      request: { url: new URL(url, origin).href, method, mode },
      respondWith(promise) { intercepted = true; result = promise; },
      waitUntil(promise) { pending.push(promise); },
    });
    const value = await result;
    await Promise.all(pending);
    return { intercepted, value };
  }
  return { dispatch, handlers, stores, fetches, deleted, writes, cacheName: context.cacheName, claims: () => claims };
}

test('a successful forest navigation saves only the canonical shell key', async () => {
  const state = worker();
  const { intercepted, value } = await state.dispatch('/forest?refresh=v153');
  assert.equal(intercepted, true);
  assert.equal(value.body, 'fresh forest');
  assert.deepEqual(state.writes.map(write => write.key), ['/forest']);
});

test('service and other navigation paths never read or replace the forest shell', async () => {
  const state = worker();
  for (const url of ['/service?returnTo=forest-challenges', '/', '/forest-other', '/forest/settings', '/forest/']) {
    assert.equal((await state.dispatch(url)).intercepted, false, url);
  }
  assert.equal(state.fetches.length, 0);
  assert.equal(state.stores.size, 0);
});

test('error and redirected responses cannot poison an existing forest shell', async () => {
  for (const options of [{ status: 401 }, { status: 404 }, { status: 500 }, { redirected: true }]) {
    const state = worker({ network: async () => response('not a forest shell', options) });
    const stored = response('offline forest');
    state.stores.set(state.cacheName, new Map([['/forest', stored]]));
    const result = await state.dispatch('/forest');
    assert.equal(result.value.body, 'not a forest shell');
    assert.equal(state.stores.get(state.cacheName).get('/forest'), stored);
    assert.equal(state.writes.length, 0);
  }
});

test('offline forest fallback uses only this worker cache, never another app cache', async () => {
  const state = worker({ network: async () => { throw new Error('offline'); } });
  state.stores.set('another-app', new Map([['/forest', response('unrelated page')]]));
  state.stores.set(state.cacheName, new Map([['/forest', response('offline forest')]]));
  assert.equal((await state.dispatch('/forest?refresh=x')).value.body, 'offline forest');
  state.stores.get(state.cacheName).clear();
  assert.equal((await state.dispatch('/forest')).value, undefined);
});

test('cache write failures do not replace a successful network page', async () => {
  const state = worker({ failPut: true });
  assert.equal((await state.dispatch('/forest')).value.body, 'fresh forest');
});

test('activation removes only obsolete forest caches and keeps other apps untouched', async () => {
  const state = worker();
  const oldCache = 'gandang-carrot-forest-pwa-v153';
  for (const name of [oldCache, state.cacheName, 'suin-service-v1', 'another-app']) state.stores.set(name, new Map());
  const pending = [];
  state.handlers.activate({ waitUntil(promise) { pending.push(promise); } });
  await Promise.all(pending);
  assert.deepEqual(state.deleted, [oldCache]);
  assert.deepEqual([...state.stores.keys()], [state.cacheName, 'suin-service-v1', 'another-app']);
  assert.equal(state.claims(), 1);
});

test('API, non-GET and cross-origin requests bypass the worker', async () => {
  const state = worker();
  for (const [url, options] of [
    ['/api/v1/auth/token/refresh', { mode: 'cors' }],
    ['/api/v1/challenge-v2/today', { mode: 'cors' }],
    ['/forest', { method: 'POST' }],
    ['https://other.test/forest', {}],
  ]) assert.equal((await state.dispatch(url, options)).intercepted, false);
  assert.equal(state.fetches.length, 0);
  assert.equal(state.stores.size, 0);
});

test('static assets use this worker cache without borrowing responses from other apps', async () => {
  const url = `${origin}/static/forest-game.js?v=test`;
  const state = worker({ network: async () => response('fresh script') });
  state.stores.set('another-app', new Map([[url, response('unrelated script')]]));
  assert.equal((await state.dispatch(url, { mode: 'cors' })).value.body, 'fresh script');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal((await state.dispatch(url, { mode: 'cors' })).value.body, 'fresh script');
  assert.equal(state.fetches.length, 1);
});
