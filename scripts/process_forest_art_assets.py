"""Normalize generated forest artwork into the runtime sprite formats."""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image


def remove_checker(image: Image.Image) -> Image.Image:
    """Remove a neutral checkerboard without erasing gray details inside outlines."""
    rgba = image.convert("RGBA")
    pixels = rgba.load()

    def is_background(x: int, y: int) -> bool:
        red, green, blue, alpha = pixels[x, y]
        return alpha == 0 or (
            max(red, green, blue) - min(red, green, blue) <= 16
            and (red + green + blue) / 3 >= 205
        )

    queue: deque[tuple[int, int]] = deque()
    visited = bytearray(rgba.width * rgba.height)
    for x in range(rgba.width):
        queue.append((x, 0))
        queue.append((x, rgba.height - 1))
    for y in range(rgba.height):
        queue.append((0, y))
        queue.append((rgba.width - 1, y))

    while queue:
        x, y = queue.popleft()
        index = y * rgba.width + x
        if visited[index] or not is_background(x, y):
            continue
        visited[index] = 1
        red, green, blue, _ = pixels[x, y]
        pixels[x, y] = (red, green, blue, 0)
        if x:
            queue.append((x - 1, y))
        if x + 1 < rgba.width:
            queue.append((x + 1, y))
        if y:
            queue.append((x, y - 1))
        if y + 1 < rgba.height:
            queue.append((x, y + 1))
    return rgba


def pack_grid(
    image: Image.Image,
    columns: int,
    rows: int,
    cell_size: int,
    row_breaks: list[int] | None = None,
    column_row_breaks: list[list[int]] | None = None,
) -> Image.Image:
    """Repack a loose generated grid into equal, bottom-aligned square cells."""
    source = remove_checker(image)
    atlas = Image.new("RGBA", (columns * cell_size, rows * cell_size), (0, 0, 0, 0))
    margin = max(8, cell_size // 24)
    for row in range(rows):
        for column in range(columns):
            left = round(source.width * column / columns)
            active_breaks = column_row_breaks[column] if column_row_breaks else row_breaks
            top = active_breaks[row] if active_breaks else round(source.height * row / rows)
            right = round(source.width * (column + 1) / columns)
            bottom = active_breaks[row + 1] if active_breaks else round(source.height * (row + 1) / rows)
            frame = source.crop((left, top, right, bottom))
            bbox = frame.getchannel("A").getbbox()
            if bbox is None:
                continue
            frame = frame.crop(bbox)
            scale = min(
                (cell_size - 2 * margin) / frame.width,
                (cell_size - 2 * margin) / frame.height,
            )
            target_size = (
                max(1, round(frame.width * scale)),
                max(1, round(frame.height * scale)),
            )
            frame = frame.resize(target_size, Image.Resampling.LANCZOS)
            x = column * cell_size + (cell_size - frame.width) // 2
            y = row * cell_size + cell_size - margin - frame.height
            atlas.alpha_composite(frame, (x, y))
    return atlas


def resize_grid(image: Image.Image, size: int) -> Image.Image:
    """Remove preview checkerboard and resize a square animation atlas."""
    source = remove_checker(image)
    return source.resize((size, size), Image.Resampling.LANCZOS)


def clean_object(image: Image.Image) -> Image.Image:
    """Remove checkerboard and tightly pad a standalone object."""
    source = remove_checker(image)
    bbox = source.getchannel("A").getbbox()
    if bbox is None:
        return source
    cropped = source.crop(bbox)
    padding = max(8, round(max(cropped.size) * 0.04))
    output = Image.new(
        "RGBA",
        (cropped.width + padding * 2, cropped.height + padding * 2),
        (0, 0, 0, 0),
    )
    output.alpha_composite(cropped, (padding, padding))
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("pack-grid", "resize-grid", "clean-object"))
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--columns", type=int, default=5)
    parser.add_argument("--rows", type=int, default=4)
    parser.add_argument("--cell-size", type=int, default=256)
    parser.add_argument(
        "--row-breaks",
        help="Comma-separated source y coordinates, including 0 and image height",
    )
    parser.add_argument(
        "--column-row-breaks",
        help="Semicolon-separated row-break lists, one list per source column",
    )
    parser.add_argument("--size", type=int, default=512)
    args = parser.parse_args()

    with Image.open(args.source) as image:
        if args.mode == "pack-grid":
            row_breaks = [int(value) for value in args.row_breaks.split(",")] if args.row_breaks else None
            column_row_breaks = (
                [[int(value) for value in group.split(",")] for group in args.column_row_breaks.split(";")]
                if args.column_row_breaks
                else None
            )
            if row_breaks and len(row_breaks) != args.rows + 1:
                parser.error("--row-breaks must contain rows + 1 coordinates")
            if column_row_breaks and (
                len(column_row_breaks) != args.columns
                or any(len(group) != args.rows + 1 for group in column_row_breaks)
            ):
                parser.error("--column-row-breaks must contain one rows + 1 list per column")
            result = pack_grid(
                image,
                args.columns,
                args.rows,
                args.cell_size,
                row_breaks,
                column_row_breaks,
            )
        elif args.mode == "resize-grid":
            result = resize_grid(image, args.size)
        else:
            result = clean_object(image)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.save(args.output, optimize=True)


if __name__ == "__main__":
    main()
