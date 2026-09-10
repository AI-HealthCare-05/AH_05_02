const { test } = require('node:test');
const assert = require('node:assert/strict');
const { proximity, nextIndex, mount } = require('../../src/frontend/education-carousel.js');

test('magnetic influence tapers symmetrically to zero beyond the cursor range', () => {
  assert.equal(proximity(0), 1);
  assert.equal(proximity(120), .5);
  assert.equal(proximity(-120), .5);
  assert.equal(proximity(240), 0);
  assert.equal(proximity(999), 0);
  assert.equal(proximity(NaN), 0);
  assert.equal(proximity(5, 0), 0);
});

test('carousel navigation handles no items and never moves past the first or final week', () => {
  assert.equal(nextIndex(-1, 1, 0), -1);
  assert.equal(nextIndex(-1, 1, 4), 0);
  assert.equal(nextIndex(-1, -1, 4), 3);
  assert.equal(nextIndex(0, -1, 4), 0);
  assert.equal(nextIndex(3, 1, 4), 3);
});

test('expanded education survives completion rerender by content ID and resets when the data disappears', () => {
  const originalWindow = global.window;
  global.window = { matchMedia: () => ({ matches: false, addEventListener() {} }), cancelAnimationFrame() {} };
  const makeNode = () => ({ hidden: false, disabled: false, textContent: '', classes: new Set(), attrs: {},
    classList: { toggle() {} }, style: { setProperty() {} }, setAttribute(key, value) { this.attrs[key] = value; }, focus() {}, scrollIntoView() {} });
  function makeCard(id, week) {
    const card = { ...makeNode(), dataset: { contentId: id, week: String(week) } };
    const toggle = { ...makeNode(), closest: () => card };
    const details = makeNode();
    card.querySelector = selector => selector === '.education-card-toggle' ? toggle : details;
    return card;
  }
  let cards = [makeCard('week-one', 1), makeCard('week-two', 2)];
  const events = {};
  const list = { ...makeNode(), querySelectorAll: () => cards, addEventListener() {} };
  const nodes = { '#education-list': list, '.education-carousel-controls': makeNode(), '#education-carousel-status': makeNode(), '[data-education-prev]': makeNode(), '[data-education-next]': makeNode() };
  const root = { querySelector: key => nodes[key], addEventListener: (key, fn) => { events[key] = fn; } };
  try {
    const view = mount(root);
    assert.equal(cards[0].querySelector('.education-card-details').hidden, true);
    const toggle = cards[1].querySelector('.education-card-toggle');
    events.click({ target: { closest: selector => selector === '.education-card-toggle' ? toggle : null } });
    assert.equal(toggle.attrs['aria-expanded'], 'true');
    assert.equal(cards[0].querySelector('.education-card-details').hidden, true);
    assert.equal(cards[1].querySelector('.education-card-details').hidden, false);
    cards = [makeCard('week-one', 1), makeCard('week-two', 2)];
    view.refresh();
    assert.equal(cards[1].querySelector('.education-card-toggle').attrs['aria-expanded'], 'true');
    assert.equal(nodes['[data-education-next]'].disabled, true);
    view.close();
    assert.equal(cards[1].querySelector('.education-card-details').hidden, true);
    const opened = [];
    const popupView = mount(root, { onOpen: id => opened.push(id) });
    const popupToggle = cards[0].querySelector('.education-card-toggle');
    events.click({ target: { closest: selector => selector === '.education-card-toggle' ? popupToggle : null } });
    assert.deepEqual(opened, ['week-one']);
    assert.equal(cards[0].querySelector('.education-card-details').hidden, true);
    popupView.close(true);
    nodes['#habit-list'] = list;
    nodes['#habit-status'] = makeNode();
    cards = [makeCard('meals', 1), makeCard('help', 2)];
    const habitView = mount(root, { listSelector: '#habit-list', statusSelector: '#habit-status', itemLabel: '생활습관', getLabel: card => card.dataset.contentId === 'help' ? '생활습관 도움말' : '식사', onOpen: id => opened.push(id) });
    assert.equal(nodes['#habit-status'].textContent, '총 2개 · 생활습관을 선택해 주세요');
    const helpToggle = cards[1].querySelector('.education-card-toggle');
    events.click({ target: { closest: selector => selector === '.education-card-toggle' ? helpToggle : null } });
    assert.equal(opened.at(-1), 'help');
    assert.equal(nodes['#habit-status'].textContent, '2 / 2 · 생활습관 도움말 선택');
    habitView.close();
    cards = [];
    popupView.refresh();
    assert.equal(nodes['.education-carousel-controls'].hidden, true);
  } finally { global.window = originalWindow; }
});
