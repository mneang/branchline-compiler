"""Guardrails for Branchline's dynamic release UI."""

from __future__ import annotations

from pathlib import Path


def test_ui_contains_all_four_tactical_priorities() -> None:
    source = Path("app.py").read_text()

    # Human-readable revision diff.
    assert "render_revision_diff(" in source

    # Animated causal explanation.
    assert "render_causal_map(" in source
    assert "causal-trace" in source

    # Evidence-checked staged progression.
    assert "run_verified_replay(" in source
    assert "validate_replay_stage(" in source
    assert "VERIFIED EXECUTION REPLAY" in source

    # Playable media.
    assert "ui.video(" in source
    assert "Play before / after media" in source


def test_async_progression_is_truthfully_labeled() -> None:
    source = Path("app.py").read_text()

    assert "async def advance()" in source
    assert "await screen.refresh()" in source

    assert (
        "LIVE ANALYSIS · VERIFIED EXECUTION REPLAY"
        in source
    )

    assert "LIVE B2 EXECUTION" in source
    assert "VERIFIED_REPLAY_FALLBACK" in source
    assert "execute_scenario_b_release" in source


def test_ui_has_no_fake_progress_percentage() -> None:
    source = Path("app.py").read_text()

    assert "fake progress" not in source.lower()
    assert "progress-bar" not in source
    assert "linear-progress" not in source


def test_primary_flow_remains_clean() -> None:
    source = Path("app.py").read_text()

    assert "ui.select(" in source
    assert "scenario-button" not in source
    assert "progress_rail" not in source

    assert "height: 100vh" in source
    assert "overflow: hidden" in source
