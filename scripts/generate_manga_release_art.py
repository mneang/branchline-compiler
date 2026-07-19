"""Transform Branchline's original environments into manga release panels.

All inputs are original procedural Branchline artwork. The transformation
creates grayscale ink, screentone, panel borders, and restrained workflow
spot colors without imitating an existing franchise or character.
"""

from __future__ import annotations

from pathlib import Path

from PIL import (
    Image,
    ImageChops,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageOps,
)


SOURCE_DIR = Path("assets/ui")
OUTPUT_DIR = Path("assets/manga")
CANVAS_SIZE = (1600, 1000)

CYAN = (57, 205, 226)
AMBER = (236, 169, 73)
ROSE = (223, 72, 103)
VIOLET = (146, 119, 210)


class MangaArtError(RuntimeError):
    """Raised when required source art is unavailable."""


def load_source(filename: str) -> Image.Image:
    path = SOURCE_DIR / filename

    if not path.exists():
        raise MangaArtError(
            f"Missing original Branchline artwork: {path}. "
            "Run scripts/generate_ui_art.py first."
        )

    with Image.open(path) as image:
        return image.convert("RGB").resize(
            CANVAS_SIZE,
            Image.Resampling.LANCZOS,
        )


def screentone_pattern(
    size: tuple[int, int],
    *,
    spacing: int = 11,
    radius: int = 2,
) -> Image.Image:
    """Create a traditional dot-pattern mask."""
    pattern = Image.new("L", size, 255)
    draw = ImageDraw.Draw(pattern)

    width, height = size

    for y in range(0, height, spacing):
        offset = spacing // 2 if (y // spacing) % 2 else 0

        for x in range(-offset, width, spacing):
            draw.ellipse(
                (
                    x - radius,
                    y - radius,
                    x + radius,
                    y + radius,
                ),
                fill=0,
            )

    return pattern


