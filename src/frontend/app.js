const state = { step: 1, token: null, checkupId: null, predictionId: null, prediction: null, cycle: null };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

function showMessage(message, kind = "error") {
  const box = $("#message");
  box.textContent = message;
  box.dataset.kind = kind;
  box.hidden = false;
  box.scrollIntoView({ behavior: "smooth", block: "center" });
}
function clearMessage() { $("#message").hidden = true; }
function showStep(step) {
  state.step = Math.max(1, Math.min(8, step));
  clearMessage();
  $$(".screen").forEach((element) => element.classList.toggle("active", Number(element.dataset.step) === state.step));
  $$("#step-list li").forEach((element, index) => {
    element.classList.toggle("active", index + 1 === state.step);
    element.classList.toggle("complete", index + 1 < state.step);
  });
  $("#step-current").textContent = state.step;
  $("#progress-bar").style.width = `${(state.step / 8) * 100}%`;
  window.scrollTo({ top: 0, behavior: "smooth" });
}
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(`/api/v1${path}`, { ...options, headers });
  let payload = {};
  try { payload = await response.json(); } catch { payload = {}; }
  if (!response.ok) {
    const detail = payload.detail;
    const message = typeof detail === "string" ? detail : detail?.message || payload.error?.message;
    throw new Error(message || "요청을 처리하지 못했습니다.");
  }
  return payload.data ?? payload;
}
async function pollPrediction(jobId) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < 35000) {
    const job = await api(`/prediction-jobs/${jobId}`);
    $("#job-status").textContent = `분석 상태: ${job.status}`;
    if (job.status === "succeeded") return job.prediction_id;
    if (job.status === "failed") {
      const suffix = job.error_code === "TIMEOUT" ? " 잠시 후 다시 시도해 주세요." : " 관리자에게 문의해 주세요.";
      throw new Error(`분석에 실패했습니다 (${job.error_code || "INFERENCE_FAILED"}).${suffix}`);
    }
    await sleep(1000);
  }
  throw new Error("상태 확인 시간이 초과되었습니다. 작업 이력에서 다시 확인해 주세요.");
}
function renderPrediction(prediction, factors) {
  const isPublic = prediction.result_status === "approved" && prediction.risk_category;
  $("#result-stage").textContent = isPublic ? prediction.risk_category_label : "범주 검토 중";
  $("#result-explain").textContent = prediction.disclaimer;
  $("#model-version").textContent = `${prediction.model_version} · ${prediction.feature_schema_version}`;
  $("#probability-policy").textContent = "검증 전 확률·개선율은 표시하지 않습니다.";
  $("#factor-list").innerHTML = factors.items.length
    ? factors.items.map((item) => `<li><strong>${item.factor_name}</strong><p>${item.description}</p></li>`).join("")
    : `<li><strong>설명 결과 준비 중</strong><p>${factors.message}</p></li>`;
  $("#high-guidance").hidden = prediction.risk_category !== "high";
  $("#analysis-failure").hidden = true;
  $("#retry-analysis").hidden = true;
  $("#result-next").disabled = false;
}
async function runPrediction() {
  $("#analysis-failure").hidden = true;
  $("#retry-analysis").hidden = true;
  $("#result-next").disabled = true;
  $("#job-status").textContent = "분석 상태: queued";
  try {
    const job = await api("/prediction-jobs", { method: "POST", body: JSON.stringify({
      checkup_id: state.checkupId, model_key: "diabetes_incidence",
    }) });
    state.predictionId = await pollPrediction(job.job_id);
    const [prediction, factors] = await Promise.all([
      api(`/predictions/${state.predictionId}`),
      api(`/predictions/${state.predictionId}/risk-factors`),
    ]);
    state.prediction = prediction;
    renderPrediction(prediction, factors);
  } catch (error) {
    $("#job-status").textContent = "분석 상태: 실패";
    $("#result-stage").textContent = "다시 시도 필요";
    $("#analysis-failure").hidden = false;
    $("#retry-analysis").hidden = false;
    showMessage(error.message);
  }
}
async function loadChallenges() {
  const query = state.predictionId ? `?prediction_id=${state.predictionId}` : "";
  const result = await api(`/challenge-recommendations${query}`);
  if (result.medical_guidance_required_first) showMessage("의료기관 안내를 먼저 확인한 뒤 챌린지를 선택해 주세요.");
  $("#challenge-list").innerHTML = result.items.map((item, index) => `<label class="challenge-card">
    <input type="checkbox" name="challenge" value="${item.challenge_id}" ${index === 0 ? "checked" : ""}>
    <span><strong>${item.title}</strong><small>목표: ${item.daily_goal}</small><small>${item.description}</small>
    <small><a href="${item.source.url}" target="_blank" rel="noopener">근거: ${item.source.title}</a></small></span>
  </label>`).join("");
}
function renderCycle(cycle) {
  state.cycle = cycle;
  $("#dashboard-cycle").textContent = `${cycle.cycle_number}회차 · 4주`;
  $("#daily-log-list").innerHTML = cycle.user_challenges.map((item) => `<label class="daily-item"><input type="checkbox" name="daily" value="${item.user_challenge_id}"><span>${item.title}</span></label>`).join("");
}
async function refreshDashboard() {
  const summary = await api("/dashboard/summary");
  const card = summary.risk_cards[0];
  $("#dashboard-stage").textContent = card ? card.risk_category_label : "기록 없음";
  $("#dashboard-notice").textContent = summary.disclaimer;
  const progress = await api("/dashboard/challenge-progress");
  $("#dashboard-complete").textContent = `${progress.recent_7_days.completed}개`;
}

