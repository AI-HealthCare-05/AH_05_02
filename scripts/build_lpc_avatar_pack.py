"""Build a curated Universal LPC avatar pack for Carrot Forest.

The upstream repository contains tens of thousands of layer files.  This tool
keeps the application small by composing only reviewed layers into the
standard 13-column LPC sheet while preserving source and licence metadata.

Usage:
    python scripts/build_lpc_avatar_pack.py \
        --source C:/path/to/Universal-LPC-Spritesheet-Character-Generator \
        --output src/frontend/assets/lpc-pack
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

FRAME = 64
SHEET_COLUMNS = 13
SHEET_ROWS = 54
ANIMATION_ROWS = {
    "spellcast": 0,
    "thrust": 4,
    "walk": 8,
    "slash": 12,
    "shoot": 16,
    "hurt": 20,
    "climb": 21,
    "idle": 22,
    "jump": 26,
    "sit": 30,
    "emote": 34,
    "run": 38,
    "combat_idle": 42,
    "backslash": 46,
    "halfslash": 50,
}


@dataclass(frozen=True)
class PackItem:
    item_id: str
    category: str
    label: str
    definition: str
    body_aware: bool = True


ITEMS = (
    PackItem("body", "body", "기본 몸", "body/body.json"),
    PackItem("bob", "hair", "단정한 단발", "hair/bob/hair_bob.json", False),
    PackItem("afro", "hair", "몽글 아프로", "hair/afro/hair_afro.json", False),
    PackItem("long", "hair", "긴 생머리", "hair/long/hair_long.json", False),
    PackItem("messy", "hair", "헝클어진 숏컷", "hair/short/hair_messy1.json", False),
    PackItem("page", "hair", "페이지 컷", "hair/short/hair_page.json", False),
    PackItem("overalls", "outfit", "정원사 멜빵", "torso/aprons/torso_aprons_overalls.json"),
    PackItem("tshirt", "outfit", "편안한 티셔츠", "torso/shirts/shortsleeve/torso_clothes_tshirt.json"),
    PackItem("cardigan", "outfit", "포근한 카디건", "torso/shirts/longsleeve/torso_clothes_longsleeve2_cardigan.json"),
    PackItem("sleeveless", "outfit", "산뜻한 민소매", "torso/shirts/sleeveless/torso_clothes_sleeveless2.json"),
    PackItem(
        "short_cardigan", "outfit", "반소매 카디건", "torso/shirts/shortsleeve/torso_clothes_shortsleeve_cardigan.json"
    ),
    PackItem("pants", "bottom", "기본 바지", "legs/pants/legs_pants.json"),
    PackItem("long_pants", "bottom", "긴 바지", "legs/pants/legs_pants2.json"),
    PackItem("shorts", "bottom", "산책 반바지", "legs/shorts/legs_shorts.json"),
    PackItem("leggings", "bottom", "활동 레깅스", "legs/leggings/legs_leggings.json"),
    PackItem("shoes", "shoes", "기본 운동화", "feet/shoes/feet_shoes_basic.json"),
    PackItem("boots", "shoes", "정원 워커", "feet/boots/feet_boots_basic.json"),
    PackItem("slippers", "shoes", "폭신 슬리퍼", "feet/feet_slippers.json"),
    PackItem("leather_cap", "hat", "가죽 산책 모자", "headwear/hats/caps/hat_cap_leather.json", False),
    PackItem("bowler", "hat", "포멀 보울러", "headwear/hats/formal/hat_formal_bowler.json", False),
    PackItem("bandana", "hat", "숲 반다나", "headwear/coverings/bandana/hat_bandana.json", False),
    PackItem("round", "glasses", "동그란 안경", "headwear/accessories/glasses/facial_glasses_round.json", False),
    PackItem("halfmoon", "glasses", "반달 안경", "headwear/accessories/glasses/facial_glasses_halfmoon.json", False),
    PackItem("sunglasses", "glasses", "선글라스", "headwear/accessories/glasses/facial_glasses_sunglasses.json", False),
)


def load_definition(source: Path, relative: str) -> dict[str, Any]:
    path = source / "sheet_definitions" / relative
    if not path.is_file():
        raise FileNotFoundError(f"Missing LPC definition: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def layer_paths(definition: dict[str, Any], body_type: str) -> list[tuple[int, str]]:
    layers: list[tuple[int, str]] = []
    for index in range(1, 10):
        layer = definition.get(f"layer_{index}")
        if not isinstance(layer, dict):
            continue
        relative = layer.get(body_type) or layer.get("male") or layer.get("female")
        if relative:
            layers.append((int(layer.get("zPos", 100)), str(relative)))
    return sorted(layers, key=lambda value: value[0])


def animation_source(folder: Path, animation: str, preferred_variant: str | None) -> Path | None:
    if preferred_variant:
        candidate = folder / animation / f"{preferred_variant}.png"
        if candidate.is_file():
            return candidate
    candidate = folder / f"{animation}.png"
    return candidate if candidate.is_file() else None


def compose_layer_sheet(
    source: Path,
    relative: str,
    declared: set[str],
    preferred_variant: str | None,
) -> tuple[Image.Image, list[str]]:
    sheet = Image.new("RGBA", (SHEET_COLUMNS * FRAME, SHEET_ROWS * FRAME), (0, 0, 0, 0))
    supported: list[str] = []
    for animation, row in ANIMATION_ROWS.items():
        source_animation = "combat" if animation == "combat_idle" else animation
        if source_animation not in declared and animation not in declared:
            continue
        path = animation_source(source / "spritesheets" / relative, animation, preferred_variant)
        if path is None and animation == "combat_idle":
            path = animation_source(source / "spritesheets" / relative, "combat", preferred_variant)
        if path is not None:
            layer = Image.open(path).convert("RGBA")
            sheet.alpha_composite(layer, (0, row * FRAME))
            supported.append(animation)
    return sheet, supported


def credit_records(definition: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for credit in definition.get("credits", []):
        records.append(
            {
                "file": credit.get("file", ""),
                "authors": credit.get("authors", []),
                "licenses": credit.get("licenses", []),
                "urls": credit.get("urls", []),
                "notes": credit.get("notes", ""),
            }
        )
    return records


def build(source: Path, output: Path) -> None:  # noqa: C901
    if not (source / "sheet_definitions").is_dir() or not (source / "spritesheets").is_dir():
        raise FileNotFoundError("--source must be a Universal LPC generator checkout")

    output.mkdir(parents=True, exist_ok=True)
    for old_sheet in output.glob("*.png"):
        old_sheet.unlink()

    manifest: dict[str, Any] = {
        "format": "gandang-lpc-pack-v1",
        "frame": FRAME,
        "columns": SHEET_COLUMNS,
        "rows": SHEET_ROWS,
        "animationRows": ANIMATION_ROWS,
        "directionRows": {"up": 0, "left": 1, "down": 2, "right": 3},
        "source": "Universal-LPC-Spritesheet-Character-Generator",
        "sourceUrl": "https://github.com/liberatedpixelcup/Universal-LPC-Spritesheet-Character-Generator",
        "items": [],
    }
    credits: list[dict[str, Any]] = []

    for item in ITEMS:
        definition = load_definition(source, item.definition)
        preferred_variant = "brown" if "variants" in definition else None
        body_types = ("male", "female") if item.body_aware else ("male",)
        sources: dict[str, list[dict[str, Any]]] = {}
        animation_union: set[str] = set()
        declared = set(definition.get("animations") or ANIMATION_ROWS)
        for body_type in body_types:
            suffix = body_type if item.body_aware else "adult"
            rendered_layers: list[dict[str, Any]] = []
            for layer_index, (z_pos, relative) in enumerate(layer_paths(definition, body_type), start=1):
                sheet, supported = compose_layer_sheet(source, relative, declared, preferred_variant)
                if not supported:
                    continue
                filename = f"{item.category}-{item.item_id}-{suffix}-layer{layer_index}.png"
                sheet.save(output / filename, optimize=True)
                rendered_layers.append({"file": filename, "z": z_pos})
                animation_union.update(supported)
            if rendered_layers:
                sources[body_type] = rendered_layers
        if not sources:
            raise RuntimeError(f"No renderable LPC layers found for {item.item_id}")
        if not item.body_aware:
            sources["female"] = sources["male"]
        manifest["items"].append(
            {
                "id": item.item_id,
                "category": item.category,
                "label": item.label,
                "sources": sources,
                "animations": sorted(animation_union, key=lambda value: list(ANIMATION_ROWS).index(value)),
                "definition": item.definition,
            }
        )
        for record in credit_records(definition):
            record["usedBy"] = item.item_id
            credits.append(record)

    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=2), encoding="utf-8")
    upstream_readme = source / "README.md"
    if upstream_readme.is_file():
        shutil.copy2(upstream_readme, output / "UPSTREAM_README.md")

    print(f"Built {len(manifest['items'])} LPC catalog items in {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    build(arguments.source.resolve(), arguments.output.resolve())


if __name__ == "__main__":
    main()
