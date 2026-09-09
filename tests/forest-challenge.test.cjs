const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const game = readFileSync(path.join(__dirname, '../src/frontend/forest-game.js'), 'utf8');
const flowCode = game.slice(game.indexOf('  let challengeFlowStep = 1;'), game.indexOf('  function ragGuideFor('));

function setup(plan) {
  const styles = ['exercise', 'diet', 'custom'].map(value => ({ value, checked: false }));
  const custom = ['walk', 'stretch', 'meal', 'vegetable', 'water', 'check'].map(value => ({ value, checked: false }));
  const sections = [1, 2, 3, 4].map(step => ({
    dataset: { flowStep: String(step) }, classList: { toggle() {} },
    controls: step === 4 ? [...styles, ...custom] : [{ required: step === 1 }],
    querySelectorAll() { return this.controls; },
  }));
  const nodes = Object.fromEntries(['challenge-flow-back', 'challenge-flow-next', 'challenge-flow-generate',
    'challenge-flow-error', 'challenge-flow-title', 'quest-generation-status', 'quest-list'].map(id => [`#${id}`, {}]));
  nodes['#custom-quest-picker'] = { querySelectorAll: () => custom };
  nodes['#challenge-flow-form'] = { reset() {}, querySelectorAll: () => styles };
  nodes['#challenge-flow-dialog'] = { open: false, showModal() { this.open = true; } };
  const state = { challengePlan: plan, quests: { meal: true }, carrots: 50, rewardClaimed: true };
  const context = vm.createContext({
    state, $: selector => nodes[selector],
    document: { querySelectorAll: selector => selector === '[data-flow-step]' ? sections : [] },
    activeQuestIds: () => state.challengePlan.questIds,
    questPlans: { exercise: ['walk', 'stretch', 'strength'], diet: ['meal', 'vegetable', 'water'] },
    window: { matchMedia: () => ({ matches: true }) },
    animationDelay: async () => {}, activateInspectorPanel() {}, syncActiveQuests() {},
    renderQuests() {}, renderGroup() {}, persist: async () => {},
  });
  vm.runInContext(flowCode, context);
  return { context, nodes, sections, styles, custom, state };
}

test('first visit opens step one; hidden fields cannot block form submission', () => {
  const { context, sections, nodes } = setup({ onboarded: false, questIds: [] });
  context.startPredictionFlow();
  assert.equal(sections[0].hidden, false);
  assert.equal(sections[3].controls[0].disabled, true);
  vm.runInContext('showChallengeFlowStep(4)', context);
  assert.equal(sections[0].controls[0].disabled, true);
  assert.equal(sections[3].controls[0].disabled, false);
  assert.equal(nodes['#challenge-flow-dialog'].open, true);
});

test('returning user edits preselected choices without changing saved data', () => {
  const plan = { onboarded: true, style: 'custom', questIds: ['walk', 'water', 'check'] };
  const { context, sections, styles, custom, state } = setup(plan);
  const before = JSON.stringify(state);
  context.startPredictionFlow();
  assert.equal(sections[3].hidden, false);
  assert.equal(styles.find(input => input.checked).value, 'custom');
  assert.deepEqual(custom.filter(input => input.checked).map(input => input.value), plan.questIds);
  assert.equal(JSON.stringify(state), before);
});

test('confirmed changes replace active quests without erasing completed records or rewards', async () => {
  const { context, state } = setup({ onboarded: true, style: 'diet', questIds: ['meal', 'vegetable', 'water'] });
  await context.generateChallengeQuests('exercise');
  assert.equal(state.challengePlan.style, 'exercise');
  assert.deepEqual(Array.from(state.challengePlan.questIds), ['walk', 'stretch', 'strength']);
  assert.equal(state.quests.meal, true);
  assert.equal(state.quests.walk, false);
  assert.equal(state.carrots, 50);
  assert.equal(state.rewardClaimed, true);
});
