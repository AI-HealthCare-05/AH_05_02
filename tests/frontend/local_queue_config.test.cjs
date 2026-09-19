// Read launcher source only; never imports config or reads .env.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
test('8022 launcher explicitly selects the project Redis published port', () => {
  const source = fs.readFileSync(path.join(__dirname, '../../scripts/run_frontend_local_8022.py'), 'utf8');
  assert.match(source, /"REDIS_HOST": "127\.0\.0\.1"/);
  assert.match(source, /"REDIS_PORT": "6380"/);
  assert.match(source, /os\.environ\.update\(local_queue_environment\(\)\)/);
  assert.match(source, /ai:jobs:local8022/);
  const worker = fs.readFileSync(path.join(__dirname, '../../scripts/run_worker_local_8022.py'), 'utf8');
  assert.match(worker, /local_queue_environment\(\)/);
  assert.match(worker, /run_worker\(prepare_schema=False\)/);
  assert.ok(!source.includes('S2_MODEL_RUNTIME_ENABLED'));
});
