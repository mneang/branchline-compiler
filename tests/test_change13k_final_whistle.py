"""Contract for the final 1280 × 720 playback fit."""

from pathlib import Path


def final_whistle_css() -> str:
    source = Path("app.py").read_text()

    marker = (
        "CHANGE 13K-J · "
        "FINAL WHISTLE FIT"
    )

    assert marker in source

    start = source.index(marker)

    end = source.index(
        "@media "
        "(prefers-reduced-motion: reduce)",
        start,
    )

    return source[start:end]


def test_short_viewport_player_fits_inside_overlay() -> None:
    css = final_whistle_css()

    assert (
        "max-height: 760px"
        in css
    )

    assert (
        "288px"
        in css
    )

    assert (
        "16 / 9"
        in css
    )


def test_player_remains_centered_and_undistorted() -> None:
    css = final_whistle_css()

    assert (
        "align-self: center"
        in css
    )

    assert (
        "object-fit: contain"
        in css
    )


def test_duplicate_post_player_copy_is_deferred() -> None:
    css = final_whistle_css()

    assert (
        "> .verified-panel-video"
        in css
    )

    assert (
        "~ *"
        in css
    )

    assert (
        "display: none"
        in css
    )
