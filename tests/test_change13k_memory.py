"""Guardrails for Branchline's memorable demo experience."""

from branchline.presentation.final_third import (
    build_final_third_context,
)
from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
)
from branchline.presentation.focused_proof import (
    build_focused_proof,
)
from branchline.presentation.one_screen_release import (
    build_one_screen_command,
)


def test_dialogue_success_lands_the_product_promise() -> None:
    command = build_one_screen_command(
        scenario_id="scenario_a",
        phase=COMPLETE,
        busy=False,
    )

    assert command["headline"] == (
        "No stale branches detected."
    )

    assert command["detail"] == (
        "1 line changed · 4 rebuilt · 2 preserved · "
        "6 / 6 B2 objects verified."
    )

    assert command["verdict"] == (
        "SAFE TO PUBLISH"
    )


def test_safety_actions_escalate_toward_a_release_decision() -> None:
    ready = build_one_screen_command(
        scenario_id="scenario_c",
        phase=READY,
        busy=False,
    )

    planned = build_one_screen_command(
        scenario_id="scenario_c",
        phase=PLANNED,
        busy=False,
    )

    assert ready["primary_label"] == (
        "Inspect release candidate"
    )

    assert planned["primary_label"] == (
        "Verify release candidate"
    )


def test_safety_completion_is_the_memorable_climax() -> None:
    command = build_one_screen_command(
        scenario_id="scenario_c",
        phase=COMPLETE,
        busy=False,
    )

    assert command["headline"] == (
        "No stale branches published."
    )

    assert command["detail"] == (
        "Ending B blocked · "
        "Ending A remains publishable and independently verified."
    )

    assert command["verdict"] == (
        "PUBLICATION STOPPED"
    )


def test_focused_proof_repeats_the_climax() -> None:
    proof = build_focused_proof(
        scenario_id="scenario_c"
    )

    assert proof["title"] == (
        "No stale branches published."
    )

    assert (
        "blocked Ending B"
        in proof["summary"]
    )

    assert (
        "Ending A remained independently verified"
        in proof["summary"]
    )


def test_one_promise_is_used_across_the_experience() -> None:
    context = build_final_third_context(
        scenario_id="scenario_a",
        phase=COMPLETE,
        scenario={},
    )

    assert context["purpose"]["supporting"] == (
        "Change one scene. "
        "Rebuild only what it affects."
    )

    assert context["purpose"]["promise"] == (
        "Publish no stale branches."
    )


def test_visual_revision_leads_with_intelligent_restraint() -> None:
    context = build_final_third_context(
        scenario_id="scenario_b",
        phase=COMPLETE,
        scenario={},
    )

    genblaze = context[
        "sponsor_strip"
    ][0]

    assert genblaze["label"] == (
        "GENBLAZE"
    )

    assert genblaze["value"] == (
        "0 unnecessary AI requests"
    )

    assert (
        "provenance reused"
        in genblaze["detail"]
    )


def test_safety_receipt_closes_the_loop() -> None:
    context = build_final_third_context(
        scenario_id="scenario_c",
        phase=COMPLETE,
        scenario={},
    )

    receipt = context[
        "final_receipt"
    ]

    assert receipt is not None

    assert receipt["title"] == (
        "No stale branches published"
    )

    assert receipt["line_one"] == (
        "Ending A remains independently verified."
    )
