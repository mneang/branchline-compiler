"""Generate original playable Branchline release previews."""

from __future__ import annotations

import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageOps,
)


ROOT = Path(__file__).resolve().parents[1]
MANGA_DIR = ROOT / "assets" / "manga"
OUTPUT_DIR = ROOT / "assets" / "release_media"
WORK_DIR = OUTPUT_DIR / "_source"

WIDTH = 1600
HEIGHT = 900
DURATION_SECONDS = 6
FPS = 30
AUDIO_RATE = 44_100


def font(
    size: int,
    *,
    bold: bool = False,
) -> ImageFont.ImageFont:
    candidates = [
        (
            "/usr/share/fonts/truetype/dejavu/"
            + (
                "DejaVuSans-Bold.ttf"
                if bold
                else "DejaVuSans.ttf"
            )
        ),
        (
            "/usr/share/fonts/truetype/liberation2/"
            + (
                "LiberationSans-Bold.ttf"
                if bold
                else "LiberationSans-Regular.ttf"
            )
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


def add_gradient(
    image: Image.Image,
) -> Image.Image:
    overlay = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(overlay)

    for y in range(HEIGHT):
        ratio = y / max(HEIGHT - 1, 1)

        top_alpha = int(
            max(
                0,
                75 * (1 - ratio * 3),
            )
        )

        bottom_alpha = int(
            max(
                0,
                215 * ((ratio - 0.45) / 0.55),
            )
        )

        alpha = max(
            top_alpha,
            bottom_alpha,
        )

        draw.line(
            (0, y, WIDTH, y),
            fill=(3, 6, 12, alpha),
        )

    return Image.alpha_composite(
        image.convert("RGBA"),
        overlay,
    ).convert("RGB")


def poster(
    *,
    source_name: str,
    output_name: str,
    eyebrow: str,
    title: str,
    dialogue: str,
    accent: tuple[int, int, int],
) -> Path:
    source_path = MANGA_DIR / source_name

    if not source_path.exists():
        raise RuntimeError(
            f"Missing manga source: {source_path}"
        )

    with Image.open(source_path) as source:
        canvas = ImageOps.fit(
            source.convert("RGB"),
            (WIDTH, HEIGHT),
            method=Image.Resampling.LANCZOS,
        )

    canvas = add_gradient(canvas)
    draw = ImageDraw.Draw(canvas)

    eyebrow_font = font(
        25,
        bold=True,
    )

    title_font = font(
        67,
        bold=True,
    )

    dialogue_font = font(
        31,
        bold=False,
    )

    draw.rounded_rectangle(
        (68, 61, 430, 118),
        radius=8,
        fill=(5, 9, 17, 215),
        outline=(*accent, 220),
        width=3,
    )

    draw.text(
        (91, 77),
        eyebrow,
        font=eyebrow_font,
        fill=(*accent, 255),
    )

    draw.text(
        (72, 650),
        title,
        font=title_font,
        fill=(248, 250, 252),
        stroke_width=2,
        stroke_fill=(5, 8, 14),
    )

    draw.rounded_rectangle(
        (70, 757, 1510, 845),
        radius=12,
        fill=(4, 8, 15, 222),
        outline=(225, 232, 240, 90),
        width=2,
    )

    draw.rectangle(
        (70, 757, 77, 845),
        fill=accent,
    )

    draw.text(
        (101, 782),
        f"“{dialogue}”",
        font=dialogue_font,
        fill=(241, 245, 249),
    )

    output = WORK_DIR / output_name

    canvas.save(
        output,
        format="PNG",
        optimize=True,
    )

    return output


def generate_ambient_audio(
    path: Path,
) -> None:
    total_frames = (
        DURATION_SECONDS
        * AUDIO_RATE
    )

    with wave.open(
        str(path),
        "wb",
    ) as audio:
        audio.setnchannels(2)
        audio.setsampwidth(2)
        audio.setframerate(AUDIO_RATE)

        for index in range(total_frames):
            time_value = (
                index / AUDIO_RATE
            )

            fade_in = min(
                1.0,
                time_value / 0.8,
            )

            fade_out = min(
                1.0,
                (
                    DURATION_SECONDS
                    - time_value
                )
                / 1.0,
            )

            envelope = max(
                0.0,
                min(
                    fade_in,
                    fade_out,
                ),
            )

            ambient = (
                0.028
                * math.sin(
                    2
                    * math.pi
                    * 55
                    * time_value
                )
                + 0.017
                * math.sin(
                    2
                    * math.pi
                    * 110
                    * time_value
                )
            )

            chime = 0.0

            for start in (
                1.25,
                4.1,
            ):
                elapsed = (
                    time_value - start
                )

                if 0 <= elapsed <= 1.5:
                    decay = math.exp(
                        -3.2 * elapsed
                    )

                    chime += (
                        0.055
                        * decay
                        * math.sin(
                            2
                            * math.pi
                            * 440
                            * elapsed
                        )
                    )

                    chime += (
                        0.025
                        * decay
                        * math.sin(
                            2
                            * math.pi
                            * 660
                            * elapsed
                        )
                    )

            sample = int(
                max(
                    -1.0,
                    min(
                        1.0,
                        (
                            ambient
                            + chime
                        )
                        * envelope,
                    ),
                )
                * 32767
            )

            packed = struct.pack(
                "<hh",
                sample,
                sample,
            )

            audio.writeframesraw(packed)


def ffmpeg_executable() -> str:
    try:
        import imageio_ffmpeg

        return (
            imageio_ffmpeg
            .get_ffmpeg_exe()
        )

    except (
        ImportError,
        RuntimeError,
    ):
        executable = shutil.which(
            "ffmpeg"
        )

        if executable:
            return executable

    raise RuntimeError(
        "No FFmpeg executable is available."
    )


def render_video(
    *,
    poster_path: Path,
    audio_path: Path,
    output_path: Path,
) -> None:
    executable = ffmpeg_executable()

    common = [
        executable,
        "-y",
        "-loglevel",
        "error",
        "-loop",
        "1",
        "-framerate",
        str(FPS),
        "-i",
        str(poster_path),
        "-i",
        str(audio_path),
        "-t",
        str(DURATION_SECONDS),
        "-vf",
        (
            "scale=1600:900,"
            "zoompan="
            "z='min(zoom+0.00045,1.04)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            f"d={DURATION_SECONDS * FPS}:"
            "s=1600x900:"
            f"fps={FPS},"
            "format=yuv420p"
        ),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        "-movflags",
        "+faststart",
    ]

    attempts = [
        common
        + [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "21",
            str(output_path),
        ],
        common
        + [
            "-c:v",
            "mpeg4",
            "-q:v",
            "3",
            str(output_path),
        ],
    ]

    errors = []

    for command in attempts:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if (
            result.returncode == 0
            and output_path.exists()
            and output_path.stat().st_size
            > 50_000
        ):
            return

        errors.append(
            result.stderr.strip()
        )

    raise RuntimeError(
        "FFmpeg could not render "
        f"{output_path.name}: "
        + " | ".join(errors)
    )


def build_preview(
    *,
    source_name: str,
    output_name: str,
    eyebrow: str,
    title: str,
    dialogue: str,
    accent: tuple[int, int, int],
    audio_path: Path,
) -> None:
    poster_path = poster(
        source_name=source_name,
        output_name=(
            output_name.replace(
                ".mp4",
                ".png",
            )
        ),
        eyebrow=eyebrow,
        title=title,
        dialogue=dialogue,
        accent=accent,
    )

    output_path = (
        OUTPUT_DIR
        / output_name
    )

    render_video(
        poster_path=poster_path,
        audio_path=audio_path,
        output_path=output_path,
    )

    print(
        f"✓ {output_path} "
        f"({output_path.stat().st_size:,} bytes)"
    )


def main() -> int:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    WORK_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    audio_path = (
        WORK_DIR
        / "original_station_ambience.wav"
    )

    generate_ambient_audio(
        audio_path
    )

    build_preview(
        source_name=(
            "ending_b_ready_manga.png"
        ),
        output_name=(
            "ending_b_before.mp4"
        ),
        eyebrow="BEFORE REVISION",
        title="Warm evening platform",
        dialogue=(
            "Cross the quiet platform "
            "before the last train leaves."
        ),
        accent=(236, 169, 73),
        audio_path=audio_path,
    )

    build_preview(
        source_name=(
            "ending_b_verified_manga.png"
        ),
        output_name=(
            "ending_b_after.mp4"
        ),
        eyebrow="AFTER SELECTIVE REBUILD",
        title="Illuminated night platform",
        dialogue=(
            "Cross the illuminated night platform."
        ),
        accent=(57, 205, 226),
        audio_path=audio_path,
    )

    build_preview(
        source_name=(
            "shared_dialogue_manga.png"
        ),
        output_name=(
            "shared_dialogue_before.mp4"
        ),
        eyebrow="ORIGINAL SHARED LINE",
        title="Last departure",
        dialogue=(
            "The last train leaves at seven."
        ),
        accent=(146, 119, 210),
        audio_path=audio_path,
    )

    build_preview(
        source_name=(
            "shared_dialogue_manga.png"
        ),
        output_name=(
            "shared_dialogue_after.mp4"
        ),
        eyebrow="REBUILT SHARED LINE",
        title="Last departure revised",
        dialogue=(
            "The last train leaves at eight."
        ),
        accent=(57, 205, 226),
        audio_path=audio_path,
    )

    build_preview(
        source_name=(
            "ending_b_blocked_manga.png"
        ),
        output_name=(
            "ending_b_blocked.mp4"
        ),
        eyebrow="PUBLICATION STOPPED",
        title="Ending B locked",
        dialogue=(
            "The required release preview "
            "could not be verified."
        ),
        accent=(223, 72, 103),
        audio_path=audio_path,
    )

    print(
        "PLAYABLE RELEASE MEDIA COMPLETED"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
