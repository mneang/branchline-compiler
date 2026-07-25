"""Guardrails for Branchline's restrained interaction choreography."""

from pathlib import Path


def app_source() -> str:
    return Path("app.py").read_text()


def test_la_pelopina_motion_layer_exists() -> None:
    source = app_source()

    assert (
        "Change 13I: La Pelopina motion layer"
        in source
    )

    assert (
        "branchline-panel-arrive-left"
        in source
    )

    assert (
        "branchline-panel-arrive-right"
        in source
    )

    assert (
        "branchline-media-reveal"
        in source
    )


def test_motion_is_stateful_not_infinite() -> None:
    source = app_source()

    assert "animation-iteration-count: infinite" not in source
    assert " infinite " not in source

    assert (
        "branchline-panel-arrive-left"
        in source
    )

    assert "both;" in source


def test_reduced_motion_is_supported() -> None:
    source = app_source()

    assert (
        "prefers-reduced-motion: reduce"
        in source
    )

    assert (
        "animation: none !important"
        in source
    )

    assert (
        "transition: none !important"
        in source
    )


def test_existing_product_surfaces_receive_motion() -> None:
    source = app_source()

    for selector in (
        ".manga-panel",
        ".story-strip",
        ".panel-media-overlay",
        ".proof-node",
        ".proof-causal-arrow",
        ".command-sponsor-line",
    ):
        assert selector in source


def test_active_scenario_and_keyboard_focus_are_visible() -> None:
    source = app_source()

    assert ".q-tab--active" in source
    assert ".q-btn:focus-visible" in source
    assert ".manga-panel:focus-within" in source
