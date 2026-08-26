(() => {
  "use strict";

  const STORAGE_KEY = "gandang-carrot-forest-demo-v1";
  const TILE = 32;
  const MAP_WIDTH = 24;
  const MAP_HEIGHT = 16;
  const WORLD_WIDTH = 768;
  const WORLD_HEIGHT = 512;
  const RENDER_SCALE = 2;
  const TODAY = new Date().toISOString().slice(0, 10);
  const $ = (selector) => document.querySelector(selector);

  const quests = [
    { id: "walk", icon: "👟", category: "움직이기", title: "가볍게 걷기", description: "내가 정한 걷기 목표 확인", reward: 20 },
    { id: "meal", icon: "🥗", category: "식사 돌아보기", title: "규칙적으로 식사하기", description: "오늘 식사 기록 남기기", reward: 20 },
    { id: "check", icon: "📝", category: "건강 기록", title: "건강 기록 확인하기", description: "입력한 생활습관 다시 보기", reward: 15 },
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
  const avatarCategories = [
    { id: "skin", label: "피부", icon: "◉" },
    { id: "outfit", label: "의상", icon: "♜" },
    { id: "hair", label: "헤어", icon: "♟" },
    { id: "face", label: "얼굴", icon: "☺" },
    { id: "accessory", label: "액세서리", icon: "◇" },
    { id: "aura", label: "아우라", icon: "✦" },
    { id: "effect", label: "이펙트", icon: "✧" },
    { id: "vehicle", label: "탈것", icon: "◈" },
    { id: "pet", label: "펫", icon: "♧" },
    { id: "speech", label: "말풍선", icon: "▢" },
  ];
  const avatarCatalog = {
    skin: [
      { id: "peach", name: "복숭아빛", visual: "#f2bd92", color: "#f2bd92" },
      { id: "rose", name: "장밋빛", visual: "#eaa68e", color: "#eaa68e" },
      { id: "warm", name: "따뜻한 갈색", visual: "#c98263", color: "#c98263" },
      { id: "deep", name: "깊은 갈색", visual: "#89503e", color: "#89503e", isNew: true },
      { id: "olive", name: "올리브", visual: "#a87f63", color: "#a87f63" },
      { id: "porcelain", name: "밝은 도자기빛", visual: "#f5cbb4", color: "#f5cbb4" },
    ],
    outfit: [
      { id: "forest", name: "숲지기 작업복", visual: "🧥" }, { id: "denim", name: "데님 산책복", visual: "👕" },
      { id: "carrot", name: "당근 탐험복", visual: "🦺" }, { id: "moon", name: "달빛 정장", visual: "👔", isNew: true },
      { id: "berry", name: "산딸기 후드", visual: "👚" }, { id: "yellow", name: "햇살 우비", visual: "🧶" },
      { id: "violet", name: "보랏빛 재킷", visual: "🥋" }, { id: "black", name: "밤숲 코트", visual: "🕴️" },
    ],
    hair: [
      { id: "soft", name: "포근한 단발", visual: "💇" }, { id: "wave", name: "물결 장발", visual: "👩‍🦱", isNew: true },
      { id: "crop", name: "산뜻한 숏컷", visual: "🧑" }, { id: "twin", name: "양갈래 머리", visual: "👧" },
      { id: "silver", name: "은빛 웨이브", visual: "🧓" }, { id: "orange", name: "당근빛 웨이브", visual: "🧑‍🦰" },
    ],
    face: [
      { id: "calm", name: "차분한 표정", visual: "🙂" }, { id: "smile", name: "환한 미소", visual: "😊" },
      { id: "sparkle", name: "반짝이는 눈", visual: "🤩", isNew: true }, { id: "blush", name: "수줍은 볼", visual: "☺️" },
      { id: "wink", name: "윙크", visual: "😉" }, { id: "cool", name: "도도한 표정", visual: "😌" },
    ],
    accessory: [
      { id: "none", name: "착용 안 함", visual: "—" }, { id: "red_scarf", name: "빨간 목도리", visual: "🧣" },
      { id: "sprout_hat", name: "새싹 모자", visual: "🌱" }, { id: "carrot_bag", name: "당근 가방", visual: "🎒" },
      { id: "round_glasses", name: "둥근 안경", visual: "👓", isNew: true }, { id: "star_glasses", name: "별빛 안경", visual: "🤓" },
    ],
    aura: [
      { id: "none", name: "아우라 없음", visual: "—" }, { id: "wings", name: "하늘빛 날개", visual: "🪽" },
      { id: "halo", name: "햇살 고리", visual: "😇" }, { id: "rainbow", name: "무지개 아치", visual: "🌈" },
      { id: "hearts", name: "마음의 온기", visual: "💞" }, { id: "forest", name: "숲의 숨결", visual: "🍃", isNew: true },
    ],
    effect: [
      { id: "none", name: "이펙트 없음", visual: "—" }, { id: "bubble", name: "비눗방울", visual: "🫧" },
      { id: "spark", name: "별빛 반짝임", visual: "✨" }, { id: "heart", name: "마음 보내기", visual: "💗" },
      { id: "carrot", name: "당근 팡", visual: "🥕" }, { id: "leaf", name: "나뭇잎 톡", visual: "🍂", isNew: true },
    ],
    vehicle: [
      { id: "none", name: "걸어서 이동", visual: "👟" }, { id: "scooter", name: "숲 스쿠터", visual: "🛵" },
      { id: "bicycle", name: "산책 자전거", visual: "🚲" }, { id: "balloon", name: "구름 열기구", visual: "🎈", isNew: true },
    ],
    pet: [
      { id: "none", name: "함께 걷기 없음", visual: "—" }, { id: "white_pup", name: "몽실이", visual: "🐶", isNew: true },
      { id: "brown_pup", name: "밤톨이", visual: "🐕" }, { id: "cat", name: "구름이", visual: "🐈" },
      { id: "fox", name: "단풍이", visual: "🦊" },
    ],
    speech: [
      { id: "none", name: "말풍선 없음", visual: "—" }, { id: "cat", name: "고양이 인사", visual: "🐱" },
      { id: "leaf", name: "네잎클로버", visual: "🍀" }, { id: "window", name: "파란 창문", visual: "🪟", isNew: true },
    ],
  };
  const defaultCosmetics = {
    skin: "peach", outfit: "forest", hair: "soft", face: "calm", accessory: "none",
    aura: "wings", effect: "none", vehicle: "scooter", pet: "none", speech: "none",
  };

  function defaultState() {
    return {
      dateKey: TODAY,
      avatar: { name: "세준", gender: "female", preset: "sprout", x: 384, y: 352, equipped: null, cosmetics: { ...defaultCosmetics }, sitting: false, mounted: false },
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
      gardenWatered: false,
    };
  }

  function normalizeState(value) {
    const fallback = defaultState();
    if (!value || value.dateKey !== TODAY) return fallback;
    const state = { ...fallback, ...value };
    state.avatar = { ...fallback.avatar, ...(value.avatar || {}) };
    state.avatar.cosmetics = { ...defaultCosmetics, ...((value.avatar || {}).cosmetics || {}) };
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
  let running = false;
  let musicEngine = null;
  let animationFrame = 0;
  let activeAvatarCategory = "skin";
  let avatarDraft = { ...defaultCosmetics };
  let avatarDraftHistory = [];
  const canvas = $("#forest-canvas");
  const context = canvas.getContext("2d");
  context.imageSmoothingEnabled = false;
  const avatarSpriteAtlas = new Image();
  const cosmeticSpriteAtlas = new Image();
  avatarSpriteAtlas.src = "/static/assets/carrot-forest-avatar-atlas-v1.png";
  cosmeticSpriteAtlas.src = "/static/assets/carrot-forest-cosmetics-atlas-v1.png";
  avatarSpriteAtlas.addEventListener("load", () => { renderCanvas(); if ($("#avatar-studio").open) renderAvatarPreview(); });
  cosmeticSpriteAtlas.addEventListener("load", () => { renderCanvas(); if ($("#avatar-studio").open) renderAvatarPreview(); });

  class CozyForestMusic {
    constructor() {
      this.audioContext = null;
      this.timer = null;
      this.step = 0;
      this.notes = [261.63, 329.63, 392, 329.63, 293.66, 349.23, 440, 349.23];
    }
    playNote(frequency, when) {
      const oscillator = this.audioContext.createOscillator();
      const gain = this.audioContext.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = frequency;
      gain.gain.setValueAtTime(.0001, when);
      gain.gain.exponentialRampToValueAtTime(.055, when + .04);
      gain.gain.exponentialRampToValueAtTime(.0001, when + .7);
      oscillator.connect(gain).connect(this.audioContext.destination);
      oscillator.start(when);
      oscillator.stop(when + .75);
    }
    async start() {
      this.audioContext ||= new (window.AudioContext || window.webkitAudioContext)();
      await this.audioContext.resume();
      const playStep = () => {
        const now = this.audioContext.currentTime;
        this.playNote(this.notes[this.step % this.notes.length], now);
        if (this.step % 2 === 0) this.playNote(this.notes[(this.step + 2) % this.notes.length] / 2, now);
        this.step += 1;
      };
      playStep();
      this.timer = window.setInterval(playStep, 760);
    }
    stop() {
      window.clearInterval(this.timer);
      this.timer = null;
      this.audioContext?.suspend();
    }
  }

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
    const sway = animationFrame % 2 ? 1 : 0;
    fillPixelRect(x + 7 * scale, y + 40 * scale, 25 * scale, 7 * scale, "rgba(34,63,40,.2)");
    fillPixelRect(x + 13 * scale, y + 23 * scale, 11 * scale, 23 * scale, "#54321f");
    fillPixelRect(x + 16 * scale, y + 24 * scale, 5 * scale, 18 * scale, "#99613a");
    fillPixelRect(x + 18 * scale, y + 29 * scale, 3 * scale, 5 * scale, "#c0824e");
    fillPixelRect(x + (3 + sway) * scale, y + 8 * scale, 31 * scale, 25 * scale, "#174e31");
    fillPixelRect(x + sway * scale, y + 15 * scale, 37 * scale, 14 * scale, "#236d3e");
    fillPixelRect(x + (8 + sway) * scale, y + 1 * scale, 22 * scale, 17 * scale, "#3e9950");
    fillPixelRect(x + (11 + sway) * scale, y + 4 * scale, 15 * scale, 8 * scale, "#68bd5d");
    fillPixelRect(x + (5 + sway) * scale, y + 17 * scale, 8 * scale, 5 * scale, "#55ac54");
    fillPixelRect(x + (25 + sway) * scale, y + 13 * scale, 6 * scale, 5 * scale, "#0f4029");
  }

  function drawFlower(x, y, petal = "#fff0a1") {
    fillPixelRect(x, y + 4, 2, 7, "#347b3f");
    fillPixelRect(x - 3, y, 3, 4, petal);
    fillPixelRect(x + 2, y, 3, 4, petal);
    fillPixelRect(x, y - 2, 2, 4, "#ffd04a");
  }

  function drawFence(x, y, length) {
    fillPixelRect(x, y + 5, length, 5, "#9a663f");
    fillPixelRect(x, y + 7, length, 2, "#d49a5e");
    for (let post = 0; post <= length; post += 24) {
      fillPixelRect(x + post, y, 6, 18, "#70472e");
      fillPixelRect(x + post + 1, y - 3, 4, 4, "#b77b48");
    }
  }

  function drawHouse() {
    fillPixelRect(42, 188, 204, 12, "rgba(45,58,37,.22)");
    fillPixelRect(48, 70, 192, 122, "#b57c45");
    fillPixelRect(56, 78, 176, 114, "#ffe6ae");
    for (let y = 84; y < 188; y += 12) fillPixelRect(58, y, 172, 2, "#edc67e");
    fillPixelRect(36, 70, 216, 24, "#71302b");
    fillPixelRect(48, 54, 192, 25, "#b83f36");
    for (let x = 52; x < 238; x += 20) {
      fillPixelRect(x, 57, 16, 6, "#da6453");
      fillPixelRect(x + 4, 67, 15, 5, "#8e302c");
    }
    fillPixelRect(68, 94, 152, 10, "#d8a954");
    fillPixelRect(122, 128, 50, 64, "#5b3524");
    fillPixelRect(130, 136, 34, 56, "#8f5935");
    fillPixelRect(157, 161, 5, 5, "#ffdc65");
    [[76, 112], [178, 112]].forEach(([x, y]) => {
      fillPixelRect(x, y, 40, 40, "#366f88");
      fillPixelRect(x + 5, y + 5, 30, 30, "#95d9ec");
      fillPixelRect(x + 8, y + 7, 9, 10, "#d9f5f7");
      fillPixelRect(x + 19, y + 5, 3, 30, "#4d8fa6");
      fillPixelRect(x + 5, y + 19, 30, 3, "#4d8fa6");
    });
    fillPixelRect(60, 188, 168, 8, "#a56e3f");
    fillPixelRect(132, 196, 31, 8, "#c69b64");
    drawFlower(72, 181, "#ff8d9b");
    drawFlower(214, 182, "#b99cff");
  }

  function drawCarrotPlot() {
    fillPixelRect(492, 46, 236, 188, "#493121");
    fillPixelRect(500, 54, 220, 172, "#835334");
    for (let row = 0; row < 4; row += 1) {
      fillPixelRect(507, 63 + row * 39, 206, 28, row % 2 ? "#6f4028" : "#75452b");
      fillPixelRect(509, 65 + row * 39, 202, 3, "#a46c42");
      for (let column = 0; column < 6; column += 1) {
        const x = 516 + column * 32;
        const y = 75 + row * 39;
        fillPixelRect(x + 7, y + 6, 8, 16, "#e86d29");
        fillPixelRect(x + 9, y + 17, 4, 6, "#c55122");
        fillPixelRect(x + 8, y, 5, 10, "#317841");
        fillPixelRect(x + 3, y - 3, 7, 7, "#48994c");
        fillPixelRect(x + 12, y - 4, 7, 8, "#65b75b");
        fillPixelRect(x + 16, y, 4, 5, "#2e713b");
      }
    }
    drawFence(490, 36, 238);
    drawFence(490, 226, 238);
  }

  function drawSharedTree() {
    fillPixelRect(326, 255, 116, 17, "rgba(28,57,35,.23)");
    fillPixelRect(361, 162, 30, 92, "#50301f");
    fillPixelRect(370, 165, 12, 82, "#9b6038");
    fillPixelRect(382, 183, 29, 10, "#694027");
    fillPixelRect(342, 117, 77, 75, "#154a2e");
    fillPixelRect(321, 139, 118, 52, "#1f6a3b");
    fillPixelRect(337, 105, 89, 55, "#31894a");
    fillPixelRect(354, 94 + (animationFrame % 2), 56, 40, "#53a952");
    fillPixelRect(346, 116, 22, 13, "#73c566");
    fillPixelRect(399, 130, 16, 10, "#0f4228");
    [[344, 155], [370, 120], [410, 158], [390, 108]].forEach(([x, y], index) => fillPixelRect(x, y + (index % 2 ? animationFrame % 2 : 0), 6, 6, "#f4b24a"));
  }

  function drawPond() {
    fillPixelRect(248, 424, 87, 50, "#3c7e88");
    fillPixelRect(254, 419, 75, 57, "#66b4b8");
    fillPixelRect(263, 425, 58, 43, "#8ad2cd");
    fillPixelRect(276 + animationFrame * 2, 432, 24, 3, "#d8f4e7");
    fillPixelRect(304 - animationFrame * 2, 455, 13, 3, "#d8f4e7");
    fillPixelRect(246, 434, 10, 8, "#4d9a54");
    fillPixelRect(327, 444, 9, 8, "#4d9a54");
  }

  function drawVehicle() {
    const x = 470;
    const y = 376;
    fillPixelRect(x - 21, y + 18, 46, 6, "rgba(31,57,45,.2)");
    fillPixelRect(x - 19, y + 7, 15, 15, "#1f3434");
    fillPixelRect(x + 9, y + 7, 15, 15, "#1f3434");
    fillPixelRect(x - 15, y + 11, 7, 7, "#a9c7c2");
    fillPixelRect(x + 13, y + 11, 7, 7, "#a9c7c2");
    fillPixelRect(x - 11, y - 1, 28, 10, "#c84e30");
    fillPixelRect(x - 3, y - 10, 18, 11, "#f58e38");
    fillPixelRect(x, y - 8, 11, 4, "#ffbd5f");
    fillPixelRect(x + 13, y - 12, 4, 14, "#384e4b");
    fillPixelRect(x + 9, y - 13, 13, 4, "#384e4b");
    fillPixelRect(x + 19, y - 15, 5, 5, "#ffdf78");
  }

  function drawMap() {
    fillPixelRect(0, 0, WORLD_WIDTH, WORLD_HEIGHT, "#65aa59");
    for (let y = 0; y < MAP_HEIGHT; y += 1) {
      for (let x = 0; x < MAP_WIDTH; x += 1) {
        const px = x * TILE;
        const py = y * TILE;
        if ((x + y) % 2 === 0) fillPixelRect(px + 6, py + 7, 3, 3, "#8bc76c");
        if ((x * 3 + y) % 5 === 0) fillPixelRect(px + 21, py + 19, 2, 5, "#438d4c");
        if ((x + y * 2) % 7 === 0) fillPixelRect(px + 13, py + 24, 4, 2, "#acd77d");
      }
    }
    fillPixelRect(0, 328, WORLD_WIDTH, 90, "#ba965e");
    fillPixelRect(0, 335, WORLD_WIDTH, 70, "#d9b779");
    fillPixelRect(352, 0, 72, WORLD_HEIGHT, "#c8a86b");
    fillPixelRect(360, 0, 56, WORLD_HEIGHT, "#e2c78f");
    for (let x = 12; x < WORLD_WIDTH; x += 36) fillPixelRect(x, 345 + (x % 3), 12, 3, "#efd39d");
    for (let y = 14; y < WORLD_HEIGHT; y += 38) fillPixelRect(371 + (y % 4), y, 18, 3, "#f0d7a5");
    drawPond();
    drawHouse();
    drawCarrotPlot();
    drawSharedTree();
    for (let x = 0; x < WORLD_WIDTH; x += 96) { drawTree(x, 0, .85); drawTree(x + 30, 445, .75); }
    for (let y = 70; y < 420; y += 100) { drawTree(4, y, .72); drawTree(725, y, .72); }
    [[275, 302, "#fff0a1"], [458, 284, "#ff9db0"], [690, 292, "#bba4ff"], [106, 285, "#fff0a1"]].forEach(([x, y, color]) => drawFlower(x, y, color));
    drawVehicle();
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
        fillPixelRect(x - 6, y - 2, 12, 16, "#eee4d2");
        fillPixelRect(x - 14, y - 15, 28, 14, "#e34e42");
        fillPixelRect(x - 9, y - 18, 18, 5, "#f26959");
        fillPixelRect(x - 7, y - 12, 4, 4, "#fff2d1");
        fillPixelRect(x + 4, y - 9, 4, 4, "#fff2d1");
      }
    });
  }

  function avatarSpriteIndex(cosmetics) {
    if (cosmetics.skin === "deep") return 9;
    if (cosmetics.hair === "silver") return 10;
    if (cosmetics.hair === "orange") return 2;
    if (cosmetics.hair === "wave") return cosmetics.outfit === "moon" ? 5 : 1;
    if (cosmetics.hair === "twin") return 7;
    if (cosmetics.outfit === "denim") return cosmetics.skin === "warm" ? 6 : 4;
    if (cosmetics.outfit === "carrot") return 9;
    if (cosmetics.outfit === "moon" || cosmetics.outfit === "violet") return 10;
    if (cosmetics.outfit === "berry") return 5;
    if (cosmetics.outfit === "yellow") return 3;
    if (cosmetics.accessory === "sprout_hat") return 8;
    return cosmetics.accessory === "round_glasses" ? 2 : cosmetics.accessory === "carrot_bag" ? 11 : 0;
  }

  function cosmeticSpriteIndex(category, itemId) {
    const indexes = {
      aura: { wings: 0, halo: 1, rainbow: 2, forest: 3, hearts: 4 },
      effect: { bubble: 5, spark: 6, heart: 7, carrot: 8, leaf: 9 },
      vehicle: { scooter: 10, bicycle: 11, balloon: 12 },
      pet: { white_pup: 15, brown_pup: 16, cat: 17, fox: 18 },
      speech: { cat: 19, leaf: 19, window: 19 },
    };
    return indexes[category]?.[itemId] ?? null;
  }

  function drawAtlasCell(target, image, index, columns, rows, x, y, width, height) {
    if (!image.complete || !image.naturalWidth || index == null) return false;
    const cellWidth = image.naturalWidth / columns;
    const cellHeight = image.naturalHeight / rows;
    const column = index % columns;
    const row = Math.floor(index / columns);
    target.drawImage(image, column * cellWidth, row * cellHeight, cellWidth, cellHeight, x, y, width, height);
    return true;
  }

  function drawGeneratedWorldAvatar(avatar, cosmetics, x, y) {
    if (!avatarSpriteAtlas.complete || !avatarSpriteAtlas.naturalWidth) return false;
    const auraIndex = cosmeticSpriteIndex("aura", cosmetics.aura);
    drawAtlasCell(context, cosmeticSpriteAtlas, auraIndex, 5, 4, x - 45, y - 49, 90, 90);
    const spriteIndex = avatarSpriteIndex(cosmetics);
    drawAtlasCell(context, avatarSpriteAtlas, spriteIndex, 4, 3, x - 31, y - 48, 62, 78);
    const effectIndex = cosmeticSpriteIndex("effect", cosmetics.effect);
    drawAtlasCell(context, cosmeticSpriteAtlas, effectIndex, 5, 4, x - 42, y - 43, 42, 42);
    const petIndex = cosmeticSpriteIndex("pet", cosmetics.pet);
    drawAtlasCell(context, cosmeticSpriteAtlas, petIndex, 5, 4, x + 20, y + 5, 35, 35);
    if (avatar.mounted) {
      const vehicleIndex = cosmeticSpriteIndex("vehicle", cosmetics.vehicle === "none" ? "scooter" : cosmetics.vehicle);
      drawAtlasCell(context, cosmeticSpriteAtlas, vehicleIndex, 5, 4, x - 38, y + 14, 76, 52);
    }
    if (cosmetics.speech !== "none") {
      const speechIndex = cosmeticSpriteIndex("speech", cosmetics.speech);
      drawAtlasCell(context, cosmeticSpriteAtlas, speechIndex, 5, 4, x + 25, y - 60, 62, 45);
      context.font = "bold 7px sans-serif"; context.textAlign = "center"; context.fillStyle = "#31343f";
      context.fillText(cosmetics.speech === "cat" ? "안녕!" : cosmetics.speech === "leaf" ? "한 걸음" : "같이 걸어요", x + 56, y - 36);
    }
    context.font = "bold 11px sans-serif"; context.textAlign = "center";
    context.fillStyle = "rgba(255,255,255,.94)"; context.fillRect(x - Math.max(25, avatar.name.length * 6), y - 63, Math.max(50, avatar.name.length * 12), 17);
    context.fillStyle = "#18382d"; context.fillText(avatar.name, x, y - 50);
    return true;
  }

  function drawAvatar() {
    const avatar = state.avatar;
    const style = presets[avatar.preset] || presets.sprout;
    const cosmetics = { ...defaultCosmetics, ...(avatar.cosmetics || {}) };
    const skin = avatarCatalog.skin.find((item) => item.id === cosmetics.skin)?.color || "#f2bd92";
    const skinShadow = cosmetics.skin === "deep" ? "#6d392f" : cosmetics.skin === "warm" ? "#a7654f" : "#d99978";
    const hairStyles = { soft: style.hair, wave: "#3b2b34", crop: "#263b43", twin: "#54313e", silver: "#8992a4", orange: "#bd6236" };
    const outfitStyles = {
      forest: ["#4f9e63", "#c8f06a"], denim: ["#4879a5", "#c8e3f8"], carrot: ["#e87531", "#ffe078"],
      moon: ["#4b527f", "#d9e3ff"], berry: ["#b44f78", "#ffd2df"], yellow: ["#e7b737", "#fff1a8"],
      violet: ["#7055af", "#d8c8ff"], black: ["#2f3441", "#9da6bc"],
    };
    const [outfitColor, outfitAccent] = outfitStyles[cosmetics.outfit] || [style.outfit, style.accent];
    const equipped = cosmetics.accessory !== "none" ? cosmetics.accessory : avatar.equipped;
    const x = Math.round(avatar.x / 4) * 4;
    const bob = avatar.sitting || avatar.mounted ? 0 : animationFrame;
    const y = Math.round(avatar.y / 4) * 4 - bob;
    if (drawGeneratedWorldAvatar(avatar, cosmetics, x, y)) return;
    if (cosmetics.aura === "wings") {
      [[-27, -13], [-34, -6], [24, -13], [31, -6]].forEach(([dx, dy], index) => fillPixelRect(x + dx, y + dy, index % 2 ? 9 : 12, 18, index % 2 ? "#bff8ff" : "#65ddea"));
    } else if (cosmetics.aura === "halo") {
      fillPixelRect(x - 13, y - 40, 26, 4, "#ffd951"); fillPixelRect(x - 9, y - 43, 18, 3, "#fff2a4");
    } else if (cosmetics.aura === "rainbow") {
      ["#e95a62", "#f4a542", "#f1d75a", "#5cc176", "#5b8ee7"].forEach((color, index) => { context.strokeStyle = color; context.lineWidth = 3; context.beginPath(); context.arc(x, y - 2, 29 + index * 3, Math.PI, Math.PI * 2); context.stroke(); });
    } else if (cosmetics.aura === "hearts") {
      context.fillStyle = "#f56f9b"; context.font = "16px sans-serif"; context.fillText("♥", x - 25, y - 14); context.fillText("♥", x + 22, y - 2);
    } else if (cosmetics.aura === "forest") {
      context.fillStyle = "#69bd5a"; context.font = "15px sans-serif"; context.fillText("❧", x - 27, y - 8); context.fillText("❧", x + 25, y - 18);
    }
    fillPixelRect(x - (avatar.mounted ? 25 : 17), y + 31, avatar.mounted ? 50 : 34, 7, "rgba(24,55,37,.26)");
    if (avatar.mounted) {
      fillPixelRect(x - 23, y + 15, 17, 17, "#1d3030");
      fillPixelRect(x + 10, y + 15, 17, 17, "#1d3030");
      fillPixelRect(x - 18, y + 20, 8, 8, "#a8c7c1");
      fillPixelRect(x + 14, y + 20, 8, 8, "#a8c7c1");
      fillPixelRect(x - 16, y + 7, 35, 12, "#bd472c");
      fillPixelRect(x - 6, y, 23, 10, "#ee8235");
      fillPixelRect(x + 15, y - 8, 4, 18, "#314845");
      fillPixelRect(x + 11, y - 10, 16, 4, "#314845");
    }
    fillPixelRect(x - 12, y - 22, 24, 24, skinShadow);
    fillPixelRect(x - 10, y - 21, 20, 21, skin);
    fillPixelRect(x - 13, y - 14, 3, 8, skinShadow);
    fillPixelRect(x + 10, y - 14, 3, 8, skinShadow);
    if (avatar.gender === "female") {
      fillPixelRect(x - 15, y - 29, 30, 11, hairStyles[cosmetics.hair]);
      fillPixelRect(x - 16, y - 20, 7, cosmetics.hair === "wave" ? 31 : 25, hairStyles[cosmetics.hair]);
      fillPixelRect(x + 9, y - 20, 7, cosmetics.hair === "wave" ? 31 : 25, hairStyles[cosmetics.hair]);
      fillPixelRect(x - 10, y - 25, 8, 5, "rgba(255,255,255,.15)");
    } else if (avatar.gender === "male") {
      fillPixelRect(x - 14, y - 28, 28, 10, hairStyles[cosmetics.hair]);
      fillPixelRect(x - 16, y - 22, 8, 12, hairStyles[cosmetics.hair]);
      fillPixelRect(x + 8, y - 23, 6, 7, hairStyles[cosmetics.hair]);
      fillPixelRect(x - 7, y - 27, 10, 4, "rgba(255,255,255,.14)");
    } else {
      fillPixelRect(x - 15, y - 28, 30, 11, hairStyles[cosmetics.hair]);
      fillPixelRect(x - 16, y - 20, 7, 17, hairStyles[cosmetics.hair]);
      fillPixelRect(x + 9, y - 20, 7, 17, hairStyles[cosmetics.hair]);
    }
    fillPixelRect(x - 8, y - 13, 4, 5, "#f9fbec");
    fillPixelRect(x + 4, y - 13, 4, 5, "#f9fbec");
    fillPixelRect(x - 7, y - 12, 2, 3, "#24322f");
    fillPixelRect(x + 5, y - 12, 2, 3, "#24322f");
    if (cosmetics.face === "wink") fillPixelRect(x + 4, y - 10, 5, 2, "#24322f");
    if (cosmetics.face === "blush" || cosmetics.face === "sparkle") { fillPixelRect(x - 10, y - 7, 4, 3, "#ed8490"); fillPixelRect(x + 6, y - 7, 4, 3, "#ed8490"); }
    fillPixelRect(x - (cosmetics.face === "smile" ? 5 : 4), y - 5, cosmetics.face === "smile" ? 10 : 8, 2, cosmetics.face === "cool" ? "#6c5c65" : "#b96c67");
    fillPixelRect(x - 15, y, 30, 25, "#203b34");
    fillPixelRect(x - 13, y + 1, 26, 22, outfitColor);
    fillPixelRect(x - 9, y + 4, 18, 5, outfitAccent);
    fillPixelRect(x - 20, y + 3, 7, 19, skinShadow);
    fillPixelRect(x - 18, y + 3, 5, 17, skin);
    fillPixelRect(x + 13, y + 3, 7, 19, skinShadow);
    fillPixelRect(x + 13, y + 3, 5, 17, skin);
    if (avatar.sitting) {
      fillPixelRect(x - 13, y + 21, 13, 10, "#334b5e");
      fillPixelRect(x, y + 21, 13, 10, "#334b5e");
      fillPixelRect(x - 19, y + 28, 19, 7, "#263946");
      fillPixelRect(x, y + 28, 19, 7, "#263946");
    } else if (!avatar.mounted) {
      fillPixelRect(x - 12, y + 23, 10, 14, "#334b5e");
      fillPixelRect(x + 2, y + 23, 10, 14, "#334b5e");
      fillPixelRect(x - 14, y + 35, 12, 5, "#253846");
      fillPixelRect(x + 2, y + 35, 12, 5, "#253846");
    }
    if (equipped === "red_scarf") fillPixelRect(x - 13, y - 1, 26, 6, "#d93432");
    if (equipped === "sprout_hat") {
      fillPixelRect(x - 16, y - 32, 32, 7, "#347f3d");
      fillPixelRect(x - 3, y - 42, 6, 11, "#216a34");
      fillPixelRect(x + 2, y - 42, 9, 6, "#5fb85d");
    }
    if (equipped === "carrot_bag") {
      fillPixelRect(x + 13, y + 6, 11, 17, "#b94f25");
      fillPixelRect(x + 15, y + 8, 8, 13, "#ee7d32");
    }
    if (equipped === "round_glasses" || equipped === "star_glasses") {
      const glassColor = equipped === "star_glasses" ? "#e75e99" : "#354751";
      context.strokeStyle = glassColor; context.lineWidth = 2; context.strokeRect(x - 10, y - 15, 8, 7); context.strokeRect(x + 2, y - 15, 8, 7); fillPixelRect(x - 2, y - 13, 4, 2, glassColor);
    }
    if (cosmetics.effect !== "none") {
      const effects = { bubble: ["○", "#7edcf2"], spark: ["✦", "#ffd85a"], heart: ["♥", "#f15f8b"], carrot: ["◆", "#ed7a31"], leaf: ["❧", "#64ac4b"] };
      const [glyph, color] = effects[cosmetics.effect] || effects.spark;
      context.fillStyle = color; context.font = "bold 13px sans-serif"; context.fillText(glyph, x - 25, y - 28); context.fillText(glyph, x + 25, y + 2);
    }
    if (cosmetics.pet !== "none") {
      const petGlyphs = { white_pup: "🐶", brown_pup: "🐕", cat: "🐈", fox: "🦊" };
      context.font = "22px sans-serif"; context.fillText(petGlyphs[cosmetics.pet], x + 34, y + 34);
    }
    context.font = "bold 13px sans-serif";
    context.textAlign = "center";
    context.fillStyle = "rgba(255,255,255,.94)";
    context.fillRect(x - Math.max(28, avatar.name.length * 7), y - 58, Math.max(56, avatar.name.length * 14), 19);
    context.fillStyle = "#18382d";
    context.fillText(avatar.name, x, y - 44);
    if (cosmetics.speech !== "none") {
      const speechText = cosmetics.speech === "cat" ? "안녕!" : cosmetics.speech === "leaf" ? "오늘도 한 걸음" : "같이 걸어요";
      context.font = "bold 9px sans-serif"; context.fillStyle = "rgba(255,255,255,.94)"; context.fillRect(x + 26, y - 48, 68, 22); context.fillStyle = "#31343f"; context.fillText(speechText, x + 60, y - 34);
    }
  }

  function renderCanvas() {
    context.setTransform(1, 0, 0, 1, 0, 0);
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.setTransform(RENDER_SCALE, 0, 0, RENDER_SCALE, 0, 0);
    context.imageSmoothingEnabled = false;
    drawMap();
    drawAvatar();
    $("#avatar-coordinate").textContent = `X ${Math.round(state.avatar.x)} · Y ${Math.round(state.avatar.y)}`;
    updateInteractionPrompt();
  }

  let lastAnimationAt = 0;
  function animateWorld(timestamp) {
    if (!document.hidden && timestamp - lastAnimationAt > 420) {
      animationFrame = (animationFrame + 1) % 2;
      renderCanvas();
      lastAnimationAt = timestamp;
    }
    window.requestAnimationFrame(animateWorld);
  }

  function distanceTo(x, y) {
    return Math.hypot(state.avatar.x - x, state.avatar.y - y);
  }

  function nearbyInteraction() {
    if (distanceTo(147, 225) < 90) return "home";
    if (distanceTo(610, 260) < 105) return "garden";
    if (distanceTo(470, 376) < 72) return "vehicle";
    return null;
  }

  function updateInteractionPrompt() {
    const target = nearbyInteraction();
    const prompt = $("#interaction-prompt");
    prompt.hidden = !target;
    if (target) prompt.querySelector("span").textContent = { home: "우리 집", garden: "공동 당근밭", vehicle: "숲 스쿠터" }[target];
  }

  function openWorldDialog(target) {
    const dialog = $("#world-dialog");
    const content = {
      home: { icon: "🏠", title: "우리 집", copy: "잠시 쉬거나 옷장을 열어 캐릭터를 꾸밀 수 있어요.", actions: '<button type="button" data-world-action="rest">소파에서 쉬기</button><button type="button" data-world-action="wardrobe">옷장 열기</button>' },
      garden: { icon: "🥕", title: "공동 당근밭", copy: `우리 모임은 오늘 ${groupCompleted()}/15개의 퀘스트를 완료했어요. 함께 돌본 만큼 당근밭이 풍성해져요.`, actions: `<button type="button" data-world-action="water" ${state.gardenWatered ? "disabled" : ""}>${state.gardenWatered ? "오늘 물주기 완료" : "당근밭 물주기"}</button><button type="button" data-world-action="team">공동 진행 보기</button>` },
      vehicle: { icon: "🛵", title: "숲 스쿠터", copy: "스쿠터를 타면 숲길을 더 빠르게 이동할 수 있어요.", actions: `<button type="button" data-world-action="ride">${state.avatar.mounted ? "스쿠터에서 내리기" : "스쿠터 타기"}</button>` },
    }[target];
    if (!content) { setStatus("상호작용할 대상 가까이 이동해 주세요."); return; }
    $("#world-dialog-icon").textContent = content.icon;
    $("#world-dialog-title").textContent = content.title;
    $("#world-dialog-copy").textContent = content.copy;
    $("#world-dialog-actions").innerHTML = content.actions;
    dialog.showModal();
  }

  function interact(target = nearbyInteraction()) {
    if (!target) { setStatus("집, 공동 당근밭 또는 스쿠터 가까이에서 Q를 눌러 주세요."); return; }
    openWorldDialog(target);
  }

  function blocked(x, y) {
    if (x < 28 || x > WORLD_WIDTH - 28 || y < 42 || y > WORLD_HEIGHT - 38) return true;
    if (x > 38 && x < 250 && y > 45 && y < 215) return true;
    if (x > 500 && x < 730 && y > 45 && y < 230) return true;
    if (x > 315 && x < 440 && y > 85 && y < 265) return true;
    return false;
  }

  async function moveAvatar(direction) {
    const step = state.avatar.mounted ? 28 : running ? 22 : 12;
    const delta = { up: [0, -step], down: [0, step], left: [-step, 0], right: [step, 0] }[direction];
    if (!delta) return;
    state.avatar.sitting = false;
    const nextX = state.avatar.x + delta[0];
    const nextY = state.avatar.y + delta[1];
    if (!blocked(nextX, nextY)) { state.avatar.x = nextX; state.avatar.y = nextY; renderCanvas(); await persist(); }
    else setStatus("그쪽에는 집·나무·당근밭이 있어요. 다른 방향으로 움직여 주세요.");
  }

  function renderQuests() {
    $("#quest-list").innerHTML = quests.map((quest) => `<label class="quest-item"><input type="checkbox" data-quest="${quest.id}" ${state.quests[quest.id] ? "checked" : ""}><span class="quest-icon" aria-hidden="true">${quest.icon}</span><span class="quest-copy"><em>${quest.category}</em><strong>${quest.title}</strong><small>${quest.description}</small></span><b class="quest-reward">+${quest.reward} 🥕</b></label>`).join("");
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
    const renderItems = (kind) => state.inventory.filter((code) => itemCatalog[code].kind === kind).map((code) => {
      const item = itemCatalog[code];
      const equipped = item.kind === "accessory" && state.avatar.equipped === code;
      const selected = item.kind === "object" && placementCode === code;
      return `<button class="inventory-item" type="button" data-item="${code}" data-kind="${item.kind}" data-placement="${selected}" aria-pressed="${equipped || selected}"><span aria-hidden="true">${item.icon}</span><strong>${item.name}</strong><small>${item.kind === "accessory" ? equipped ? "장착 중" : "장착하기" : selected ? "맵을 눌러 배치" : "배치 선택"}</small></button>`;
    }).join("");
    $("#wardrobe-list").innerHTML = renderItems("accessory") || "<p class=\"empty-assets\">획득한 의상이 없습니다.</p>";
    $("#storage-list").innerHTML = renderItems("object") || "<p class=\"empty-assets\">보관 중인 오브젝트가 없습니다.</p>";
    $("#cancel-placement").hidden = !placementCode;
    $("#placement-mode").textContent = placementCode ? `${itemCatalog[placementCode].name} 배치 위치를 맵에서 선택하세요` : "배치할 아이템 없음";
  }

  function renderPlaced() {
    $("#object-count").textContent = `${state.placed.length}개`;
    $("#placed-list").innerHTML = state.placed.length
      ? state.placed.map((item, index) => `<div class="placed-object-row"><span aria-hidden="true">${itemCatalog[item.code].icon}</span><strong>${itemCatalog[item.code].name}</strong><button class="remove-object" type="button" data-remove="${index}">창고로 돌려놓기</button></div>`).join("")
      : "<p>아직 배치한 오브젝트가 없습니다.</p>";
  }

  function selectedAvatarItem(category, id = avatarDraft[category]) {
    return avatarCatalog[category].find((item) => item.id === id) || avatarCatalog[category][0];
  }

  function renderAvatarPreview() {
    const preview = $("#avatar-preview-canvas");
    const previewContext = preview.getContext("2d");
    previewContext.setTransform(1, 0, 0, 1, 0, 0);
    previewContext.clearRect(0, 0, preview.width, preview.height);
    previewContext.setTransform(2, 0, 0, 2, 0, 0);
    previewContext.imageSmoothingEnabled = false;
    const auraIndex = cosmeticSpriteIndex("aura", avatarDraft.aura);
    drawAtlasCell(previewContext, cosmeticSpriteAtlas, auraIndex, 5, 4, 46, 55, 188, 188);
    drawAtlasCell(previewContext, avatarSpriteAtlas, avatarSpriteIndex(avatarDraft), 4, 3, 58, 38, 164, 205);
    const effectIndex = cosmeticSpriteIndex("effect", avatarDraft.effect);
    drawAtlasCell(previewContext, cosmeticSpriteAtlas, effectIndex, 5, 4, 16, 50, 80, 80);
    const vehicleIndex = cosmeticSpriteIndex("vehicle", avatarDraft.vehicle);
    drawAtlasCell(previewContext, cosmeticSpriteAtlas, vehicleIndex, 5, 4, 18, 213, 82, 65);
    const petIndex = cosmeticSpriteIndex("pet", avatarDraft.pet);
    drawAtlasCell(previewContext, cosmeticSpriteAtlas, petIndex, 5, 4, 190, 205, 72, 72);
    const speechIndex = cosmeticSpriteIndex("speech", avatarDraft.speech);
    if (drawAtlasCell(previewContext, cosmeticSpriteAtlas, speechIndex, 5, 4, 175, 8, 96, 70)) {
      previewContext.textAlign = "center"; previewContext.font = "bold 9px sans-serif"; previewContext.fillStyle = "#30323b";
      previewContext.fillText(avatarDraft.speech === "cat" ? "안녕하세요!" : avatarDraft.speech === "leaf" ? "오늘도 한 걸음" : "같이 걸어요", 223, 42);
    }
  }

  function renderAvatarStudio() {
    $("#avatar-category-nav").innerHTML = avatarCategories.map((category) => `<button class="avatar-category-button" type="button" data-avatar-category="${category.id}" aria-pressed="${activeAvatarCategory === category.id}"><span aria-hidden="true">${category.icon}</span>${category.label}</button>`).join("");
    const category = avatarCategories.find((entry) => entry.id === activeAvatarCategory);
    const items = avatarCatalog[activeAvatarCategory];
    $("#avatar-category-title").textContent = category.label;
    $("#avatar-item-count").textContent = `${items.length}개`;
    $("#avatar-item-grid").innerHTML = items.map((item) => {
      const cosmeticIndex = cosmeticSpriteIndex(activeAvatarCategory, item.id);
      let visual;
      if (["skin", "outfit", "hair", "face", "accessory"].includes(activeAvatarCategory)) {
        const previewCosmetics = { ...avatarDraft, [activeAvatarCategory]: item.id };
        const index = avatarSpriteIndex(previewCosmetics);
        const x = index % 4 * 100 / 3;
        const y = Math.floor(index / 4) * 50;
        visual = `<span class="item-visual sprite-thumb avatar-sprite-thumb" style="background-position:${x}% ${y}%" aria-hidden="true"></span>`;
      } else if (cosmeticIndex != null) {
        const x = cosmeticIndex % 5 * 25;
        const y = Math.floor(cosmeticIndex / 5) * 100 / 3;
        visual = `<span class="item-visual sprite-thumb cosmetic-sprite-thumb" style="background-position:${x}% ${y}%" aria-hidden="true"></span>`;
      } else {
        visual = '<span class="item-visual empty-sprite-thumb" aria-hidden="true">없음</span>';
      }
      return `<button class="avatar-item-card" type="button" data-avatar-item="${item.id}" aria-pressed="${avatarDraft[activeAvatarCategory] === item.id}">${item.isNew ? '<span class="new-badge">N</span>' : ""}${visual}<span class="item-name">${item.name}</span><small>${avatarDraft[activeAvatarCategory] === item.id ? "선택됨" : "보유 아이템"}</small></button>`;
    }).join("");
    $("#preview-carrot-balance").textContent = state.carrots;
    $("#avatar-preview-name").textContent = state.avatar.name;
    $("#avatar-selection-name").textContent = selectedAvatarItem(activeAvatarCategory).name;
    $("#avatar-undo").disabled = avatarDraftHistory.length === 0;
    renderAvatarPreview();
  }

  function openAvatarStudio() {
    avatarDraft = { ...defaultCosmetics, ...(state.avatar.cosmetics || {}) };
    avatarDraftHistory = [];
    activeAvatarCategory = "skin";
    renderAvatarStudio();
    $("#avatar-studio").showModal();
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

  $("#open-avatar-studio").addEventListener("click", openAvatarStudio);
  $("#avatar-studio-close").addEventListener("click", () => $("#avatar-studio").close());
  $("#avatar-studio").addEventListener("click", (event) => {
    if (event.target === $("#avatar-studio")) $("#avatar-studio").close();
  });
  $("#avatar-category-nav").addEventListener("click", (event) => {
    const button = event.target.closest("[data-avatar-category]");
    if (!button) return;
    activeAvatarCategory = button.dataset.avatarCategory;
    renderAvatarStudio();
  });
  $("#avatar-item-grid").addEventListener("click", (event) => {
    const button = event.target.closest("[data-avatar-item]");
    if (!button || avatarDraft[activeAvatarCategory] === button.dataset.avatarItem) return;
    avatarDraftHistory.push({ ...avatarDraft });
    avatarDraft[activeAvatarCategory] = button.dataset.avatarItem;
    renderAvatarStudio();
  });
  $("#avatar-undo").addEventListener("click", () => {
    const previous = avatarDraftHistory.pop();
    if (!previous) return;
    avatarDraft = previous;
    renderAvatarStudio();
  });
  $("#avatar-randomize").addEventListener("click", () => {
    avatarDraftHistory.push({ ...avatarDraft });
    avatarCategories.forEach(({ id }) => {
      const choices = avatarCatalog[id];
      avatarDraft[id] = choices[Math.floor(Math.random() * choices.length)].id;
    });
    renderAvatarStudio();
  });
  $("#avatar-studio-save").addEventListener("click", async () => {
    state.avatar.cosmetics = { ...avatarDraft };
    state.avatar.equipped = avatarDraft.accessory === "none" ? null : avatarDraft.accessory;
    renderInventory();
    renderCanvas();
    $("#avatar-studio").close();
    await persist(`${state.avatar.name}님의 새 코디를 저장했습니다.`);
  });

  $("#asset-dock").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-item]");
    if (!button) return;
    const code = button.dataset.item;
    if (button.dataset.kind === "accessory") {
      state.avatar.equipped = state.avatar.equipped === code ? null : code;
      state.avatar.cosmetics.accessory = state.avatar.equipped || "none";
      placementCode = null;
      renderInventory(); renderCanvas(); await persist(`${itemCatalog[code].name} ${state.avatar.equipped === code ? "장착" : "해제"} 완료.`);
      return;
    }
    placementCode = placementCode === code ? null : code;
    renderInventory();
    setStatus(placementCode ? `${itemCatalog[code].name}을 놓을 위치를 맵에서 눌러 주세요.` : "오브젝트 배치를 취소했습니다.");
  });

  $("#unequip-button").addEventListener("click", async () => {
    state.avatar.equipped = null; state.avatar.cosmetics.accessory = "none"; renderInventory(); renderCanvas(); await persist("액세서리를 해제했습니다.");
  });
  $("#cancel-placement").addEventListener("click", () => { placementCode = null; renderInventory(); setStatus("오브젝트 배치를 취소했습니다."); });

  $("#placed-list").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-remove]");
    if (!button) return;
    const [removed] = state.placed.splice(Number(button.dataset.remove), 1);
    renderPlaced(); renderCanvas(); await persist(`${itemCatalog[removed.code].name}을 창고로 돌려놓았습니다.`);
  });

  canvas.addEventListener("click", async (event) => {
    const bounds = canvas.getBoundingClientRect();
    const x = Math.round((event.clientX - bounds.left) * WORLD_WIDTH / bounds.width / 4) * 4;
    const y = Math.round((event.clientY - bounds.top) * WORLD_HEIGHT / bounds.height / 4) * 4;
    if (!placementCode) {
      canvas.focus();
      if (x >= 38 && x <= 250 && y >= 45 && y <= 215) interact("home");
      else if (x >= 496 && x <= 724 && y >= 48 && y <= 230) interact("garden");
      else if (x >= 440 && x <= 505 && y >= 345 && y <= 410) interact("vehicle");
      else setStatus("집·공동 당근밭·스쿠터를 클릭하거나 가까이에서 Q를 눌러 보세요.");
      return;
    }
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

  function toggleChat(force) {
    const panel = $("#chat-panel");
    panel.hidden = force === undefined ? !panel.hidden : !force;
    if (!panel.hidden) window.setTimeout(() => $("#chat-input").focus(), 0);
    else canvas.focus();
  }

  async function toggleSit() {
    if (state.avatar.mounted) { setStatus("탈것에서 내린 뒤 앉을 수 있어요."); return; }
    state.avatar.sitting = !state.avatar.sitting;
    renderCanvas();
    await persist(state.avatar.sitting ? "풀밭에 앉아 잠시 쉬고 있어요." : "자리에서 일어났습니다.");
  }

  async function toggleRide(requireNearby = true) {
    if (!state.avatar.mounted && requireNearby && distanceTo(470, 376) >= 72) {
      setStatus("숲 스쿠터 가까이 이동한 뒤 E를 눌러 주세요.");
      return;
    }
    state.avatar.mounted = !state.avatar.mounted;
    state.avatar.sitting = false;
    if (!state.avatar.mounted) { state.avatar.x = 470; state.avatar.y = 410; }
    renderCanvas();
    await persist(state.avatar.mounted ? "숲 스쿠터에 탔습니다. 이동 속도가 빨라졌어요." : "숲 스쿠터에서 내렸습니다.");
  }

  document.addEventListener("keydown", (event) => {
    if (["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(document.activeElement?.tagName)) return;
    if (["q", "Q", "r", "R", "c", "C", "x", "X", "e", "E"].includes(event.key)) event.preventDefault();
    if (event.key === "q" || event.key === "Q") { interact(); return; }
    if (event.key === "r" || event.key === "R") { running = true; setStatus("달리기 모드입니다. 방향키나 WASD로 빠르게 이동하세요."); return; }
    if (event.key === "c" || event.key === "C") { toggleChat(); return; }
    if (event.key === "x" || event.key === "X") { toggleSit(); return; }
    if (event.key === "e" || event.key === "E") { toggleRide(); return; }
    const direction = { ArrowUp: "up", w: "up", W: "up", ArrowDown: "down", s: "down", S: "down", ArrowLeft: "left", a: "left", A: "left", ArrowRight: "right", d: "right", D: "right" }[event.key];
    if (!direction) return;
    event.preventDefault(); moveAvatar(direction);
  });
  document.addEventListener("keyup", (event) => {
    if (event.key === "r" || event.key === "R") { running = false; setStatus("달리기를 멈췄습니다."); }
  });
  document.querySelectorAll("[data-move]").forEach((button) => button.addEventListener("pointerdown", (event) => { event.preventDefault(); moveAvatar(button.dataset.move); }));
  document.querySelectorAll("[data-action]").forEach((button) => button.addEventListener("click", async () => {
    const action = button.dataset.action;
    if (action === "interact") interact();
    if (action === "run") { running = !running; button.setAttribute("aria-pressed", String(running)); setStatus(running ? "달리기 모드가 켜졌습니다." : "달리기 모드를 껐습니다."); }
    if (action === "chat") toggleChat();
    if (action === "sit") await toggleSit();
    if (action === "ride") await toggleRide();
  }));

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

  $("#world-dialog-close").addEventListener("click", () => $("#world-dialog").close());
  $("#world-dialog-actions").addEventListener("click", async (event) => {
    const action = event.target.closest("[data-world-action]")?.dataset.worldAction;
    if (!action) return;
    if (action === "rest") {
      state.avatar.sitting = true;
      state.avatar.mounted = false;
      $("#world-dialog").close();
      renderCanvas();
      await persist("우리 집 소파에서 편안하게 쉬고 있어요.");
    }
    if (action === "wardrobe") {
      $("#world-dialog").close();
      openAvatarStudio();
    }
    if (action === "water" && !state.gardenWatered) {
      state.gardenWatered = true;
      state.carrots += 10;
      $("#carrot-balance").textContent = state.carrots;
      $("#world-dialog").close();
      await persist("공동 당근밭에 물을 주고 당근 10개를 받았습니다.");
    }
    if (action === "team") {
      $("#world-dialog").close();
      $("#team-inspector").scrollIntoView({ behavior: "smooth", block: "center" });
    }
    if (action === "ride") {
      $("#world-dialog").close();
      await toggleRide(false);
    }
  });

  $("#chat-close").addEventListener("click", () => toggleChat(false));
  $("#chat-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = $("#chat-input");
    const message = input.value.trim();
    if (!message) return;
    const row = document.createElement("p");
    const author = document.createElement("strong");
    const copy = document.createElement("span");
    author.textContent = state.avatar.name;
    copy.textContent = message;
    row.append(author, copy);
    $("#chat-messages").append(row);
    input.value = "";
    $("#chat-messages").scrollTop = $("#chat-messages").scrollHeight;
  });

  $("#music-toggle").addEventListener("click", async (event) => {
    musicEngine ||= new CozyForestMusic();
    const enabled = event.currentTarget.getAttribute("aria-pressed") !== "true";
    try {
      if (enabled) await musicEngine.start(); else musicEngine.stop();
    } catch {
      setStatus("이 브라우저에서는 배경음악을 재생할 수 없습니다. 다른 기능은 계속 이용할 수 있어요.");
      return;
    }
    event.currentTarget.setAttribute("aria-pressed", String(enabled));
    event.currentTarget.textContent = enabled ? "Ⅱ 음악 끄기" : "♪ 숲 음악 켜기";
    setStatus(enabled ? "오리지널 숲 배경음악을 재생합니다." : "숲 배경음악을 멈췄습니다.");
  });

  const installButton = $("#install-pwa");
  let deferredInstallPrompt = null;
  const standalone = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  if (!standalone) {
    window.addEventListener("beforeinstallprompt", (event) => {
      event.preventDefault();
      deferredInstallPrompt = event;
      installButton.hidden = false;
    });
  }
  installButton.addEventListener("click", async () => {
    if (!deferredInstallPrompt) {
      setStatus("브라우저 메뉴에서 ‘앱 설치’ 또는 ‘홈 화면에 추가’를 선택해 주세요.");
      return;
    }
    deferredInstallPrompt.prompt();
    const choice = await deferredInstallPrompt.userChoice;
    deferredInstallPrompt = null;
    installButton.hidden = true;
    setStatus(choice.outcome === "accepted" ? "당근의 숲 앱 설치를 시작합니다." : "설치를 취소했습니다.");
  });
  window.addEventListener("appinstalled", () => {
    installButton.hidden = true;
    setStatus("당근의 숲이 앱으로 설치되었습니다.");
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/forest-sw.js", { scope: "/forest" }).catch(() => {
        setStatus("오프라인 준비에 실패했습니다. 온라인 게임은 계속 이용할 수 있습니다.");
      });
    });
  }

  window.CarrotForestAdapters = { DemoForestAdapter, ApiForestAdapter };
  adapter.load().then((loaded) => {
    state = loaded;
    renderAll();
    setStatus("당근의 숲이 준비되었습니다. 오늘의 퀘스트부터 시작해 보세요.");
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) window.requestAnimationFrame(animateWorld);
  });
})();
