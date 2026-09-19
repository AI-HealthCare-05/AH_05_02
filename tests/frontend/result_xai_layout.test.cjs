const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const html = fs.readFileSync(path.join(root, 'src/frontend/index.html'), 'utf8');
const css = fs.readFileSync(path.join(root, 'src/frontend/result-xai.css'), 'utf8');

test('both explanation panels share the scoped stylesheet after legacy themes', () => {
  assert.ok(html.indexOf('/static/result-xai.css') > html.indexOf('/static/wood-sign-theme.css'));
  for (const id of ['current-factor-title', 'future-factor-title']) {
    assert.match(html, new RegExp(`class="[^"]*result-xai-card[^\"]*"[^>]*aria-labelledby="${id}"`));
  }
});

test('factor layout remains gated by xai-ready and supports narrow screens', () => {
  assert.match(css, /\.result-xai-card\.xai-ready \.factor-list li\s*\{\s*display: grid/);
  assert.match(css, /grid-template-columns: 36px minmax\(0, 1fr\)/);
  assert.match(css, /@media \(max-width: 600px\)/);
  assert.match(css, /overflow-wrap: anywhere/);
  assert.doesNotMatch(css, /overflow:\s*hidden|text-overflow:\s*ellipsis/);
});

test('only conflicting model outcomes receive the prominent guidance style', () => {
  assert.match(css, /data-code="CURRENT_SIGNAL_FUTURE_LOW"/);
  assert.match(css, /data-code="CURRENT_LOW_FUTURE_ELEVATED"/);
  assert.doesNotMatch(css, /data-code="BOTH_SIGNALS_(?:LOW|ELEVATED)"/);
  assert.match(css, /font-size: 1\.5rem/);
});
