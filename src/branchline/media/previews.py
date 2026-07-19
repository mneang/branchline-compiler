"""Deterministic preview frames whose inputs match story dependencies."""

from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

from branchline.media.thumbnails import (
    HEIGHT,
    WIDTH,
    load_font,
)


def create_story_preview_frame(
    path: str | Path,
    *,
    branch_label: str,
    destination: str,
    dialogue: str,
    background: tuple[int, int, int],
) -> Path:
    """Render a frame derived from branch visuals and shared dialogue."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        background,
    )

    draw = ImageDraw.Draw(image)

    small = load_font(23, bold=True)
    heading = load_font(57, bold=True)
    dialogue_font = load_font(36)
    destination_font = load_font(29, bold=True)

    draw.rounded_rectangle(
        (52, 46, 1228, 674),
        radius=34,
        fill=(12, 16, 28),
        outline=(218, 224, 238),
        width=3,
    )

    draw.text(
        (94, 82),
        "BRANCHLINE • STORY PREVIEW",
        font=small,
        fill=(192, 202, 220),
    )

    draw.text(
        (94, 146),
        branch_label,
        font=heading,
        fill=(255, 255, 255),
    )

    draw.line(
        (94, 236, 700, 236),
        fill=(154, 166, 188),
        width=3,
    )

    y = 290

    for line in textwrap.wrap(dialogue, width=45):
        draw.text(
            (94, y),
            line,
            font=dialogue_font,
            fill=(229, 233, 242),
        )
        y += 48

    draw.text(
        (94, 548),
        destination,
        font=destination_font,
        fill=(255, 225, 145),
    )

    draw.text(
        (94, 612),
        "Voice + caption + branch visual",
        font=small,
        fill=(154, 166, 188),
    )

    image.save(
        output_path,
        format="PNG",
        optimize=True,
    )

    return output_path
