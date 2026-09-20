const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const code = readFileSync(path.join(__dirname, '../src/frontend/forest-game.js'), 'utf8');
const context = vm.createContext({});
vm.runInContext(code.slice(code.indexOf('  function isCoveredTop('), code.indexOf('  const footwearPreviewBounds')), context);
test('open-front and low-neck tops are excluded, covered everyday tops remain', () => {
  for (const definition of ['torso/vest/torso_clothes_vest_open.json', 'torso/jacket/torso_jacket_frock.json',
    'torso/shirts/shortsleeve/torso_clothes_tshirt_vneck.json', 'torso/shirts/longsleeve/torso_clothes_longsleeve_scoop.json',
    'torso/dresses/kimono/dress_kimono_oversize.json']) {
    assert.equal(context.isCoveredTop({ definition }), false, definition);
  }
  for (const definition of ['torso/shirts/shortsleeve/torso_clothes_tshirt.json',
    'torso/shirts/longsleeve/torso_clothes_longsleeve_formal.json', 'torso/jacket/torso_jacket_trench.json']) {
    assert.equal(context.isCoveredTop({ definition }), true, definition);
  }
});
test('shoe cards use short fitted trousers without modifying saved outfit', () => {
  const draft = { lpcBottom: 'plain_skirt', lpcOutfit: 'robe', lpcShoes: 'boots', shoeColor: 'red', bottomColor: 'blue' };
  const result = context.footwearPreviewCosmetics(draft);
  assert.equal(result.lpcBottom, 'short_short');
  assert.equal(result.bottomColor, 'black');
  assert.equal(result.lpcShoes, 'boots');
  assert.equal(result.shoeColor, 'red');
  assert.equal(draft.lpcBottom, 'plain_skirt');
  assert.ok(code.includes('category === "lpcShoes" ? footwearPreviewBounds'));
  assert.ok(code.includes('category === "shoeColor" ? footwearPreviewBounds'));
  assert.ok(code.includes('lpcBottom: avatarDraft.lpcBottom || "short_short"'));
  const bounds = vm.runInNewContext('(' + code.match(/const footwearPreviewBounds = (\{[^;]+\});/)[1] + ')');
  // LPC shoes occupy y=54..62; keep both toes and the fitted shorts in frame.
  assert.ok(54 * bounds.height / 64 + bounds.y >= 0);
  assert.ok(62 * bounds.height / 64 + bounds.y <= 96);
  assert.ok(45 * bounds.height / 64 + bounds.y >= 0);
});
