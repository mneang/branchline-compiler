"""Guardrails for Branchline's guided three-workflow story."""

from pathlib import Path

from branchline.presentation.director_cut import (
    build_director_cut,
    next_workflow_action,
)
from branchline.presentation.flow import (
    COMPLETE,
    READY,
)
from branchline.presentation.one_screen_release import (
    workflow_options,
)


def test_dialogue_revision_opens_the_story() -> None:
    assert [
        item["id"]
        for item in workflow_options()
    ] == [
        "scenario_a",
        "scenario_b",
        "scenario_c",
    ]

    app = Path("app.py").read_text()

    assert (
        'state: dict[str, Any] = {\n'
        '        "scenario_id": "scenario_a",'
        in app
    )


def test_dialogue_guides_to_selective_reuse() -> None:
    action = next_workflow_action(
        scenario_id="scenario_a",
        phase=COMPLETE,
    )

    assert action is not None
    assert action["scenario_id"] == (
        "scenario_b"
    )

    assert action["label"] == (
        "Next: See selective B2 reuse"
    )


def test_visual_guides_to_safety() -> None:
    action = next_workflow_action(
        scenario_id="scenario_b",
        phase=COMPLETE,
    )

    assert action is not None
    assert action["scenario_id"] == (
        "scenario_c"
    )

    assert action["label"] == (
        "Next: Test publication safety"
    )


def test_safety_is_the_end_of_guided_story() -> None:
    assert next_workflow_action(
        scenario_id="scenario_c",
        phase=COMPLETE,
    ) is None

    assert next_workflow_action(
        scenario_id="scenario_a",
        phase=READY,
    ) is None


def test_director_cut_contains_next_action() -> None:
    result = build_director_cut(
        scenario_id="scenario_a",
        phase=COMPLETE,
        busy=False,
    )

    assert result[
        "next_workflow"
    ] is not None


def test_ui_uses_existing_scenario_reset() -> None:
    app = Path("app.py").read_text()

    assert (
        '"on_next_workflow"'
        in app
    )

    assert (
        "= choose_scenario"
        in app
    )

    assert "director-next" in app
    assert 'icon="arrow_forward"' in app
