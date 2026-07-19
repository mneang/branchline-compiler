"""Generate original anime-inspired environment art for Branchline."""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


OUTPUT_DIR = Path("assets/ui")
WIDTH = 1600
HEIGHT = 1000


def vertical_gradient(
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)

    for y in range(HEIGHT):
        ratio = y / max(HEIGHT - 1, 1)

        color = tuple(
            int(top[index] * (1 - ratio) + bottom[index] * ratio)
            for index in range(3)
        )

        draw.line(
            (0, y, WIDTH, y),
            fill=color,
        )

    return image.convert("RGBA")


def add_glow(
    image: Image.Image,
    *,
    x: int,
    y: int,
    radius: int,
    color: tuple[int, int, int],
    strength: int = 170,
) -> None:
    layer = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(layer)

    draw.ellipse(
        (
            x - radius,
            y - radius,
            x + radius,
            y + radius,
        ),
        fill=(*color, strength),
    )

    layer = layer.filter(
        ImageFilter.GaussianBlur(radius / 2)
    )

    image.alpha_composite(layer)


def draw_city(
    image: Image.Image,
    *,
    horizon: int,
    seed: int,
    window_color: tuple[int, int, int],
) -> None:
    random.seed(seed)
    draw = ImageDraw.Draw(image)

    x = 0

    while x < WIDTH:
        building_width = random.randint(50, 125)
        building_height = random.randint(80, 330)

        top = horizon - building_height

        shade = random.randint(12, 34)

        draw.rectangle(
            (
                x,
                top,
                x + building_width,
                horizon,
            ),
            fill=(shade, shade + 4, shade + 13, 255),
        )

        for window_x in range(
            x + 15,
            x + building_width - 10,
            22,
        ):
            for window_y in range(
                top + 18,
                horizon - 15,
                30,
            ):
                if random.random() > 0.58:
                    draw.rectangle(
                        (
                            window_x,
                            window_y,
                            window_x + 7,
                            window_y + 12,
                        ),
                        fill=(*window_color, random.randint(105, 220)),
                    )

        x += building_width + random.randint(4, 12)


def draw_stars(
    image: Image.Image,
    *,
    seed: int,
    count: int,
) -> None:
    random.seed(seed)
    draw = ImageDraw.Draw(image)

    for _ in range(count):
        x = random.randint(15, WIDTH - 15)
        y = random.randint(10, 420)
        radius = random.choice([1, 1, 1, 2])

        draw.ellipse(
            (
                x - radius,
                y - radius,
                x + radius,
                y + radius,
            ),
            fill=(220, 232, 255, random.randint(120, 230)),
        )


def draw_station_geometry(
    image: Image.Image,
    *,
    platform: tuple[int, int, int],
    line_color: tuple[int, int, int],
    horizon: int = 525,
) -> None:
    draw = ImageDraw.Draw(image)

    # Main platform plane.
    draw.polygon(
        [
            (0, HEIGHT),
            (0, horizon + 95),
            (760, horizon),
            (WIDTH, horizon + 150),
            (WIDTH, HEIGHT),
        ],
        fill=(*platform, 255),
    )

    # Track bed.
    draw.polygon(
        [
            (545, HEIGHT),
            (735, horizon + 30),
            (945, horizon + 43),
            (1370, HEIGHT),
        ],
        fill=(12, 15, 25, 255),
    )

    # Perspective track lines.
    vanishing = (820, horizon + 15)

    for bottom_x in (590, 710, 1185, 1325):
        draw.line(
            (
                bottom_x,
                HEIGHT,
                vanishing[0],
                vanishing[1],
            ),
            fill=(*line_color, 210),
            width=8,
        )

    # Platform guide lines.
    draw.line(
        (
            0,
            835,
            780,
            horizon + 40,
        ),
        fill=(244, 201, 81, 235),
        width=11,
    )

    draw.line(
        (
            WIDTH,
            905,
            860,
            horizon + 50,
        ),
        fill=(244, 201, 81, 205),
        width=8,
    )

    # Roof supports.
    for x in (105, 390, 1195, 1460):
        draw.polygon(
            [
                (x, 75),
                (x + 22, 75),
                (x + 70, HEIGHT),
                (x + 25, HEIGHT),
            ],
            fill=(20, 24, 37, 245),
        )

    draw.polygon(
        [
            (0, 0),
            (WIDTH, 0),
            (WIDTH, 105),
            (1020, 185),
            (490, 165),
            (0, 115),
        ],
        fill=(12, 16, 29, 245),
    )


