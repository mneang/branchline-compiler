"""Tests for Branchline's cinematic creator experience."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from branchline.presentation.cinematic import (
    build_cinematic_view,
)
from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
)


ART_DIR = Path("assets/ui")


def test_original_story_art_exists() -> None:
    expected = {
        "ending_a.png",
        "ending_b_before.png",
        "ending_b_after.png",
        "shared_dialogue.png",
    }

    assert {
        path.name
        for path in ART_DIR.glob("*.png")
    } >= expected

    for filename in expected:
        path = ART_DIR / filename

        assert path.stat().st_size > 20_000

        with Image.open(path) as image:
            assert image.size == (1600, 1000)
            assert image.mode == "RGB"


def test_scenario_b_visually_transforms() -> None:
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

    assert ready["image"].endswith(
        "ending_b_before.png"
    )

    assert planned["image"].endswith(
        "ending_b_before.png"
    )

    assert complete["image"].endswith(
        "ending_b_after.png"
    )

    assert len(
        planned["summary_metrics"]
    ) == 3

    assert complete["blocked"] is False


def test_scenario_b_preserves_ending_a() -> None:
    planned = build_cinematic_view(
        "scenario_b",
        PLANNED,
    )

    route_states = {
        route["path_id"]: route["status"]
        for route in planned[
            "route_cards"
        ]
    }

    assert route_states == {
        "ending_a": "PRESERVE",
        "ending_b": "REBUILD",
    }


def test_scenario_c_locks_only_ending_b() -> None:
    complete = build_cinematic_view(
        "scenario_c",
        COMPLETE,
    )

    route_states = {
        route["path_id"]: route["status"]
        for route in complete[
            "route_cards"
        ]
    }

    assert complete["blocked"] is True

    assert route_states == {
        "ending_a": "VERIFIED",
        "ending_b": "BLOCKED",
    }


def test_main_experience_never_exposes_more_than_three_metrics() -> None:
    for scenario_id in (
        "scenario_a",
        "scenario_b",
        "scenario_c",
    ):
        for phase in (
            READY,
            PLANNED,
            COMPLETE,
        ):
            view = build_cinematic_view(
                scenario_id,
                phase,
            )

            assert len(
                view["summary_metrics"]
            ) <= 3
