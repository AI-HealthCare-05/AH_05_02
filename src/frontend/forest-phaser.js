(() => {
  "use strict";

  if (!window.Phaser || !document.getElementById("phaser-world")) return;

  const STORAGE_KEY = "gandang-carrot-forest-demo-v1";
  const WORLD = { width: 768, height: 512 };
  const directionRows = { up: 0, left: 1, down: 2, right: 3 };
  const assetRoot = "/static/assets/lpc/";
  const defaultCosmetics = {
    skin: "peach", outfit: "forest", bottom: "cream", shoes: "brown", hair: "soft",
    hat: "none", glasses: "none", face: "calm", accessory: "none",
  };
  const skinTints = { peach: 0xf2bd92, rose: 0xeaa68e, warm: 0xc98263, deep: 0x89503e, olive: 0xa87f63, porcelain: 0xf5cbb4 };
  const topStyles = {
    forest: ["polo", 0x315f42], denim: ["long", 0x3f6c96], carrot: ["vneck", 0xe9752f], moon: ["long", 0x34395f],
    berry: ["long", 0xa94670], yellow: ["long", 0xe6b927], violet: ["vneck", 0x594488], black: ["long", 0x24262f],
    navy_garden: ["vneck", 0x26395f], cow_vest: ["vneck", 0xc65b2c], blue_overalls: ["polo", 0x315d8f], teal_garden: ["vneck", 0x288c83],
  };
  const bottomTints = { cream: 0xe8dcc0, denim: 0x496e96, charcoal: 0x333944, olive: 0x66734c, plum: 0x704c68 };
  const shoeTints = { brown: 0x62422f, white: 0xe7e2d6, black: 0x24252a, orange: 0xbd5d25 };
  const hairStyles = {
    soft: ["messy", 0x4b2f24], wave: ["long", 0x6a3c2c], crop: ["pixie", 0x3f2d28], twin: ["ponytail", 0x55332b],
    silver: ["bob", 0x9aa1ae], orange: ["spiked", 0xb85b2f], red_wave: ["long", 0xb84f31], cow_brown: ["bob", 0x6e452f],
    midnight: ["messy", 0x25283a], blue_short: ["pixie", 0x294967], teal_bob: ["bob", 0x684737],
  };
  const hatStyles = { cap: "hat-cap", headband: "hat-headband" };
  const glassesStyles = { round: "glasses-round", sun: "glasses-sun", round_glasses: "glasses-round", star_glasses: "glasses-sun" };

  function storedState() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch { return {}; }
  }

  function normalizedAvatar(source = {}) {
    return {
      name: source.name || "세준", gender: source.gender === "male" ? "male" : "female",
      x: Number.isFinite(source.x) ? source.x : 384, y: Number.isFinite(source.y) ? source.y : 352,
      direction: directionRows[source.direction] == null ? "down" : source.direction,
      mounted: Boolean(source.mounted), sitting: Boolean(source.sitting),
      cosmetics: { ...defaultCosmetics, ...(source.cosmetics || {}) },
    };
  }

  class ForestScene extends Phaser.Scene {
    constructor() {
      super("forest-world");
      this.avatar = normalizedAvatar(storedState().avatar);
      this.sceneName = "world";
      this.layers = [];
      this.lastPersist = 0;
      this.forcedDirection = null;
      this.forcedUntil = 0;
    }

    preload() {
      this.load.image("world-bg", "/static/assets/carrot-forest-world-v2.png");
      this.load.image("home-bg", "/static/assets/carrot-forest-home-v1.png");
      this.load.image("garden-bg", "/static/assets/carrot-forest-garden-v1.png");
      ["male", "female"].forEach((gender) => {
        this.load.spritesheet(`body-${gender}`, `${assetRoot}body-${gender}.png`, { frameWidth: 64, frameHeight: 64 });
        this.load.spritesheet(`pants-${gender}`, `${assetRoot}pants-${gender}.png`, { frameWidth: 64, frameHeight: 64 });
        this.load.spritesheet(`shoes-${gender}`, `${assetRoot}shoes-${gender}.png`, { frameWidth: 64, frameHeight: 64 });
        ["long", "polo", "vneck"].forEach((style) => this.load.spritesheet(`top-${style}-${gender}`, `${assetRoot}top-${style}-${gender}.png`, { frameWidth: 64, frameHeight: 64 }));
      });
      ["bob", "long", "messy", "pixie", "spiked"].forEach((style) => this.load.spritesheet(`hair-${style}`, `${assetRoot}hair-${style}.png`, { frameWidth: 64, frameHeight: 64 }));
      this.load.spritesheet("hair-ponytail-bg", `${assetRoot}hair-ponytail-bg.png`, { frameWidth: 64, frameHeight: 64 });
      this.load.spritesheet("hair-ponytail-fg", `${assetRoot}hair-ponytail-fg.png`, { frameWidth: 64, frameHeight: 64 });
      ["hat-cap", "hat-headband", "glasses-round", "glasses-sun"].forEach((key) => this.load.spritesheet(key, `${assetRoot}${key}.png`, { frameWidth: 64, frameHeight: 64 }));
      this.load.spritesheet("cat-pets", "/static/assets/carrot-forest-cat-pets-v1.png", { frameWidth: 887, frameHeight: 887 });
    }

    create() {
      this.background = this.add.image(WORLD.width / 2, WORLD.height / 2, "world-bg").setDisplaySize(WORLD.width, WORLD.height);
      this.shadow = this.add.ellipse(0, 16, 42, 15, 0x16382a, 0.25);
      this.player = this.add.container(this.avatar.x, this.avatar.y);
      this.player.add(this.shadow);
      this.vehicle = this.makeVehicle();
      this.player.add(this.vehicle);
      this.pet = this.add.sprite(39, 12, "cat-pets", 0).setOrigin(0.5, 1).setScale(0.057).setDepth(1);
      this.player.add(this.pet);
      this.nameplate = this.add.text(0, -50, this.avatar.name, {
        fontFamily: "Pretendard, Noto Sans KR, sans-serif", fontSize: "12px", fontStyle: "bold",
        color: "#173528", backgroundColor: "rgba(255,255,255,.92)", padding: { x: 7, y: 3 },
      }).setOrigin(0.5).setStroke("#ffffff", 2);
      this.player.add(this.nameplate);
      this.rebuildAvatar();
      this.keys = this.input.keyboard.addKeys("W,A,S,D,R,Q,C,X,E");
      this.cursors = this.input.keyboard.createCursorKeys();
      this.input.keyboard.on("keydown-Q", () => window.dispatchEvent(new CustomEvent("forest-phaser-interact")));
      this.input.keyboard.on("keydown-C", () => window.dispatchEvent(new CustomEvent("forest-phaser-action", { detail: "chat" })));
      this.input.keyboard.on("keydown-X", () => window.dispatchEvent(new CustomEvent("forest-phaser-action", { detail: "sit" })));
      this.input.keyboard.on("keydown-E", () => window.dispatchEvent(new CustomEvent("forest-phaser-action", { detail: "ride" })));
      this.events.on("shutdown", () => this.detachWindowEvents());
      this.attachWindowEvents();
      document.documentElement.classList.add("phaser-world-ready");
      window.carrotForestPhaserActive = true;
      window.carrotForestPhaserMove = (direction) => this.nudge(direction);
      this.input.once("pointerdown", () => document.getElementById("phaser-world")?.focus());
      this.renderPreview(this.avatar.cosmetics);
      this.emitPosition(true);
    }

    makeVehicle() {
      const graphics = this.add.graphics();
      graphics.fillStyle(0x29323a).fillCircle(-18, 18, 7).fillCircle(20, 18, 7);
      graphics.fillStyle(0xe87924).fillRoundedRect(-24, 8, 48, 7, 3).fillRoundedRect(17, -17, 5, 29, 2);
      graphics.lineStyle(4, 0xf29a42).lineBetween(20, -16, 29, -16);
      graphics.setVisible(this.avatar.mounted).setDepth(1);
      return graphics;
    }

    sprite(key, tint = null) {
      const sprite = this.add.sprite(0, 0, key, directionRows[this.avatar.direction] * 9).setOrigin(0.5, 0.82).setScale(1.36);
      if (tint != null) sprite.setTint(tint);
      this.player.add(sprite);
      this.layers.push(sprite);
      return sprite;
    }

    rebuildAvatar() {
      this.layers.forEach((layer) => layer.destroy());
      this.layers = [];
      const c = this.avatar.cosmetics;
      const gender = this.avatar.gender;
      const [hairStyle, hairTint] = hairStyles[c.hair] || hairStyles.soft;
      const [topStyle, topTint] = topStyles[c.outfit] || topStyles.forest;
      if (hairStyle === "ponytail") this.sprite("hair-ponytail-bg", hairTint);
      this.sprite(`body-${gender}`, skinTints[c.skin] || skinTints.peach);
      this.sprite(`pants-${gender}`, bottomTints[c.bottom] || bottomTints.cream);
      this.sprite(`shoes-${gender}`, shoeTints[c.shoes] || shoeTints.brown);
      this.sprite(`top-${topStyle}-${gender}`, topTint);
      this.sprite(hairStyle === "ponytail" ? "hair-ponytail-fg" : `hair-${hairStyle}`, hairTint);
      const hatKey = hatStyles[c.hat] || (c.accessory === "sprout_hat" ? "hat-headband" : null);
      const glassesKey = glassesStyles[c.glasses] || glassesStyles[c.accessory];
      if (hatKey) this.sprite(hatKey, c.hat === "cap" ? 0x4672a5 : 0xd15454);
      if (glassesKey) this.sprite(glassesKey);
      this.layers.forEach((layer, index) => layer.setDepth(2 + index));
      this.nameplate?.setDepth(30).setText(this.avatar.name);
      this.vehicle?.setVisible(this.avatar.mounted);
      const pet = c.pet;
      this.pet?.setVisible(["cat", "blue_eyes_white_cat", "gold_eyes_orange_cat"].includes(pet));
      this.pet?.setFrame(pet === "gold_eyes_orange_cat" ? 1 : 0);
    }

    attachWindowEvents() {
      this.onAvatar = (event) => { this.avatar = normalizedAvatar({ ...this.avatar, ...(event.detail || {}) }); this.rebuildAvatar(); this.renderPreview(this.avatar.cosmetics); };
      this.onDraft = (event) => this.renderPreview({ ...this.avatar.cosmetics, ...(event.detail || {}) });
      this.onState = (event) => {
        const detail = event.detail || {};
        if (detail.avatar) { this.avatar = normalizedAvatar(detail.avatar); this.player.setPosition(this.avatar.x, this.avatar.y); this.rebuildAvatar(); }
        if (detail.scene) this.setScene(detail.scene);
      };
      window.addEventListener("forest-avatar-updated", this.onAvatar);
      window.addEventListener("forest-avatar-draft", this.onDraft);
      window.addEventListener("forest-state-updated", this.onState);
    }

    detachWindowEvents() {
      window.removeEventListener("forest-avatar-updated", this.onAvatar);
      window.removeEventListener("forest-avatar-draft", this.onDraft);
      window.removeEventListener("forest-state-updated", this.onState);
    }

    setScene(sceneName) {
      this.sceneName = ["world", "home", "garden"].includes(sceneName) ? sceneName : "world";
      this.background.setTexture(`${this.sceneName}-bg`).setDisplaySize(WORLD.width, WORLD.height);
    }

    nudge(direction) {
      this.forcedDirection = directionRows[direction] == null ? null : direction;
      this.forcedUntil = performance.now() + 170;
      document.getElementById("phaser-world")?.focus();
    }

    isBlocked(x, y) {
      if (x < 28 || x > WORLD.width - 28 || y < 42 || y > WORLD.height - 32) return true;
      if (this.sceneName === "home") return x < 64 || x > 710 || y < 100 || y > 458;
      if (this.sceneName === "garden") return x < 105 || x > 675 || y < 105 || y > 458;
      return (x > 45 && x < 335 && y > 55 && y < 275) || (x > 465 && x < 735 && y > 45 && y < 255) || (x > 35 && x < 270 && y > 300 && y < 475);
    }

    emitPosition(force = false) {
      const now = performance.now();
      if (!force && now - this.lastPersist < 180) return;
      this.lastPersist = now;
      window.dispatchEvent(new CustomEvent("forest-phaser-position", { detail: { x: this.avatar.x, y: this.avatar.y, direction: this.avatar.direction } }));
    }

    update(time, delta) {
      const inputAllowed = !["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(document.activeElement?.tagName);
      let direction = performance.now() < this.forcedUntil ? this.forcedDirection : null;
      if (inputAllowed) {
        if (this.cursors.left.isDown || this.keys.A.isDown) direction = "left";
        else if (this.cursors.right.isDown || this.keys.D.isDown) direction = "right";
        else if (this.cursors.up.isDown || this.keys.W.isDown) direction = "up";
        else if (this.cursors.down.isDown || this.keys.S.isDown) direction = "down";
      }
      const running = inputAllowed && this.keys.R.isDown;
      if (!direction) {
        const idle = directionRows[this.avatar.direction] * 9;
        this.layers.forEach((layer) => layer.setFrame(idle));
        return;
      }
      const speed = this.avatar.mounted ? 185 : running ? 150 : 92;
      const distance = speed * Math.min(delta, 40) / 1000;
      const vector = { left: [-distance, 0], right: [distance, 0], up: [0, -distance], down: [0, distance] }[direction];
      const nextX = this.avatar.x + vector[0];
      const nextY = this.avatar.y + vector[1];
      this.avatar.direction = direction;
      if (!this.isBlocked(nextX, nextY)) {
        this.avatar.x = nextX; this.avatar.y = nextY;
        this.player.setPosition(nextX, nextY).setDepth(nextY);
      }
      const row = directionRows[direction];
      const rate = this.avatar.mounted || running ? 70 : 105;
      const frame = row * 9 + 1 + Math.floor(time / rate) % 8;
      this.layers.forEach((layer) => layer.setFrame(frame));
      this.emitPosition();
    }

    drawAvatarCanvas(canvas, cosmetics, sizeOverride = null) {
      if (!canvas || !this.textures) return;
      const target = canvas.getContext("2d");
      target.clearRect(0, 0, canvas.width, canvas.height);
      const avatar = normalizedAvatar({ ...this.avatar, cosmetics: { ...this.avatar.cosmetics, ...cosmetics } });
      const c = avatar.cosmetics;
      const [hairStyle, hairTint] = hairStyles[c.hair] || hairStyles.soft;
      const [topStyle, topTint] = topStyles[c.outfit] || topStyles.forest;
      const layers = [];
      if (hairStyle === "ponytail") layers.push(["hair-ponytail-bg", hairTint]);
      layers.push([`body-${avatar.gender}`, skinTints[c.skin] || skinTints.peach]);
      layers.push([`pants-${avatar.gender}`, bottomTints[c.bottom] || bottomTints.cream]);
      layers.push([`shoes-${avatar.gender}`, shoeTints[c.shoes] || shoeTints.brown]);
      layers.push([`top-${topStyle}-${avatar.gender}`, topTint]);
      layers.push([hairStyle === "ponytail" ? "hair-ponytail-fg" : `hair-${hairStyle}`, hairTint]);
      const hatKey = hatStyles[c.hat] || (c.accessory === "sprout_hat" ? "hat-headband" : null);
      const glassesKey = glassesStyles[c.glasses] || glassesStyles[c.accessory];
      if (hatKey) layers.push([hatKey, c.hat === "cap" ? 0x4672a5 : 0xd15454]);
      if (glassesKey) layers.push([glassesKey, null]);
      const size = sizeOverride || 300, x = (canvas.width - size) / 2, y = (canvas.height - size) / 2 - (sizeOverride ? 0 : 8);
      layers.forEach(([key, tint]) => {
        const image = this.textures.get(key)?.getSourceImage();
        if (!image) return;
        const buffer = document.createElement("canvas"); buffer.width = 64; buffer.height = 64;
        const bx = buffer.getContext("2d"); bx.imageSmoothingEnabled = false;
        bx.drawImage(image, 0, 128, 64, 64, 0, 0, 64, 64);
        if (tint != null) {
          bx.globalCompositeOperation = "source-atop";
          bx.fillStyle = `#${tint.toString(16).padStart(6, "0")}`;
          bx.globalAlpha = .72; bx.fillRect(0, 0, 64, 64); bx.globalAlpha = 1; bx.globalCompositeOperation = "source-over";
        }
        target.imageSmoothingEnabled = false;
        target.drawImage(buffer, x, y, size, size);
      });
    }

    renderPreview(cosmetics) {
      this.drawAvatarCanvas(document.getElementById("avatar-preview-canvas"), cosmetics);
      document.querySelectorAll("canvas[data-lpc-item-category]").forEach((canvas) => {
        const category = canvas.dataset.lpcItemCategory;
        const item = canvas.dataset.lpcItemId;
        this.drawAvatarCanvas(canvas, { ...cosmetics, [category]: item }, 88);
      });
    }
  }

  const game = new Phaser.Game({
    type: Phaser.AUTO,
    parent: "phaser-world",
    width: WORLD.width,
    height: WORLD.height,
    backgroundColor: "#78b96a",
    pixelArt: true,
    roundPixels: true,
    render: { antialias: false, pixelArt: true, roundPixels: true },
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
    scene: ForestScene,
  });
  window.carrotForestPhaserGame = game;
})();