def add_panel_geometry(
    image: Image.Image,
    *,
    accent: tuple[int, int, int],
) -> Image.Image:
    """Add strong manga framing without embedding text."""
    result = image.convert("RGBA")
    overlay = Image.new(
        "RGBA",
        result.size,
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(overlay)

    width, height = result.size

    # Heavy exterior ink frame.
    draw.rectangle(
        (14, 14, width - 15, height - 15),
        outline=(9, 11, 16, 255),
        width=22,
    )

    draw.rectangle(
        (34, 34, width - 35, height - 35),
        outline=(245, 247, 250, 210),
        width=3,
    )

    # Asymmetric crop marks communicate authored panel composition.
    crop = 90
    line_width = 7

    draw.line(
        (44, 44, 44 + crop, 44),
        fill=(*accent, 230),
        width=line_width,
    )
    draw.line(
        (44, 44, 44, 44 + crop),
        fill=(*accent, 230),
        width=line_width,
    )

    draw.line(
        (width - 44, height - 44, width - 44 - crop, height - 44),
        fill=(*accent, 230),
        width=line_width,
    )
    draw.line(
        (width - 44, height - 44, width - 44, height - 44 - crop),
        fill=(*accent, 230),
        width=line_width,
    )

    return Image.alpha_composite(
        result,
        overlay,
    ).convert("RGB")


def apply_resolution_lines(
    image: Image.Image,
    *,
    accent: tuple[int, int, int],
) -> Image.Image:
    """Add restrained directional energy to a verified rebuilt panel."""
    result = image.convert("RGBA")
    overlay = Image.new(
        "RGBA",
        result.size,
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(overlay)

    width, height = result.size
    origin = (int(width * 0.72), int(height * 0.42))

    endpoints = [
        (-120, 180),
        (-90, 340),
        (-40, 520),
        (50, 760),
        (260, height + 100),
        (510, height + 130),
        (790, height + 170),
        (width + 100, 870),
        (width + 130, 690),
        (width + 150, 520),
    ]

    for index, endpoint in enumerate(endpoints):
        alpha = 40 + index * 5

        draw.line(
            (
                origin[0],
                origin[1],
                endpoint[0],
                endpoint[1],
            ),
            fill=(*accent, min(alpha, 95)),
            width=2 if index % 2 else 4,
        )

    result = Image.alpha_composite(
        result,
        overlay,
    )

    return result.convert("RGB")


def apply_blocked_treatment(
    image: Image.Image,
) -> Image.Image:
    """Crosshatch only the failed route rather than tinting the whole app."""
    result = image.convert("RGBA")

    shade = Image.new(
        "RGBA",
        result.size,
        (45, 4, 18, 90),
    )

    result = Image.alpha_composite(
        result,
        shade,
    )

    overlay = Image.new(
        "RGBA",
        result.size,
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(overlay)

    width, height = result.size

    for offset in range(-height, width, 42):
        draw.line(
            (
                offset,
                height,
                offset + height,
                0,
            ),
            fill=(*ROSE, 65),
            width=5,
        )

    for offset in range(0, width + height, 84):
        draw.line(
            (
                offset,
                0,
                offset - height,
                height,
            ),
            fill=(12, 13, 19, 70),
            width=3,
        )

    # Route-lock frame.
    draw.rectangle(
        (52, 52, width - 53, height - 53),
        outline=(*ROSE, 225),
        width=13,
    )

    return Image.alpha_composite(
        result,
        overlay,
    ).convert("RGB")


def manga_render(
    source: Image.Image,
    *,
    accent: tuple[int, int, int],
    resolved: bool = False,
    blocked: bool = False,
) -> Image.Image:
    """Create a high-contrast manga panel with one controlled spot color."""
    gray = ImageOps.grayscale(source)
    gray = ImageOps.autocontrast(
        gray,
        cutoff=2,
    )
    gray = ImageEnhance.Contrast(
        gray
    ).enhance(1.48)

    # Posterize values into more deliberate ink regions.
    poster = ImageOps.posterize(
        gray.convert("RGB"),
        bits=3,
    )
    poster = ImageEnhance.Contrast(
        poster
    ).enhance(1.18)

    # Extract and thicken scene edges.
    edges = gray.filter(
        ImageFilter.FIND_EDGES
    ).filter(
        ImageFilter.MaxFilter(3)
    )

    ink_mask = edges.point(
        lambda value: (
            0
            if value > 34
            else 255
        )
    )

    ink_rgb = Image.merge(
        "RGB",
        (
            ink_mask,
            ink_mask,
            ink_mask,
        ),
    )

    inked = ImageChops.multiply(
        poster,
        ink_rgb,
    )

    # Apply screentone primarily to shadows.
    tone = screentone_pattern(
        inked.size,
    )

    tone_rgb = Image.merge(
        "RGB",
        (
            tone,
            tone,
            tone,
        ),
    )

    shadow_mask = gray.point(
        lambda value: int(
            max(
                0,
                min(
                    255,
                    (158 - value) * 2.45,
                ),
            )
        )
    )

    toned_version = ImageChops.multiply(
        inked,
        tone_rgb,
    )

    inked = Image.composite(
        toned_version,
        inked,
        shadow_mask,
    )

    # Spot color appears only in bright environmental details.
    light_mask = gray.point(
        lambda value: int(
            max(
                0,
                min(
                    170,
                    (value - 154) * 2.0,
                ),
            )
        )
    )

    accent_image = Image.new(
        "RGB",
        inked.size,
        accent,
    )

    accented_highlights = Image.composite(
        accent_image,
        inked,
        light_mask,
    )

    result = Image.blend(
        inked,
        accented_highlights,
        0.38,
    )

    result = add_panel_geometry(
        result,
        accent=accent,
    )

    if resolved:
        result = apply_resolution_lines(
            result,
            accent=accent,
        )

    if blocked:
        result = apply_blocked_treatment(
            result
        )

    result = ImageEnhance.Sharpness(
        result
    ).enhance(1.35)

    return result


def write_panel(
    *,
    source_name: str,
    output_name: str,
    accent: tuple[int, int, int],
    resolved: bool = False,
    blocked: bool = False,
) -> None:
    source = load_source(source_name)

    output = manga_render(
        source,
        accent=accent,
        resolved=resolved,
        blocked=blocked,
    )

    path = OUTPUT_DIR / output_name

    output.save(
        path,
        format="PNG",
        optimize=True,
    )

    print(
        f"✓ {path} "
        f"({path.stat().st_size:,} bytes)"
    )


def main() -> int:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_panel(
        source_name="ending_a.png",
        output_name="ending_a_manga.png",
        accent=CYAN,
    )

    write_panel(
        source_name="ending_b_before.png",
        output_name="ending_b_ready_manga.png",
        accent=AMBER,
    )

    write_panel(
        source_name="ending_b_after.png",
        output_name="ending_b_verified_manga.png",
        accent=CYAN,
        resolved=True,
    )

    write_panel(
        source_name="ending_b_after.png",
        output_name="ending_b_blocked_manga.png",
        accent=ROSE,
        blocked=True,
    )

    write_panel(
        source_name="shared_dialogue.png",
        output_name="shared_dialogue_manga.png",
        accent=VIOLET,
    )

    print("MANGA RELEASE ART COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
