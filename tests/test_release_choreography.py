"""Tests for Branchline's dynamic release choreography."""

from __future__ import annotations

from branchline.application.live_analysis import (
    analyze_story_revision,
)
from branchline.presentation.judge_view import (
    build_scenario_view,
)
from branchline.presentation.release_choreography import (
    build_causal_route,
    build_revision_story,
    build_verified_replay_stages,
    media_comparison,
    validate_replay_stage,
)


def test_human_readable_selective_rebuild_diff() -> None:
    analysis = analyze_story_revision(
        "scenario_b"
    )

    revision = build_revision_story(
        "scenario_b",
        analysis,
    )

    assert revision["subject"] == (
        "Ending B platform scene"
    )

    assert revision["before"] == (
        "Warm evening platform"
    )

    assert revision["after"] == (
        "Illuminated night platform"
    )

    assert revision["calculated_source_ids"] == [
        "image.ending_b",
    ]

    assert len(
        revision["plan_sha256"]
    ) == 64


def test_selective_rebuild_has_concise_causal_route() -> None:
    route = build_causal_route(
        "scenario_b"
    )

    assert route == {
        "source": "ENDING B SCENE",
        "assets": [
            "ROUTE ARTWORK",
            "ROUTE PREVIEW",
        ],
        "destination": "ENDING B",
        "result": "2 assets rebuild",
        "preserved": (
            "Ending A remains untouched"
        ),
    }


def test_scenario_b_replay_stages_are_evidence_backed() -> None:
    analysis = analyze_story_revision(
        "scenario_b"
    )

    scenario = build_scenario_view(
        "scenario_b"
    )

    stages = build_verified_replay_stages(
        "scenario_b"
    )

    assert len(stages) == 5

    for stage in stages:
        validate_replay_stage(
            stage,
            scenario_id="scenario_b",
            scenario=scenario,
            analysis=analysis,
        )


def test_scenario_c_replay_stages_prove_containment() -> None:
    scenario = build_scenario_view(
        "scenario_c"
    )

    stages = build_verified_replay_stages(
        "scenario_c"
    )

    assert len(stages) == 4

    for stage in stages:
        validate_replay_stage(
            stage,
            scenario_id="scenario_c",
            scenario=scenario,
            analysis=None,
        )


def test_every_scenario_has_playable_media() -> None:
    for scenario_id in (
        "scenario_a",
        "scenario_b",
        "scenario_c",
    ):
        comparison = media_comparison(
            scenario_id
        )

        assert comparison["before"].endswith(
            ".mp4"
        )

        assert comparison["after"].endswith(
            ".mp4"
        )
