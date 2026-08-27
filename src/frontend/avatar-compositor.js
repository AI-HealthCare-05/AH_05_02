(() => {
  "use strict";

  const CELL_WIDTH = 224;
  const CELL_HEIGHT = 288;
  const HEAD_CUT = 166;
  const HEAD_OFFSET_Y = -6;
  const modularHairRows = { red_bow: 1, cow_hood: 2, midnight: 3, blue_cap: 4, teal_bob: 5 };
  const modularOutfitRows = { red_bow: 6, cow_hood: 7, midnight: 8, blue_cap: 9, teal_bob: 10 };
  const directionRows = { down: 0, up: 1, left: 2, right: 3 };
  const directionColumns = { down: 0, up: 1, left: 2, right: 3 };

  function framePosition(options, rows) {
    const direction = directionRows[options.direction] == null ? "down" : options.direction;
    if (options.mounted) {
      return {
        row: options.moving && rows === 6 ? 5 : 4,
        column: directionColumns[direction],
      };
    }
    return {
      row: directionRows[direction],
      column: options.moving ? Number(options.frame || 0) % 4 : 0,
    };
  }

  function drawSource(context, image, frame, destination) {
    context.drawImage(
      image,
      frame.column * CELL_WIDTH,
      frame.row * CELL_HEIGHT,
      CELL_WIDTH,
      CELL_HEIGHT,
      destination.x,
      destination.y,
      destination.width,
      destination.height,
    );
  }

  function drawModularFrame(context, source, options, target) {
    const column = directionColumns[options.direction] == null ? 0 : directionColumns[options.direction];
    const base = { row: 0, column };
    const outfit = { row: modularOutfitRows[options.outfitPreset] ?? 9, column };
    const hair = { row: modularHairRows[options.hairPreset] ?? 4, column };
    const bob = options.moving ? (Number(options.frame || 0) % 2 ? -2 : 1) : 0;
    const headOffsetY = Number.isFinite(options.headOffsetY) ? options.headOffsetY : HEAD_OFFSET_Y;
    const outfitOffsetY = Number.isFinite(options.outfitOffsetY) ? options.outfitOffsetY : 0;
    const bodyTarget = { ...target, y: target.y + bob };

    context.save();
    context.imageSmoothingEnabled = false;
    drawSource(context, source.image, base, bodyTarget);
    drawSource(context, source.image, outfit, { ...bodyTarget, y: bodyTarget.y + outfitOffsetY });
    drawSource(context, source.image, hair, { ...target, y: target.y + bob + headOffsetY });
    context.restore();
  }

  function drawAccessory(context, options, destination) {
    if (options.direction === "up") return;
    context.save();
    context.translate(destination.x, destination.y);
    context.scale(destination.width / CELL_WIDTH, destination.height / CELL_HEIGHT);
    context.imageSmoothingEnabled = false;
    const directionOffset = options.direction === "left" ? -7 : options.direction === "right" ? 7 : 0;
    const headOffsetY = Number.isFinite(options.headOffsetY) ? options.headOffsetY : HEAD_OFFSET_Y;
    const headAdjustmentY = headOffsetY - HEAD_OFFSET_Y;
    const glassesOffsetY = Number.isFinite(options.glassesOffsetY) ? options.glassesOffsetY : 0;
    const glasses = options.glasses !== "none" ? options.glasses : ["round_glasses", "star_glasses"].includes(options.accessory) ? options.accessory : "none";
    if (glasses !== "none") {
      context.strokeStyle = glasses === "star_glasses" || glasses === "sun" ? "#51284f" : "#27353d";
      context.fillStyle = glasses === "sun" ? "rgba(49, 33, 69, .72)" : "rgba(186, 226, 235, .22)";
      context.lineWidth = 2.5;
      if (options.direction === "left" || options.direction === "right") {
        const lensX = (options.direction === "left" ? 98 : 126) + directionOffset;
        context.beginPath();
        context.ellipse(lensX, 123 + headAdjustmentY + glassesOffsetY, 13, 9, 0, 0, Math.PI * 2);
        context.fill();
        context.stroke();
      } else {
        for (const lensX of [96, 128]) {
          context.beginPath();
          context.ellipse(lensX, 123 + headAdjustmentY + glassesOffsetY, 14, 10, 0, 0, Math.PI * 2);
          context.fill();
          context.stroke();
        }
        context.fillStyle = context.strokeStyle;
        context.fillRect(110, 121 + headAdjustmentY + glassesOffsetY, 4, 3);
      }
    }
    if (options.accessory === "red_scarf") {
      context.fillStyle = "#b92f34";
      context.fillRect(77 + directionOffset, 157, 72, 10);
      context.fillStyle = "#e14b49";
      context.fillRect(86 + directionOffset, 156, 54, 5);
    }
    if (options.accessory === "carrot_bag" && options.direction !== "left") {
      context.fillStyle = "#b95824";
      context.fillRect(146 + directionOffset, 176, 28, 42);
      context.fillStyle = "#ef8632";
      context.fillRect(151 + directionOffset, 181, 18, 31);
    }
    if (options.accessory === "sprout_hat" || options.hat === "headband") {
      context.fillStyle = options.hat === "headband" ? "#cb3d45" : "#3a8e48";
      context.fillRect(72 + directionOffset, 49 + headAdjustmentY, 80, 10);
      if (options.accessory === "sprout_hat") {
        context.fillRect(107 + directionOffset, 28 + headAdjustmentY, 9, 22);
        context.fillRect(116 + directionOffset, 30 + headAdjustmentY, 20, 9);
      }
    }
    context.restore();
  }

  function drawFrame(context, sources, options, destination = {}) {
    const target = {
      x: destination.x || 0,
      y: destination.y || 0,
      width: destination.width || CELL_WIDTH,
      height: destination.height || CELL_HEIGHT,
    };
    if (sources.modular?.image) {
      drawModularFrame(context, sources.modular, options, target);
      drawAccessory(context, options, { ...target, y: target.y + (options.moving ? -1 : 0) });
      return true;
    }
    const outfit = sources[options.outfitPreset] || sources[options.preset];
    const hair = sources[options.hairPreset] || sources[options.preset] || outfit;
    if (!outfit?.image || !hair?.image) return false;
    const outfitFrame = framePosition(options, outfit.rows);
    const hairFrame = framePosition(options, hair.rows);
    context.save();
    context.imageSmoothingEnabled = false;
    drawSource(context, outfit.image, outfitFrame, target);
    const cutHeight = target.height * HEAD_CUT / CELL_HEIGHT;
    context.clearRect(target.x, target.y, target.width, cutHeight);
    context.beginPath();
    context.rect(target.x, target.y, target.width, cutHeight + 3);
    context.clip();
    drawSource(context, hair.image, hairFrame, target);
    context.restore();
    drawAccessory(context, options, target);
    return true;
  }

  window.CarrotAvatarCompositor = { CELL_WIDTH, CELL_HEIGHT, drawFrame, framePosition };
})();
