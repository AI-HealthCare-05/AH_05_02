const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("src/frontend/app.js", "utf8");

function load(names, context) {
  const ctx = vm.createContext(context);
  for (const name of names) {
    const fn = source.match(new RegExp(`^(?:async )?function ${name}\\([^]*?^}`, "m"));
    assert.ok(fn, name);
    vm.runInContext(fn[0], ctx);
  }
  return ctx;
}

test("new user without a cycle can select from home; ongoing cycle hides the extra entry", () => {
  const nodes = {};
  const $ = key => nodes[key] ||= { hidden: false, textContent: "" };
  const state = { cycle: null, dailyCompleted: new Set(), visitedSteps: new Set([2, 3, 4, 5, 6, 8]) };
  const ctx = load(["hasCurrentChallengeCycle", "renderTodayTaskStatus"], { $, state });
  ctx.renderTodayTaskStatus();
  assert.equal($("#today-select-challenge").hidden, false);
  assert.match($("#today-task-title").textContent, /선택한 챌린지가 없/);
  state.cycle = { status: "active", user_challenges: [{ user_challenge_id: 1 }] };
  ctx.renderTodayTaskStatus();
  assert.equal($("#today-select-challenge").hidden, true);
});

test("newly analysed user reaches selection before slow recommendations complete", async () => {
  const state = { token: "test-session", cycle: null, step: 8, visitedSteps: new Set([2, 3, 4, 5, 6, 8]) };
  let resolve;
  let started = false;
  const ctx = load(["hasCurrentChallengeCycle", "openChallengeTab"], {
    state,
    isLocalPreview: () => false,
    requireActiveHealthConsent: () => true,
    api: async () => {
      throw Object.assign(new Error("진행 중인 챌린지가 없습니다."), { status: 404 });
    },
    clearCurrentChallengeCycle() { state.cycle = null; },
    showChallengeSelectionView() {},
    showStep(step) { state.step = step; },
    loadChallenges() {
      started = true;
      return new Promise(done => { resolve = done; });
    },
  });
  const pending = ctx.openChallengeTab();
  await new Promise(done => setImmediate(done));
  assert.equal(started, true);
  assert.equal(state.step, 7);
  resolve();
  await pending;
});

test("cycle lookup failure is not treated as an empty cycle or allowed to replace it", async () => {
  const state = { token: "test-session", cycle: null };
  let selected = false;
  const ctx = load(["hasCurrentChallengeCycle", "openChallengeTab"], {
    state,
    isLocalPreview: () => false,
    requireActiveHealthConsent: () => true,
    api: async () => {
      throw Object.assign(new Error("서비스 연결 실패"), { status: 503 });
    },
    showChallengeSelectionView() { selected = true; },
    loadChallenges() { selected = true; },
  });
  await assert.rejects(ctx.openChallengeTab(), /서비스 연결 실패/);
  assert.equal(selected, false);
});

test("empty recording state always includes a selection button", () => {
  const nodes = {};
  const $ = key => nodes[key] ||= { hidden: false, innerHTML: "", closest() { return this; } };
  const state = { cycle: null, activeWorkspace: "challenge" };
  const ctx = load(["hasCurrentChallengeCycle", "renderDailyRecordList"], { $, state });
  ctx.renderDailyRecordList();
  assert.match($("#daily-log-list").innerHTML, /기록할 챌린지가 없습니다/);
  assert.match($("#daily-log-list").innerHTML, /class="primary daily-record-select"/);
  assert.match($("#daily-log-list").innerHTML, /챌린지 선택하러 가기/);
});
