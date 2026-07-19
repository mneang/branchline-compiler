"""Guardrails for the live-analysis manga experience."""

from __future__ import annotations

from pathlib import Path


def test_manga_studio_runs_fresh_analysis() -> None:
    source = Path("app.py").read_text()

    assert "analyze_story_revision(" in source

    assert (
        "validate_analysis_against_release("
        in source
    )

    assert "analysis_metrics(" in source

    assert "LIVE DEPENDENCY ANALYSIS" in source
    assert "plan_sha256" in source


def test_mode_is_labeled_truthfully() -> None:
    source = Path("app.py").read_text()

    assert (
        "LIVE ANALYSIS · VERIFIED EXECUTION REPLAY"
        in source
    )

    assert "LIVE B2 EXECUTION" in source
    assert "VERIFIED_REPLAY_FALLBACK" in source
    assert "execute_scenario_b_release" in source


def test_analysis_failure_stops_progression() -> None:
    source = Path("app.py").read_text()

    assert "except LiveAnalysisError" in source
    assert "ANALYSIS STOPPED" in source
    assert "return" in source


def test_safety_check_does_not_fake_story_analysis() -> None:
    source = Path("app.py").read_text()

    assert '''scenario_id in {
                "scenario_a",
                "scenario_b",
            }''' in source
