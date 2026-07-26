"""Contracts for Branchline's no-scroll spacing pass."""

from pathlib import Path


def pelopina_css() -> str:
    source = Path("app.py").read_text()

    start_marker = (
        "CHANGE 13K-E · "
        "LA PELOPINA SPACING LOCK"
    )

    assert start_marker in source

    start = source.index(
        start_marker
    )

    end_marker = (
        "@media "
        "(prefers-reduced-motion: reduce)"
    )

    end = source.index(
        end_marker,
        start,
    )

    return source[start:end]


def test_decision_deck_receives_a_guaranteed_row() -> None:
    css = pelopina_css()

    assert (
        "clamp("
        in css
    )

    assert (
        "224px"
        in css
    )

    assert (
        "grid-template-rows:"
        in css
    )


def test_artwork_flexes_instead_of_forcing_page_height() -> None:
    css = pelopina_css()

    assert (
        ".spread-stage"
        in css
    )

    assert (
        "min-height: 0 !important;"
        in css
    )


def test_redundant_main_screen_copy_is_removed() -> None:
    css = pelopina_css()

    assert (
        ".director-change-subject"
        in css
    )

    assert (
        ".director-change-impact"
        in css
    )

    assert (
        ".one-screen-command.observe"
        in css
    )


def test_three_decision_columns_have_real_padding() -> None:
    css = pelopina_css()

    assert (
        ".command-copy,"
        in css
    )

    assert (
        ".command-evidence,"
        in css
    )

    assert (
        ".command-actions"
        in css
    )

    assert (
        "16px 22px"
        in css
    )


def test_primary_action_has_judge_facing_presence() -> None:
    css = pelopina_css()

    assert (
        ".one-screen-primary"
        in css
    )

    assert (
        "min-height: 52px"
        in css
    )
