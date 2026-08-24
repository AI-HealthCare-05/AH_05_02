const state = { step: 1, token: null, checkupId: null, predictionId: null, prediction: null, cycle: null, wearableConnectionId: null, notificationsEnabled: true, foodAnalysisId: null, foodCategory: null, ocrDraftId: null };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);

const eligibilityGuidance = {
  URGENT_MEDICAL_ATTENTION: {
    code: "E03", title: "즉시 의료 확인이 필요합니다",
    message: "급한 경고 증상이 있으면 온라인 위험 분석을 진행하지 않습니다.",
    action: "지체하지 말고 119 또는 가까운 응급의료기관에 연락하세요.",
  },
  DIAGNOSED_DIABETES: {
    code: "D01", title: "당뇨병 기진단자는 예측 대상이 아닙니다",
    message: "이미 진단받은 분에게 신규 발병 위험 예측을 제공하지 않습니다.",
    action: "담당 의료진의 치료 지침을 우선하고 일반 건강정보를 확인하세요.",
  },
  UNDER_MINIMUM_SERVICE_AGE: {
    code: "E02", title: "만 19세 미만은 서비스를 이용할 수 없습니다",
    message: "현재 서비스의 이용 가능 연령은 만 19세 이상입니다.",
    action: "건강 문제가 있다면 보호자와 함께 의료기관에 상담하세요.",
  },
  MODEL_AGE_OUT_OF_RANGE: {
    code: "E05", title: "현재 모델의 적용 연령 범위가 아닙니다",
    message: "서비스는 이용할 수 있지만 현재 예측 모델은 만 45세 이상에게만 적용합니다.",
    action: "예측 대신 일반 건강정보를 확인하고 필요한 경우 건강검진을 받으세요.",
  },
  MODEL_POPULATION_OUT_OF_SCOPE: {
    code: "E05", title: "현재 모델의 적용 대상이 아닙니다",
    message: "현재 모델이 검증된 대상 범위 밖이므로 개인화 예측을 제공하지 않습니다.",
    action: "일반 건강정보를 확인하고 필요한 경우 의료진과 상담하세요.",
  },
  CONSENT_REQUIRED: {
    code: "E01", title: "건강정보 처리 동의가 필요합니다",
    message: "개인화 예측에는 건강정보 수집·이용 동의가 필요합니다.",
    action: "동의 내용을 다시 확인한 뒤 동의 여부를 선택하세요.",
  },
};

function showEligibilityGuidance(reasonCodes) {
  const priority = [
    "URGENT_MEDICAL_ATTENTION", "DIAGNOSED_DIABETES", "UNDER_MINIMUM_SERVICE_AGE",
    "MODEL_AGE_OUT_OF_RANGE", "MODEL_POPULATION_OUT_OF_SCOPE", "CONSENT_REQUIRED",
  ];
  const reason = priority.find((code) => reasonCodes.includes(code));
  const guidance = eligibilityGuidance[reason] || {
    code: "E00", title: "개인화 예측을 진행할 수 없습니다",
    message: "현재 입력 조건으로는 개인화 예측을 제공하지 않습니다.",
    action: "입력정보를 확인하거나 일반 건강정보를 이용하세요.",
  };
  $("#eligibility-guidance-code").textContent = guidance.code;
  $("#eligibility-guidance-title").textContent = guidance.title;
  $("#eligibility-guidance-message").textContent = guidance.message;
  $("#eligibility-guidance-action").textContent = guidance.action;
  $("#eligibility-guidance").hidden = false;
  $("#eligibility-guidance").scrollIntoView({ behavior: "smooth", block: "center" });
}

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
  if (state.step === 6) updateLifestyleMap(state.mapTopic || "rhythm");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function lifestyleMapContent(topic) {
  const height = Number($("#height").value || 0);
  const weight = Number($("#weight").value || 0);
  const bmi = height && weight ? (weight / ((height / 100) ** 2)).toFixed(1) : null;
  const waist = $("#waist").value;
  return {
    rhythm: { number: "1", title: "생활 리듬", value: "현재 건강입력에는 수면 정보가 포함되지 않았어요.", action: "웨어러블을 연결하면 주간 리포트에서 수면 기록을 확인할 수 있습니다." },
    activity: { number: "2", title: "활동 습관", value: $("#regular-exercise").checked ? "규칙적으로 운동한다고 기록했어요." : "규칙적인 운동을 하지 않는다고 기록했어요.", action: "몸 상태에 맞는 작은 활동 챌린지를 직접 선택할 수 있습니다." },
    body: { number: "3", title: "체형 기록", value: bmi ? `입력값으로 계산한 BMI는 ${bmi}${waist ? `, 허리둘레는 ${waist}cm` : ""}입니다.` : "키와 몸무게 기록이 필요합니다.", action: "수치는 위험 판정이 아니라 입력한 건강정보를 다시 확인하기 위한 표시입니다." },
    walking: { number: "4", title: "걷기 습관", value: "아직 걸음 수 기록을 연결하지 않았어요.", action: "챌린지에서 걷기 목표를 고르거나 건강도구에서 워치 기록을 연결해 보세요." },
  }[topic];
}

