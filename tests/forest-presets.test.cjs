const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const code = readFileSync(path.join(__dirname, '../src/frontend/forest-game.js'), 'utf8');
function setup() {
  const context = vm.createContext({ defaultCosmetics: {}, defaultAvatarTuning: {} });
  vm.runInContext(code.slice(code.indexOf('  const OUTFIT_DEFAULT_VERSION'), code.indexOf('  function defaultState()')), context);
  return context;
}
test('six stable presets include a female mage, elf archer and muscular inventor', () => {
  const c = setup(), target = { outfitHistory: [], avatar: { name: 'unchanged' } };
  c.ensureGenderDefaultOutfits(target);
  assert.deepEqual(Array.from(target.outfitHistory, p => p.label), ['농부', '사냥꾼', '달빛 마법사', '숲의 엘프', '숲속 발명가', '숲의 기사']);
  const [mage, witch, inventor, knight] = target.outfitHistory.slice(2);
  assert.deepEqual([mage.presetNumber, witch.presetNumber, inventor.presetNumber, knight.presetNumber], [3, 4, 5, 6]);
  for (const look of [mage, witch]) {
    assert.equal(look.cosmetics.bodyType, 'female');
  }
  assert.equal(mage.cosmetics.lpcWeapon, 'wand');
  assert.equal(witch.cosmetics.lpcWeapon, 'bow');
  assert.equal(inventor.gender, 'male');
  assert.equal(inventor.cosmetics.bodyType, 'muscular');
  assert.equal(inventor.cosmetics.lpcTool, 'hammer');
  assert.equal(inventor.cosmetics.lpcOutfit, 'apron_full');
  assert.deepEqual(target.avatar, { name: 'unchanged' });
  const saved = JSON.stringify(target.outfitHistory);
  c.ensureGenderDefaultOutfits(target);
  assert.equal(JSON.stringify(target.outfitHistory), saved);
});
test('saved preset4 is upgraded from wand to bow without duplicating its card', () => {
  const c = setup();
  const old = c.createAdditionalDefaultLooks()[1];
  old.label = '숲의 마녀';
  old.cosmetics.lpcWeapon = 'wand';
  const target = { outfitHistory: [old] };
  c.ensureGenderDefaultOutfits(target);
  const elf = target.outfitHistory.filter(p => p.presetNumber === 4);
  assert.equal(elf.length, 1);
  assert.equal(elf[0].id, old.id);
  assert.equal(elf[0].label, '숲의 엘프');
  assert.equal(elf[0].cosmetics.lpcWeapon, 'bow');
});
test('migration preserves eight personal looks, existing gender presets and current avatar', () => {
  const c = setup();
  const avatar = c.createGenderDefaultAvatar('male');
  const personal = Array.from({ length: 8 }, (_, i) => c.createOutfitSnapshot(avatar, i + 1, `나만의 코디 ${i + 1}`));
  const female = c.normalizeGenderDefaultOutfit(null, 'female');
  female.cosmetics.hairColor = 'custom-preserved';
  const target = { avatar, outfitHistory: [female, ...personal] };
  const before = JSON.stringify(avatar);
  c.applyRequestedDefaultOutfit(target, 5);
  target.outfitHistory = c.normalizeOutfitHistory(target.outfitHistory, avatar);
  c.applyRequestedDefaultOutfit(target, 5);
  assert.equal(target.outfitHistory.length, 14);
  assert.equal(target.outfitHistory[0].cosmetics.hairColor, 'custom-preserved');
  assert.equal(JSON.stringify(target.avatar), before);
  assert.deepEqual(new Set(target.outfitHistory.filter(p => !p.presetRole).map(p => p.id)), new Set(personal.map(p => p.id)));
  c.state = target;
  c.rememberCurrentOutfit();
  assert.equal(target.outfitHistory.filter(p => p.presetRole).length, 6);
  assert.equal(target.outfitHistory.find(p => p.presetRole === 'inventor').cosmetics.bodyType, 'muscular');
});
