(() => {
  "use strict";

  document.documentElement.classList.add("forest-script-ready");

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
    custom: { label: "나만의 조합", hair: "#4b2f24", outfit: "#4f9e63", accent: "#c8f06a" },
    sprout: { label: "새싹 정원사", hair: "#4b2f24", outfit: "#4f9e63", accent: "#c8f06a" },
    carrot: { label: "당근 탐험가", hair: "#7b3d20", outfit: "#f07b32", accent: "#ffe078" },
    moon: { label: "달빛 산책가", hair: "#303c61", outfit: "#536eb5", accent: "#d9e3ff" },
    berry: { label: "산딸기 수집가", hair: "#5d2949", outfit: "#b44f78", accent: "#ffd2df" },
    red_bow: { label: "리본 정원사", hair: "#c8542c", outfit: "#26395f", accent: "#f7e7cc" },
    cow_hood: { label: "음메 목장지기", hair: "#6e452f", outfit: "#c54f24", accent: "#f7ead2" },
    midnight: { label: "한밤 숲지기", hair: "#17192e", outfit: "#29243f", accent: "#8d72c9" },
    blue_cap: { label: "파란 모자 농부", hair: "#26313d", outfit: "#254c7e", accent: "#f2dfbd" },
    teal_bob: { label: "미소 정원사", hair: "#8a5538", outfit: "#67623b", accent: "#2c9b92" },
  };
  const presetBundles = {
    sprout: { hair: "soft", outfit: "forest", bottom: "cream", shoes: "brown", face: "calm", accessory: "none", hat: "none", glasses: "none" },
    red_bow: { hair: "red_wave", outfit: "navy_garden", bottom: "cream", shoes: "brown", face: "smile", accessory: "none", hat: "headband", glasses: "none" },
    cow_hood: { hair: "cow_brown", outfit: "cow_vest", bottom: "charcoal", shoes: "brown", face: "smile", accessory: "none", hat: "cap", glasses: "none" },
    midnight: { hair: "midnight", outfit: "violet", bottom: "charcoal", shoes: "black", face: "calm", accessory: "none", hat: "none", glasses: "round" },
    blue_cap: { hair: "blue_short", outfit: "blue_overalls", bottom: "denim", shoes: "white", face: "calm", accessory: "none", hat: "cap", glasses: "none" },
    teal_bob: { hair: "teal_bob", outfit: "teal_garden", bottom: "olive", shoes: "brown", face: "smile", accessory: "none", hat: "none", glasses: "none" },
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
    { id: "preset", label: "완성형 코디", icon: "🧑‍🌾" },
    { id: "hair", label: "헤어", icon: "💇" },
    { id: "outfit", label: "의상", icon: "👕" },
    { id: "accessory", label: "액세서리", icon: "👜" },
    { id: "hat", label: "모자", icon: "🧢" },
    { id: "glasses", label: "안경", icon: "👓" },
    { id: "aura", label: "아우라", icon: "✨" },
    { id: "effect", label: "찌르기 이펙트", icon: "💫" },
    { id: "vehicle", label: "탈것", icon: "🛴" },
    { id: "pet", label: "펫", icon: "🐾" },
    { id: "speech", label: "말풍선", icon: "💬" },
  ];
  const avatarCatalog = {
    preset: [
      { id: "red_bow", name: "리본 정원사", isNew: true },
      { id: "cow_hood", name: "음메 목장지기", isNew: true }, { id: "midnight", name: "한밤 숲지기", isNew: true },
      { id: "blue_cap", name: "파란 모자 농부", isNew: true }, { id: "teal_bob", name: "미소 정원사", isNew: true },
    ],
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
      { id: "navy_garden", name: "리본 네이비 원피스", visual: "👗" }, { id: "cow_vest", name: "목장 주황 조끼", visual: "🦺" },
      { id: "blue_overalls", name: "파란 농부 멜빵", visual: "👖" }, { id: "teal_garden", name: "청록 리본 작업복", visual: "🥼" },
    ],
    bottom: [
      { id: "cream", name: "크림 작업바지", visual: "🤍" }, { id: "denim", name: "데님 바지", visual: "💙" },
      { id: "charcoal", name: "차콜 바지", visual: "🖤" }, { id: "olive", name: "올리브 바지", visual: "💚" },
      { id: "plum", name: "플럼 바지", visual: "💜" },
    ],
    shoes: [
      { id: "brown", name: "브라운 워커", visual: "🥾" }, { id: "white", name: "화이트 스니커즈", visual: "👟" },
      { id: "black", name: "블랙 로퍼", visual: "👞" }, { id: "orange", name: "오렌지 러너", visual: "🟠" },
    ],
    hair: [
      { id: "soft", name: "포근한 단발", visual: "💇" }, { id: "wave", name: "물결 장발", visual: "👩‍🦱", isNew: true },
      { id: "crop", name: "산뜻한 숏컷", visual: "🧑" }, { id: "twin", name: "양갈래 머리", visual: "👧" },
      { id: "silver", name: "은빛 웨이브", visual: "🧓" }, { id: "orange", name: "당근빛 웨이브", visual: "🧑‍🦰" },
      { id: "red_wave", name: "리본빛 긴 머리", visual: "👩‍🦰" }, { id: "cow_brown", name: "목장 단발", visual: "💇" },
      { id: "midnight", name: "한밤 레이어드", visual: "🧑" }, { id: "blue_short", name: "파란 모자 숏컷", visual: "🧑" },
      { id: "teal_bob", name: "미소 갈색 단발", visual: "💇" },
    ],
    face: [
      { id: "calm", name: "차분한 표정", visual: "🙂" }, { id: "smile", name: "환한 미소", visual: "😊" },
      { id: "sparkle", name: "반짝이는 눈", visual: "🤩", isNew: true }, { id: "blush", name: "수줍은 볼", visual: "☺️" },
      { id: "wink", name: "윙크", visual: "😉" }, { id: "cool", name: "도도한 표정", visual: "😌" },
    ],
    hat: [
      { id: "none", name: "모자 없음", visual: "—" }, { id: "cap", name: "산책 캡", visual: "🧢" },
      { id: "headband", name: "리본 헤드밴드", visual: "🎀" },
    ],
    glasses: [
      { id: "none", name: "안경 없음", visual: "—" }, { id: "round", name: "둥근 안경", visual: "👓" },
      { id: "sun", name: "선글라스", visual: "🕶️" },
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
      { id: "blue_eyes_white_cat", name: "설빛 고양이", visual: "🐈", isNew: true },
      { id: "gold_eyes_orange_cat", name: "호박눈 고양이", visual: "🐈", isNew: true },
    ],
    speech: [
      { id: "none", name: "말풍선 없음", visual: "—" }, { id: "cat", name: "고양이 인사", visual: "🐱" },
      { id: "leaf", name: "네잎클로버", visual: "🍀" }, { id: "window", name: "파란 창문", visual: "🪟", isNew: true },
    ],
  };
  const defaultCosmetics = {
    skin: "peach", outfit: "forest", bottom: "cream", shoes: "brown", hair: "soft", face: "calm", hat: "none", glasses: "none", accessory: "none",
    aura: "wings", effect: "none", vehicle: "scooter", pet: "none", speech: "none",
  };

  function defaultState() {
    return {
      dateKey: TODAY,
      avatar: { name: "세준", gender: "male", preset: "blue_cap", x: 384, y: 352, direction: "down", equipped: null, cosmetics: { ...defaultCosmetics }, sitting: false, mounted: false },
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
      fishCaught: false,
      fishing: false,
    };
  }

  function normalizeState(value) {
    const fallback = defaultState();
    if (!value || value.dateKey !== TODAY) return fallback;
    const state = { ...fallback, ...value };
    state.avatar = { ...fallback.avatar, ...(value.avatar || {}) };
    if (!presetBundles[state.avatar.preset]) state.avatar.preset = "blue_cap";
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
  let walkingUntil = 0;
  let walkAnimationFrame = 0;
  let currentScene = "world";
  let activeAvatarCategory = "preset";
  let avatarDraft = { ...defaultCosmetics };
  let avatarDraftHistory = [];
  const canvas = $("#forest-canvas");
  const context = canvas.getContext("2d");
  context.imageSmoothingEnabled = false;
  const avatarSpriteAtlas = new Image();
  const cosmeticSpriteAtlas = new Image();
  const catPetAtlas = new Image();
  const storageSpriteAtlas = new Image();
  const basicWalkAtlas = new Image();
  const basicScooterAtlas = new Image();
  const presetSpriteAtlases = {
    red_bow: { image: new Image(), rows: 6, file: "carrot-forest-avatar-red_bow-normalized-v2.png" },
    cow_hood: { image: new Image(), rows: 5, file: "carrot-forest-avatar-cow_hood-normalized-v2.png" },
    midnight: { image: new Image(), rows: 6, file: "carrot-forest-avatar-midnight-normalized-v2.png" },
    blue_cap: { image: new Image(), rows: 6, file: "carrot-forest-avatar-blue_cap-normalized-v2.png" },
    teal_bob: { image: new Image(), rows: 6, file: "carrot-forest-avatar-teal_bob-normalized-v2.png" },
  };
  const sceneImages = { world: new Image(), home: new Image(), garden: new Image() };
  avatarSpriteAtlas.src = "/static/assets/carrot-forest-avatar-atlas-v1.png";
  cosmeticSpriteAtlas.src = "/static/assets/carrot-forest-cosmetics-atlas-v1.png";
  catPetAtlas.src = "/static/assets/carrot-forest-cat-pets-v1.png";
  storageSpriteAtlas.src = "/static/assets/carrot-forest-storage-atlas-v1.png";
  basicWalkAtlas.src = "/static/assets/carrot-forest-basic-walk-atlas-v1.png";
  basicScooterAtlas.src = "/static/assets/carrot-forest-basic-scooter-atlas-v1.png";
  Object.values(presetSpriteAtlases).forEach((atlas) => { atlas.image.src = `/static/assets/${atlas.file}`; });
  sceneImages.world.src = "/static/assets/carrot-forest-world-v2.png";
  sceneImages.home.src = "/static/assets/carrot-forest-home-v1.png";
  sceneImages.garden.src = "/static/assets/carrot-forest-garden-v1.png";
  avatarSpriteAtlas.addEventListener("load", () => { renderCanvas(); if ($("#avatar-studio").open) renderAvatarStudio(); });
  cosmeticSpriteAtlas.addEventListener("load", () => { renderCanvas(); if ($("#avatar-studio").open) renderAvatarStudio(); });
  catPetAtlas.addEventListener("load", () => { renderCanvas(); if ($("#avatar-studio").open) renderAvatarStudio(); });
  storageSpriteAtlas.addEventListener("load", () => { renderInventory(); renderCanvas(); });
  basicWalkAtlas.addEventListener("load", renderCanvas);
  basicScooterAtlas.addEventListener("load", renderCanvas);
  Object.values(presetSpriteAtlases).forEach((atlas) => atlas.image.addEventListener("load", () => {
    renderCanvas();
    if ($("#avatar-studio").open) renderAvatarStudio();
  }));
  Object.values(sceneImages).forEach((image) => image.addEventListener("load", renderCanvas));

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
    window.dispatchEvent(new CustomEvent("forest-state-updated", { detail: { avatar: state.avatar, scene: currentScene } }));
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
    const sceneImage = sceneImages[currentScene];
    if (sceneImage?.complete && sceneImage.naturalWidth) {
      context.drawImage(sceneImage, 0, 0, WORLD_WIDTH, WORLD_HEIGHT);
      if (currentScene === "world") {
        drawVehicle();
        drawPlacedObjects();
      }
      return;
    }
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
      const storageIndex = { flower_patch: 0, lantern: 1, mushroom: 2, bench: 3 }[item.code];
      if (drawAtlasCell(context, storageSpriteAtlas, storageIndex, 4, 1, x - 28, y - 34, 56, 56)) return;
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

  function catPetSpriteIndex(itemId) {
    return { blue_eyes_white_cat: 0, gold_eyes_orange_cat: 1 }[itemId] ?? null;
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

  function isAnimatedBasicPreset(cosmetics) {
    return cosmetics.skin === "peach"
      && cosmetics.outfit === "forest"
      && cosmetics.hair === "soft"
      && cosmetics.face === "calm"
      && cosmetics.accessory === "none";
  }

  function drawAnimatedAccessoryOverlay(avatar, cosmetics, x, y) {
    const direction = avatar.direction || "down";
    const accessory = cosmetics.accessory;
    if (accessory === "red_scarf") {
      fillPixelRect(x - 15, y - 22, 30, 6, "#cf3435");
      if (direction === "left") fillPixelRect(x + 9, y - 18, 12, 5, "#e34c49");
      if (direction === "right") fillPixelRect(x - 21, y - 18, 12, 5, "#e34c49");
    }
    if (accessory === "sprout_hat") {
      fillPixelRect(x - 18, y - 55, 36, 7, "#347f3d"); fillPixelRect(x - 3, y - 66, 6, 12, "#216a34"); fillPixelRect(x + 2, y - 66, 12, 7, "#65b85d");
    }
    if (accessory === "round_glasses" || accessory === "star_glasses") {
      const color = accessory === "star_glasses" ? "#e75e99" : "#354751";
      if (direction === "down") {
        context.strokeStyle = color; context.lineWidth = 2; context.strokeRect(x - 15, y - 40, 12, 9); context.strokeRect(x + 3, y - 40, 12, 9); fillPixelRect(x - 3, y - 37, 6, 2, color);
      } else if (direction === "left" || direction === "right") {
        context.strokeStyle = color; context.lineWidth = 2; context.strokeRect(x + (direction === "left" ? -17 : 5), y - 39, 13, 9);
      }
    }
    if (accessory === "carrot_bag") {
      const side = direction === "left" ? 12 : direction === "right" ? -23 : 14;
      fillPixelRect(x + side, y - 5, 12, 22, "#bd4e25"); fillPixelRect(x + side + 2, y - 2, 8, 16, "#ef7c31");
    }
  }

  function drawAnimatedBasicWorldAvatar(avatar, cosmetics, x, y) {
    const presetAtlas = presetSpriteAtlases[avatar.preset];
    const direction = avatar.direction || "down";
    const moving = performance.now() < walkingUntil;
    if (!avatar.mounted) {
      const auraIndex = cosmeticSpriteIndex("aura", cosmetics.aura);
      drawAtlasCell(context, cosmeticSpriteAtlas, auraIndex, 5, 4, x - 45, y - 51, 90, 90);
    }

    if (presetAtlas) {
      if (!presetAtlas.image.complete || !presetAtlas.image.naturalWidth) return false;
      const directionColumn = { down: 0, up: 1, left: 2, right: 3 }[direction] ?? 0;
      if (avatar.mounted) {
        const motionRow = moving && presetAtlas.rows === 6 ? 5 : 4;
        const rideBob = moving && presetAtlas.rows === 5 ? walkAnimationFrame % 2 : 0;
        drawAtlasCell(context, presetAtlas.image, motionRow * 4 + directionColumn, 4, presetAtlas.rows, x - 48, y - 57 - rideBob, 96, 96);
      } else {
        const directionRow = { down: 0, up: 1, left: 2, right: 3 }[direction] ?? 0;
        const frame = moving ? walkAnimationFrame % 4 : 0;
        drawAtlasCell(context, presetAtlas.image, directionRow * 4 + frame, 4, presetAtlas.rows, x - 36, y - 56, 72, 88);
      }
    } else if (avatar.mounted) {
      if (!basicScooterAtlas.complete || !basicScooterAtlas.naturalWidth) return false;
      const directionColumn = { down: 0, up: 1, left: 2, right: 3 }[direction] ?? 0;
      const motionRow = moving ? walkAnimationFrame % 2 : 0;
      drawAtlasCell(context, basicScooterAtlas, motionRow * 4 + directionColumn, 4, 2, x - 52, y - 62, 104, 104);
    } else {
      if (!basicWalkAtlas.complete || !basicWalkAtlas.naturalWidth) return false;
      const directionRow = { down: 0, up: 1, left: 2, right: 3 }[direction] ?? 0;
      const frame = moving ? walkAnimationFrame % 4 : 0;
      drawAtlasCell(context, basicWalkAtlas, directionRow * 4 + frame, 4, 4, x - 34, y - 54, 68, 86);
    }

    drawAnimatedAccessoryOverlay(avatar, cosmetics, x, y);

    const effectIndex = cosmeticSpriteIndex("effect", cosmetics.effect);
    drawAtlasCell(context, cosmeticSpriteAtlas, effectIndex, 5, 4, x - 42, y - 43, 42, 42);
    const petIndex = cosmeticSpriteIndex("pet", cosmetics.pet);
    const catIndex = catPetSpriteIndex(cosmetics.pet);
    if (!drawAtlasCell(context, catPetAtlas, catIndex, 2, 1, x + 18, y - 2, 46, 46)) {
      drawAtlasCell(context, cosmeticSpriteAtlas, petIndex, 5, 4, x + 20, y + 5, 35, 35);
    }
    if (cosmetics.speech !== "none") {
      const speechIndex = cosmeticSpriteIndex("speech", cosmetics.speech);
      drawAtlasCell(context, cosmeticSpriteAtlas, speechIndex, 5, 4, x + 25, y - 65, 62, 45);
      context.font = "bold 7px sans-serif"; context.textAlign = "center"; context.fillStyle = "#31343f";
      context.fillText(cosmetics.speech === "cat" ? "안녕!" : cosmetics.speech === "leaf" ? "한 걸음" : "같이 걸어요", x + 56, y - 41);
    }
    context.font = "bold 11px sans-serif"; context.textAlign = "center";
    context.fillStyle = "rgba(255,255,255,.94)"; context.fillRect(x - Math.max(25, avatar.name.length * 6), y - 69, Math.max(50, avatar.name.length * 12), 17);
    context.fillStyle = "#18382d"; context.fillText(avatar.name, x, y - 56);
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
    const catIndex = catPetSpriteIndex(cosmetics.pet);
    if (!drawAtlasCell(context, catPetAtlas, catIndex, 2, 1, x + 18, y - 2, 46, 46)) {
      drawAtlasCell(context, cosmeticSpriteAtlas, petIndex, 5, 4, x + 20, y + 5, 35, 35);
    }
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
    if (drawAnimatedBasicWorldAvatar(avatar, cosmetics, x, y)) return;
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
      const catIndex = catPetSpriteIndex(cosmetics.pet);
      if (!drawAtlasCell(context, catPetAtlas, catIndex, 2, 1, x + 18, y - 2, 46, 46)) {
        context.font = "22px sans-serif"; context.fillText(petGlyphs[cosmetics.pet] || "🐾", x + 34, y + 34);
      }
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

  function drawSceneEffects() {
    if (currentScene === "home" && state.avatar.sitting) {
      context.fillStyle = "rgba(255,255,255,.9)";
      context.font = "bold 15px sans-serif";
      context.fillText("Z", state.avatar.x + 31, state.avatar.y - 55);
      context.font = "bold 10px sans-serif";
      context.fillText("z", state.avatar.x + 43, state.avatar.y - 68);
    }
    if (currentScene === "world" && state.fishing) {
      context.strokeStyle = "#5a412b";
      context.lineWidth = 3;
      context.beginPath();
      context.moveTo(state.avatar.x + 16, state.avatar.y - 5);
      context.lineTo(280, 399);
      context.stroke();
      context.strokeStyle = "#e8f5ee";
      context.lineWidth = 1;
      context.beginPath();
      context.moveTo(280, 399);
      context.lineTo(250, 432);
      context.stroke();
      context.fillStyle = "#ffd45c";
      context.font = "18px sans-serif";
      context.fillText(state.fishCaught ? "✦" : "~", 246, 436);
    }
  }

  function renderSceneChrome() {
    const sceneCopy = {
      world: { title: "우리의 작은 숲", aria: "집, 당근밭, 연못이 있는 고해상도 픽셀 숲 월드" },
      home: { title: "나의 홈피 · 포근한 거실", aria: "소파와 옷장이 있는 집 내부 장면" },
      garden: { title: "공동 당근밭", aria: "당근밭과 물뿌리개가 있는 농장 장면" },
    }[currentScene];
    $("#map-title").textContent = sceneCopy.title;
    canvas.setAttribute("aria-label", `${sceneCopy.aria}. 방향키나 WASD로 이동하고 Q키로 상호작용할 수 있습니다.`);
    $("#scene-exit").hidden = currentScene === "world";
    $(".home-label").hidden = currentScene !== "world";
    $(".garden-label").hidden = currentScene !== "world";
  }

  function renderCanvas() {
    context.setTransform(1, 0, 0, 1, 0, 0);
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.setTransform(RENDER_SCALE, 0, 0, RENDER_SCALE, 0, 0);
    context.imageSmoothingEnabled = false;
    drawMap();
    drawAvatar();
    drawSceneEffects();
    renderSceneChrome();
    $("#avatar-coordinate").textContent = `X ${Math.round(state.avatar.x)} · Y ${Math.round(state.avatar.y)}`;
    updateInteractionPrompt();
  }

  let lastAnimationAt = 0;
  let lastWalkAnimationAt = 0;
  function animateWorld(timestamp) {
    let needsRender = false;
    if (!document.hidden && timestamp - lastAnimationAt > 420) {
      animationFrame = (animationFrame + 1) % 2;
      lastAnimationAt = timestamp;
      needsRender = true;
    }
    const moving = timestamp < walkingUntil;
    if (!document.hidden && moving && timestamp - lastWalkAnimationAt > (state.avatar.mounted ? 115 : 95)) {
      walkAnimationFrame = (walkAnimationFrame + 1) % 4;
      lastWalkAnimationAt = timestamp;
      needsRender = true;
    } else if (!moving && walkAnimationFrame !== 0) {
      walkAnimationFrame = 0;
      needsRender = true;
    }
    if (needsRender) renderCanvas();
    window.requestAnimationFrame(animateWorld);
  }

  function distanceTo(x, y) {
    return Math.hypot(state.avatar.x - x, state.avatar.y - y);
  }

  function nearbyInteraction() {
    if (currentScene === "home") {
      if (distanceTo(292, 246) < 95) return "sofa";
      if (distanceTo(558, 205) < 100) return "wardrobe";
      if (distanceTo(384, 438) < 78) return "exit_home";
      return null;
    }
    if (currentScene === "garden") {
      if (distanceTo(384, 215) < 120 || distanceTo(622, 382) < 90) return "crops";
      if (distanceTo(384, 430) < 78) return "exit_garden";
      return null;
    }
    if (distanceTo(200, 270) < 95) return "home";
    if (distanceTo(600, 255) < 110) return "garden";
    if (distanceTo(285, 405) < 105) return "pond";
    if (distanceTo(470, 376) < 72) return "vehicle";
    return null;
  }

  function updateInteractionPrompt() {
    const target = nearbyInteraction();
    const prompt = $("#interaction-prompt");
    prompt.hidden = !target;
    if (target) prompt.querySelector("span").textContent = {
      home: "집 안으로", garden: "당근밭으로", pond: "물고기 잡기", vehicle: "숲 스쿠터",
      sofa: "소파에서 쉬기", wardrobe: "옷장 열기", exit_home: "집 밖으로",
      crops: "당근 돌보기", exit_garden: "숲으로 돌아가기",
    }[target];
  }

  function openWorldDialog(target) {
    const dialog = $("#world-dialog");
    const content = {
      home: { icon: "🏠", title: "우리 집", copy: "문을 열고 나만의 포근한 홈피로 들어가요.", actions: '<button type="button" data-world-action="enter_home">집 안으로 들어가기</button>' },
      garden: { icon: "🥕", title: "공동 당근밭", copy: `우리 모임은 오늘 ${groupCompleted()}/15개의 퀘스트를 완료했어요. 밭 안으로 들어가 당근을 돌봐요.`, actions: '<button type="button" data-world-action="enter_garden">당근밭 들어가기</button><button type="button" data-world-action="team">공동 진행 보기</button>' },
      pond: { icon: "🎣", title: "숲의 연못", copy: state.fishCaught ? "오늘 낚시를 즐겼어요. 물결을 바라보며 잠시 쉬어가도 좋아요." : "낚싯대를 드리우고 숲의 물고기를 기다려 볼까요?", actions: `<button type="button" data-world-action="fish">${state.fishCaught ? "한 번 더 낚시하기" : "물고기 잡기"}</button>` },
      vehicle: { icon: "🛵", title: "숲 스쿠터", copy: "스쿠터를 타면 숲길을 더 빠르게 이동할 수 있어요.", actions: `<button type="button" data-world-action="ride">${state.avatar.mounted ? "스쿠터에서 내리기" : "스쿠터 타기"}</button>` },
      sofa: { icon: "🛋️", title: "포근한 소파", copy: "소파에 앉아 창밖의 숲을 바라보며 쉬어가요.", actions: '<button type="button" data-world-action="rest">소파에서 쉬기</button>' },
      wardrobe: { icon: "👗", title: "나의 옷장", copy: "아바타와 함께 걷는 펫을 꾸밀 수 있어요.", actions: '<button type="button" data-world-action="wardrobe">아바타 꾸미기</button>' },
      exit_home: { icon: "🚪", title: "현관문", copy: "작은 숲으로 다시 나갈까요?", actions: '<button type="button" data-world-action="exit_scene">집 밖으로 나가기</button>' },
      crops: { icon: "🥕", title: "공동 당근", copy: "오늘의 실천이 모일수록 공동 당근이 튼튼하게 자라요.", actions: `<button type="button" data-world-action="water" ${state.gardenWatered ? "disabled" : ""}>${state.gardenWatered ? "오늘 물주기 완료" : "당근에 물주기"}</button><button type="button" data-world-action="team">공동 진행 보기</button>` },
      exit_garden: { icon: "🌲", title: "숲으로 가는 문", copy: "공동 당근밭을 나가 작은 숲으로 돌아가요.", actions: '<button type="button" data-world-action="exit_scene">숲으로 돌아가기</button>' },
    }[target];
    if (!content) { setStatus("상호작용할 대상 가까이 이동해 주세요."); return; }
    $("#world-dialog-icon").textContent = content.icon;
    $("#world-dialog-title").textContent = content.title;
    $("#world-dialog-copy").textContent = content.copy;
    $("#world-dialog-actions").innerHTML = content.actions;
    dialog.showModal();
  }

  function interact(target = nearbyInteraction()) {
    if (!target) { setStatus("상호작용할 대상 가까이 이동한 뒤 Q를 눌러 주세요."); return; }
    openWorldDialog(target);
  }

  function switchScene(scene) {
    currentScene = scene;
    state.avatar.sitting = false;
    state.avatar.mounted = false;
    state.fishing = false;
    const positions = { world: [384, 352], home: [384, 410], garden: [384, 410] };
    [state.avatar.x, state.avatar.y] = positions[scene];
    placementCode = null;
    renderInventory();
    renderCanvas();
    canvas.focus();
  }

  function blocked(x, y) {
    if (x < 28 || x > WORLD_WIDTH - 28 || y < 42 || y > WORLD_HEIGHT - 38) return true;
    if (currentScene === "home") {
      if (x < 64 || x > 710 || y < 100 || y > 458) return true;
      return false;
    }
    if (currentScene === "garden") {
      if (x < 105 || x > 675 || y < 105 || y > 458) return true;
      return false;
    }
    if (x > 45 && x < 335 && y > 55 && y < 275) return true;
    if (x > 465 && x < 735 && y > 45 && y < 255) return true;
    if (x > 35 && x < 270 && y > 300 && y < 475) return true;
    return false;
  }

  async function moveAvatar(direction) {
    if (window.carrotForestPhaserActive && window.carrotForestPhaserMove) {
      window.carrotForestPhaserMove(direction);
      return;
    }
    const step = state.avatar.mounted ? 28 : running ? 22 : 12;
    const delta = { up: [0, -step], down: [0, step], left: [-step, 0], right: [step, 0] }[direction];
    if (!delta) return;
    state.avatar.direction = direction;
    state.avatar.sitting = false;
    state.fishing = false;
    walkingUntil = performance.now() + (state.avatar.mounted ? 260 : 220);
    const nextX = state.avatar.x + delta[0];
    const nextY = state.avatar.y + delta[1];
    if (!blocked(nextX, nextY)) { state.avatar.x = nextX; state.avatar.y = nextY; renderCanvas(); await persist(); }
    else { renderCanvas(); setStatus("그쪽에는 집·나무·당근밭이 있어요. 다른 방향으로 움직여 주세요."); }
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
      if (item.kind === "object") {
        const storageIndex = { flower_patch: 0, lantern: 1, mushroom: 2, bench: 3 }[code];
        const backgroundPosition = `${storageIndex * 100 / 3}% 0%`;
        const action = selected ? "선택됨, 맵에서 배치 위치 선택" : "배치 선택";
        return `<button class="inventory-item storage-icon-item" type="button" data-item="${code}" data-kind="object" data-placement="${selected}" aria-pressed="${selected}" aria-label="${item.name}, ${action}" title="${item.name}"><span class="storage-sprite-thumb" style="background-position:${backgroundPosition}" aria-hidden="true"></span></button>`;
      }
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

  const avatarThumbnailIndexes = {
    outfit: { forest: 0, denim: 4, carrot: 8, moon: 2, berry: 5, yellow: 3, violet: 10, black: 6 },
    hair: { soft: 0, wave: 1, crop: 4, twin: 7, silver: 10, orange: 9 },
    face: { calm: 0, smile: 1, sparkle: 5, blush: 7, wink: 3, cool: 10 },
    accessory: { none: null, red_scarf: 0, sprout_hat: 8, carrot_bag: 11, round_glasses: 2, star_glasses: 3 },
  };
  const stylePresetByItem = {
    red_wave: "red_bow", navy_garden: "red_bow", cow_brown: "cow_hood", cow_vest: "cow_hood",
    midnight: "midnight", violet: "midnight", blue_short: "blue_cap", blue_overalls: "blue_cap", teal_bob: "teal_bob", teal_garden: "teal_bob",
  };

  function renderCatalogThumbnailCanvases() {
    document.querySelectorAll("canvas[data-preset-thumb]").forEach((thumbnail) => {
      const target = thumbnail.getContext("2d");
      target.clearRect(0, 0, thumbnail.width, thumbnail.height);
      target.imageSmoothingEnabled = true;
      const preset = thumbnail.dataset.presetThumb;
      if (preset === "custom") {
        target.font = "42px sans-serif";
        target.textAlign = "center";
        target.fillText("🧩", 48, 64);
        return;
      }
      if (preset === "sprout") {
        drawAtlasCell(target, basicWalkAtlas, 0, 4, 4, 11, 5, 74, 88);
        return;
      }
      const atlas = presetSpriteAtlases[preset];
      if (atlas) {
        const crop = thumbnail.dataset.presetCrop;
        if (crop === "head") target.drawImage(atlas.image, 0, 0, 224, 166, 9, 4, 78, 91);
        else if (crop === "body") target.drawImage(atlas.image, 0, 136, 224, 152, 9, 5, 78, 88);
        else drawAtlasCell(target, atlas.image, 0, 4, atlas.rows, 9, 5, 78, 88);
      }
    });
    document.querySelectorAll("canvas[data-avatar-thumb]").forEach((thumbnail) => {
      const target = thumbnail.getContext("2d");
      target.clearRect(0, 0, thumbnail.width, thumbnail.height);
      target.imageSmoothingEnabled = true;
      if (!avatarSpriteAtlas.complete || !avatarSpriteAtlas.naturalWidth) return;
      const index = Number(thumbnail.dataset.avatarThumb);
      const cellWidth = avatarSpriteAtlas.naturalWidth / 4;
      const cellHeight = avatarSpriteAtlas.naturalHeight / 3;
      const column = index % 4;
      const row = Math.floor(index / 4);
      const headOnly = thumbnail.dataset.avatarCrop === "head";
      const sx = column * cellWidth + cellWidth * (headOnly ? .2 : .08);
      const sy = row * cellHeight + cellHeight * (headOnly ? .01 : .035);
      const sw = cellWidth * (headOnly ? .6 : .84);
      const sh = cellHeight * (headOnly ? .56 : .92);
      const dx = headOnly ? 11 : 8;
      const dy = headOnly ? 8 : 5;
      const dw = headOnly ? 74 : 80;
      const dh = headOnly ? 78 : 88;
      target.drawImage(avatarSpriteAtlas, sx, sy, sw, sh, dx, dy, dw, dh);
    });
    document.querySelectorAll("canvas[data-cosmetic-thumb]").forEach((thumbnail) => {
      const target = thumbnail.getContext("2d");
      target.clearRect(0, 0, thumbnail.width, thumbnail.height);
      target.imageSmoothingEnabled = true;
      drawAtlasCell(target, cosmeticSpriteAtlas, Number(thumbnail.dataset.cosmeticThumb), 5, 4, 8, 8, 80, 80);
    });
    document.querySelectorAll("canvas[data-cat-thumb]").forEach((thumbnail) => {
      const target = thumbnail.getContext("2d");
      target.clearRect(0, 0, thumbnail.width, thumbnail.height);
      target.imageSmoothingEnabled = true;
      drawAtlasCell(target, catPetAtlas, Number(thumbnail.dataset.catThumb), 2, 1, 7, 7, 82, 82);
    });
  }

  function drawLayeredAvatarPreview(target, cosmetics) {
    const rect = (x, y, width, height, color) => {
      target.fillStyle = color;
      target.fillRect(Math.round(x), Math.round(y), Math.round(width), Math.round(height));
    };
    const skin = avatarCatalog.skin.find((item) => item.id === cosmetics.skin)?.color || "#f2bd92";
    const skinShadow = cosmetics.skin === "deep" ? "#6d392f" : cosmetics.skin === "warm" ? "#a7654f" : "#d99978";
    const hairColor = { soft: "#4b2f24", wave: "#3b2b34", crop: "#263b43", twin: "#54313e", silver: "#8992a4", orange: "#bd6236" }[cosmetics.hair] || "#4b2f24";
    const outfit = {
      forest: ["#255c3d", "#f5e4bd"], denim: ["#35688f", "#c8e3f8"], carrot: ["#d65d25", "#ffe078"],
      moon: ["#424b7d", "#d9e3ff"], berry: ["#9e3d68", "#ffd2df"], yellow: ["#d9a51f", "#fff1a8"],
      violet: ["#60439e", "#d8c8ff"], black: ["#252a36", "#9da6bc"],
    }[cosmetics.outfit] || ["#255c3d", "#f5e4bd"];
    target.fillStyle = "rgba(36,48,45,.13)";
    target.beginPath(); target.ellipse(140, 252, 57, 13, 0, 0, Math.PI * 2); target.fill();
    rect(103, 107, 74, 69, "#2c241f");
    rect(108, 112, 64, 61, skinShadow); rect(112, 114, 56, 57, skin);
    if (cosmetics.hair === "crop") {
      rect(104, 97, 72, 25, hairColor); rect(106, 113, 12, 27, hairColor);
    } else if (cosmetics.hair === "twin") {
      rect(103, 94, 74, 27, hairColor); rect(91, 113, 18, 50, hairColor); rect(171, 113, 18, 50, hairColor);
    } else if (cosmetics.hair === "wave") {
      rect(101, 94, 78, 28, hairColor); rect(98, 111, 17, 72, hairColor); rect(165, 111, 17, 72, hairColor);
    } else {
      rect(102, 95, 76, 28, hairColor); rect(102, 112, 15, 38, hairColor); rect(165, 112, 15, 38, hairColor);
    }
    rect(112, 101, 26, 7, "rgba(255,255,255,.16)");
    rect(121, 138, 10, 10, "#fff"); rect(149, 138, 10, 10, "#fff");
    rect(124, 140, 5, 7, "#27352f"); rect(152, 140, 5, 7, "#27352f");
    if (cosmetics.face === "wink") rect(148, 143, 13, 3, "#27352f");
    if (["blush", "sparkle"].includes(cosmetics.face)) { rect(114, 153, 11, 5, "#ef8b98"); rect(155, 153, 11, 5, "#ef8b98"); }
    rect(cosmetics.face === "smile" ? 130 : 134, 157, cosmetics.face === "smile" ? 20 : 12, 4, cosmetics.face === "cool" ? "#635763" : "#b76067");
    rect(105, 174, 70, 55, "#173c2e"); rect(109, 178, 62, 47, outfit[0]);
    rect(119, 178, 42, 47, outfit[1]); rect(125, 178, 5, 47, outfit[0]); rect(151, 178, 5, 47, outfit[0]);
    rect(90, 179, 19, 44, outfit[0]); rect(171, 179, 19, 44, outfit[0]);
    rect(94, 217, 15, 13, skin); rect(171, 217, 15, 13, skin);
    rect(112, 225, 25, 27, "#594330"); rect(143, 225, 25, 27, "#594330");
    rect(108, 246, 31, 10, "#31271f"); rect(141, 246, 31, 10, "#31271f");
    if (cosmetics.accessory === "red_scarf") rect(105, 170, 70, 12, "#d93432");
    if (cosmetics.accessory === "sprout_hat") {
      rect(97, 91, 86, 14, "#347f3d"); rect(135, 71, 10, 22, "#216a34"); rect(143, 72, 20, 11, "#65b85d");
    }
    if (cosmetics.accessory === "carrot_bag") { rect(173, 187, 22, 37, "#b94f25"); rect(177, 191, 15, 29, "#ee7d32"); }
    if (["round_glasses", "star_glasses"].includes(cosmetics.accessory)) {
      target.strokeStyle = cosmetics.accessory === "star_glasses" ? "#e75e99" : "#354751"; target.lineWidth = 4;
      target.strokeRect(115, 134, 21, 18); target.strokeRect(144, 134, 21, 18); rect(136, 140, 8, 4, target.strokeStyle);
    }
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
    const previewPreset = avatarDraft.preset || "blue_cap";
    const previewAtlas = presetSpriteAtlases[previewPreset];
    const presetSources = Object.fromEntries(Object.entries(presetSpriteAtlases).map(([preset, atlas]) => [preset, atlas]));
    if (previewAtlas?.image.complete && previewAtlas.image.naturalWidth && window.CarrotAvatarCompositor) {
      window.CarrotAvatarCompositor.drawFrame(previewContext, presetSources, {
        preset: previewPreset,
        hairPreset: stylePresetByItem[avatarDraft.hair] || previewPreset,
        outfitPreset: stylePresetByItem[avatarDraft.outfit] || previewPreset,
        direction: "down", mounted: false, moving: false, frame: 0,
        accessory: avatarDraft.accessory, hat: avatarDraft.hat, glasses: avatarDraft.glasses,
      }, { x: 58, y: 24, width: 164, height: 224 });
    } else if (basicWalkAtlas.complete && basicWalkAtlas.naturalWidth) {
      drawAtlasCell(previewContext, basicWalkAtlas, 0, 4, 4, 66, 42, 148, 205);
    } else {
      drawLayeredAvatarPreview(previewContext, avatarDraft);
    }
    const effectIndex = cosmeticSpriteIndex("effect", avatarDraft.effect);
    drawAtlasCell(previewContext, cosmeticSpriteAtlas, effectIndex, 5, 4, 16, 50, 80, 80);
    const vehicleIndex = cosmeticSpriteIndex("vehicle", avatarDraft.vehicle);
    drawAtlasCell(previewContext, cosmeticSpriteAtlas, vehicleIndex, 5, 4, 18, 213, 82, 65);
    const petIndex = cosmeticSpriteIndex("pet", avatarDraft.pet);
    const catIndex = catPetSpriteIndex(avatarDraft.pet);
    if (!drawAtlasCell(previewContext, catPetAtlas, catIndex, 2, 1, 178, 188, 100, 100)) {
      drawAtlasCell(previewContext, cosmeticSpriteAtlas, petIndex, 5, 4, 190, 205, 72, 72);
    }
    const speechIndex = cosmeticSpriteIndex("speech", avatarDraft.speech);
    if (drawAtlasCell(previewContext, cosmeticSpriteAtlas, speechIndex, 5, 4, 175, 8, 96, 70)) {
      previewContext.textAlign = "center"; previewContext.font = "bold 9px sans-serif"; previewContext.fillStyle = "#30323b";
      previewContext.fillText(avatarDraft.speech === "cat" ? "안녕하세요!" : avatarDraft.speech === "leaf" ? "오늘도 한 걸음" : "같이 걸어요", 223, 42);
    }
  }

  function drawPreviewAccessoryOverlay(target, accessory) {
    if (accessory === "none") return;
    const rect = (x, y, width, height, color) => {
      target.fillStyle = color;
      target.fillRect(x, y, width, height);
    };
    if (accessory === "red_scarf") rect(108, 160, 64, 12, "#d93432");
    if (accessory === "sprout_hat") {
      rect(100, 83, 80, 13, "#347f3d"); rect(134, 63, 11, 22, "#216a34"); rect(143, 64, 20, 10, "#65b85d");
    }
    if (accessory === "carrot_bag") { rect(174, 177, 24, 40, "#b94f25"); rect(179, 182, 14, 29, "#ee7d32"); }
    if (["round_glasses", "star_glasses"].includes(accessory)) {
      const color = accessory === "star_glasses" ? "#e75e99" : "#354751";
      target.strokeStyle = color; target.lineWidth = 4;
      target.strokeRect(112, 119, 24, 19); target.strokeRect(144, 119, 24, 19); rect(136, 126, 8, 4, color);
    }
  }

  function renderAvatarStudio() {
    $("#avatar-category-nav").innerHTML = avatarCategories.map((category) => `<button class="avatar-category-button" type="button" data-avatar-category="${category.id}" aria-pressed="${activeAvatarCategory === category.id}"><span aria-hidden="true">${category.icon}</span>${category.label}</button>`).join("");
    const category = avatarCategories.find((entry) => entry.id === activeAvatarCategory);
    const items = ["hair", "outfit"].includes(activeAvatarCategory)
      ? avatarCatalog[activeAvatarCategory].filter((item) => stylePresetByItem[item.id])
      : avatarCatalog[activeAvatarCategory];
    $("#avatar-category-title").textContent = category.label;
    $("#avatar-item-count").textContent = `${items.length}개`;
    $("#avatar-item-grid").innerHTML = items.map((item) => {
      const cosmeticIndex = cosmeticSpriteIndex(activeAvatarCategory, item.id);
      const catIndex = activeAvatarCategory === "pet" ? catPetSpriteIndex(item.id) : null;
      let visual;
      if (activeAvatarCategory === "preset") {
        visual = `<canvas class="item-visual catalog-thumb" width="96" height="96" data-preset-thumb="${item.id}" aria-hidden="true"></canvas>`;
      } else if (["hair", "outfit"].includes(activeAvatarCategory)) {
        visual = `<canvas class="item-visual catalog-thumb" width="96" height="96" data-preset-thumb="${stylePresetByItem[item.id]}" data-preset-crop="${activeAvatarCategory === "hair" ? "head" : "body"}" aria-hidden="true"></canvas>`;
      } else if (["face", "accessory"].includes(activeAvatarCategory)) {
        const itemPreset = stylePresetByItem[item.id];
        const index = avatarThumbnailIndexes[activeAvatarCategory][item.id];
        visual = itemPreset
          ? `<canvas class="item-visual catalog-thumb" width="96" height="96" data-preset-thumb="${itemPreset}" aria-hidden="true"></canvas>`
          : index == null
            ? '<span class="item-visual empty-sprite-thumb" aria-hidden="true">없음</span>'
            : `<canvas class="item-visual catalog-thumb" width="96" height="96" data-avatar-thumb="${index}" data-avatar-crop="${["hair", "face", "accessory"].includes(activeAvatarCategory) ? "head" : "body"}" aria-hidden="true"></canvas>`;
      } else if (catIndex != null) {
        visual = `<canvas class="item-visual catalog-thumb" width="96" height="96" data-cat-thumb="${catIndex}" aria-hidden="true"></canvas>`;
      } else if (cosmeticIndex != null) {
        visual = `<canvas class="item-visual catalog-thumb" width="96" height="96" data-cosmetic-thumb="${cosmeticIndex}" aria-hidden="true"></canvas>`;
      } else {
        visual = `<span class="item-visual" aria-hidden="true">${item.visual || "—"}</span>`;
      }
      const selected = avatarDraft[activeAvatarCategory] === item.id;
      return `<button class="avatar-item-card" type="button" data-avatar-item="${item.id}" aria-pressed="${selected}">${item.isNew ? '<span class="new-badge">N</span>' : ""}${visual}<span class="item-name">${item.name}</span><small>${selected ? "선택됨" : "보유 아이템"}</small></button>`;
    }).join("");
    $("#preview-carrot-balance").textContent = state.carrots;
    $("#avatar-preview-name").textContent = state.avatar.name;
    $("#avatar-selection-name").textContent = selectedAvatarItem(activeAvatarCategory).name;
    $("#avatar-undo").disabled = avatarDraftHistory.length === 0;
    renderCatalogThumbnailCanvases();
    renderAvatarPreview();
    window.dispatchEvent(new CustomEvent("forest-avatar-draft", { detail: avatarDraft }));
  }

  function openAvatarStudio() {
    avatarDraft = { ...defaultCosmetics, ...(state.avatar.cosmetics || {}), preset: state.avatar.preset || "blue_cap" };
    avatarDraftHistory = [];
    activeAvatarCategory = "preset";
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
    if (presetBundles[state.avatar.preset]) {
      state.avatar.cosmetics = { ...state.avatar.cosmetics, ...presetBundles[state.avatar.preset] };
      state.avatar.equipped = null;
    }
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
    const linkedPreset = activeAvatarCategory === "preset" ? button.dataset.avatarItem : null;
    if (linkedPreset && presetBundles[linkedPreset]) {
      avatarDraft = { ...avatarDraft, preset: linkedPreset, ...presetBundles[linkedPreset] };
    }
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
    state.avatar.preset = avatarDraft.preset || state.avatar.preset;
    const { preset: _preset, ...savedCosmetics } = avatarDraft;
    state.avatar.cosmetics = { ...savedCosmetics };
    state.avatar.equipped = avatarDraft.accessory === "none" ? null : avatarDraft.accessory;
    $("#avatar-preset").value = state.avatar.preset;
    renderInventory();
    renderCanvas();
    window.dispatchEvent(new CustomEvent("forest-avatar-updated", { detail: state.avatar }));
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
      if (currentScene === "home") {
        if (x >= 155 && x <= 440 && y >= 120 && y <= 285) interact("sofa");
        else if (x >= 480 && x <= 670 && y >= 55 && y <= 260) interact("wardrobe");
        else if (x >= 330 && x <= 440 && y >= 380) interact("exit_home");
        else setStatus("소파·옷장·현관문을 클릭하거나 가까이에서 Q를 눌러 보세요.");
      } else if (currentScene === "garden") {
        if ((x >= 75 && x <= 320 && y >= 90 && y <= 380) || (x >= 455 && x <= 700 && y >= 90 && y <= 410)) interact("crops");
        else if (x >= 330 && x <= 445 && y >= 370) interact("exit_garden");
        else setStatus("당근밭이나 출구를 클릭하거나 가까이에서 Q를 눌러 보세요.");
      } else if (x >= 45 && x <= 335 && y >= 45 && y <= 300) interact("home");
      else if (x >= 460 && x <= 735 && y >= 45 && y <= 290) interact("garden");
      else if (x >= 15 && x <= 330 && y >= 285 && y <= 500) interact("pond");
      else if (x >= 440 && x <= 505 && y >= 345 && y <= 410) interact("vehicle");
      else setStatus("집·당근밭·연못·스쿠터를 클릭하거나 가까이에서 Q를 눌러 보세요.");
      return;
    }
    if (currentScene !== "world") { setStatus("숲 오브젝트는 월드 장면에서만 배치할 수 있어요."); return; }
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
    if (currentScene !== "world") { setStatus("탈것은 숲 월드에서 이용할 수 있어요."); return; }
    if (!state.avatar.mounted && requireNearby && distanceTo(470, 376) >= 72) {
      setStatus("숲 스쿠터 가까이 이동한 뒤 E를 눌러 주세요.");
      return;
    }
    state.avatar.mounted = !state.avatar.mounted;
    state.avatar.sitting = false;
    walkingUntil = 0;
    walkAnimationFrame = 0;
    if (!state.avatar.mounted) { state.avatar.x = 470; state.avatar.y = 410; }
    renderCanvas();
    await persist(state.avatar.mounted ? "숲 스쿠터에 탔습니다. 이동 속도가 빨라졌어요." : "숲 스쿠터에서 내렸습니다.");
  }

  let phaserPersistTimer = null;
  window.addEventListener("forest-phaser-position", (event) => {
    const detail = event.detail || {};
    if (!Number.isFinite(detail.x) || !Number.isFinite(detail.y)) return;
    state.avatar.x = detail.x;
    state.avatar.y = detail.y;
    if (detail.direction) state.avatar.direction = detail.direction;
    $("#avatar-coordinate").textContent = `X ${Math.round(detail.x)} · Y ${Math.round(detail.y)}`;
    updateInteractionPrompt();
    window.clearTimeout(phaserPersistTimer);
    phaserPersistTimer = window.setTimeout(() => adapter.save(state), 240);
  });
  window.addEventListener("forest-phaser-interact", () => interact());
  window.addEventListener("forest-phaser-action", async (event) => {
    if (event.detail === "chat") toggleChat();
    if (event.detail === "sit") await toggleSit();
    if (event.detail === "ride") await toggleRide();
  });

  document.addEventListener("keydown", (event) => {
    if (["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(document.activeElement?.tagName)) return;
    if (window.carrotForestPhaserActive) return;
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
    if (window.carrotForestPhaserActive) return;
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
    const positions = { world: [384, 352], home: [384, 410], garden: [384, 410] };
    [state.avatar.x, state.avatar.y] = positions[currentScene];
    renderCanvas();
    await persist("아바타를 시작 위치로 이동했습니다.");
    canvas.focus();
  });

  $("#world-dialog-close").addEventListener("click", () => $("#world-dialog").close());
  $("#world-dialog-actions").addEventListener("click", async (event) => {
    const action = event.target.closest("[data-world-action]")?.dataset.worldAction;
    if (!action) return;
    if (action === "enter_home") {
      $("#world-dialog").close();
      switchScene("home");
      await persist("우리 집 안으로 들어왔습니다. 소파와 옷장을 이용해 보세요.");
    }
    if (action === "enter_garden") {
      $("#world-dialog").close();
      switchScene("garden");
      await persist("공동 당근밭 안으로 들어왔습니다. 당근 가까이에서 물을 줄 수 있어요.");
    }
    if (action === "exit_scene") {
      $("#world-dialog").close();
      switchScene("world");
      await persist("우리의 작은 숲으로 돌아왔습니다.");
    }
    if (action === "rest") {
      currentScene = "home";
      state.avatar.x = 292;
      state.avatar.y = 232;
      state.avatar.sitting = true;
      state.avatar.mounted = false;
      state.fishing = false;
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
      renderCanvas();
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
    if (action === "fish") {
      const firstCatch = !state.fishCaught;
      currentScene = "world";
      state.avatar.x = 305;
      state.avatar.y = 390;
      state.avatar.sitting = true;
      state.avatar.mounted = false;
      state.fishing = true;
      state.fishCaught = true;
      if (firstCatch) state.carrots += 5;
      $("#carrot-balance").textContent = state.carrots;
      $("#world-dialog").close();
      renderCanvas();
      await persist(firstCatch ? "은빛 붕어를 잡고 당근 5개를 받았습니다!" : "연못에 낚싯대를 드리우고 잠시 쉬고 있어요.");
    }
  });

  $("#scene-exit").addEventListener("click", async () => {
    if (currentScene === "world") return;
    switchScene("world");
    await persist("우리의 작은 숲으로 돌아왔습니다.");
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

  const localDemoOrigin = ["127.0.0.1", "localhost"].includes(window.location.hostname);
  if ("serviceWorker" in navigator && !localDemoOrigin) {
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
