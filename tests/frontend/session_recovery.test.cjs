const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../src/frontend/app.js'), 'utf8');
const functionNames = [
  'healthDraftOwnerId', 'currentHealthInputPanel', 'healthDraftFieldValues',
  'persistHealthDraft', 'clearHealthDraft', 'readHealthDraft', 'restoreHealthDraft',
  'persistSessionRecovery', 'storedSessionRecovery', 'clearSessionRecovery',
];

function storageFrom(map) {
  return {
    setItem(key, value) { map.set(key, value); },
    getItem(key) { return map.get(key) ?? null; },
    removeItem(key) { map.delete(key); },
  };
}

function harness(map, ownerId = 7) {
  const fields = [
    { id: 'height', type: 'number', value: '181', checked: false },
    { id: 'current-drinker-yes', type: 'radio', value: 'true', checked: true },
    { id: 'current-drinker-no', type: 'radio', value: 'false', checked: false },
  ].map(field => ({ ...field, closest: selector => selector === '#health-form' ? {} : null }));
  const nodes = Object.fromEntries(fields.map(field => [field.id, field]));
  nodes['health-metrics-panel'] = { hidden: true };
  nodes['lifestyle-input-panel'] = { hidden: false };
  nodes['detail-health-panel'] = { hidden: true };
  nodes['health-review-panel'] = { hidden: true };
  const context = vm.createContext({
    state: { userProfile: { id: ownerId }, healthDraftDirty: false, sessionRecovery: null },
    sessionStorage: storageFrom(map), Date, JSON,
    document: { getElementById: id => nodes[id] || null },
    $$: () => fields,
    syncExerciseDetails() {}, syncAlcoholFrequencyDetails() {}, syncLifestyleAvatar() {},
  });
  vm.runInContext(`
    const HEALTH_DRAFT_STORAGE_KEY = 'gandang-health-draft-v1';
    const SESSION_RECOVERY_STORAGE_KEY = 'gandang-session-recovery-v1';
    const HEALTH_DRAFT_MAX_AGE_MS = 12 * 60 * 60 * 1000;
  `, context);
  for (const name of functionNames) {
    const match = source.match(new RegExp(`^function ${name}\\([^]*?^}`, 'm'));
    assert.ok(match, `missing ${name}`);
    vm.runInContext(match[0], context);
  }
  return { context, fields };
}

test('health draft is session-only, contains no credentials, and restores for the same user', () => {
  const map = new Map();
  const first = harness(map);
  assert.equal(first.context.persistHealthDraft({ markDirty: true }), true);
  const serialized = map.get('gandang-health-draft-v1');
  assert.ok(serialized);
  assert.doesNotMatch(serialized, /password|token|email/i);
  const payload = JSON.parse(serialized);
  assert.equal(payload.ownerId, '7');
  assert.equal(payload.panel, 'lifestyle');

  const reopened = harness(map);
  reopened.fields[0].value = '160';
  reopened.fields[1].checked = false;
  assert.ok(reopened.context.restoreHealthDraft());
  assert.equal(reopened.fields[0].value, '181');
  assert.equal(reopened.fields[1].checked, true);
});

test('a different user cannot receive a prior health draft', () => {
  const map = new Map();
  harness(map, 7).context.persistHealthDraft({ markDirty: true });
  assert.equal(harness(map, 8).context.readHealthDraft(), null);
  assert.equal(map.has('gandang-health-draft-v1'), false);
});

test('session recovery stores only a safe destination and is owner-scoped', () => {
  const map = new Map();
  const first = harness(map, 7);
  first.context.persistSessionRecovery({ returnStep: 5, healthPanel: 'review', ownerId: '7' });
  const serialized = map.get('gandang-session-recovery-v1');
  assert.doesNotMatch(serialized, /password|token|email/i);
  const sameUser = harness(map, 7);
  assert.equal(sameUser.context.storedSessionRecovery().returnStep, 5);
  const otherUser = harness(map, 8);
  assert.equal(otherUser.context.storedSessionRecovery(), null);
  const inMemoryOtherUser = harness(new Map(), 8);
  inMemoryOtherUser.context.state.sessionRecovery = { returnStep: 5, ownerId: '7' };
  assert.equal(inMemoryOtherUser.context.storedSessionRecovery(), null);
});

test('successful health save clears the temporary draft after the optional snapshot attempt', () => {
  const firstSave = source.indexOf('await saveCurrentScreeningInputSnapshot();');
  assert.ok(firstSave > 0);
  assert.equal(source.slice(firstSave, firstSave + 100).includes('clearHealthDraft();'), true);
});
