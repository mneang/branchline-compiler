"""Tests for Branchline's fresh dependency analysis."""

from __future__ import annotations

import pytest

from branchline.application.live_analysis import (
    LiveAnalysisError,
    analysis_metrics,
    analyze_story_revision,
    validate_analysis_against_release,
)
from branchline.presentation.judge_view import (
    build_scenario_view,
)


def test_scenario_b_is_calculated_live() -> None:
    analysis = analyze_story_revision(
        "scenario_b"
    )

    assert analysis["mode"] == "LIVE_ANALYSIS"

    assert analysis["changed_sources"] == [
        "image.ending_b",
    ]

    assert analysis["stale_assets"] == [
        "preview.ending_b",
        "thumbnail.ending_b",
    ]

    assert analysis["reused_assets"] == [
        "caption.opening",
        "preview.ending_a",
        "thumbnail.ending_a",
        "voice.opening",
    ]

    assert analysis["affected_paths"] == [
        "ending_b",
    ]

    assert analysis["unaffected_paths"] == [
        "ending_a",
    ]

    assert analysis["metrics"][
        "assets_to_rebuild"
    ] == 2

    assert analysis["metrics"][
        "assets_to_reuse"
    ] == 4

    assert analysis["metrics"][
        "reuse_rate_percent"
    ] == 66.7


def test_scenario_a_is_calculated_live() -> None:
    analysis = analyze_story_revision(
        "scenario_a"
    )

    assert analysis["changed_sources"] == [
        "dialogue.opening",
    ]

    assert analysis["stale_assets"] == [
        "caption.opening",
        "preview.ending_a",
        "preview.ending_b",
        "voice.opening",
    ]

    assert analysis["reused_assets"] == [
        "thumbnail.ending_a",
        "thumbnail.ending_b",
    ]

    assert analysis["affected_paths"] == [
        "ending_a",
        "ending_b",
    ]


def test_live_plan_matches_verified_scenario_b() -> None:
    analysis = analyze_story_revision(
        "scenario_b"
    )

    scenario = build_scenario_view(
        "scenario_b"
    )

    validate_analysis_against_release(
        analysis,
        scenario,
    )


def test_plan_hash_is_stable_for_same_inputs() -> None:
    first = analyze_story_revision(
        "scenario_b"
    )

    second = analyze_story_revision(
        "scenario_b"
    )

    assert (
        first["plan_sha256"]
        == second["plan_sha256"]
    )

    assert len(first["plan_sha256"]) == 64


def test_creator_metrics_remain_concise() -> None:
    analysis = analyze_story_revision(
        "scenario_b"
    )

    metrics = analysis_metrics(
        analysis
    )

    assert metrics == [
        {
            "label": "REBUILD",
            "value": "2",
            "detail": "affected assets",
        },
        {
            "label": "PRESERVE",
            "value": "4",
            "detail": "verified B2 objects",
        },
        {
            "label": "REUSE",
            "value": "66.7%",
            "detail": "generation avoided",
        },
    ]


def test_safety_scenario_does_not_fake_live_analysis() -> None:
    with pytest.raises(
        LiveAnalysisError,
        match="does not support live analysis",
    ):
        analyze_story_revision(
            "scenario_c"
        )


def test_mismatch_blocks_presentation() -> None:
    analysis = analyze_story_revision(
        "scenario_b"
    )

    incorrect_scenario = {
        "rebuilt_assets": [
            "voice.opening",
        ],
        "reused_assets": [],
    }

    with pytest.raises(
        LiveAnalysisError,
        match="disagrees",
    ):
        validate_analysis_against_release(
            analysis,
            incorrect_scenario,
        )
