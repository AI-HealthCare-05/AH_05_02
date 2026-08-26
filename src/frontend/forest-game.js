(() => {
  "use strict";

  const STORAGE_KEY = "gandang-carrot-forest-demo-v1";
  const TILE = 32;
  const MAP_WIDTH = 24;
  const MAP_HEIGHT = 16;
  const TODAY = new Date().toISOString().slice(0, 10);
  const $ = (selector) => document.querySelector(selector);

  const quests = [
    { id: "walk", title: "가볍게 걷기", description: "내가 정한 걷기 목표 확인" },
    { id: "meal", title: "규칙적으로 식사하기", description: "오늘 식사 기록 남기기" },
    { id: "check", title: "건강 기록 확인하기", description: "입력한 생활습관 다시 보기" },
  ];
  const presets = {
    sprout: { label: "새싹 정원사", hair: "#4b2f24", outfit: "#4f9e63", accent: "#c8f06a" },
    carrot: { label: "당근 탐험가", hair: "#7b3d20", outfit: "#f07b32", accent: "#ffe078" },
    moon: { label: "달빛 산책가", hair: "#303c61", outfit: "#536eb5", accent: "#d9e3ff" },
    berry: { label: "산딸기 수집가", hair: "#5d2949", outfit: "#b44f78", accent: "#ffd2df" },
  };
  const itemCatalog = {
    red_scarf: { name: "빨간 목도리", kind: "accessory", icon: "🧣" },
    sprout_hat: { name: "새싹 모자", kind: "accessory", icon: "🌱" },
    carrot_bag: { name: "당근 가방", kind: "accessory", icon: "🎒" },
    flower_patch: { name: "꽃밭", kind: "object", icon: "🌼" },
    lantern: { name: "숲 등불", kind: "object", icon: "🏮" },
    mushroom: { name: "버섯 장식", kind: "object", icon: "🍄" },
    bench: { name: "나무 벤치", kind: "object", icon: "🪵" },
  };
  const rewardPool = ["sprout_hat", "carrot_bag", "lantern", "mushroom"];

  function defaultState() {
    return {
      dateKey: TODAY,
      avatar: { name: "세준", gender: "female", preset: "sprout", x: 384, y: 352, equipped: null },
      quests: { walk: false, meal: false, check: false },
      members: [
        { id: "me", name: "나", completed: 0, me: true },
        { id: "m2", name: "빛샘", completed: 3 },
        { id: "m3", name: "준혁", completed: 3 },
        { id: "m4", name: "수인", completed: 3 },
        { id: "m5", name: "숲지기", completed: 3 },
      ],
      carrots: 100,
      inventory: ["red_scarf", "flower_patch", "bench"],
      placed: [],
      rewardClaimed: false,
    };
  }

  function normalizeState(value) {
    const fallback = defaultState();
    if (!value || value.dateKey !== TODAY) return fallback;
    const state = { ...fallback, ...value };
    state.avatar = { ...fallback.avatar, ...(value.avatar || {}) };
    state.quests = { ...fallback.quests, ...(value.quests || {}) };
    state.members = Array.isArray(value.members) && value.members.length === 5 ? value.members : fallback.members;
    state.inventory = [...new Set(Array.isArray(value.inventory) ? value.inventory : fallback.inventory)]
      .filter((code) => itemCatalog[code]);
    state.placed = Array.isArray(value.placed) ? value.placed.filter((item) => itemCatalog[item.code]) : [];
    return state;
  }

  class DemoForestAdapter {
    constructor() { this.mode = "demo"; }
    async load() {
      try { return normalizeState(JSON.parse(localStorage.getItem(STORAGE_KEY))); }
      catch { return defaultState(); }
    }
    async save(state) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      return state;
    }
  }

  class ApiForestAdapter {
    constructor(token) { this.mode = "api"; this.token = token; }
    async request(path, options = {}) {
      const response = await fetch(`/api/v1${path}`, {
        ...options,
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${this.token}` },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail?.message || payload.detail || "당근의 숲 API 요청에 실패했습니다.");
      return payload.data ?? payload;
    }
    loadForest(groupId) { return this.request(`/forest/spaces/${groupId}`); }
    updateAvatar(body) { return this.request("/forest/avatar", { method: "PATCH", body: JSON.stringify(body) }); }
    updateQuest(userChallengeId, logDate, completed) {
      return this.request(`/user-challenges/${userChallengeId}/logs/${logDate}`, {
        method: "PUT", body: JSON.stringify({ is_completed: completed, input_source: "manual" }),
      });
    }
    claimReward(groupId) { return this.request(`/forest/spaces/${groupId}/rewards/group-daily`, { method: "POST" }); }
    placeObject(groupId, body) {
      return this.request(`/forest/spaces/${groupId}/objects`, { method: "POST", body: JSON.stringify(body) });
    }
  }

  const adapter = new DemoForestAdapter();
  let state = defaultState();
  let placementCode = null;
  const canvas = $("#forest-canvas");
  const context = canvas.getContext("2d");
  context.imageSmoothingEnabled = false;

  function setStatus(message) { $("#game-status").textContent = message; }
  function personalCompleted() { return Object.values(state.quests).filter(Boolean).length; }
  function groupCompleted() { return state.members.reduce((total, member) => total + member.completed, 0); }
  async function persist(message = null) {
    await adapter.save(state);
    if (message) setStatus(message);
  }

  function fillPixelRect(x, y, width, height, color) {
    context.fillStyle = color;
    context.fillRect(Math.round(x), Math.round(y), Math.round(width), Math.round(height));
  }

  function drawTree(x, y, scale = 1) {
    fillPixelRect(x + 12 * scale, y + 24 * scale, 10 * scale, 20 * scale, "#75462a");
    fillPixelRect(x + 4 * scale, y + 8 * scale, 28 * scale, 24 * scale, "#236b3b");
    fillPixelRect(x, y + 14 * scale, 36 * scale, 12 * scale, "#2f7e46");
    fillPixelRect(x + 10 * scale, y, 18 * scale, 12 * scale, "#55a94e");
  }

  function drawMap() {
    fillPixelRect(0, 0, canvas.width, canvas.height, "#75b965");
    for (let y = 0; y < MAP_HEIGHT; y += 1) {
      for (let x = 0; x < MAP_WIDTH; x += 1) {
        if ((x + y) % 3 === 0) fillPixelRect(x * TILE + 6, y * TILE + 7, 4, 4, "#9ad175");
      }
    }
    fillPixelRect(0, 330, canvas.width, 86, "#d8b472");
    fillPixelRect(352, 0, 72, canvas.height, "#e2c689");
    fillPixelRect(500, 54, 220, 170, "#9a643e");
    for (let row = 0; row < 4; row += 1) {
      for (let column = 0; column < 6; column += 1) {
        const x = 515 + column * 32;
        const y = 72 + row * 36;
        fillPixelRect(x, y, 20, 24, "#6f3f27");
        fillPixelRect(x + 8, y - 7, 5, 12, "#f4812d");
        fillPixelRect(x + 5, y - 10, 4, 8, "#3b914a");
        fillPixelRect(x + 12, y - 10, 4, 8, "#51aa58");
      }
    }
    fillPixelRect(54, 58, 180, 128, "#f3cc6d");
    fillPixelRect(42, 74, 204, 32, "#b64a35");
    fillPixelRect(66, 98, 156, 102, "#f8e2a4");
    fillPixelRect(126, 136, 42, 64, "#7a4b2e");
    fillPixelRect(82, 118, 30, 34, "#8ad0e8");
    fillPixelRect(180, 118, 30, 34, "#8ad0e8");
    drawTree(330, 116, 2.15);
    for (let x = 0; x < canvas.width; x += 96) { drawTree(x, 0, .85); drawTree(x + 30, 445, .75); }
    for (let y = 70; y < 420; y += 100) { drawTree(4, y, .72); drawTree(725, y, .72); }
    drawPlacedObjects();
  }

  function drawPlacedObjects() {
    state.placed.forEach((item) => {
      const x = item.x;
      const y = item.y;
      if (item.code === "flower_patch") {
        fillPixelRect(x - 15, y - 7, 30, 14, "#4b8e3f");
        [[-10, -8, "#ffcf43"], [0, -12, "#f16d77"], [10, -7, "#fff2a8"]].forEach(([dx, dy, color]) => fillPixelRect(x + dx, y + dy, 7, 7, color));
      } else if (item.code === "bench") {
        fillPixelRect(x - 18, y - 10, 36, 9, "#875333"); fillPixelRect(x - 14, y, 28, 7, "#a86a3f");
        fillPixelRect(x - 12, y + 7, 5, 10, "#5b3a28"); fillPixelRect(x + 8, y + 7, 5, 10, "#5b3a28");
      } else if (item.code === "lantern") {
        fillPixelRect(x - 3, y - 18, 6, 34, "#49362e"); fillPixelRect(x - 10, y - 20, 20, 18, "#ffd456"); fillPixelRect(x - 6, y - 16, 12, 10, "#ff9340");
      } else {
        fillPixelRect(x - 10, y - 4, 20, 12, "#eee4d2"); fillPixelRect(x - 7, y - 16, 14, 13, "#e34e42");
      }
    });
  }

  function drawAvatar() {
    const avatar = state.avatar;
    const style = presets[avatar.preset] || presets.sprout;
    const x = Math.round(avatar.x / 4) * 4;
    const y = Math.round(avatar.y / 4) * 4;
    fillPixelRect(x - 15, y + 26, 30, 7, "rgba(33,65,44,.25)");
    fillPixelRect(x - 10, y - 19, 20, 19, "#f0b98e");
    if (avatar.gender === "female") {
      fillPixelRect(x - 14, y - 24, 28, 10, style.hair); fillPixelRect(x - 14, y - 14, 6, 21, style.hair); fillPixelRect(x + 8, y - 14, 6, 21, style.hair);
    } else if (avatar.gender === "male") {
      fillPixelRect(x - 12, y - 24, 24, 9, style.hair); fillPixelRect(x - 14, y - 19, 7, 10, style.hair);
    } else {
      fillPixelRect(x - 13, y - 24, 26, 10, style.hair); fillPixelRect(x + 8, y - 15, 6, 14, style.hair);
    }
    fillPixelRect(x - 13, y, 26, 22, style.outfit); fillPixelRect(x - 18, y + 3, 6, 17, "#f0b98e"); fillPixelRect(x + 12, y + 3, 6, 17, "#f0b98e");
    fillPixelRect(x - 11, y + 22, 9, 13, "#334b5e"); fillPixelRect(x + 2, y + 22, 9, 13, "#334b5e");
    fillPixelRect(x - 7, y - 11, 3, 3, "#2d2a28"); fillPixelRect(x + 4, y - 11, 3, 3, "#2d2a28");
    fillPixelRect(x - 9, y + 3, 18, 5, style.accent);
    if (avatar.equipped === "red_scarf") fillPixelRect(x - 13, y - 1, 26, 6, "#d93432");
    if (avatar.equipped === "sprout_hat") { fillPixelRect(x - 15, y - 28, 30, 6, "#4a9b46"); fillPixelRect(x - 2, y - 36, 5, 9, "#2f7f3c"); }
    if (avatar.equipped === "carrot_bag") fillPixelRect(x + 13, y + 7, 9, 14, "#ec7a2f");
    context.font = "bold 15px sans-serif";
    context.textAlign = "center";
    context.fillStyle = "rgba(255,255,255,.94)";
    context.fillRect(x - Math.max(30, avatar.name.length * 8), y - 56, Math.max(60, avatar.name.length * 16), 22);
    context.fillStyle = "#18382d";
    context.fillText(avatar.name, x, y - 40);
  }

  function renderCanvas() {
    context.clearRect(0, 0, canvas.width, canvas.height);
    drawMap();
    drawAvatar();
    $("#avatar-coordinate").textContent = `X ${Math.round(state.avatar.x)} · Y ${Math.round(state.avatar.y)}`;
  }

  function blocked(x, y) {
    if (x < 28 || x > canvas.width - 28 || y < 42 || y > canvas.height - 38) return true;
    if (x > 38 && x < 250 && y > 45 && y < 215) return true;
    if (x > 500 && x < 730 && y > 45 && y < 230) return true;
    if (x > 315 && x < 440 && y > 85 && y < 265) return true;
    return false;
  }

  async function moveAvatar(direction) {
    const delta = { up: [0, -12], down: [0, 12], left: [-12, 0], right: [12, 0] }[direction];
    if (!delta) return;
    const nextX = state.avatar.x + delta[0];
    const nextY = state.avatar.y + delta[1];
    if (!blocked(nextX, nextY)) { state.avatar.x = nextX; state.avatar.y = nextY; renderCanvas(); await persist(); }
    else setStatus("그쪽에는 집·나무·당근밭이 있어요. 다른 방향으로 움직여 주세요.");
  }

  function renderQuests() {
    $("#quest-list").innerHTML = quests.map((quest) => `<label class="quest-item"><input type="checkbox" data-quest="${quest.id}" ${state.quests[quest.id] ? "checked" : ""}><span><strong>${quest.title}</strong><small>${quest.description}</small></span></label>`).join("");
    const completed = personalCompleted();
    state.members.find((member) => member.me).completed = completed;
    $("#personal-progress").textContent = `${completed}/3`;
    $("#heading-personal-progress").textContent = `${completed} / 3`;
  }

  function renderGroup() {
    const completed = groupCompleted();
    $("#group-progress").textContent = `${completed}/15`;
    $("#heading-group-progress").textContent = `${completed} / 15`;
    const progressbar = $(".progress-track[role='progressbar']");
    progressbar.setAttribute("aria-valuenow", String(completed));
    $("#group-progress-bar").style.width = `${completed / 15 * 100}%`;
    $("#member-list").innerHTML = state.members.map((member) => `<li><span aria-hidden="true">${member.completed === 3 ? "✅" : "🌱"}</span><span><strong>${member.name}</strong><small>${member.me ? "내 퀘스트" : "구성원"}</small></span><span class="member-progress">${member.completed}/3</span></li>`).join("");
    const rewardButton = $("#reward-button");
    rewardButton.disabled = completed < 15 || state.rewardClaimed;
    rewardButton.textContent = state.rewardClaimed ? "오늘의 보물상자 받음" : completed >= 15 ? "무료 보물상자 열기" : `${15 - completed}개 더 완료하면 보물상자 열기`;
  }

  function renderInventory() {
    $("#inventory-list").innerHTML = state.inventory.map((code) => {
      const item = itemCatalog[code];
      const equipped = item.kind === "accessory" && state.avatar.equipped === code;
      const selected = item.kind === "object" && placementCode === code;
      return `<button class="inventory-item" type="button" data-item="${code}" data-kind="${item.kind}" data-placement="${selected}" aria-pressed="${equipped || selected}"><span aria-hidden="true">${item.icon}</span><strong>${item.name}</strong><small>${item.kind === "accessory" ? equipped ? "장착 중" : "장착하기" : selected ? "맵을 눌러 배치" : "배치 선택"}</small></button>`;
    }).join("");
    $("#cancel-placement").hidden = !placementCode;
    $("#placement-mode").textContent = placementCode ? `${itemCatalog[placementCode].name} 배치 위치를 맵에서 선택하세요` : "배치할 아이템 없음";
  }

  function renderPlaced() {
    $("#object-count").textContent = `${state.placed.length}개`;
    $("#placed-list").innerHTML = state.placed.length
      ? state.placed.map((item, index) => `<div class="placed-object-row"><span aria-hidden="true">${itemCatalog[item.code].icon}</span><strong>${itemCatalog[item.code].name}</strong><button class="remove-object" type="button" data-remove="${index}">창고로 돌려놓기</button></div>`).join("")
      : "<p>아직 배치한 오브젝트가 없습니다.</p>";
  }

  function renderAll() {
    $("#adapter-badge").textContent = adapter.mode === "demo" ? "Demo Adapter" : "Live API";
    $("#carrot-balance").textContent = state.carrots;
    $("#avatar-name").value = state.avatar.name;
    $("#avatar-gender").value = state.avatar.gender;
    $("#avatar-preset").value = state.avatar.preset;
    renderQuests(); renderGroup(); renderInventory(); renderPlaced(); renderCanvas();
  }

  function deterministicReward() {
    const seed = [...TODAY].reduce((total, character) => total + character.charCodeAt(0), state.inventory.length);
    const candidates = rewardPool.filter((code) => !state.inventory.includes(code));
    return candidates.length ? candidates[seed % candidates.length] : null;
  }

  $("#quest-list").addEventListener("change", async (event) => {
    const checkbox = event.target.closest("[data-quest]");
    if (!checkbox) return;
    state.quests[checkbox.dataset.quest] = checkbox.checked;
    renderQuests(); renderGroup();
    await persist(`${quests.find((quest) => quest.id === checkbox.dataset.quest).title} 퀘스트를 ${checkbox.checked ? "완료" : "미완료"}로 기록했습니다.`);
  });

  $("#avatar-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    state.avatar.name = $("#avatar-name").value.trim();
    state.avatar.gender = $("#avatar-gender").value;
    state.avatar.preset = $("#avatar-preset").value;
    renderCanvas(); await persist(`${state.avatar.name} 아바타를 저장했습니다.`);
  });

  $("#inventory-list").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-item]");
    if (!button) return;
    const code = button.dataset.item;
    if (button.dataset.kind === "accessory") {
      state.avatar.equipped = state.avatar.equipped === code ? null : code;
      placementCode = null;
      renderInventory(); renderCanvas(); await persist(`${itemCatalog[code].name} ${state.avatar.equipped === code ? "장착" : "해제"} 완료.`);
      return;
    }
    placementCode = placementCode === code ? null : code;
    renderInventory();
    setStatus(placementCode ? `${itemCatalog[code].name}을 놓을 위치를 맵에서 눌러 주세요.` : "오브젝트 배치를 취소했습니다.");
  });

  $("#unequip-button").addEventListener("click", async () => {
    state.avatar.equipped = null; renderInventory(); renderCanvas(); await persist("액세서리를 해제했습니다.");
  });
  $("#cancel-placement").addEventListener("click", () => { placementCode = null; renderInventory(); setStatus("오브젝트 배치를 취소했습니다."); });

  $("#placed-list").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-remove]");
    if (!button) return;
    const [removed] = state.placed.splice(Number(button.dataset.remove), 1);
    renderPlaced(); renderCanvas(); await persist(`${itemCatalog[removed.code].name}을 창고로 돌려놓았습니다.`);
  });

  canvas.addEventListener("click", async (event) => {
    if (!placementCode) { canvas.focus(); return; }
    const bounds = canvas.getBoundingClientRect();
    const x = Math.round((event.clientX - bounds.left) * canvas.width / bounds.width / 8) * 8;
    const y = Math.round((event.clientY - bounds.top) * canvas.height / bounds.height / 8) * 8;
    if (blocked(x, y)) { setStatus("그 위치에는 오브젝트를 놓을 수 없습니다."); return; }
    const existing = state.placed.findIndex((item) => item.code === placementCode);
    if (existing >= 0) state.placed.splice(existing, 1);
    state.placed.push({ code: placementCode, x, y });
    const name = itemCatalog[placementCode].name;
    placementCode = null;
    renderInventory(); renderPlaced(); renderCanvas(); await persist(`${name}을 숲에 배치했습니다.`);
  });

  $("#reward-button").addEventListener("click", async () => {
    if (groupCompleted() < 15 || state.rewardClaimed) return;
    const reward = deterministicReward();
    state.rewardClaimed = true;
    state.carrots += 50;
    if (reward) state.inventory.push(reward);
    renderAll();
    await persist(reward ? `${itemCatalog[reward].name}과 당근 50개를 받았습니다!` : "당근 50개를 받았습니다!");
  });

  document.addEventListener("keydown", (event) => {
    if (["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(document.activeElement?.tagName)) return;
    const direction = { ArrowUp: "up", w: "up", W: "up", ArrowDown: "down", s: "down", S: "down", ArrowLeft: "left", a: "left", A: "left", ArrowRight: "right", d: "right", D: "right" }[event.key];
    if (!direction) return;
    event.preventDefault(); moveAvatar(direction);
  });
  document.querySelectorAll("[data-move]").forEach((button) => button.addEventListener("pointerdown", (event) => { event.preventDefault(); moveAvatar(button.dataset.move); }));

  $("#large-text-toggle").addEventListener("click", (event) => {
    const enabled = document.body.classList.toggle("large-text");
    event.currentTarget.setAttribute("aria-pressed", String(enabled));
    event.currentTarget.textContent = enabled ? "기본 글자" : "글자 크게";
  });

  document.querySelectorAll("[data-workspace-target]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-workspace-target]").forEach((item) => {
        const active = item === button;
        item.classList.toggle("is-active", active);
        item.setAttribute("aria-pressed", String(active));
      });
      const target = document.getElementById(button.dataset.workspaceTarget);
      target?.scrollIntoView({ behavior: "smooth", block: "center" });
      target?.classList.add("workspace-focus");
      window.setTimeout(() => target?.classList.remove("workspace-focus"), 700);
    });
  });

  document.querySelectorAll("[data-inspector-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-inspector-tab]").forEach((item) => {
        const active = item === button;
        item.classList.toggle("is-active", active);
        item.setAttribute("aria-selected", String(active));
      });
      document.getElementById(button.dataset.inspectorTab)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  });

  $("#zoom-toggle").addEventListener("click", (event) => {
    const zoomed = $(".canvas-frame").classList.toggle("is-zoomed");
    event.currentTarget.setAttribute("aria-pressed", String(zoomed));
    event.currentTarget.textContent = zoomed ? "화면 맞춤" : "확대 보기";
    setStatus(zoomed ? "월드 화면을 확대했습니다. 아래와 오른쪽으로 이동해 살펴보세요." : "월드 화면을 작업 영역에 맞췄습니다.");
  });

  $("#reset-position").addEventListener("click", async () => {
    state.avatar.x = 384;
    state.avatar.y = 352;
    renderCanvas();
    await persist("아바타를 시작 위치로 이동했습니다.");
    canvas.focus();
  });

  window.CarrotForestAdapters = { DemoForestAdapter, ApiForestAdapter };
  adapter.load().then((loaded) => { state = loaded; renderAll(); setStatus("당근의 숲이 준비되었습니다. 오늘의 퀘스트부터 시작해 보세요."); });
})();
