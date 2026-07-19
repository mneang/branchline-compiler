"""Guardrails for Branchline's anime-inspired presentation."""

from __future__ import annotations

import re
from pathlib import Path

from branchline.presentation.cinematic import (
    SCENE_CONFIG,
    build_cinematic_view,
)
from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
)


JAPANESE_CHARACTER_PATTERN = re.compile(
    r"[\u3040-\u30ff\u3400-\u9fff]"
)


def test_every_scene_has_restrained_visual_metadata() -> None:
    assert set(SCENE_CONFIG) == {
        "scenario_a",
        "scenario_b",
        "scenario_c",
    }

    for config in SCENE_CONFIG.values():
        assert config["accent"] in {
            "cyan",
            "violet",
            "rose",
        }

        assert config["chapter_label"]
        assert config["dialogue_line"]
        assert len(config["dialogue_line"]) <= 80


def test_visible_scene_copy_is_english_only() -> None:
    visible_copy: list[str] = []

    for config in SCENE_CONFIG.values():
        visible_copy.extend(
            [
                config["story_label"],
                config["route_label"],
                config["chapter_label"],
                config["dialogue_line"],
                config["ready_title"],
                config["ready_caption"],
                config["planned_title"],
                config["planned_caption"],
                config["complete_title"],
                config["complete_caption"],
            ]
        )

    assert not any(
        JAPANESE_CHARACTER_PATTERN.search(text)
        for text in visible_copy
    )


def test_visual_layer_preserves_two_click_hero_flow() -> None:
    ready = build_cinematic_view(
        "scenario_b",
        READY,
    )

    planned = build_cinematic_view(
        "scenario_b",
        PLANNED,
    )

    complete = build_cinematic_view(
        "scenario_b",
        COMPLETE,
    )

    assert ready["primary_action"] == "Analyze impact"

    assert planned["primary_action"] == (
        "Approve plan & replay verified release"
    )

    assert complete["primary_action"] == "Replay scenario"


def test_each_phase_keeps_the_same_story_identity() -> None:
    views = [
        build_cinematic_view(
            "scenario_b",
            phase,
        )
        for phase in (
            READY,
            PLANNED,
            COMPLETE,
        )
    ]

    assert {
        view["chapter_label"]
        for view in views
    } == {
        "CHAPTER 04 · NIGHT PLATFORM"
    }

    assert {
        view["dialogue_line"]
        for view in views
    } == {
        "Cross the illuminated night platform."
    }


def test_app_uses_focused_manga_release_studio() -> None:
    """Change 11 replaces the older layered anime dashboard."""
    source = Path("app.py").read_text()

    assert "build_release_spread" in source
    assert "app.add_static_files(" in source
    assert '"/manga-art"' in source

    assert "ui.select(" in source
    assert "View technical proof" in source

    assert "release-shell" in source
    assert "manga-panel" in source
    assert "decision-rail" in source
    assert "sponsor-strip" in source

    assert "screen()" in source

    # Old Change 10 layering should not remain in the rebuilt app.
    assert "install_anime_style()" not in source
    assert "render_scene_fx(" not in source
    assert "render_story_quote(" not in source

    # Alternative incidents stay secondary to the hero flow.
    assert "scenario-button" not in source
    assert "progress_rail" not in source
    assert "anime-route-ribbon" not in source
