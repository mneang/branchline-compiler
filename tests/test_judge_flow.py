"""Tests for Branchline's minimal judge interaction."""

from __future__ import annotations

from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
    next_phase,
    primary_action_label,
    step_label,
)


def test_hero_release_uses_two_meaningful_clicks() -> None:
    phase = READY

    assert primary_action_label(
        "scenario_b",
        phase,
    ) == "Analyze impact"

    phase = next_phase(
        "scenario_b",
        phase,
    )

    assert phase == PLANNED

    assert primary_action_label(
        "scenario_b",
        phase,
    ) == (
        "Approve plan & replay verified release"
    )

    phase = next_phase(
        "scenario_b",
        phase,
    )

    assert phase == COMPLETE


def test_safety_check_uses_one_meaningful_click() -> None:
    assert next_phase(
        "scenario_c",
        READY,
    ) == COMPLETE

    assert primary_action_label(
        "scenario_c",
        READY,
    ) == "Verify reachable media"


def test_completed_flow_can_reset() -> None:
    assert next_phase(
        "scenario_b",
        COMPLETE,
    ) == READY


def test_progress_copy_is_concise() -> None:
    assert step_label(
        "scenario_b",
        READY,
    ) == "1 OF 2 · CHANGE DETECTED"

    assert step_label(
        "scenario_c",
        COMPLETE,
    ) == "VERIFIED"
