"""Guardrails for the guided, dynamic release experience."""

from __future__ import annotations

from pathlib import Path


def test_guided_view_is_the_default() -> None:
    source = Path("app.py").read_text()

    # Change 13C makes the focused one-screen experience
    # the default rather than exposing a Guided/Proof toggle.
    assert "build_one_screen_command(" in source
    assert "render_one_screen_command(" in source
    assert "one-screen-workflows" in source
    assert "one-screen-command" in source

    assert "GUIDED VIEW" not in source
    assert "PROOF VIEW" not in source

def test_change_director_replaces_technical_selector() -> None:
    source = Path("app.py").read_text()

    assert "render_workflow_segments(" in source
    assert "workflow_options()" in source
    assert "one-screen-workflows" in source
    assert "ui.select(" not in source


def test_route_causality_moves_into_story_panels() -> None:
    source = Path("app.py").read_text()

    assert "focus_class=" in source
    assert "focus_badges=" in source

    assert "panel-preserved" in source
    assert "panel-affected" in source
    assert "panel-working" in source
    assert "panel-verified" in source


def test_dependency_reasoning_is_plain_language() -> None:
    source = Path("app.py").read_text()

    assert "Why these assets?" in source
    assert "why_dialog" in source
    assert "DEPENDENCY EXPLANATION" in source


def test_evidence_uses_progressive_disclosure() -> None:
    source = Path("app.py").read_text()

    # Evidence is now revealed inside one phase-aware command bar.
    assert "render_one_screen_command(" in source
    assert 'command["metrics"]' in source
    assert 'command["lineage"]' in source
    assert 'command["sponsor_line"]' in source

    # The permanent evidence wall and decision rail are removed
    # from the visible winning journey.
    assert """.decision-rail {
        display: none !important;
      }""" in source

    rendered_area = source.split(
        "primary_callback = advance",
        1,
    )[1]

    assert "render_lineage_ribbon(" not in rendered_area

    assert (
        'with ui.element("footer").classes('
        not in rendered_area
    )

def test_animation_is_explanatory_not_looping() -> None:
    source = Path("app.py").read_text()

    assert "execution-sweep" in source
    assert "focus-badge-arrival" in source

    execution_keyframe = source.split(
        "@keyframes execution-sweep",
        1,
    )[1].split(
        "}",
        2,
    )[0]

    assert "infinite" not in execution_keyframe
