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


BODY_TYPES = ("male", "female", "muscular", "teen", "child")

ITEMS = (
    PackItem("body", "body", "기본 몸", "body/body.json"),
    PackItem("bob", "hair", "단정한 단발", "hair/bob/hair_bob.json", False),
    PackItem("afro", "hair", "몽글 아프로", "hair/afro/hair_afro.json", False),
    PackItem("long", "hair", "긴 생머리", "hair/long/hair_long.json", False),
    PackItem("messy", "hair", "헝클어진 숏컷", "hair/short/hair_messy1.json", False),
    PackItem("page", "hair", "페이지 컷", "hair/short/hair_page.json", False),
    PackItem("pixie", "hair", "픽시", "hair/short/hair_pixie.json", False),
    PackItem("bedhead", "hair", "베드헤드", "hair/short/hair_bedhead.json", False),
    PackItem("curtains", "hair", "커튼", "hair/short/hair_curtains.json", False),
    PackItem("idol", "hair", "아이돌", "hair/short/hair_idol.json", False),
    PackItem("buzzcut", "hair", "버즈컷", "hair/bald/hair_buzzcut.json", False),
    PackItem("shorthawk", "hair", "숏호크", "hair/bald/hair_shorthawk.json", False),
    PackItem("lob", "hair", "롱보브", "hair/bob/hair_lob.json", False),
    PackItem("side_bob", "hair", "사이드 보브", "hair/bob/hair_bob_side_part.json", False),
    PackItem("braid", "hair", "브레이드", "hair/braids/hair_braid.json", False),
    PackItem("ponytail", "hair", "포니테일", "hair/braids/hair_ponytail.json", False),
    PackItem("high_ponytail", "hair", "하이 포니테일", "hair/braids/hair_high_ponytail.json", False),
    PackItem("topknot", "hair", "탑노트", "hair/braids/hair_topknot_short.json", False),
    PackItem("curly", "hair", "컬리", "hair/curly/hair_curly_short.json", False),
    PackItem("curly_long", "hair", "롱 컬리", "hair/curly/hair_curly_long.json", False),
    PackItem("natural", "hair", "내추럴", "hair/afro/hair_natural.json", False),
    PackItem("cornrows", "hair", "콘로우", "hair/afro/hair_cornrows.json", False),
    PackItem("dreadlocks", "hair", "드레드록", "hair/afro/hair_dreadlocks_long.json", False),
    PackItem("pigtails", "hair", "피그테일", "hair/pigtails/hair_pigtails.json", False),
    PackItem("wavy", "hair", "웨이브", "hair/long/hair_wavy.json", False),
    PackItem("overalls", "outfit", "정원사 멜빵", "torso/aprons/torso_aprons_overalls.json"),
    PackItem("tshirt", "outfit", "편안한 티셔츠", "torso/shirts/shortsleeve/torso_clothes_tshirt.json"),
    PackItem("cardigan", "outfit", "포근한 카디건", "torso/shirts/longsleeve/torso_clothes_longsleeve2_cardigan.json"),
    PackItem("sleeveless", "outfit", "산뜻한 민소매", "torso/shirts/sleeveless/torso_clothes_sleeveless2.json"),
    PackItem(
        "short_cardigan", "outfit", "반소매 카디건", "torso/shirts/shortsleeve/torso_clothes_shortsleeve_cardigan.json"
    ),
    PackItem("blouse", "outfit", "블라우스", "torso/shirts/torso_clothes_blouse.json"),
    PackItem("long_blouse", "outfit", "긴 블라우스", "torso/shirts/torso_clothes_blouse_longsleeve.json"),
    PackItem("tunic", "outfit", "튜닉", "torso/shirts/torso_clothes_tunic.json"),
    PackItem("robe", "outfit", "로브", "torso/shirts/torso_clothes_robe.json"),
    PackItem("corset", "outfit", "코르셋", "torso/shirts/torso_clothes_corset.json"),
    PackItem("child_shirt", "outfit", "아동 셔츠", "torso/shirts/torso_clothes_child_shirt.json"),
    PackItem("formal", "outfit", "포멀", "torso/shirts/longsleeve/torso_clothes_longsleeve_formal.json"),
    PackItem("laced", "outfit", "레이스", "torso/shirts/longsleeve/torso_clothes_longsleeve_laced.json"),
    PackItem("polo", "outfit", "폴로", "torso/shirts/longsleeve/torso_clothes_longsleeve2_polo.json"),
    PackItem("buttoned", "outfit", "버튼 셔츠", "torso/shirts/longsleeve/torso_clothes_longsleeve2_buttoned.json"),
    PackItem("vneck", "outfit", "브이넥", "torso/shirts/longsleeve/torso_clothes_longsleeve2_vneck.json"),
    PackItem("short_polo", "outfit", "반소매 폴로", "torso/shirts/shortsleeve/torso_clothes_shortsleeve_polo.json"),
    PackItem("tshirt_vneck", "outfit", "브이넥 티", "torso/shirts/shortsleeve/torso_clothes_tshirt_vneck.json"),
    PackItem("tanktop", "outfit", "탱크톱", "torso/shirts/sleeveless/torso_clothes_sleeveless_tanktop.json"),
    PackItem("vest", "outfit", "조끼", "torso/vest/torso_clothes_vest.json"),
    PackItem("pants", "bottom", "기본 바지", "legs/pants/legs_pants.json"),
    PackItem("long_pants", "bottom", "긴 바지", "legs/pants/legs_pants2.json"),
    PackItem("shorts", "bottom", "산책 반바지", "legs/shorts/legs_shorts.json"),
    PackItem("leggings", "bottom", "활동 레깅스", "legs/leggings/legs_leggings.json"),
    PackItem("leggings2", "bottom", "슬림 레깅스", "legs/leggings/legs_leggings2.json"),
    PackItem("hose", "bottom", "호즈", "legs/leggings/legs_hose.json"),
    PackItem("short_short", "bottom", "짧은 반바지", "legs/shorts/legs_shorts_short.json"),
    PackItem("formal_pants", "bottom", "정장 바지", "legs/pants/legs_formal.json"),
    PackItem("cuffed", "bottom", "커프 바지", "legs/pants/legs_cuffed.json"),
    PackItem("pantaloons", "bottom", "판탈롱", "legs/pants/legs_pantaloons.json"),
    PackItem("childpants", "bottom", "아동 바지", "legs/pants/legs_childpants.json"),
    PackItem("widepants", "bottom", "와이드 팬츠", "legs/pants/legs_widepants.json"),
    PackItem("plain_skirt", "bottom", "기본 스커트", "legs/skirts/legs_skirts_plain.json"),
    PackItem("slit_skirt", "bottom", "슬릿 스커트", "legs/skirts/legs_skirts_slit.json"),
    PackItem("childskirts", "bottom", "아동 스커트", "legs/skirts/legs_childskirts.json"),
    PackItem("shoes", "shoes", "기본 운동화", "feet/shoes/feet_shoes_basic.json"),
    PackItem("boots", "shoes", "정원 워커", "feet/boots/feet_boots_basic.json"),
    PackItem("slippers", "shoes", "폭신 슬리퍼", "feet/feet_slippers.json"),
    PackItem("sandals", "shoes", "샌들", "feet/feet_sandals.json"),
    PackItem("shoe_revised", "shoes", "가죽 구두", "feet/shoes/feet_shoes_revised.json"),
    PackItem("ghillies", "shoes", "길리 슈즈", "feet/shoes/feet_shoes_ghillies.json"),
    PackItem("sara_shoes", "shoes", "사라 슈즈", "feet/shoes/feet_shoes_sara.json"),
    PackItem("boots_fold", "shoes", "폴드 부츠", "feet/boots/feet_boots_fold.json"),
    PackItem("boots_rim", "shoes", "림 부츠", "feet/boots/feet_boots_rim.json"),
    PackItem("boots_revised", "shoes", "롱 부츠", "feet/boots/feet_boots_revised.json"),
    PackItem("ankle_socks", "shoes", "앵클 삭스", "feet/socks/feet_socks_ankle.json"),
    PackItem("high_socks", "shoes", "하이 삭스", "feet/socks/feet_socks_high.json"),
    PackItem("leather_cap", "hat", "가죽 산책 모자", "headwear/hats/caps/hat_cap_leather.json", False),
    PackItem("bowler", "hat", "포멀 보울러", "headwear/hats/formal/hat_formal_bowler.json", False),
    PackItem("bandana", "hat", "숲 반다나", "headwear/coverings/bandana/hat_bandana.json", False),
    PackItem("bonnie", "hat", "보니", "headwear/hats/caps/hat_cap_bonnie.json", False),
    PackItem("bonnie_feather", "hat", "깃털 보니", "headwear/hats/caps/hat_cap_bonnie_feather.json", False),
    PackItem("cavalier", "hat", "카발리에", "headwear/hats/caps/hat_cap_cavalier.json", False),
    PackItem("leather_feather", "hat", "깃털 가죽캡", "headwear/hats/caps/hat_cap_leather_feather.json", False),
    PackItem("crown", "hat", "왕관", "headwear/hats/formal/hat_formal_crown.json", False),
    PackItem("tiara", "hat", "티아라", "headwear/hats/formal/hat_formal_tiara.json", False),
    PackItem("tophat", "hat", "톱햇", "headwear/hats/formal/hat_formal_tophat.json", False),
    PackItem("wizard", "hat", "마법사", "headwear/hats/magic/hat_magic_wizard.json", False),
    PackItem("wizard_buckle", "hat", "버클 마법사", "headwear/hats/magic/hat_magic_wizard_buckle.json", False),
    PackItem("celestial", "hat", "천체 모자", "headwear/hats/magic/hat_magic_celestial.json", False),
    PackItem("celestial_moon", "hat", "달 모자", "headwear/hats/magic/hat_magic_celestial_moon.json", False),
    PackItem("santa", "hat", "산타", "headwear/hats/holiday/hat_holiday_santa.json", False),
    PackItem("elf", "hat", "엘프", "headwear/hats/holiday/hat_holiday_elf.json", False),
    PackItem("tricorne", "hat", "트라이콘", "headwear/hats/tricorne/hat_tricorne.json", False),
    PackItem("pirate_bandana", "hat", "해적 반다나", "headwear/coverings/bandana/hat_bandana_pirate.json", False),
    PackItem("hijab", "hat", "히잡", "headwear/coverings/hoods/hat_hood_hijab.json", False),
    PackItem("round", "eyewear", "동그란 안경", "headwear/accessories/glasses/facial_glasses_round.json", False),
    PackItem("halfmoon", "eyewear", "반달 안경", "headwear/accessories/glasses/facial_glasses_halfmoon.json", False),
    PackItem("sunglasses", "eyewear", "선글라스", "headwear/accessories/glasses/facial_glasses_sunglasses.json", False),
    PackItem("basic_glasses", "eyewear", "기본 안경", "headwear/accessories/glasses/facial_glasses.json", False),
    PackItem("nerd", "eyewear", "너드 안경", "headwear/accessories/glasses/facial_glasses_nerd.json", False),
    PackItem("secretary", "eyewear", "세크리터리", "headwear/accessories/glasses/facial_glasses_secretary.json", False),
    PackItem("shades", "eyewear", "셰이드", "headwear/accessories/glasses/facial_glasses_shades.json", False),
    PackItem("patch_left", "eyewear", "왼쪽 안대", "headwear/accessories/eyepatch/facial_eyepatch_left.json", False),
    PackItem(
        "patch_right", "eyewear", "오른쪽 안대", "headwear/accessories/eyepatch/facial_eyepatch_right.json", False
    ),
    PackItem(
        "patch_small_left",
        "eyewear",
        "작은 왼쪽 안대",
        "headwear/accessories/eyepatch/facial_eyepatch_small_left.json",
        False,
    ),
    PackItem(
        "patch_small_right",
        "eyewear",
        "작은 오른쪽 안대",
        "headwear/accessories/eyepatch/facial_eyepatch_small_right.json",
        False,
    ),
    PackItem("patch_ambi", "eyewear", "양안대", "headwear/accessories/eyepatch/facial_eyepatch_ambi.json", False),
    PackItem("monocle_left", "eyewear", "왼쪽 모노클", "headwear/accessories/monocle/facial_monocle_left.json", False),
    PackItem(
        "monocle_right", "eyewear", "오른쪽 모노클", "headwear/accessories/monocle/facial_monocle_right.json", False
    ),
    PackItem(
        "monocle_frame_left",
        "eyewear",
        "왼쪽 프레임",
        "headwear/accessories/monocle/facial_monocle_left_frame.json",
        False,
    ),
    PackItem(
        "monocle_frame_right",
        "eyewear",
        "오른쪽 프레임",
        "headwear/accessories/monocle/facial_monocle_right_frame.json",
        False,
    ),
    *(
        PackItem(name.removeprefix("face_"), "expression", name, f"head/faces/{name}.json")
        for name in (
            "face_angry",
            "face_angry2",
            "face_blush",
            "face_closed",
            "face_closing",
            "face_eyeroll",
            "face_happy",
            "face_happy2",
            "face_look_l",
            "face_look_r",
            "face_neutral",
            "face_sad",
            "face_sad2",
            "face_shame",
            "face_shock",
            "face_tears",
        )
    ),
    PackItem("thick", "eyebrow", "굵은 눈썹", "head/eyebrows/eyebrows_thick.json"),
    PackItem("thin", "eyebrow", "얇은 눈썹", "head/eyebrows/eyebrows_thin.json"),
    PackItem("big", "nose", "큰 코", "head/nose/head_nose_big.json"),
    PackItem("button", "nose", "버튼 코", "head/nose/head_nose_button.json"),
    PackItem("elderly", "nose", "노년 코", "head/nose/head_nose_elderly.json"),
    PackItem("large", "nose", "넓은 코", "head/nose/head_nose_large.json"),
    PackItem("straight", "nose", "곧은 코", "head/nose/head_nose_straight.json"),
    PackItem("cyclops", "eyes", "특수 눈 1", "head/eyes/eyes_cyclops.json"),
    PackItem("cyclops2", "eyes", "특수 눈 2", "head/eyes/eyes_cyclops2.json"),
    PackItem("wrinkles", "wrinkles", "주름", "head/head_wrinkles.json"),
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
        relative = layer.get(body_type)
        if relative:
            head_type = "female" if body_type == "female" else "male"
            layers.append((int(layer.get("zPos", 100)), str(relative).replace("${head}", head_type)))
    return sorted(layers, key=lambda value: value[0])


def animation_source(folder: Path, animation: str, preferred_variant: str | None) -> Path | None:
    if preferred_variant:
        candidate = folder / animation / f"{preferred_variant}.png"
        if candidate.is_file():
            return candidate
    candidate = folder / f"{animation}.png"
    if candidate.is_file():
        return candidate
    variants = sorted((folder / animation).glob("*.png"))
    return variants[0] if variants else None


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
        body_types = BODY_TYPES if item.body_aware else ("male",)
        sources: dict[str, list[dict[str, Any]]] = {}
        animation_union: set[str] = set()
        declared = set(definition.get("animations") or ANIMATION_ROWS)
        for body_type in body_types:
            suffix = body_type if item.body_aware else "adult"
            rendered_layers: list[dict[str, Any]] = []
            paths = layer_paths(definition, body_type)
            if not paths and not item.body_aware:
                paths = layer_paths(definition, "female")
            for layer_index, (z_pos, relative) in enumerate(paths, start=1):
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
            for body_type in BODY_TYPES:
                sources[body_type] = sources["male"]
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