function updateLifestyleMap(topic) {
  state.mapTopic = topic;
  const content = lifestyleMapContent(topic);
  $("#map-detail-number").textContent = content.number;
  $("#map-detail-title").textContent = content.title;
  $("#map-detail-value").textContent = content.value;
  $("#map-detail-action").textContent = content.action;
  $$(".body-map-point").forEach((button) => button.classList.toggle("active", button.dataset.mapTopic === topic));
}
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(`/api/v1${path}`, { ...options, headers });
  let payload = {};
  try { payload = await response.json(); } catch { payload = {}; }
  if (!response.ok) {
    const detail = payload.detail;
    const validationMessage = Array.isArray(detail)
      ? detail.map((item) => `${item.loc?.slice(1).join(".") || "입력값"}: ${item.msg}`).join(" / ")
      : null;
    const message = typeof detail === "string" ? detail : validationMessage || detail?.message || payload.error?.message;
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
      const error = new Error(job.error_message || "분석 작업을 완료하지 못했습니다.");
      error.code = job.error_code || "INFERENCE_FAILED";
      throw error;
    }
    await sleep(1000);
  }
  throw new Error("상태 확인 시간이 초과되었습니다. 작업 이력에서 다시 확인해 주세요.");
}
function renderPrediction(prediction, factors) {
  const isPublic = prediction.result_status === "approved" && prediction.risk_category;
  $("#result-stage").textContent = isPublic ? prediction.risk_category_label : "범주 검토 중";
  $("#result-explain").textContent = prediction.disclaimer;
  $("#probability-policy").textContent = "검증 전 확률·개선율은 표시하지 않습니다.";
  $("#factor-list").innerHTML = factors.items.length
    ? factors.items.map((item) => `<li><strong>${item.factor_name}</strong><p>${item.description}</p></li>`).join("")
    : `<li><strong>설명 결과 준비 중</strong><p>${factors.message}</p></li>`;
  const isHighRisk = prediction.risk_category === "high";
  $("#high-guidance").hidden = !isHighRisk;
  $("#medical-guidance-detail").hidden = !isHighRisk;
  $("#result-next").textContent = isHighRisk ? "검사·의료기관 안내 보기" : "결과 설명 보기";
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
    const isTimeout = error.code === "TIMEOUT";
    $("#job-status").textContent = isTimeout ? "분석 상태: 시간 초과" : "분석 상태: 실패";
    $("#result-stage").textContent = "다시 시도 필요";
    $("#analysis-failure-title").textContent = isTimeout ? "분석 시간이 초과되었습니다" : "분석을 완료하지 못했습니다";
    $("#analysis-failure-message").textContent = isTimeout
      ? "입력정보는 보존되어 있습니다. 잠시 후 같은 정보로 다시 시도해 주세요."
      : "입력정보를 확인한 뒤 다시 시도해 주세요. 문제가 계속되면 관리자에게 문의하세요.";
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
    <span><strong>${item.title}</strong><small>목표: ${item.daily_goal}</small><small>${item.description}</small><small>추천 이유: ${item.recommendation_reason}</small>
    <small><a href="${item.source.url}" target="_blank" rel="noopener">근거: ${item.source.title}</a></small></span>
  </label>`).join("");
}
function renderCycle(cycle) {
  state.cycle = cycle;
  $("#dashboard-cycle").textContent = `${cycle.cycle_number}회차 · 4주`;
  $("#daily-log-list").innerHTML = cycle.user_challenges.map((item) => `<label class="daily-item"><input type="checkbox" name="daily" value="${item.user_challenge_id}"><span>${item.title}</span></label>`).join("");
  $("#barrier-challenge").innerHTML = cycle.user_challenges.map((item) => `<option value="${item.user_challenge_id}">${item.title}</option>`).join("");
}
async function loadWeeklyReport() {
  const report = await api("/weekly-reports/current");
  if (report.status === "empty") {
    $("#weekly-report").innerHTML = `<article><strong>기록 없음</strong><p>${report.message}</p></article>`;
    return;
  }
  $("#weekly-report").innerHTML = `<article><small>최근 7일 달성률</small><strong>${report.completion.rate}%</strong><p>${report.completion.completed}/${report.completion.planned}회</p></article>
    <article><small>가장 잘 실천한 습관</small><strong>${report.best_habit?.title || "기록 없음"}</strong><p>${report.best_habit?.completion_rate || 0}%</p></article>
    <article><small>기록 요약</small><strong>${report.next_adjustment.message}</strong><p>${report.record_summary}</p></article>`;
}
async function loadEducation() {
  const contents = await api("/education-contents");
  $("#education-list").innerHTML = contents.items.map((item) => {
    const noAnswer = item.quiz_question.includes("진단") || item.quiz_question.includes("치료") || item.quiz_question.includes("포기");
    return `<article class="challenge-card"><span><strong>${item.week_number}주차 · ${item.title}</strong><small>${item.summary}</small><small>${item.quiz_question}</small><button class="secondary education-complete" type="button" data-id="${item.content_id}" data-answer="${noAnswer ? "아니요" : "네"}">${item.completed ? "다시 확인" : "퀴즈 답변·완료"}</button><small><a href="${item.source.url}" target="_blank" rel="noopener">근거: ${item.source.title}</a></small></span></article>`;
  }).join("");
}
async function loadConnections() {
  const result = await api("/connections");
  $("#connection-list").innerHTML = result.items.length ? result.items.map((item) => `<article class="challenge-card"><span><strong>연결 사용자 #${item.connected_user_id}</strong><small>${item.relation_type} · 공유: 챌린지 수행 상태</small><small>건강정보 공유: 안 함</small><button class="text-button disconnect-connection" data-id="${item.connection_id}" type="button">연결 해제</button> <button class="text-button block-connection" data-id="${item.connection_id}" type="button">차단</button></span></article>`).join("") : `<p class="lead">아직 연결된 가족·친구가 없습니다.</p>`;
}

