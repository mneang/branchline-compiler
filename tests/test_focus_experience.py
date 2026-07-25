"""Tests for Branchline's phase-driven focus experience."""

from __future__ import annotations

from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
)
from branchline.presentation.focus_experience import (
    build_focus_experience,
    director_options,
)


def test_director_exposes_three_real_workflows() -> None:
    options = director_options()

    assert [
        item["id"]
        for item in options
    ] == [
        "scenario_b",
        "scenario_a",
        "scenario_c",
    ]

    assert all(
        item["title"]
        and item["summary"]
        and item["result"]
        for item in options
    )


def test_ready_state_is_creator_focused() -> None:
    focus = build_focus_experience(
        scenario_id="scenario_b",
        phase=READY,
        busy=False,
        proof_mode=False,
        execution_mode=None,
    )

    assert focus["stage"] == "OBSERVE"
    assert focus["compact_shell"] is True
    assert focus["show_lineage"] is False
    assert focus["show_sponsor_strip"] is False

    assert focus[
        "panels"
    ]["right"]["badges"] == [
        "REVISION DETECTED",
    ]


def test_planned_state_spotlights_only_affected_route() -> None:
    focus = build_focus_experience(
        scenario_id="scenario_b",
        phase=PLANNED,
        busy=False,
        proof_mode=False,
        execution_mode=None,
    )

    assert focus["stage"] == (
        "DIAGNOSE + PLAN"
    )

    assert focus[
        "panels"
    ]["left"]["class"] == (
        "panel-preserved"
    )

    assert focus[
        "panels"
    ]["right"]["class"] == (
        "panel-affected"
    )

    assert focus[
        "panels"
    ]["right"]["badges"] == [
        "ROUTE ARTWORK · REBUILD",
        "ROUTE PREVIEW · REBUILD",
    ]


def test_live_execution_moves_action_into_panels() -> None:
    focus = build_focus_experience(
        scenario_id="scenario_b",
        phase=PLANNED,
        busy=True,
        proof_mode=False,
        execution_mode="LIVE_EXECUTION",
        active_stage="build",
    )

    assert focus["stage"] == "ACT"

    assert focus[
        "context_bar"
    ]["value"] == (
        "LIVE SELECTIVE RELEASE"
    )

    assert focus[
        "panels"
    ]["right"]["class"] == (
        "panel-working"
    )


def test_complete_state_restores_full_proof() -> None:
    focus = build_focus_experience(
        scenario_id="scenario_b",
        phase=COMPLETE,
        busy=False,
        proof_mode=False,
        execution_mode="LIVE_EXECUTION",
    )

    assert focus["stage"] == (
        "VERIFY + RECORD"
    )

    assert focus["show_lineage"] is True
    assert focus["show_sponsor_strip"] is True
    assert focus["compact_shell"] is False

    assert focus[
        "panels"
    ]["left"]["badges"] == [
        "PRESERVED · VERIFIED",
    ]

    assert focus[
        "panels"
    ]["right"]["badges"] == [
        "REBUILT · VERIFIED",
    ]


def test_proof_mode_expands_evidence_before_completion() -> None:
    focus = build_focus_experience(
        scenario_id="scenario_b",
        phase=READY,
        busy=False,
        proof_mode=True,
        execution_mode=None,
    )

    assert focus["show_lineage"] is True
    assert focus["show_sponsor_strip"] is True
    assert focus["compact_shell"] is False
