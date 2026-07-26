"""Guardrails for Branchline's final-control UX pass."""

from __future__ import annotations

from pathlib import Path


def source() -> str:
    return Path("app.py").read_text()


def test_focused_proof_precedes_complete_graph() -> None:
    app = source()

    assert "build_focused_proof" in app
    assert "FOCUSED CAUSAL PROOF" in app
    assert "full_graph_dialog" in app

    assert (
        "View complete dependency graph"
        in app
    )


def test_media_layer_repairs_panel_clipping() -> None:
    app = source()

    assert (
        ".manga-panel.right:"
        "has(.panel-media-overlay)"
        in app
    )

    assert (
        "clip-path: none !important"
        in app
    )

    assert (
        "inset: 0 0 94px 0 !important"
        in app
    )


def test_playback_action_reflects_open_state() -> None:
    app = source()

    assert (
        '"Close playback"'
        in app
    )

    assert (
        '"primary_kind": "close_media"'
        in app
    )

    assert (
        "media-open"
        in app
    )

    assert (
        "close-media-action"
        in app
    )


def test_dialogue_uses_the_unified_stage() -> None:
    app = source()

    assert (
        "build_dialogue_evidence_bundle"
        in app
    )

    assert (
        "open_dialogue_media"
        in app
    )

    assert (
        "VERIFIED_GENBLAZE_EVIDENCE"
        in app
    )


def test_b2_playback_is_explicit() -> None:
    app = source()

    assert "SERVED FROM B2" in app
    assert "SHA-256 VERIFIED" in app
    assert "5-MINUTE URL" in app


def test_safety_proof_is_not_globally_verified() -> None:
    proof = Path(
        "src/branchline/presentation/"
        "focused_proof.py"
    ).read_text()

    assert "5 verified · 1 missing" in proof
    assert "Ending B blocked" in proof
    assert "Verified provenance retained" in proof


def test_complete_graph_legend_has_reserved_space() -> None:
    judge = Path(
        "src/branchline/presentation/"
        "judge_view.py"
    ).read_text()

    assert (
        "_branchline_full_dependency_graph"
        in judge
    )

    # Graph spacing is applied dynamically to every
    # ECharts graph-series entry.
    assert 'item["top"] = 76' in judge
    assert 'item["bottom"] = 28' in judge

    # The legend itself remains a dictionary configuration.
    assert '"itemGap": 30' in judge
