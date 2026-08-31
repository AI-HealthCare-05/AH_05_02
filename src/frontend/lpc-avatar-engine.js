(() => {
  "use strict";

  const BASE = "/static/assets/lpc-pack/";
  const FRAME = 64;
  const animationCycles = {
    idle: [0, 0, 1], walk: [1, 2, 3, 4, 5, 6, 7, 8], run: [0, 1, 2, 3, 4, 5, 6, 7],
    sit: [0, 0, 1, 1, 2, 2], jump: [0, 1, 2, 3, 4, 1], emote: [0, 0, 1, 1, 2, 2],
    spellcast: [0, 1, 2, 3, 4, 5, 6], thrust: [0, 1, 2, 3, 4, 5, 6, 7],
    slash: [0, 1, 2, 3, 4, 5], shoot: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    hurt: [0, 1, 2, 3, 4, 5], climb: [0, 1, 2, 3, 4, 5], combat_idle: [0, 0, 1],
    backslash: [0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12], halfslash: [0, 1, 2, 3, 4, 5],
  };
  const colorFilters = {
    natural: "none", peach: "none", rose: "hue-rotate(-9deg) saturate(.92) brightness(1.02)",
    warm: "sepia(.28) saturate(1.18) brightness(.88)", deep: "sepia(.38) saturate(1.25) brightness(.62)",
    olive: "sepia(.3) hue-rotate(18deg) saturate(.9) brightness(.78)", porcelain: "saturate(.72) brightness(1.08)",
    sand: "sepia(.18) saturate(1.08) brightness(.93)", golden: "sepia(.34) saturate(1.22) brightness(.79)",
    amber: "sepia(.4) saturate(1.25) brightness(.7)", bronze: "sepia(.42) saturate(1.2) brightness(.61)",
    espresso: "sepia(.45) saturate(1.1) brightness(.45)", neutral: "sepia(.2) saturate(.95) brightness(.84)",
    brown: "hue-rotate(-18deg) saturate(.72) brightness(.66)", black: "grayscale(1) brightness(.32)",
    silver: "grayscale(1) brightness(1.42)", blue: "hue-rotate(165deg) saturate(1.3) brightness(.8)",
    teal: "hue-rotate(120deg) saturate(1.15) brightness(.82)", red: "hue-rotate(-28deg) saturate(1.25) brightness(.86)",
    orange: "none", green: "hue-rotate(66deg) saturate(1.05) brightness(.84)",
    navy: "hue-rotate(172deg) saturate(1.25) brightness(.56)", cream: "saturate(.38) brightness(1.42)",
    pink: "hue-rotate(-38deg) saturate(.82) brightness(1.18)", purple: "hue-rotate(225deg) saturate(1.15) brightness(.76)",
    white: "grayscale(1) brightness(1.7)", gray: "grayscale(1) brightness(.78)", yellow: "hue-rotate(25deg) saturate(1.4) brightness(1.2)",
  };
  const poseLabels = {
    idle: "가만히", walk: "걷기", run: "달리기", sit: "앉기", jump: "점프", emote: "기쁨 표현",
    spellcast: "반짝임 만들기", thrust: "앞으로 뻗기", slash: "힘차게 휘두르기", shoot: "멀리 가리키기",
    hurt: "깜짝 놀라기", combat_idle: "준비 자세",
  };
  const poseAnimationAliases = {
    harvest: "thrust", fishing: "shoot", door: "thrust", attack: "slash", dance: "emote",
  };

  let manifest = null;
  const items = new Map();
  const images = new Map();
  const pendingImages = new Map();
  let assetEventPending = false;

  function loadImage(url) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.decoding = "async";
      image.addEventListener("load", () => resolve(image), { once: true });
      image.addEventListener("error", () => reject(new Error(`LPC image load failed: ${url}`)), { once: true });
      image.src = url;
    });
  }

  const readyPromise = fetch(`${BASE}manifest.json?v=20260831-1`)
    .then((response) => {
      if (!response.ok) throw new Error("LPC manifest load failed");
      return response.json();
    })
    .then((value) => {
      manifest = value;
      value.items.forEach((item) => items.set(`${item.category}:${item.id}`, item));
      window.dispatchEvent(new CustomEvent("lpc-avatar-ready"));
      return value;
    })
    .catch((error) => {
      console.error(error);
      return null;
    });

  function item(category, id, fallback) {
    return items.get(`${category}:${id}`) || items.get(`${category}:${fallback}`);
  }

  function ensureImage(file) {
    if (!file || images.has(file) || pendingImages.has(file)) return;
    const request = loadImage(`${BASE}${file}`)
      .then((image) => {
        images.set(file, image);
        if (!assetEventPending) {
          assetEventPending = true;
          requestAnimationFrame(() => {
            assetEventPending = false;
            window.dispatchEvent(new CustomEvent("lpc-avatar-assets-updated"));
          });
        }
      })
      .catch((error) => console.error(error))
      .finally(() => pendingImages.delete(file));
    pendingImages.set(file, request);
  }

  function selectedLayers(avatar) {
    const cosmetics = avatar.cosmetics || {};
    const gender = avatar.gender === "female" ? "female" : "male";
    const bodyType = cosmetics.bodyType || gender;
    const selectedExpression = cosmetics.lpcExpression || "neutral";
    const selections = [
      ["body", "body", "body", cosmetics.skin || "peach"],
      ["bottom", cosmetics.lpcBottom, "pants", cosmetics.bottomColor || "navy"],
      ["shoes", cosmetics.lpcShoes, "shoes", cosmetics.shoeColor || "brown"],
      ["outfit", cosmetics.lpcOutfit, "overalls", cosmetics.outfitColor || "green"],
      // happy2·blush처럼 얼굴의 일부만 담은 표정도 있다. 중립 얼굴을
      // 바탕에 항상 그린 뒤 선택 표정을 겹쳐 눈·코·입이 비지 않게 한다.
      ["expression", "neutral", "neutral", "natural"],
      ...(selectedExpression === "neutral" ? [] : [["expression", selectedExpression, "neutral", "natural"]]),
      ["eyebrow", cosmetics.lpcEyebrow, "thick", cosmetics.hairColor || "brown"],
      ["nose", cosmetics.lpcNose, "button", cosmetics.skin || "peach"],
      ["eyes", cosmetics.lpcEyes, "cyclops", "natural"],
      ["wrinkles", cosmetics.lpcWrinkles, "wrinkles", cosmetics.skin || "peach"],
      ["hair", cosmetics.lpcHair, "bob", cosmetics.hairColor || "brown"],
      ["eyewear", cosmetics.lpcGlasses, "round", cosmetics.glassesColor || "brown"],
      ["hat", cosmetics.lpcHat, "leather_cap", cosmetics.hatColor || "brown"],
    ];
    const output = [];
    selections.forEach(([category, selected, fallback, color]) => {
      if (selected === "none") return;
      const record = item(category, selected, fallback);
      const layers = record?.sources?.[bodyType] || record?.sources?.[gender] || record?.sources?.male || [];
      layers.forEach((layer) => output.push({ ...layer, color, category, item: record }));
    });
    return output.sort((left, right) => left.z - right.z);
  }

  function resolvedAnimation(avatar, options) {
    if (options.pose === "attack") {
      const effect = avatar.cosmetics?.effect || "sword_arc";
      if (effect === "magic_burst") return "spellcast";
      if (effect === "arrow_volley") return "shoot";
      if (effect === "leaf_blade") return "thrust";
      return "slash";
    }
    if (poseAnimationAliases[options.pose]) return poseAnimationAliases[options.pose];
    if (options.pose && animationCycles[options.pose]) return options.pose;
    if (avatar.sitting) return "sit";
    if (avatar.mounted) return "sit";
    if (options.moving) return options.running ? "run" : "walk";
    return "idle";
  }

  function drawActionProp(context, destination, direction, pose, frame, cosmetics = {}) {
    if (!pose) return;
    const scaleX = destination.width / FRAME;
    const scaleY = destination.height / FRAME;
    context.save();
    context.lineCap = "round";
    if (pose === "fishing") {
      const handX = destination.x + (direction === "left" ? 21 : 43) * scaleX;
      const handY = destination.y + 37 * scaleY;
      const endX = handX + (direction === "left" ? -24 : 24) * scaleX;
      const endY = destination.y + (22 + Math.min(frame, 6)) * scaleY;
      context.strokeStyle = "#76502f";
      context.lineWidth = Math.max(2, scaleX);
      context.beginPath(); context.moveTo(handX, handY); context.lineTo(endX, endY); context.stroke();
      context.strokeStyle = "#dbeef4";
      context.lineWidth = Math.max(1, scaleX * 0.55);
      context.beginPath(); context.moveTo(endX, endY); context.quadraticCurveTo(endX + 8 * scaleX, endY + 12 * scaleY, endX + 3 * scaleX, destination.y + 61 * scaleY); context.stroke();
      context.fillStyle = "#e85d48";
      context.fillRect(endX + 2 * scaleX, destination.y + 59 * scaleY, 2 * scaleX, 2 * scaleY);
    } else if (pose === "harvest") {
      const side = direction === "left" ? 17 : 43;
      drawPixel(context, destination, side, 44, 4, 7, "#ed7c2e");
      drawPixel(context, destination, side - 1, 42, 3, 3, "#559c45");
      drawPixel(context, destination, side + 2, 41, 3, 3, "#6fb659");
    } else if (pose === "attack") {
      const effect = cosmetics.effect || "sword_arc";
      const cx = destination.x + 32 * scaleX;
      const cy = destination.y + 34 * scaleY;
      const horizontal = direction === "left" ? -1 : 1;
      if (effect === "magic_burst") {
        const pulse = 8 + (frame % 7) * 3;
        context.strokeStyle = "rgba(153, 116, 255, .95)"; context.lineWidth = Math.max(2, 2 * scaleX);
        context.beginPath(); context.arc(cx, cy, pulse * scaleX, 0, Math.PI * 2); context.stroke();
        context.fillStyle = "rgba(220, 201, 255, .95)";
        for (let index = 0; index < 5; index += 1) {
          const angle = index * Math.PI * .4 + frame * .18;
          context.fillRect(cx + Math.cos(angle) * pulse * scaleX, cy + Math.sin(angle) * pulse * scaleY, Math.max(2, 2 * scaleX), Math.max(2, 2 * scaleY));
        }
      } else if (effect === "arrow_volley") {
        context.strokeStyle = "#805331"; context.fillStyle = "#f1d39a"; context.lineWidth = Math.max(1, scaleX);
        for (let index = -1; index <= 1; index += 1) {
          const tipX = cx + horizontal * (22 + frame * 2) * scaleX;
          const arrowY = cy + index * 7 * scaleY;
          context.beginPath(); context.moveTo(cx, arrowY); context.lineTo(tipX, arrowY); context.stroke();
          context.beginPath(); context.moveTo(tipX, arrowY); context.lineTo(tipX - horizontal * 5 * scaleX, arrowY - 3 * scaleY); context.lineTo(tipX - horizontal * 5 * scaleX, arrowY + 3 * scaleY); context.closePath(); context.fill();
        }
      } else if (effect === "leaf_blade") {
        context.fillStyle = "rgba(104, 190, 93, .95)";
        for (let index = 0; index < 4; index += 1) {
          const leafX = cx + horizontal * (12 + frame * 3 + index * 7) * scaleX;
          const leafY = cy + (index - 1.5) * 6 * scaleY;
          context.save(); context.translate(leafX, leafY); context.rotate(horizontal * (.5 + index * .2));
          context.beginPath(); context.ellipse(0, 0, 6 * scaleX, 3 * scaleY, 0, 0, Math.PI * 2); context.fill(); context.restore();
        }
      } else {
        context.strokeStyle = "rgba(255, 224, 113, .96)";
        context.lineWidth = Math.max(2, 3 * scaleX); context.beginPath();
        const start = horizontal > 0 ? -1.35 : 2.35;
        context.arc(cx, cy, (18 + frame) * scaleX, start, start + horizontal * 2.15, horizontal < 0); context.stroke();
      }
    } else if (pose === "door") {
      drawPixel(context, destination, direction === "left" ? 15 : 47, 34, 2, 2, "#ffe69a");
    }
    context.restore();
  }

  function drawPixel(context, destination, x, y, width, height, color) {
    const scaleX = destination.width / FRAME;
    const scaleY = destination.height / FRAME;
    context.fillStyle = color;
    context.fillRect(
      Math.round(destination.x + x * scaleX), Math.round(destination.y + y * scaleY),
      Math.max(1, Math.round(width * scaleX)), Math.max(1, Math.round(height * scaleY)),
    );
  }

  function drawScooter(context, destination, direction, moving, frame) {
    if (direction === "up") return;
    const scaleX = destination.width / FRAME;
    const scaleY = destination.height / FRAME;
    const y = destination.y + 56 * scaleY;
    const left = destination.x + 8 * scaleX;
    context.save();
    context.strokeStyle = "#d96827";
    context.lineWidth = Math.max(2, 2 * scaleX);
    context.lineCap = "square";
    context.beginPath();
    context.moveTo(left + 6 * scaleX, y);
    context.lineTo(left + 43 * scaleX, y);
    context.lineTo(left + 48 * scaleX, y - 25 * scaleY);
    context.stroke();
    context.fillStyle = "#253338";
    context.beginPath(); context.arc(left + 7 * scaleX, y + 1 * scaleY, 5 * scaleX, 0, Math.PI * 2); context.fill();
    context.beginPath(); context.arc(left + 44 * scaleX, y + 1 * scaleY, 5 * scaleX, 0, Math.PI * 2); context.fill();
    context.fillStyle = "#f29a35";
    context.fillRect(left + 5 * scaleX, y - 3 * scaleY, 40 * scaleX, 3 * scaleY);
    if (moving && frame % 2) {
      context.fillStyle = "rgba(255,255,255,.78)";
      context.fillRect(destination.x, y - 10 * scaleY, 8 * scaleX, 1 * scaleY);
      context.fillRect(destination.x + 3 * scaleX, y - 5 * scaleY, 11 * scaleX, 1 * scaleY);
    }
    context.restore();
  }

  function draw(context, avatar, options = {}, destination = {}) {
    if (!manifest) return false;
    const target = { x: destination.x || 0, y: destination.y || 0, width: destination.width || 192, height: destination.height || 192 };
    const direction = ["up", "left", "down", "right"].includes(options.direction || avatar.direction)
      ? (options.direction || avatar.direction) : "down";
    const animation = resolvedAnimation(avatar, options);
    const cycles = animationCycles[animation] || animationCycles.idle;
    const frameIndex = avatar.sitting && !options.pose
      ? cycles[cycles.length - 1]
      : cycles[Math.abs(Number(options.frame || 0)) % cycles.length];
    const rowBase = manifest.animationRows[animation] ?? manifest.animationRows.idle;
    const directionRow = animation === "hurt" || animation === "climb" ? 0 : manifest.directionRows[direction];

    context.save();
    context.imageSmoothingEnabled = false;
    if (avatar.mounted) drawScooter(context, target, direction, Boolean(options.moving), frameIndex);
    selectedLayers(avatar).forEach((layer) => {
      const image = images.get(layer.file);
      if (!image) { ensureImage(layer.file); return; }
      context.save();
      context.filter = colorFilters[layer.color] || "none";
      context.drawImage(
        image, frameIndex * FRAME, (rowBase + directionRow) * FRAME, FRAME, FRAME,
        target.x, target.y, target.width, target.height,
      );
      context.restore();
    });
    drawActionProp(context, target, direction, options.pose, frameIndex, avatar.cosmetics || {});
    context.restore();
    return true;
  }

  function catalog(category) {
    if (category === "pose") return Object.entries(poseLabels).map(([id, label]) => ({ id, label }));
    return manifest?.items.filter((record) => record.category === category) || [];
  }

  window.LpcAvatarEngine = {
    ready: () => readyPromise,
    isReady: () => Boolean(manifest),
    draw,
    catalog,
    poseLabels,
    colors: colorFilters,
  };
})();
