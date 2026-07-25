"""Guardrails for final-third creator and judge clarity."""

from __future__ import annotations

from pathlib import Path


def test_product_purpose_is_visible_without_navigation() -> None:
    source = Path("app.py").read_text()

    # The purpose is now shorter and directly visible in the
    # compact one-screen header.
    assert (
        "Revise a branching story without "
        in source
    )

    assert (
        "publishing stale media."
        in source
    )

    assert (
        "Rebuild only what changed. "
        in source
    )

    assert "Verify every route." in source

    # Creator workflows are visible without navigation or a modal.
    assert "render_workflow_segments(" in source
    assert "workflow_options()" in source

def test_creator_language_replaces_test_case_language() -> None:
    app_source = Path("app.py").read_text()

    presentation_source = Path(
        "src/branchline/presentation/final_third.py"
    ).read_text()

    focus_source = Path(
        "src/branchline/presentation/focus_experience.py"
    ).read_text()

    # The application consumes one presentation model instead of
    # duplicating creator copy throughout app.py.
    assert "build_final_third_context(" in app_source
    assert "build_focus_experience(" in app_source

    assert '"label": "Ending B visual revision"' in (
        presentation_source
    )

    assert '"label": "Missing branch preview"' in (
        presentation_source
    )

    assert '"label": "Shared dialogue revision"' in (
        presentation_source
    )

    # The new Change Director uses concise creator actions.
    assert '"title": "Revise Ending B"' in focus_source

    assert (
        '"title": "Revise shared dialogue"'
        in focus_source
    )

    assert (
        '"title": "Detect missing media"'
        in focus_source
    )

    assert "CHANGE DIRECTOR" in app_source
    assert "ui.select(" not in app_source

def test_b2_release_lineage_is_persistent() -> None:
    source = Path("app.py").read_text()

    assert "render_lineage_ribbon(" in source
    assert "PREVIOUS RELEASE" in source
    assert "CURRENT RELEASE" in source

    assert "lineage-ribbon" in source
    assert "VERIFIED RELEASE LINEAGE" in Path(
        "src/branchline/presentation/final_third.py"
    ).read_text()


def test_final_state_has_auditable_receipt() -> None:
    source = Path("app.py").read_text()

    assert "render_final_receipt(" in source
    assert "FINAL RELEASE RECEIPT" in Path(
        "src/branchline/presentation/final_third.py"
    ).read_text()

    assert "Approval " in source
    assert "RELEASE" in source


def test_sponsor_proof_is_reactive() -> None:
    source = Path("app.py").read_text()

    assert '''view["sponsor_strip"] = (
            final_third["sponsor_strip"]
        )''' in source