function showWorkspace(name) {
  $$(".workspace-tab").forEach((button) => {
    const selected = button.dataset.workspace === name;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-selected", String(selected));
  });
  $$("[data-workspace-panel]").forEach((panel) => {
    const selected = panel.dataset.workspacePanel === name;
    panel.hidden = !selected;
    panel.classList.toggle("active", selected);
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}
async function loadSharedGroups() {
  const result = await api("/shared-challenge-groups");
  $("#shared-group-list").innerHTML = result.items.length ? result.items.map((group) => {
    const me = group.members.find((member) => member.is_me);
    const partner = group.members.find((member) => !member.is_me && member.status === "active");
    const action = me?.status === "pending"
      ? `<button class="text-button accept-shared" data-id="${group.group_id}" type="button">공동 챌린지 수락</button>`
      : partner ? `<button class="text-button cheer-shared" data-id="${group.group_id}" data-user="${partner.user_id}" type="button">응원 보내기</button>` : "";
    return `<article class="challenge-card"><span><strong>${escapeHtml(group.title)}</strong><small>${escapeHtml(group.common_goal)}</small><small>참여자 ${group.members.length}명 · 수행 상태만 공유</small>${action}</span></article>`;
  }).join("") : `<p class="lead">아직 공동 챌린지가 없습니다.</p>`;
}
async function loadNotifications() {
  const [preferences, notifications] = await Promise.all([api("/notification-preferences"), api("/notifications")]);
  state.notificationsEnabled = preferences.in_app_enabled;
  $("#notification-toggle").textContent = state.notificationsEnabled ? "웹 알림 끄기" : "웹 알림 켜기";
  $("#notification-list").innerHTML = notifications.items.length ? notifications.items.map((item) => `<article class="challenge-card"><span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.message)}</small></span></article>`).join("") : `<p class="lead">표시할 웹 알림이 없습니다.</p>`;
}
async function refreshDashboard() {
  const summary = await api("/dashboard/summary");
  const card = summary.risk_cards[0];
  $("#dashboard-stage").textContent = card ? card.risk_category_label : "기록 없음";
  $("#dashboard-notice").textContent = summary.disclaimer;
  const progress = await api("/dashboard/challenge-progress");
  $("#dashboard-complete").textContent = `${progress.recent_7_days.completed}개`;
  await Promise.all([loadWeeklyReport(), loadEducation(), loadConnections(), loadSharedGroups(), loadNotifications()]);
}

$$('.next').forEach((button) => button.addEventListener("click", () => showStep(state.step + 1)));
$$('.back').forEach((button) => button.addEventListener("click", () => showStep(state.step - 1)));
$$('.workspace-tab, .workspace-shortcut').forEach((button) => button.addEventListener("click", () => showWorkspace(button.dataset.workspace)));
$$('.body-map-point').forEach((button) => button.addEventListener("click", () => updateLifestyleMap(button.dataset.mapTopic)));
$("#font-toggle").addEventListener("click", (event) => {
  const enabled = document.body.classList.toggle("large-text");
  event.currentTarget.setAttribute("aria-pressed", String(enabled));
  event.currentTarget.textContent = enabled ? "기본 글자" : "글자 크게";
});
$("#signup-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    $("#eligibility-guidance").hidden = true;
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
    $("#eligibility-guidance").hidden = true;
    const result = await api("/eligibility-checks", { method: "POST", body: JSON.stringify({
      birth_date: $("#birth-date").value,
      has_diabetes_diagnosis: $("#diagnosed-diabetes").checked,
      has_urgent_warning_sign: $("#urgent-warning").checked,
      population_in_scope: true,
    }) });
    if (!result.model_eligible) {
      showEligibilityGuidance(result.reason_codes);
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
$("#barrier-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await api(`/user-challenges/${$("#barrier-challenge").value}/barriers`, { method: "POST", body: JSON.stringify({
      log_date: new Date().toISOString().slice(0, 10), reason_code: $("#barrier-reason").value,
    }) });
    $("#barrier-suggestion").textContent = result.suggestion;
    await loadWeeklyReport();
  } catch (error) { showMessage(error.message); }
});
$("#education-list").addEventListener("click", async (event) => {
  const button = event.target.closest(".education-complete");
  if (!button) return;
  try {
    const result = await api(`/education-contents/${button.dataset.id}/progress`, { method: "PUT", body: JSON.stringify({ quiz_answer: button.dataset.answer }) });
    showMessage(result.is_correct ? "정답입니다. 교육 콘텐츠를 완료했습니다." : "내용을 다시 확인해 주세요.", result.is_correct ? "success" : "error");
    await loadEducation();
  } catch (error) { showMessage(error.message); }
});
$("#invite-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await api("/invitations", { method: "POST", body: JSON.stringify({
      invitee_email: $("#invite-email").value, relation_type: $("#relation-type").value,
    }) });
    const box = $("#invite-result");
    box.hidden = false;
    box.innerHTML = `<div><strong>초대 코드가 생성되었습니다</strong><p class="invite-code">${result.token}</p><small>${result.notice}</small></div>`;
  } catch (error) { showMessage(error.message); }
});
$("#accept-invite-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/invitations/accept", { method: "POST", body: JSON.stringify({ token: $("#invite-token").value }) });
    showMessage("가족·친구 연결을 완료했습니다.", "success");
    await loadConnections();
  } catch (error) { showMessage(error.message); }
});
$("#connection-list").addEventListener("click", async (event) => {
  const disconnect = event.target.closest(".disconnect-connection");
  const block = event.target.closest(".block-connection");
  if (!disconnect && !block) return;
  try {
    const target = disconnect || block;
    await api(`/connections/${target.dataset.id}${block ? "/block" : ""}`, { method: block ? "POST" : "DELETE" });
    await loadConnections();
    showMessage(block ? "연결을 차단했습니다." : "연결을 해제했습니다.", "success");
  } catch (error) { showMessage(error.message); }
});
$("#shared-challenge-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.cycle?.user_challenges?.length) return showMessage("먼저 개인 챌린지를 시작해 주세요.");
  const start = new Date();
  const end = new Date(); end.setDate(end.getDate() + 6);
  try {
    await api("/shared-challenge-groups", { method: "POST", body: JSON.stringify({
      title: "함께하는 생활습관 챌린지", challenge_id: state.cycle.user_challenges[0].challenge_id,
      start_date: start.toISOString().slice(0, 10), end_date: end.toISOString().slice(0, 10),
      common_goal: "서로 응원하며 일주일 실천", owner_goal: "하루 한 번 실천",
      members: [{ user_id: Number($("#shared-member-id").value), personal_goal: $("#shared-goal").value }],
    }) });
    await loadSharedGroups(); showMessage("공동 챌린지 초대를 만들었습니다.", "success");
  } catch (error) { showMessage(error.message); }
});
$("#login-existing").addEventListener("click", async () => {
  try {
    const login = await api("/auth/login", { method: "POST", body: JSON.stringify({ email: $("#email").value, password: $("#password").value }) });
    state.token = login.access_token;
    const consents = await api("/consents");
    if (!consents.items.some((item) => item.is_agreed && !item.withdrawn_at)) {
      showMessage("활성 건강정보 동의가 없습니다. 새 동의 절차를 진행해 주세요.");
      return;
    }
    try {
      const cycle = await api("/challenge-cycles/current");
      renderCycle(cycle);
      await refreshDashboard();
      showStep(8);
      return;
    } catch (cycleError) {
      if (!cycleError.message.includes("진행 중인 챌린지가 없습니다")) throw cycleError;
    }
    showStep(3);
  } catch (error) { showMessage(error.message); }
});
$("#shared-group-list").addEventListener("click", async (event) => {
  const accept = event.target.closest(".accept-shared");
  const cheer = event.target.closest(".cheer-shared");
  if (!accept && !cheer) return;
  try {
    if (accept) {
      await api(`/shared-challenge-groups/${accept.dataset.id}/accept`, { method: "POST" });
      showMessage("공동 챌린지에 참여했습니다.", "success");
    } else {
      await api(`/shared-challenge-groups/${cheer.dataset.id}/encouragements`, { method: "POST", body: JSON.stringify({ recipient_user_id: Number(cheer.dataset.user), template_code: "together" }) });
      showMessage("함께하는 사람에게 응원을 보냈습니다.", "success");
    }
    await loadSharedGroups();
  } catch (error) { showMessage(error.message); }
});
$("#wearable-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    if (!state.wearableConnectionId) {
      const connection = await api("/wearables/connections", { method: "POST", body: JSON.stringify({ provider: "development_mock", scopes: ["activity"] }) });
      state.wearableConnectionId = connection.connection_id;
    }
    const result = await api("/wearables/daily-summaries/import", { method: "POST", body: JSON.stringify({ connection_id: state.wearableConnectionId, items: [{ summary_date: new Date().toISOString().slice(0, 10), steps: Number($("#wearable-steps").value), active_minutes: Number($("#wearable-active").value) }] }) });
    const box = $("#wearable-result"); box.hidden = false; box.textContent = `${result.imported_count}일 기록을 가져왔습니다. 자동 챌린지 기록 ${result.auto_logged_challenges.length}건`;
    await refreshDashboard();
  } catch (error) { showMessage(error.message); }
});
$("#rag-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await api("/health-education/questions", { method: "POST", body: JSON.stringify({ question: $("#rag-question").value }) });
    const citations = result.citations.map((item) => `<li><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a></li>`).join("");
    const box = $("#rag-result"); box.hidden = false; box.innerHTML = `<div><strong>${escapeHtml(result.answer)}</strong>${citations ? `<ul>${citations}</ul>` : ""}<small>${escapeHtml(result.medical_notice)}</small></div>`;
  } catch (error) { showMessage(error.message); }
});
$("#food-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await api("/food-analyses", { method: "POST", body: JSON.stringify({ image_name: $("#food-image-name").value }) });
    state.foodAnalysisId = result.analysis_id;
    state.foodCategory = result.predicted_category;
    $("#confirm-food").hidden = false;
    const box = $("#assist-result"); box.hidden = false; box.textContent = `식단 분류 초안: ${result.predicted_category}. ${result.notice}`;
  } catch (error) { showMessage(error.message); }
});
$("#ocr-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await api("/ocr-drafts", { method: "POST", body: JSON.stringify({ document_name: "checkup-image.jpg", extracted_fields: { systolic_bp: Number($("#ocr-systolic").value) } }) });
    state.ocrDraftId = result.draft_id;
    $("#confirm-ocr").hidden = false;
    const box = $("#assist-result"); box.hidden = false; box.textContent = `OCR 초안: 수축기 혈압 ${result.extracted_fields.systolic_bp}. ${result.notice}`;
  } catch (error) { showMessage(error.message); }
});
$("#confirm-food").addEventListener("click", async () => {
  if (!state.foodAnalysisId) return;
  try {
    const result = await api(`/food-analyses/${state.foodAnalysisId}/confirm`, { method: "PATCH", body: JSON.stringify({ confirmed_category: state.foodCategory || "확인불가" }) });
    $("#assist-result").textContent = `식단 기록을 ${result.confirmed_category}로 확인했습니다.`;
    $("#confirm-food").hidden = true;
  } catch (error) { showMessage(error.message); }
});
$("#confirm-ocr").addEventListener("click", async () => {
  if (!state.ocrDraftId) return;
  try {
    const result = await api(`/ocr-drafts/${state.ocrDraftId}/confirm`, { method: "POST" });
    $("#assist-result").textContent = `${result.next_action} 건강검진 기록에는 아직 저장되지 않았습니다.`;
    $("#confirm-ocr").hidden = true;
  } catch (error) { showMessage(error.message); }
});
$("#notification-toggle").addEventListener("click", async () => {
  try {
    await api("/notification-preferences", { method: "PUT", body: JSON.stringify({ in_app_enabled: !state.notificationsEnabled, challenge_reminder_enabled: true, weekly_report_enabled: true, quiet_start_hour: 21, quiet_end_hour: 8 }) });
    await loadNotifications();
  } catch (error) { showMessage(error.message); }
});
$("#download-report").addEventListener("click", async () => {
  try {
    const response = await fetch("/api/v1/weekly-reports/current/pdf", { headers: { Authorization: `Bearer ${state.token}` } });
    if (!response.ok) throw new Error("PDF를 만들지 못했습니다.");
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a"); link.href = url; link.download = "간당간당_주간리포트.pdf"; link.click(); URL.revokeObjectURL(url);
  } catch (error) { showMessage(error.message); }
});
$("#restart").addEventListener("click", () => window.location.reload());
