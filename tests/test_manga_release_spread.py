"""Tests for Branchline's one-screen manga release experience."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
)
from branchline.presentation.release_spread import (
    SCENARIO_COPY,
    build_release_spread,
)


ART_DIRECTORY = Path(
    "assets/manga"
)

JAPANESE_CHARACTER_PATTERN = re.compile(
    r"[\u3040-\u30ff\u3400-\u9fff]"
)


def test_original_manga_panels_exist() -> None:
    expected = {
        "ending_a_manga.png",
        "ending_b_ready_manga.png",
        "ending_b_verified_manga.png",
        "ending_b_blocked_manga.png",
        "shared_dialogue_manga.png",
    }

    actual = {
        path.name
        for path in ART_DIRECTORY.glob(
            "*.png"
        )
    }

    assert actual >= expected

    for filename in expected:
        path = ART_DIRECTORY / filename

        assert path.stat().st_size > 20_000

        with Image.open(path) as image:
            assert image.size == (
                1600,
                1000,
            )
            assert image.mode == "RGB"


def test_manga_states_are_visually_distinct() -> None:
    ready = (
        ART_DIRECTORY
        / "ending_b_ready_manga.png"
    ).read_bytes()

    verified = (
        ART_DIRECTORY
        / "ending_b_verified_manga.png"
    ).read_bytes()

    blocked = (
        ART_DIRECTORY
        / "ending_b_blocked_manga.png"
    ).read_bytes()

    assert ready != verified
    assert verified != blocked
    assert ready != blocked


def test_selective_rebuild_has_exact_route_story() -> None:
    ready = build_release_spread(
        "scenario_b",
        READY,
    )

    planned = build_release_spread(
        "scenario_b",
        PLANNED,
    )

    complete = build_release_spread(
        "scenario_b",
        COMPLETE,
    )

    assert [
        panel["status"]
        for panel in ready["panels"]
    ] == [
        "PROTECTED",
        "CHANGE PENDING",
    ]

    assert [
        panel["status"]
        for panel in planned["panels"]
    ] == [
        "PRESERVE",
        "REBUILD",
    ]

    assert [
        panel["status"]
        for panel in complete["panels"]
    ] == [
        "VERIFIED",
        "VERIFIED",
    ]

    assert planned["action_label"] == (
        "Approve selective rebuild"
    )

    assert complete[
        "publication_status"
    ] == "SAFE_TO_PUBLISH"


def test_failure_is_contained_to_ending_b() -> None:
    complete = build_release_spread(
        "scenario_c",
        COMPLETE,
    )

    assert complete["blocked"] is True

    assert [
        panel["status"]
        for panel in complete["panels"]
    ] == [
        "VERIFIED",
        "BLOCKED",
    ]

    assert complete["panels"][1][
        "image"
    ].endswith(
        "ending_b_blocked_manga.png"
    )


def test_main_decision_never_exceeds_three_metrics() -> None:
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
            view = build_release_spread(
                scenario_id,
                phase,
            )

            assert len(
                view["metrics"]
            ) <= 3

            assert len(
                view["sponsor_strip"]
            ) == 3


def test_visible_release_copy_is_english_only() -> None:
    visible_copy = []

    for phases in SCENARIO_COPY.values():
        for copy in phases.values():
            visible_copy.extend(
                [
                    copy["eyebrow"],
                    copy["title"],
                    copy["body"],
                ]
            )

    assert not any(
        JAPANESE_CHARACTER_PATTERN.search(
            text
        )
        for text in visible_copy
    )


def test_app_uses_one_incident_selector_not_three_hero_buttons() -> None:
    source = Path("app.py").read_text()

    assert "ui.select(" in source
    assert "View technical proof" in source
    assert "screen()" in source

    assert "scenario-button" not in source
    assert "progress_rail" not in source
    assert "anime-route-ribbon" not in source

    # Desktop primary path is designed as one viewport.
    assert "height: 100vh" in source
    assert "overflow: hidden" in source
