"""Guardrails for verified media inside Ending B."""

from __future__ import annotations

from pathlib import Path


def app_source() -> str:
    return Path("app.py").read_text()


def test_scenario_b_uses_verified_b2_service() -> None:
    source = app_source()

    assert "load_verified_media_bundle" in source
    assert "open_verified_media" in source
    assert "asyncio.to_thread(" in source
    assert "scenario_b" in source


def test_verified_media_is_embedded_in_ending_b() -> None:
    source = app_source()

    assert "panel-media-overlay" in source
    assert "verified-panel-video" in source
    assert "media_bundle=" in source
    assert "media_loading=" in source
    assert "media_tab=" in source
    assert "VERIFIED B2 MEDIA" in source


def test_before_and_verified_tabs_need_no_modal() -> None:
    source = app_source()

    assert "Before revision" in source
    assert "Verified release" in source
    assert "open_verified_media" in source
    assert "set_verified_media_tab" in source


def test_fallback_is_never_silently_claimed_as_b2() -> None:
    source = app_source()

    assert "LOCAL PRESENTATION FALLBACK" in source

    # app.py intentionally formats this sentence across adjacent
    # source-code string literals, so verify each honest phrase.
    assert "This video is a local presentation " in source
    assert "copy and is not being represented " in source
    assert "as direct B2 playback." in source

    assert "Remote playback unavailable" in source


def test_long_lived_credentials_are_not_rendered() -> None:
    source = app_source()

    renderer = source.split(
        "def render_panel(",
        1,
    )[1]

    if "def render_metric" in renderer:
        renderer = renderer.split(
            "def render_metric",
            1,
        )[0]

    assert "B2_APP_KEY" not in renderer
    assert "B2_KEY_ID" not in renderer
