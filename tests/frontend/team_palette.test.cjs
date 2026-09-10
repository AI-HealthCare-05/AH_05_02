const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const styles = fs.readFileSync(path.join(root, 'src/frontend/styles.css'), 'utf8');
const forest = fs.readFileSync(path.join(root, 'src/frontend/forest-game.css'), 'utf8');
// The user withdrew the unified palette; retain the distinct original themes.
test('main frontend restores the original background and buttons', () => {
  assert.match(styles, /--bg:#f6f7f4/);
  assert.match(styles, /--green:#176b5b/);
  assert.doesNotMatch(styles, /team palette: standardize/);
});
test('forest restores its original theme and avatar colors', () => {
  assert.match(forest, /--green:#2d8a5f/);
  assert.match(forest, /--paper:#fff;/);
  assert.doesNotMatch(forest, /team palette: unify/);
});
