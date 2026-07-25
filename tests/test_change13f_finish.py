"""Guardrails for Branchline's clean finishing pass."""

from __future__ import annotations

from pathlib import Path

from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
)
from branchline.presentation.one_screen_release import (
    build_one_screen_command,
)


def test_dialogue_plan_requests_human_approval() -> None:
    command = build_one_screen_command(
        scenario_id="scenario_a",
        phase=PLANNED,
        busy=False,
    )

    assert command["primary_label"] == (
        "Approve & rebuild 4 assets"
    )


def test_safety_action_describes_evidence() -> None:
    command = build_one_screen_command(
        scenario_id="scenario_c",
        phase=COMPLETE,
        busy=False,
    )

    assert command["primary_label"] == (
        "Inspect failure evidence"
    )

    assert command["lineage"] == (
        "preview.ending_b missing → "
        "Ending B blocked"
    )


def test_panel_status_is_data_driven() -> None:
    source = Path("app.py").read_text()

    assert (
        "def _precise_panel_status("
        in source
    )

    assert "PREVIEW REBUILD" in source
    assert "ARTWORK" in source
    assert "PRESERVE" in source

    assert (
        "render_panel lacks required context"
        not in source
    )


def test_safety_badges_explain_cause() -> None:
    combined = "\n".join(
        path.read_text()
        for path in [
            Path("app.py"),
            *Path(
                "src/branchline/presentation"
            ).glob("*.py"),
        ]
    )

    assert (
        "REQUIRED OBJECTS VERIFIED"
        in combined
    )

    assert (
        "MISSING · preview.ending_b"
        in combined
    )


def test_final_proof_fits_and_footer_stays_visible() -> None:
    source = Path("app.py").read_text()

    assert "proof-actions" in source
    assert "position: sticky" in source
    assert "max-height: 94vh" in source
    assert "font-size: 34px" in source


def test_default_evidence_is_readable_and_compact() -> None:
    source = Path("app.py").read_text()

    assert ".command-lineage" in source
    assert "text-overflow: ellipsis" in source
    assert ".command-sponsor-line" in source
    assert "font-weight: 750" in source
