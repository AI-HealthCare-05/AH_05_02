(() => {
  "use strict";

  if (!window.Phaser || !document.getElementById("phaser-world")) return;

  const STORAGE_KEY = "gandang-carrot-forest-demo-v1";
  const WORLD = { width: 768, height: 512 };
  const AVATAR_RENDER_SCALE = 0.43;
  const NAMEPLATE_Y = -126;
  const directionRows = { down: 0, up: 1, left: 2, right: 3 };
  const premiumPresets = {
    red_bow: { path: "/static/assets/carrot-forest-avatar-red_bow-normalized-v2.png", rows: 6 },
    cow_hood: { path: "/static/assets/carrot-forest-avatar-cow_hood-normalized-v2.png", rows: 5 },
    midnight: { path: "/static/assets/carrot-forest-avatar-midnight-normalized-v2.png", rows: 6 },
    blue_cap: { path: "/static/assets/carrot-forest-avatar-blue_cap-normalized-v2.png", rows: 6 },
    teal_bob: { path: "/static/assets/carrot-forest-avatar-teal_bob-normalized-v2.png", rows: 6 },
  };
  const defaultCosmetics = {
    skin: "peach", outfit: "forest", bottom: "cream", shoes: "brown", hair: "soft",
    hat: "none", glasses: "none", face: "calm", accessory: "none",
  };
  const defaultTuning = { headOffsetY: -6, outfitOffsetY: 0, glassesOffsetY: 0, worldScale: AVATAR_RENDER_SCALE };
  const hairPresetByStyle = {
    red_wave: "red_bow", cow_brown: "cow_hood", midnight: "midnight",
    blue_short: "blue_cap", teal_bob: "teal_bob",
  };
  const outfitPresetByStyle = {
    navy_garden: "red_bow", cow_vest: "cow_hood", violet: "midnight",
    blue_overalls: "blue_cap", teal_garden: "teal_bob",
  };

  function storedState() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch { return {}; }
  }

  function normalizedAvatar(source = {}) {
    return {
      name: source.name || "세준", gender: source.gender === "male" ? "male" : "female",
      preset: premiumPresets[source.preset] ? source.preset : "blue_cap",
      x: Number.isFinite(source.x) ? source.x : 384, y: Number.isFinite(source.y) ? source.y : 352,
      direction: directionRows[source.direction] == null ? "down" : source.direction,
      mounted: Boolean(source.mounted), sitting: Boolean(source.sitting),
      cosmetics: { ...defaultCosmetics, ...(source.cosmetics || {}) },
      tuning: { ...defaultTuning, ...(source.tuning || {}) },
    };
  }

  class ForestScene extends Phaser.Scene {
    constructor() {
      super("forest-world");
      this.avatar = normalizedAvatar(storedState().avatar);
      this.sceneName = "world";
      this.lastPersist = 0;
      this.forcedDirection = null;
      this.forcedUntil = 0;
      this.mountTransitioning = false;
    }

    preload() {
      this.load.image("world-bg", "/static/assets/carrot-forest-world-v2.png");
      this.load.image("home-bg", "/static/assets/carrot-forest-home-v1.png");
      this.load.image("garden-bg", "/static/assets/carrot-forest-garden-v1.png");
      this.load.image("avatar-modular-v3", "/static/assets/carrot-forest-modular-avatar-atlas-v3.png");
      Object.entries(premiumPresets).forEach(([key, config]) => this.load.spritesheet(`preset-${key}`, config.path, { frameWidth: 224, frameHeight: 288 }));
      this.load.spritesheet("cat-pets", "/static/assets/carrot-forest-cat-pets-v1.png", { frameWidth: 887, frameHeight: 887 });
    }

    create() {
      this.background = this.add.image(WORLD.width / 2, WORLD.height / 2, "world-bg").setDisplaySize(WORLD.width, WORLD.height);
      this.shadow = this.add.ellipse(0, 13, 34, 11, 0x16382a, 0.25);
      this.player = this.add.container(this.avatar.x, this.avatar.y);
      this.player.add(this.shadow);
      this.motionFx = this.add.graphics().setDepth(2);
      this.player.add(this.motionFx);
      this.presetSources = Object.fromEntries(Object.entries(premiumPresets).map(([preset, config]) => [preset, {
        image: this.textures.get(`preset-${preset}`).getSourceImage(), rows: config.rows,
      }]));
      this.presetSources.modular = { image: this.textures.get("avatar-modular-v3").getSourceImage(), rows: 11 };
      if (this.textures.exists("avatar-composite")) this.textures.remove("avatar-composite");
      this.compositeTexture = this.textures.createCanvas("avatar-composite", 224, 288);
      this.premiumAvatar = this.add.image(0, 0, "avatar-composite").setOrigin(0.5, 0.96).setDepth(3);
      this.player.add(this.premiumAvatar);
      this.pet = this.add.sprite(31, 10, "cat-pets", 0).setOrigin(0.5, 1).setScale(0.045).setDepth(1);
      this.player.add(this.pet);
      this.nameplate = this.add.text(0, NAMEPLATE_Y, this.avatar.name, {
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
      this.emitPosition(true);
    }

    rebuildAvatar() {
      const c = this.avatar.cosmetics;
      this.setPremiumFrame(this.avatar.direction, false, 0);
      this.nameplate?.setDepth(30).setText(this.avatar.name);
      const pet = c.pet;
      this.pet?.setVisible(["cat", "blue_eyes_white_cat", "gold_eyes_orange_cat"].includes(pet));
      this.pet?.setFrame(pet === "gold_eyes_orange_cat" ? 1 : 0);
    }

    attachWindowEvents() {
      this.onAvatar = (event) => this.applyAvatarUpdate(normalizedAvatar({ ...this.avatar, ...(event.detail || {}) }));
      this.onState = (event) => {
        const detail = event.detail || {};
        if (detail.avatar) {
          const nextAvatar = normalizedAvatar(detail.avatar);
          this.player.setPosition(nextAvatar.x, nextAvatar.y);
          this.applyAvatarUpdate(nextAvatar);
        }
        if (detail.scene) this.setScene(detail.scene);
      };
      window.addEventListener("forest-avatar-updated", this.onAvatar);
      window.addEventListener("forest-state-updated", this.onState);
    }

    detachWindowEvents() {
      window.removeEventListener("forest-avatar-updated", this.onAvatar);
      window.removeEventListener("forest-state-updated", this.onState);
    }

    applyAvatarUpdate(nextAvatar) {
      if (nextAvatar.mounted !== this.avatar.mounted && this.premiumAvatar) {
        this.playMountTransition(nextAvatar);
        return;
      }
      this.avatar = nextAvatar;
      this.rebuildAvatar();
    }

    playMountTransition(nextAvatar) {
      this.mountTransitioning = true;
      this.tweens.killTweensOf(this.premiumAvatar);
      this.motionFx.clear();
      this.motionFx.lineStyle(3, 0xffd76a, 0.9).strokeCircle(0, 4, 18);
      this.tweens.add({
        targets: [this.premiumAvatar, this.shadow],
        alpha: 0,
        y: "-=10",
        duration: 120,
        ease: "Quad.easeIn",
        onComplete: () => {
          this.avatar = nextAvatar;
          this.setPremiumFrame(this.avatar.direction, false, performance.now());
          this.premiumAvatar.setY(9).setAlpha(0);
          this.shadow.setY(16).setAlpha(0);
          this.motionFx.clear().lineStyle(4, 0xffef9a, 1).strokeCircle(0, 5, 10);
          this.tweens.add({
            targets: this.premiumAvatar,
            alpha: 1,
            y: 0,
            duration: 190,
            ease: "Back.easeOut",
          });
          this.tweens.add({
            targets: this.shadow,
            alpha: 1,
            y: 13,
            duration: 170,
            ease: "Quad.easeOut",
            onComplete: () => {
              this.mountTransitioning = false;
              this.motionFx.clear();
              this.rebuildAvatar();
            },
          });
        },
      });
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
      if (this.mountTransitioning) return;
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
        this.setPremiumFrame(this.avatar.direction, false, time);
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
      this.setPremiumFrame(direction, true, time, running);
      this.emitPosition();
    }

    setPremiumFrame(direction, moving, time, running = false) {
      if (!this.premiumAvatar || !window.CarrotAvatarCompositor) return;
      const rate = running || this.avatar.mounted ? 90 : 140;
      const cosmetics = this.avatar.cosmetics;
      const context = this.compositeTexture.getContext();
      context.clearRect(0, 0, 224, 288);
      window.CarrotAvatarCompositor.drawFrame(context, this.presetSources, {
        preset: this.avatar.preset,
        hairPreset: hairPresetByStyle[cosmetics.hair] || this.avatar.preset,
        outfitPreset: outfitPresetByStyle[cosmetics.outfit] || this.avatar.preset,
        direction,
        mounted: this.avatar.mounted,
        moving,
        frame: Math.floor(time / rate) % 4,
        accessory: cosmetics.accessory,
        hat: cosmetics.hat,
        glasses: cosmetics.glasses,
        ...this.avatar.tuning,
      });
      this.compositeTexture.refresh();
      this.drawMotionEffects(direction, moving, Math.floor(time / rate) % 4);
      const worldScale = Math.min(0.58, Math.max(0.32, Number(this.avatar.tuning.worldScale) || AVATAR_RENDER_SCALE));
      this.premiumAvatar.setScale(worldScale);
      this.shadow.setScale(worldScale / AVATAR_RENDER_SCALE);
      this.nameplate?.setY(-Math.round(288 * worldScale * 0.96) - 7);
    }

    drawMotionEffects(direction, moving, frame) {
      if (!this.motionFx || this.mountTransitioning) return;
      this.motionFx.clear();
      if (!moving) return;
      const directionSign = direction === "left" ? 1 : direction === "right" ? -1 : 0;
      if (this.avatar.mounted) {
        this.motionFx.lineStyle(2, 0xffffff, 0.68);
        const baseX = directionSign ? directionSign * 30 : -22;
        for (let index = 0; index < 3; index += 1) {
          const lineY = 2 + index * 6 + (frame % 2) * 2;
          this.motionFx.lineBetween(baseX, lineY, baseX + directionSign * 13 - (directionSign ? 0 : 12), lineY);
        }
        this.motionFx.fillStyle(0xe8d6a2, 0.55);
        this.motionFx.fillCircle(directionSign ? directionSign * 25 : -18, 12, frame % 2 ? 3 : 2);
      } else if (frame % 2 === 1) {
        this.motionFx.fillStyle(0xe8d6a2, 0.42);
        this.motionFx.fillCircle(direction === "left" ? 13 : -13, 13, 2.5);
      }
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
