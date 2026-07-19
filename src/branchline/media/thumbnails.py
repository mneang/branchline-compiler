"""Deterministic branch thumbnails with truthful dependency boundaries."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1280
HEIGHT = 720


def load_font(
    size: int,
    *,
    bold: bool = False,
) -> ImageFont.ImageFont:
    """Load a predictable local font with a safe fallback."""
    candidates = [
        (
            "/usr/share/fonts/truetype/dejavu/"
            f"DejaVuSans{'-Bold' if bold else ''}.ttf"
        ),
        (
            "/usr/share/fonts/truetype/liberation2/"
            f"LiberationSans-{'Bold' if bold else 'Regular'}.ttf"
        ),
    ]

    for candidate in candidates:
        path = Path(candidate)

        if path.exists():
            return ImageFont.truetype(
                str(path),
                size=size,
            )

    return ImageFont.load_default()


def create_branch_thumbnail(
    path: str | Path,
    *,
    branch_label: str,
    destination: str,
    background: tuple[int, int, int],
    release_label: str = "BRANCHLINE • VERIFIED STORY ASSET",
) -> Path:
    """Create a thumbnail derived only from branch-visual inputs.

    Deliberately excluded:
    - shared dialogue
    - voice text
    - captions
    - unrelated branch content

    This keeps the renderer consistent with story-graph dependencies.
    """
    output_path = Path(path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        background,
    )

    draw = ImageDraw.Draw(image)

    small = load_font(24, bold=True)
    heading = load_font(68, bold=True)
    destination_font = load_font(38, bold=True)
    footer = load_font(25)

    draw.rounded_rectangle(
        (54, 48, 1226, 672),
        radius=34,
        fill=(12, 16, 28),
        outline=(218, 224, 238),
        width=3,
    )

    draw.text(
        (96, 88),
        release_label,
        font=small,
        fill=(192, 202, 220),
    )

    draw.text(
        (96, 188),
        branch_label,
        font=heading,
        fill=(255, 255, 255),
    )

    draw.line(
        (96, 290, 650, 290),
        fill=(154, 166, 188),
        width=3,
    )

    draw.text(
        (96, 345),
        destination,
        font=destination_font,
        fill=(255, 225, 145),
    )

    draw.text(
        (96, 590),
        "Branch-specific visual • Content-addressed media",
        font=footer,
        fill=(154, 166, 188),
    )

    image.save(
        output_path,
        format="PNG",
        optimize=True,
    )

    return output_path
