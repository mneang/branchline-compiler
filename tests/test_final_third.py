"""Tests for creator clarity, B2 lineage, and final receipts."""

from __future__ import annotations

from branchline.presentation.final_third import (
    PURPOSE,
    build_final_third_context,
    build_release_lineage,
)
from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
)


def scenario_view() -> dict:
    return {
        "publication_status": (
            "SAFE_TO_PUBLISH"
        ),
        "provenance": {
            "release_id": (
                "ending-b-visual-v3"
            ),
        },
    }


def test_product_purpose_is_immediately_clear() -> None:
    assert PURPOSE == {
        "brand": "BRANCHLINE",
        "headline": (
            "Revise your story without breaking "
            "its generated media."
        ),
        "supporting": (
            "Change one scene. Rebuild only what depends on it."
        ),
        "promise": (
            "Publish only after every route is verified."
        ),
    }


def test_ready_lineage_exposes_the_problem() -> None:
    lineage = build_release_lineage(
        scenario_id="scenario_b",
        phase=READY,
        scenario=scenario_view(),
    )

    assert lineage["source"] == (
        "shared-dialogue-v2"
    )

    assert lineage["movement"] == (
        "REVISION DETECTED"
    )

    assert lineage["target"] == (
        "IMPACT NOT YET CALCULATED"
    )


def test_planned_lineage_explains_minimum_rebuild() -> None:
    analysis = {
        "metrics": {
            "assets_to_rebuild": 2,
            "assets_to_reuse": 4,
        },
    }

    lineage = build_release_lineage(
        scenario_id="scenario_b",
        phase=PLANNED,
        scenario=scenario_view(),
        analysis=analysis,
    )

    assert lineage["movement"] == (
        "4 REUSE · 2 REBUILD"
    )

    assert lineage["target"] == (
        "AWAITING CREATOR APPROVAL"
    )


def test_live_completion_uses_fresh_release_identity() -> None:
    execution = {
        "release_id": (
            "ending-b-live-20260719-ab12cd34"
        ),
        "approval_id": (
            "approval-live-1"
        ),
        "assets_rebuilt": 2,
        "assets_reused": 4,
        "publication_status": (
            "SAFE_TO_PUBLISH"
        ),
    }

    context = build_final_third_context(
        scenario_id="scenario_b",
        phase=COMPLETE,
        scenario=scenario_view(),
        execution=execution,
    )

    assert context["lineage"]["target"] == (
        "ending-b-live-20260719-ab12cd34"
    )

    assert context["lineage"]["movement"] == (
        "4 REUSED · 2 REBUILT"
    )

    receipt = context[
        "final_receipt"
    ]

    assert receipt is not None

    assert receipt["approval_id"] == (
        "approval-live-1"
    )

    assert receipt["status"] == (
        "SAFE_TO_PUBLISH"
    )

    assert (
        context["sponsor_strip"][1]["value"]
        == "4 reused · 2 rebuilt · 6 / 6 verified"
    )


def test_safety_case_ends_with_contained_failure() -> None:
    context = build_final_third_context(
        scenario_id="scenario_c",
        phase=COMPLETE,
        scenario={
            "publication_status": "BLOCKED",
            "provenance": {},
        },
    )

    assert context["lineage"]["target"] == (
        "ENDING B BLOCKED"
    )

    assert context[
        "final_receipt"
    ]["title"] == (
        "Unsafe branch contained"
    )

    assert context[
        "sponsor_strip"
    ][2]["value"] == (
        "ENDING B BLOCKED"
    )
