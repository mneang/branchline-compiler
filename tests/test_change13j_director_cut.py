"""Director's Cut presentation guardrails."""

from branchline.presentation.director_cut import (
    AUDIENCE,
    build_change_receipt,
    build_director_cut,
    build_proof_cells,
    build_release_rail,
    replay_action,
)
from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
)


def test_audience_is_explicit() -> None:
    assert AUDIENCE == (
        "FOR VISUAL NOVEL & INTERACTIVE COMIC TEAMS"
    )


def test_dialogue_change_is_visible_without_playback() -> None:
    receipt = build_change_receipt(
        "scenario_a"
    )

    assert "seven" in receipt["before"]
    assert "eight" in receipt["after"]
    assert "1 linked Genblaze run" in (
        receipt["impact"]
    )


def test_visual_change_explains_selective_scope() -> None:
    receipt = build_change_receipt(
        "scenario_b"
    )

    assert receipt["subject"] == (
        "Ending B artwork"
    )

    assert "2 rebuild" in receipt["impact"]
    assert "4 preserve" in receipt["impact"]
    assert "byte-identical" in receipt["impact"]


def test_ready_rail_starts_at_change() -> None:
    rail = build_release_rail(
        scenario_id="scenario_b",
        phase=READY,
        busy=False,
    )

    assert rail[0] == {
        "label": "CHANGE",
        "status": "active",
    }

    assert all(
        item["status"] == "pending"
        for item in rail[1:]
    )


def test_planned_rail_waits_for_approval() -> None:
    rail = build_release_rail(
        scenario_id="scenario_a",
        phase=PLANNED,
        busy=False,
    )

    assert [
        item["status"]
        for item in rail
    ] == [
        "done",
        "done",
        "done",
        "active",
        "pending",
        "pending",
    ]


def test_complete_success_finishes_every_stage() -> None:
    rail = build_release_rail(
        scenario_id="scenario_b",
        phase=COMPLETE,
        busy=False,
    )

    assert all(
        item["status"] == "done"
        for item in rail
    )


def test_safety_publish_stage_is_blocked() -> None:
    rail = build_release_rail(
        scenario_id="scenario_c",
        phase=COMPLETE,
        busy=False,
    )

    assert rail[-1] == {
        "label": "PUBLISH",
        "status": "blocked",
    }


def test_visual_proof_cells_assign_responsibility() -> None:
    cells = build_proof_cells(
        scenario_id="scenario_b",
        phase=COMPLETE,
        busy=False,
    )

    assert [
        cell["label"]
        for cell in cells
    ] == [
        "GENBLAZE",
        "B2 BYTES",
        "BRANCHLINE GUARD",
    ]

    assert cells[0]["value"] == (
        "0 new AI requests"
    )

    assert cells[1]["value"] == (
        "6 / 6 matches"
    )


def test_safety_cells_do_not_claim_global_success() -> None:
    cells = build_proof_cells(
        scenario_id="scenario_c",
        phase=COMPLETE,
        busy=False,
    )

    assert cells[1]["value"] == (
        "5 matches · 1 missing"
    )

    assert cells[2]["value"] == (
        "Ending B blocked"
    )


def test_complete_phase_exposes_replay() -> None:
    action = replay_action(
        COMPLETE
    )

    assert action is not None
    assert action["label"] == (
        "Replay workflow"
    )

    assert replay_action(
        READY
    ) is None


def test_aggregate_contains_all_surfaces() -> None:
    result = build_director_cut(
        scenario_id="scenario_a",
        phase=COMPLETE,
        busy=False,
    )

    assert set(result) == {
        "audience",
        "change",
        "rail",
        "proof_cells",
        "next_workflow",
        "replay",
    }
