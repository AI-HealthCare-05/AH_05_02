const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');

const root = path.join(__dirname, '../src/frontend');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
const tokens = read('suin/design-tokens.css');

test('main MVP and forest share the exact eleven-color UI palette', () => {
  const expected = {
    '--ui-base': '#F5F4EF', '--ui-section': '#D7E3DF', '--ui-border': '#C7DCD4',
    '--ui-selected': '#B7D4C8', '--ui-utility': '#92B2A2', '--ui-success': '#9FC0A2',
    '--ui-reward': '#D5E7AF', '--ui-primary': '#176B5B', '--ui-primary-hover': '#0B4D42',
    '--ui-text': '#14213D', '--ui-muted': '#586477',
  };
  for (const [name, color] of Object.entries(expected)) {
    assert.match(tokens, new RegExp(`${name}:${color}`, 'i'), `${name} remains ${color}`);
  }
  for (const file of ['index.html', 'suin/index.html', 'forest.html']) {
    const html = read(file);
    assert.match(html, /suin\/design-tokens\.css\?v=20260908-1/);
    const tokenIndex = html.indexOf('design-tokens.css');
    assert.ok(tokenIndex > html.indexOf('styles.css'), `${file} loads tokens after its base stylesheet`);
  }
});

test('medical danger and warning states retain their separate fixed palette', () => {
  for (const [name, color] of Object.entries({
    '--safety-danger': '#A32828', '--safety-warning': '#8A4B08',
    '--safety-danger-bg': '#FFF2EF', '--safety-warning-bg': '#FFF4DF',
  })) assert.match(tokens, new RegExp(`${name}:${color}`, 'i'));
  assert.match(tokens, /\.notice\.safety[^\{]*\{[^\}]*--safety-warning/s);
  assert.match(tokens, /\.auth-error-summary[^\{]*[\s\S]*?--safety-danger/s);
});

test('primary, selected, disabled, success and reward states use semantic tokens', () => {
  assert.match(tokens, /\.primary[^\{]*\{[^\}]*--ui-primary/s);
  assert.match(tokens, /\.tool-button\.is-active[^\{]*[\s\S]*?--ui-selected/s);
  assert.match(tokens, /button:disabled[^\{]*\{[^\}]*--ui-utility/s);
  assert.match(tokens, /\.quest-item\.is-complete[^\{]*[\s\S]*?--ui-success/s);
  assert.match(tokens, /\.reward-button:not\(:disabled\)[^\{]*[\s\S]*?--ui-reward/s);
});
