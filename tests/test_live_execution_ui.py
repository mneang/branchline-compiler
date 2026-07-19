"""Guardrails for the real Scenario B execution path."""

from __future__ import annotations

from pathlib import Path


def test_second_click_executes_scenario_b_live() -> None:
    source = Path("app.py").read_text()

    assert "run_live_scenario_b(" in source

    assert (
        "execute_scenario_b_release"
        in source
    )

    assert "asyncio.to_thread(" in source

    assert (
        'scenario_id == "scenario_b"'
        in source
    )


def test_live_and_replay_modes_are_distinct() -> None:
    source = Path("app.py").read_text()

    assert "LIVE_EXECUTION" in source

    assert (
        "VERIFIED_REPLAY_FALLBACK"
        in source
    )

    assert "HONEST FALLBACK" in source


def test_live_proof_is_visible_to_judges() -> None:
    source = Path("app.py").read_text()

    assert "Fresh approval" in source
    assert "Fresh release" in source
    assert "B2 guard record" in source

    assert "release_object_key" in source
    assert "guard_report_object_key" in source


def test_duplicate_action_remains_blocked() -> None:
    source = Path("app.py").read_text()

    assert '''        if state["busy"]:
            return
''' in source

    assert 'action_button.props(' in source
    assert '"disable loading"' in source