$$('.next').forEach((button) => button.addEventListener("click", () => showStep(state.step + 1)));
$$('.back').forEach((button) => button.addEventListener("click", () => showStep(state.step - 1)));
$("#font-toggle").addEventListener("click", (event) => {
  const enabled = document.body.classList.toggle("large-text");
  event.currentTarget.setAttribute("aria-pressed", String(enabled));
  event.currentTarget.textContent = enabled ? "기본 글자" : "글자 크게";
});
$("#signup-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const email = $("#email").value;
    const password = $("#password").value;
    await api("/auth/signup", { method: "POST", body: JSON.stringify({
      email, password, gender: $("#gender").value,
      birth_date: $("#birth-date").value,
    }) });
    const login = await api("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
    state.token = login.access_token;
    await api("/consents", { method: "POST", body: JSON.stringify({ consent_item: "health_data", version: "1.0", is_agreed: true }) });
    showStep(3);
  } catch (error) { showMessage(error.message); }
});
$("#eligibility-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await api("/eligibility-checks", { method: "POST", body: JSON.stringify({
      birth_date: $("#birth-date").value,
      has_diabetes_diagnosis: $("#diagnosed-diabetes").checked,
      has_urgent_warning_sign: $("#urgent-warning").checked,
      population_in_scope: true,
    }) });
    if (!result.model_eligible) {
      showMessage(`개인화 예측을 진행할 수 없습니다: ${result.reason_codes.join(", ")}. 다음 안내: ${result.next_action}`);
      return;
    }
    showStep(4);
  } catch (error) { showMessage(error.message); }
});
$("#health-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = event.submitter;
  submit.disabled = true;
  submit.textContent = "분석 요청 중…";
  try {
    const checkup = await api("/health-checkups", { method: "POST", body: JSON.stringify({
      checkup_type: "initial", checkup_date: new Date().toISOString().slice(0, 10),
      height_cm: Number($("#height").value), weight_kg: Number($("#weight").value),
      waist_cm: $("#waist").value ? Number($("#waist").value) : null,
      systolic_bp: $("#systolic").value ? Number($("#systolic").value) : null,
      diastolic_bp: $("#diastolic").value ? Number($("#diastolic").value) : null,
      self_rated_health: $("#self-health").value, meal_count_yesterday: Number($("#meal-count").value),
      regular_exercise: $("#regular-exercise").checked, current_smoker: $("#current-smoker").checked,
      current_drinker: $("#current-drinker").checked, feature_schema_version: "klosa-diabetes-incident-v1",
    }) });
    state.checkupId = checkup.checkup_id;
    showStep(5);
    await runPrediction();
  } catch (error) { showMessage(error.message); }
  finally { submit.disabled = false; submit.textContent = "미래 발병 위험 분석 요청"; }
});
$("#retry-analysis").addEventListener("click", runPrediction);
$("#feedback-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.predictionId) return showMessage("피드백을 연결할 분석 결과가 없습니다.");
  try {
    await api("/feedback", { method: "POST", body: JSON.stringify({
      context_type: "prediction",
      prediction_id: state.predictionId,
      rating: Number($("#feedback-rating").value),
      comment: $("#feedback-comment").value || null,
    }) });
    showMessage("의견을 저장했습니다.", "success");
  } catch (error) { showMessage(error.message); }
});
$("#to-challenges").addEventListener("click", async () => {
  try { await loadChallenges(); showStep(7); } catch (error) { showMessage(error.message); }
});
$("#challenge-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const ids = $$("input[name='challenge']:checked").map((input) => Number(input.value));
  if (!ids.length) return showMessage("챌린지를 하나 이상 선택해 주세요.");
  try {
    const cycle = await api("/challenge-cycles", { method: "POST", body: JSON.stringify({
      start_date: new Date().toISOString().slice(0, 10), challenge_ids: ids, prediction_id: state.predictionId,
    }) });
    renderCycle(cycle); await refreshDashboard(); showStep(8);
  } catch (error) { showMessage(error.message); }
});
$("#daily-log-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const today = new Date().toISOString().slice(0, 10);
    await Promise.all($$("input[name='daily']").map((input) => api(`/user-challenges/${input.value}/logs/${today}`, {
      method: "PUT", body: JSON.stringify({ is_completed: input.checked, source: "self_report", note: null }),
    })));
    await refreshDashboard(); showMessage("오늘 기록을 저장했습니다.", "success");
  } catch (error) { showMessage(error.message); }
});
$("#restart").addEventListener("click", () => window.location.reload());
