"""Contracts for the final live verified-media finish."""

from pathlib import Path


def villa_css() -> str:
    source = Path("app.py").read_text()

    marker = (
        "CHANGE 13K-G · "
        "VILLA FINISH"
    )

    assert marker in source

    start = source.index(marker)

    end = source.index(
        "@media "
        "(prefers-reduced-motion: reduce)",
        start,
    )

    return source[start:end]


def test_live_overlay_is_the_target() -> None:
    css = villa_css()

    assert (
        ".panel-media-overlay"
        in css
    )

    assert (
        ".verified-panel-video"
        in css
    )


def test_live_video_uses_a_real_sixteen_by_nine_frame() -> None:
    css = villa_css()

    assert (
        "aspect-ratio:"
        in css
    )

    assert (
        "16 / 9"
        in css
    )

    assert (
        "370px"
        in css
    )

    assert (
        "object-fit: contain"
        in css
    )


def test_close_playback_is_secondary() -> None:
    css = villa_css()

    assert (
        ".one-screen-command.media-open"
        in css
    )

    assert (
        ".one-screen-primary.bg-primary"
        in css
    )

    assert (
        "background-image:"
        in css
    )

    assert (
        "none"
        in css
    )

    assert (
        "box-shadow: none"
        in css
    )


def test_next_workflow_remains_the_primary_finish() -> None:
    css = villa_css()

    assert (
        ".director-next"
        in css
    )

    assert (
        "min-height: 44px"
        in css
    )
