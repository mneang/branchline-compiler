"""Tests for Branchline's one-screen release commands."""

from __future__ import annotations

from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
)
from branchline.presentation.one_screen_release import (
    build_one_screen_command,
    workflow_options,
)


def test_three_workflows_are_always_visible() -> None:
    options = workflow_options()

    assert [
        (
            option["id"],
            option["label"],
        )
        for option in options
    ] == [
        (
            "scenario_a",
            "Dialogue revision",
        ),
        (
            "scenario_b",
            "Visual revision",
        ),
        (
            "scenario_c",
            "Safety check",
        ),
    ]


def test_visual_revision_requires_two_primary_clicks() -> None:
    ready = build_one_screen_command(
        scenario_id="scenario_b",
        phase=READY,
        busy=False,
    )

    planned = build_one_screen_command(
        scenario_id="scenario_b",
        phase=PLANNED,
        busy=False,
        analysis={
            "metrics": {
                "assets_to_rebuild": 2,
                "assets_to_reuse": 4,
            },
        },
    )

    assert ready["primary_label"] == (
        "Analyze impact"
    )

    assert planned["primary_label"] == (
        "Approve 2-asset rebuild"
    )

    assert ready["primary_kind"] == "advance"
    assert planned["primary_kind"] == "advance"


def test_planned_state_has_three_metrics_maximum() -> None:
    command = build_one_screen_command(
        scenario_id="scenario_b",
        phase=PLANNED,
        busy=False,
    )

    assert len(command["metrics"]) == 3

    assert command["headline"] == (
        "Rebuild 2. Preserve 4."
    )

    assert (
        "shared voice"
        in command["explanation"]
    )


def test_live_execution_has_no_fake_percentage() -> None:
    command = build_one_screen_command(
        scenario_id="scenario_b",
        phase=PLANNED,
        busy=True,
        active_stage="guard",
    )

    assert command["metrics"] == []

    assert command["headline"] == (
        "Verifying every route"
    )

    assert command["primary_kind"] == (
        "disabled"
    )


def test_verified_state_has_one_decisive_verdict() -> None:
    command = build_one_screen_command(
        scenario_id="scenario_b",
        phase=COMPLETE,
        busy=False,
        execution={
            "release_id": (
                "ending-b-live-test"
            ),
        },
    )

    assert command["verdict"] == (
        "SAFE TO PUBLISH"
    )

    assert [
        metric["value"]
        for metric in command["metrics"]
    ] == [
        "6 / 6",
        "2 / 2",
        "0",
    ]

    assert (
        "ending-b-live-test"
        in command["lineage"]
    )

    assert command["primary_kind"] == (
        "media"
    )


def test_safety_state_preserves_the_healthy_route() -> None:
    command = build_one_screen_command(
        scenario_id="scenario_c",
        phase=COMPLETE,
        busy=False,
    )

    assert command["headline"] == (
        "No stale branches published."
    )

    assert command["verdict"] == (
        "PUBLICATION STOPPED"
    )

    assert (
        "Ending A remains publishable"
        in command["detail"]
    )

    assert command["primary_kind"] == (
        "proof"
    )