def draw_station_lights(
    image: Image.Image,
    *,
    color: tuple[int, int, int],
    count: int,
) -> None:
    draw = ImageDraw.Draw(image)

    for index in range(count):
        ratio = index / max(count - 1, 1)

        x = int(150 + ratio * 1280)
        y = int(125 + abs(0.5 - ratio) * 60)

        add_glow(
            image,
            x=x,
            y=y,
            radius=50,
            color=color,
            strength=150,
        )

        draw.ellipse(
            (x - 10, y - 7, x + 10, y + 7),
            fill=(*color, 255),
        )


def draw_silhouette(
    image: Image.Image,
    *,
    x: int,
    y: int,
    scale: float,
    facing: str,
) -> None:
    draw = ImageDraw.Draw(image)

    head_radius = int(25 * scale)
    body_width = int(50 * scale)
    body_height = int(145 * scale)

    draw.ellipse(
        (
            x - head_radius,
            y - body_height - head_radius * 2,
            x + head_radius,
            y - body_height,
        ),
        fill=(8, 10, 19, 255),
    )

    direction = -1 if facing == "left" else 1

    draw.polygon(
        [
            (x - body_width, y),
            (x - body_width // 2, y - body_height),
            (x + body_width // 2, y - body_height),
            (x + body_width, y),
            (
                x + direction * int(35 * scale),
                y + int(30 * scale),
            ),
        ],
        fill=(7, 9, 18, 255),
    )

    draw.line(
        (
            x - int(22 * scale),
            y,
            x - int(35 * scale),
            y + int(105 * scale),
        ),
        fill=(7, 9, 18, 255),
        width=max(4, int(17 * scale)),
    )

    draw.line(
        (
            x + int(20 * scale),
            y,
            x + int(32 * scale),
            y + int(105 * scale),
        ),
        fill=(7, 9, 18, 255),
        width=max(4, int(17 * scale)),
    )


def draw_train(
    image: Image.Image,
    *,
    color: tuple[int, int, int],
    window: tuple[int, int, int],
) -> None:
    draw = ImageDraw.Draw(image)

    body = [
        (50, 410),
        (680, 445),
        (790, 535),
        (715, 710),
        (65, 785),
    ]

    draw.polygon(
        body,
        fill=(*color, 255),
        outline=(205, 221, 238, 225),
    )

    for index in range(6):
        x = 115 + index * 92

        draw.polygon(
            [
                (x, 477),
                (x + 65, 483),
                (x + 61, 575),
                (x - 1, 579),
            ],
            fill=(*window, 235),
        )

        add_glow(
            image,
            x=x + 32,
            y=530,
            radius=32,
            color=window,
            strength=85,
        )

    draw.line(
        (70, 682, 720, 626),
        fill=(235, 241, 249, 210),
        width=4,
    )


def add_speed_lines(
    image: Image.Image,
    *,
    color: tuple[int, int, int],
    seed: int,
) -> None:
    random.seed(seed)
    draw = ImageDraw.Draw(image)

    origin_x = 810
    origin_y = 500

    for _ in range(35):
        angle = random.uniform(
            math.radians(190),
            math.radians(350),
        )

        start = random.randint(480, 720)
        end = start + random.randint(70, 210)

        x1 = origin_x + math.cos(angle) * start
        y1 = origin_y + math.sin(angle) * start

        x2 = origin_x + math.cos(angle) * end
        y2 = origin_y + math.sin(angle) * end

        draw.line(
            (x1, y1, x2, y2),
            fill=(*color, random.randint(35, 90)),
            width=random.choice([1, 2, 3]),
        )


def finish(
    image: Image.Image,
    path: Path,
) -> None:
    image = image.convert("RGB")
    image.save(
        path,
        format="PNG",
        optimize=True,
    )


def ending_b_before() -> None:
    image = vertical_gradient(
        (17, 20, 48),
        (91, 28, 65),
    )

    draw_stars(image, seed=12, count=110)

    draw_city(
        image,
        horizon=535,
        seed=42,
        window_color=(255, 184, 116),
    )

    draw_station_geometry(
        image,
        platform=(49, 30, 49),
        line_color=(131, 107, 148),
    )

    draw_station_lights(
        image,
        color=(255, 176, 129),
        count=7,
    )

    draw_silhouette(
        image,
        x=1180,
        y=795,
        scale=1.25,
        facing="left",
    )

    add_glow(
        image,
        x=900,
        y=560,
        radius=170,
        color=(205, 86, 143),
        strength=95,
    )

    finish(
        image,
        OUTPUT_DIR / "ending_b_before.png",
    )


def ending_b_after() -> None:
    image = vertical_gradient(
        (8, 26, 52),
        (17, 78, 103),
    )

    draw_stars(image, seed=18, count=145)

    draw_city(
        image,
        horizon=530,
        seed=55,
        window_color=(119, 223, 255),
    )

    draw_station_geometry(
        image,
        platform=(21, 50, 67),
        line_color=(102, 214, 235),
    )

    draw_station_lights(
        image,
        color=(118, 239, 255),
        count=9,
    )

    draw_silhouette(
        image,
        x=1180,
        y=795,
        scale=1.25,
        facing="left",
    )

    add_glow(
        image,
        x=900,
        y=535,
        radius=220,
        color=(45, 192, 220),
        strength=120,
    )

    add_speed_lines(
        image,
        color=(132, 233, 255),
        seed=93,
    )

    finish(
        image,
        OUTPUT_DIR / "ending_b_after.png",
    )


def ending_a() -> None:
    image = vertical_gradient(
        (9, 18, 48),
        (29, 62, 112),
    )

    draw_stars(image, seed=25, count=150)

    draw_city(
        image,
        horizon=530,
        seed=70,
        window_color=(255, 223, 151),
    )

    draw_station_geometry(
        image,
        platform=(24, 39, 65),
        line_color=(113, 156, 222),
    )

    draw_station_lights(
        image,
        color=(255, 221, 151),
        count=8,
    )

    draw_train(
        image,
        color=(32, 63, 113),
        window=(255, 223, 151),
    )

    draw_silhouette(
        image,
        x=1260,
        y=805,
        scale=1.18,
        facing="left",
    )

    add_speed_lines(
        image,
        color=(157, 199, 255),
        seed=105,
    )

    finish(
        image,
        OUTPUT_DIR / "ending_a.png",
    )


def shared_dialogue() -> None:
    image = vertical_gradient(
        (22, 17, 55),
        (39, 61, 105),
    )

    draw_stars(image, seed=38, count=175)

    draw_city(
        image,
        horizon=535,
        seed=88,
        window_color=(215, 199, 255),
    )

    draw_station_geometry(
        image,
        platform=(35, 37, 67),
        line_color=(151, 142, 209),
    )

    draw_station_lights(
        image,
        color=(213, 192, 255),
        count=8,
    )

    draw_silhouette(
        image,
        x=790,
        y=795,
        scale=1.28,
        facing="right",
    )

    # Two diverging route glows.
    draw = ImageDraw.Draw(image)

    draw.line(
        (805, 710, 240, 965),
        fill=(107, 195, 255, 210),
        width=15,
    )

    draw.line(
        (825, 710, 1380, 965),
        fill=(255, 136, 190, 210),
        width=15,
    )

    add_glow(
        image,
        x=390,
        y=850,
        radius=160,
        color=(72, 169, 255),
        strength=80,
    )

    add_glow(
        image,
        x=1235,
        y=850,
        radius=160,
        color=(237, 92, 170),
        strength=80,
    )

    finish(
        image,
        OUTPUT_DIR / "shared_dialogue.png",
    )


def main() -> int:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ending_b_before()
    ending_b_after()
    ending_a()
    shared_dialogue()

    for path in sorted(
        OUTPUT_DIR.glob("*.png")
    ):
        print(
            f"✓ {path} "
            f"({path.stat().st_size:,} bytes)"
        )

    print("ORIGINAL UI ART COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
