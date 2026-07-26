"""Guardrails for the final judge-facing legibility pass."""

from pathlib import Path

from branchline.presentation.flow import COMPLETE
from branchline.presentation.focused_proof import (
    build_focused_proof,
)
from branchline.presentation.one_screen_release import (
    build_one_screen_command,
)


def test_visual_completion_leads_with_restraint() -> None:
    command = build_one_screen_command(
        scenario_id="scenario_b",
        phase=COMPLETE,
        busy=False,
    )

    assert command["headline"] == (
        "0 unnecessary AI requests."
    )

    assert command["detail"] == (
        "Ending B rebuilt · "
        "4 verified assets reused from B2 · "
        "Ending A remained byte-identical."
    )


def test_safety_proof_keeps_the_healthy_route_explicit() -> None:
    proof = build_focused_proof(
        scenario_id="scenario_c"
    )

    assert (
        "Ending B"
        in proof["summary"]
    )

    assert (
        "independently verified and publishable"
        in proof["summary"]
    )


def test_legibility_lock_is_present() -> None:
    source = Path("app.py").read_text()

    required = (
        "CHANGE 13K-D · XABI LEGIBILITY LOCK",
        ".director-proof-detail",
        ".focused-proof-card",
        "grid-template-columns:",
        "overflow: hidden !important;",
        ".proof-facts",
        ".proof-verdict",
        "max-height: 760px",
    )

    for marker in required:
        assert marker in source
