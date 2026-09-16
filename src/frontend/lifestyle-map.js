/* Shared health-tools view. Calculations never write health records or model inputs. */
(function (root, factory) {
  const exports = factory();
  if (typeof module === "object" && module.exports) module.exports = exports;
  else root.LifestyleMap = exports;
})(typeof window === "undefined" ? globalThis : window, function () {
  "use strict";
  const topics = {
    meals: { label: "식사", icon: "1", question: "식사 습관은 어떻게 기록하나요?" },
    activity: { label: "활동", icon: "2", question: "작은 활동 목표는 어떻게 정하나요?" },
    metabolic: { label: "생활습관", icon: "3", question: "생활습관은 어떻게 점검하나요?" },
    checkup: { label: "정기 점검", icon: "4", question: "정기 검진 기록은 어떻게 관리하나요?" },
    body: { label: "체형 기록", icon: "5", question: "BMI는 어떤 참고 정보인가요?" },
  };
  function summaryContent(health = {}, medicalGuidance = false) {
    const meals = health.meal_count_yesterday;
    const hasMeals = Number.isInteger(meals) && meals >= 0;
    const exercise = health.regular_exercise;
    const smoking = health.smoking_status;
    const recordedHabit = smoking === "current" || health.current_smoker === true || health.current_drinker === true;
    const hasHabits = smoking || typeof health.current_smoker === "boolean" || typeof health.current_drinker === "boolean";
    return {
      meals: { value: hasMeals ? `어제 식사 횟수는 ${meals}회로 기록했어요.` : "식사 횟수는 하루 리듬을 확인하는 참고 정보예요.", action: hasMeals ? "규칙적인 식사 리듬을 챌린지로 이어갈 수 있어요." : "다음 입력 때 식사 리듬을 함께 점검해요." },
      activity: { value: exercise === true ? "규칙적인 운동을 하고 있다고 기록했어요." : exercise === false ? "규칙적인 운동을 하지 않는다고 기록했어요." : "운동 습관 기록이 필요합니다.", action: exercise === true ? "지금의 활동 습관을 무리 없이 유지해 보세요." : "짧은 걷기처럼 부담 낮은 활동부터 시작할 수 있어요." },
      metabolic: { value: recordedHabit ? "흡연·음주와 관련된 생활습관 기록이 있어요." : smoking === "former" ? "과거 흡연 이력이 기록되어 있어요." : hasHabits ? "입력한 생활습관과 신체·검진 정보를 확인했어요." : "아직 저장된 흡연·음주 생활습관 기록이 없어요.", action: recordedHabit ? "현재 기록을 바탕으로 바꾸기 쉬운 생활습관부터 점검해요." : "이 정보는 위험 판정이 아니라 생활습관 점검을 위한 참고 신호예요." },
      checkup: { value: medicalGuidance ? "확인할 검사·의료기관 상담 안내가 있어요." : "현재 위험 신호와 관계없이 정기적인 확인이 필요해요.", action: medicalGuidance ? "챌린지보다 검사·의료기관 상담 안내를 먼저 확인해 주세요." : "정기 검진과 생활습관 기록을 이어가 주세요." },
    };
  }
  const escape = value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  function positiveNumber(value) {
    if (value === null || value === undefined || typeof value === "boolean" || String(value).trim() === "") return null;
    const number = Number(value);
    return Number.isFinite(number) && number > 0 ? number : null;
  }
  function calculateBmi(height, weight) {
    const h = positiveNumber(height), w = positiveNumber(weight);
    const value = h && w ? w / ((h / 100) ** 2) : NaN;
    return Number.isFinite(value) ? value.toFixed(1) : null;
  }
  function challengeTopic(item, catalog = []) {
    const source = catalog.find(row => String(row.challenge_id) === String(item.challenge_id)) || item;
    const title = String(item.title || source.title || "");
    if (/수면|취침|기상|금연|흡연|음주/.test(title)) return "metabolic";
    if (/체중|체형|허리둘레|BMI/i.test(title)) return "body";
    if (/검진|검사|정기 점검/.test(title)) return "checkup";
    if (source.category === "diet" || /식사|식단|채소|음료|통곡물|덜 달게/.test(title)) return "meals";
    if (/걷기|걷|걸음/.test(title)) return "activity";
    if (source.category === "activity" || /운동|움직|근력|스트레칭|균형|유연성/.test(title)) return "activity";
    return null;
  }
  function weeklyProgress(report, item) {
    const row = report?.challenge_details?.find(row => String(row.user_challenge_id) === String(item.user_challenge_id));
    if (!row || !Number.isInteger(row.completed) || !Number.isInteger(row.planned)
      || row.completed < 0 || row.planned <= 0 || row.completed > row.planned) return null;
    return { completed: row.completed, planned: row.planned };
  }
  function mount(element, adapter) {
    if (!element) return null;
    const $ = selector => element.querySelector(selector);
    let carousel = null;
    let selected = "meals", built = false, helpOpen = false, draft = null, sourceKey = null, lastTrigger = null;
    const dialog = $("#habit-map-dialog");
    function data() { return adapter.getData(); }
    function syncSource(snapshot) {
      const health = snapshot.health || {};
      // Reset a calculator draft when its account, saved source, or source values change.
      const key = JSON.stringify([snapshot.owner, health.checkup_id, health.height_cm, health.weight_kg]);
      if (key !== sourceKey) {
        sourceKey = key;
        draft = { height: health.height_cm ?? "", weight: health.weight_kg ?? "" };
        $("#map-height").value = draft.height;
        $("#map-weight").value = draft.weight;
      }
    }
    function linked(snapshot, topic) {
      return (snapshot.challenges || []).filter(item => challengeTopic(item, snapshot.catalog) === topic);
    }
    function metric(snapshot, topic) {
      const health = snapshot.health || {};
      if (topic === "body") return calculateBmi(draft.height, draft.weight) ? `BMI ${calculateBmi(draft.height, draft.weight)}` : "계산 대기";
      return summaryContent(health, snapshot.medicalGuidance)[topic]?.value || "";
    }

    function sourceLabel(snapshot, topic) {
      if (topic === "body") return `키 ${positiveNumber(draft.height) ?? "—"}cm · 몸무게 ${positiveNumber(draft.weight) ?? "—"}kg`;
      if (topic === "checkup") return "정기 점검 안내";
      const health = snapshot.health || {};
      return (health.checkup_date || health.created_at) ? `${String(health.checkup_date || health.created_at).slice(0, 10)} · 건강정보 입력` : "건강정보 입력 기준";
    }
    function renderCards() {
      if (built) return;
      const assets = { meals: "card-meal", activity: "card-activity", metabolic: "cheer", checkup: "guide", body: "card-body-record" };
      const colors = { meals: "#e5ddec", activity: "#eadfc5", metabolic: "#d4e7ec", checkup: "#d5e8df", body: "#e0e8d2" };
      $("#habit-map-topics").innerHTML = Object.entries(topics).map(([key, topic]) => `<article class="education-overview-card" data-content-id="${key}" data-label="${topic.label}" style="--education-art:${colors[key]}"><button class="education-card-toggle" id="habit-toggle-${key}" type="button" aria-label="${topic.label} 기록 팝업 열기" aria-haspopup="dialog" aria-controls="habit-map-dialog"><span class="education-card-week">${topic.label}</span><span class="education-card-art"><img src="/static/assets/hyeoldangi-${assets[key]}.png" alt="" loading="lazy"></span></button></article>`).join("");
      built = true;
    }
    function renderBmi(snapshot) {
      const value = calculateBmi(draft.height, draft.weight);
      $("#map-bmi-value").textContent = value ?? "—";
      $("#map-bmi-summary").textContent = value ? sourceLabel(snapshot, "body") : "키와 몸무게를 양수로 모두 입력해 주세요.";
      const waist = positiveNumber(snapshot.health?.waist_cm);
      $("#map-waist").hidden = waist === null;
      $("#map-waist").textContent = waist ? `저장된 허리둘레 ${waist}cm` : "";
    }
    function renderChallenges(snapshot) {
      const items = linked(snapshot, selected);
      const list = $("#habit-map-challenges");
      if (!items.length) {
        list.innerHTML = '<p class="habit-map-empty">이 습관에 연결된 챌린지가 아직 없어요.</p>';
        return;
      }
      list.innerHTML = items.map(item => {
        const progress = weeklyProgress(snapshot.report, item);
        const done = snapshot.dailyStatus === "ready" ? snapshot.completed?.has(String(item.user_challenge_id)) : null;
        const today = done === null ? snapshot.dailyStatus === "error" ? "오늘 기록 확인 실패" : "오늘 기록 확인 중" : done ? "오늘 실천 완료" : "오늘 실천 기록 전";
        // The report supplies aggregates, not daily dates. Do not invent calendar ticks.
        return `<article class="habit-linked-challenge"><strong>${escape(item.title)}</strong><small>${today}</small>${progress ? `<div class="habit-progress-copy"><span>조회 기간 실천</span><b>${progress.completed} / ${progress.planned}회</b></div><progress max="${progress.planned}" value="${progress.completed}" aria-label="${escape(item.title)} 조회 기간 실천"></progress>` : `<p class="habit-map-empty">${snapshot.preview ? "기간별 기록은 실제 로그인 후 확인할 수 있어요." : snapshot.reportStatus === "error" ? "기간별 기록을 불러오지 못했어요." : "기간별 기록을 확인하고 있어요."}</p>`}</article>`;
      }).join("");
    }
    function refresh() {
      const snapshot = data();
      syncSource(snapshot);
      renderBmi(snapshot);
      $("#habit-body-panel").hidden = helpOpen || selected !== "body";
      $("#habit-record-panel").hidden = helpOpen || selected === "body";
      $("#lifestyle-help").hidden = !helpOpen;
      $("#habit-map-shared-actions").hidden = helpOpen;
      $("#habit-detail-label").textContent = `${topics[selected].icon} · 선택한 생활습관`;
      $("#habit-detail-title").textContent = topics[selected].label;
      $("#habit-detail-metric").textContent = metric(snapshot, selected);
      $("#habit-detail-source").textContent = sourceLabel(snapshot, selected);
      $("#habit-detail-note").textContent = summaryContent(snapshot.health, snapshot.medicalGuidance)[selected]?.action || "";
      $("#habit-help-topic").textContent = `${topics[selected].label} · 생활습관 도움말`;
      renderChallenges(snapshot);
      renderCards(snapshot);
      $("#habit-dialog-title").textContent = helpOpen ? `${topics[selected].label} · 도움말` : topics[selected].label;
    }
    function select(topic, showHelp = false, trigger = null) {
      selected = Object.hasOwn(topics, topic) ? topic : "body";
      helpOpen = showHelp;
      refresh();
      if (!dialog.open) {
        lastTrigger = trigger || $("#habit-toggle-" + selected);
        dialog.hidden = false;
        dialog.showModal();
        element.ownerDocument?.body.classList.add("habit-modal-open");
      }
      $("#rag-question").placeholder = `예: ${topics[selected].question}`;
      (helpOpen ? $("#rag-question") : $("#habit-dialog-title")).focus({ preventScroll: true });
    }
    dialog.addEventListener("close", () => {
      dialog.hidden = true;
      element.ownerDocument?.body.classList.remove("habit-modal-open");
      carousel?.close();
      lastTrigger?.focus({ preventScroll: true });
    });
    dialog.addEventListener("click", event => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    });
    element.addEventListener("input", event => {
      if (!["map-height", "map-weight"].includes(event.target.id)) return;
      draft.height = $("#map-height").value;
      draft.weight = $("#map-weight").value;
      const snapshot = data();
      renderBmi(snapshot);
      renderCards(snapshot);
    });
    element.addEventListener("click", event => {
      const button = event.target.closest("button");
      if (!button || button.disabled) return;
      if (button.id === "habit-dialog-close") dialog.close();
      if (button.id === "habit-help-back") { helpOpen = false; refresh(); $("#habit-dialog-title").focus(); }
      if (button.id === "habit-map-continue") adapter.openChallenge(linked(data(), selected)[0]);
      if (button.id === "habit-bmi-reset") { sourceKey = null; refresh(); }
    });
    refresh();
    carousel = adapter.mountCarousel?.($("#habit-carousel"), {
      listSelector: "#habit-carousel-list", statusSelector: "#habit-carousel-status", itemLabel: "생활습관",
      getLabel: card => card.dataset.label,
      onOpen: topic => select(topic === "help" ? selected : topic, topic === "help", topic === "help" ? $("#habit-map-help") : $("#habit-toggle-" + topic)),
    });
    return { refresh, select };
  }
  return { calculateBmi, positiveNumber, challengeTopic, weeklyProgress, summaryContent, mount };
});
