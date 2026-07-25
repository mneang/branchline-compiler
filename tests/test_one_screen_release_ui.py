"""Guardrails for Branchline's one-screen manga release room."""

from __future__ import annotations

from pathlib import Path


def app_source() -> str:
    return Path("app.py").read_text()


def test_three_workflows_are_visible_without_a_modal() -> None:
    source = app_source()

    assert "render_workflow_segments(" in source
    assert "workflow_options()" in source

    assert "Visual revision" in Path(
        "src/branchline/presentation/"
        "one_screen_release.py"
    ).read_text()

    assert "Dialogue revision" in Path(
        "src/branchline/presentation/"
        "one_screen_release.py"
    ).read_text()

    assert "Safety check" in Path(
        "src/branchline/presentation/"
        "one_screen_release.py"
    ).read_text()


def test_permanent_decision_rail_is_removed_visually() -> None:
    source = app_source()

    assert """.decision-rail {
        display: none !important;
      }""" in source

    assert (
        "main *:has(> .decision-rail)"
        in source
    )


def test_one_command_bar_replaces_evidence_walls() -> None:
    source = app_source()

    assert "render_one_screen_command(" in source
    assert "one-screen-command" in source

    rendered_area = source.split(
        "primary_callback = advance",
        1,
    )[1]

    assert (
        "render_lineage_ribbon("
        not in rendered_area
    )

    assert (
        'with ui.element("footer").classes('
        not in rendered_area
    )


def test_winning_flow_uses_one_primary_action() -> None:
    source = app_source()

    renderer = source.split(
        "def render_one_screen_command(",
        1,
    )[1].split(
        "def render_focus_bar(",
        1,
    )[0]

    assert renderer.count(
        "one-screen-primary"
    ) == 1

    assert (
        'command["primary_label"]'
        in renderer
    )


def test_inline_explanation_requires_no_click() -> None:
    source = app_source()

    renderer = source.split(
        "def render_one_screen_command(",
        1,
    )[1].split(
        "def render_focus_bar(",
        1,
    )[0]

    assert (
        'command["explanation"]'
        in renderer
    )

    assert "why_dialog.open" not in renderer


def test_final_command_exposes_sponsor_jobs() -> None:
    model = Path(
        "src/branchline/presentation/"
        "one_screen_release.py"
    ).read_text()

    assert (
        "Genblaze provenance reused"
        in model
    )

    assert (
        "Backblaze B2 remotely verified"
        in model
    )

    assert (
        "Publication guard passed"
        in model
    )


def test_no_replay_demonstration_in_new_command_model() -> None:
    model = Path(
        "src/branchline/presentation/"
        "one_screen_release.py"
    ).read_text()

    assert "Replay demonstration" not in model
    assert "Replay demo" not in model
