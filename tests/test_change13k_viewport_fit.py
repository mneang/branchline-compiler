"""Contract for the final 1280 × 720 command-deck fit."""

from pathlib import Path


def final_fit_css() -> str:
    source = Path("app.py").read_text()

    marker = (
        "CHANGE 13K-I · "
        "FINAL VIEWPORT FIT"
    )

    assert marker in source

    start = source.index(marker)

    end = source.index(
        "@media "
        "(prefers-reduced-motion: reduce)",
        start,
    )

    return source[start:end]


def test_release_shell_fits_the_judge_viewport() -> None:
    css = final_fit_css()

    assert (
        "calc(100vh - 82px)"
        in css
    )

    assert (
        "244px"
        in css
    )


def test_action_column_keeps_every_control_visible() -> None:
    css = final_fit_css()

    assert (
        ".command-actions > *"
        in css
    )

    assert (
        "flex-shrink: 0"
        in css
    )

    assert (
        "gap: 7px"
        in css
    )


def test_command_surface_stays_inside_the_viewport() -> None:
    css = final_fit_css()

    assert (
        "calc(100% - 4px)"
        in css
    )

    assert (
        "align-self: start"
        in css
    )
