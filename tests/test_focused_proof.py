"""Tests for Branchline's concise causal proof."""

from __future__ import annotations

from branchline.presentation.focused_proof import (
    build_focused_proof,
)


def test_visual_proof_has_no_more_than_five_nodes() -> None:
    proof = build_focused_proof(
        scenario_id="scenario_b",
        execution={
            "release_id": "ending-b-live-test",
        },
    )

    assert len(proof["nodes"]) <= 5
    assert proof["verdict"] == "SAFE TO PUBLISH"
    assert "ending-b-live-test" in [
        fact["value"]
        for fact in proof["facts"]
    ]


def test_dialogue_proof_keeps_genblaze_load_bearing() -> None:
    proof = build_focused_proof(
        scenario_id="scenario_a"
    )

    assert proof["nodes"][0]["label"] == (
        "dialogue.opening"
    )

    assert any(
        fact["label"] == "GENBLAZE"
        and "verified" in fact["value"].lower()
        for fact in proof["facts"]
    )


def test_safety_proof_reports_partial_failure() -> None:
    proof = build_focused_proof(
        scenario_id="scenario_c"
    )

    assert proof["verdict"] == (
        "PUBLICATION STOPPED"
    )

    values = {
        metric["label"]: metric["value"]
        for metric in proof["metrics"]
    }

    assert values == {
        "VERIFIED": "5",
        "MISSING": "1",
        "SAFE ROUTES": "1",
    }

    assert any(
        fact["value"] == "5 verified · 1 missing"
        for fact in proof["facts"]
    )


def test_entity_types_use_three_distinct_kinds() -> None:
    proof = build_focused_proof(
        scenario_id="scenario_b"
    )

    assert {
        item["kind"]
        for item in proof["legend"]
    } == {
        "source",
        "media",
        "route",
    }
