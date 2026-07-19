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
    visible_copy = []

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

    assert ready["primary_action"] == (
        "Analyze impact"
    )

    assert planned["primary_action"] == (
        "Approve plan & replay verified release"
    )

    assert complete["primary_action"] == (
        "Replay scenario"
    )


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


def test_app_installs_visual_layer_without_new_navigation() -> None:
    source = Path("app.py").read_text()

    assert "install_anime_style()" in source
    assert "render_scene_fx(" in source
    assert "render_story_quote(" in source

    # The main experience remains three scenario choices,
    # not a growing application navigation system.
    assert source.count(
        '"SELECTIVE REBUILD"'
    ) == 1

    assert source.count(
        '"SAFETY CHECK"'
    ) == 1

    assert source.count(
        '"SHARED CHANGE"'
    ) == 1
