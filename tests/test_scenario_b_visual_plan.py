"""Scenario B must isolate one branch-specific visual change."""

from __future__ import annotations

from branchline.domain.approval import (
    create_approval,
    validate_approval,
)
from branchline.domain.story_graph import (
    load_story,
    plan_rebuild,
)
from branchline.media.visual_sources import (
    resolve_branch_visual,
)


def scenario_b_plan() -> dict:
    previous = load_story(
        "fixtures/main_story/story_v2_shared_dialogue.json"
    )

    current = load_story(
        "fixtures/main_story/story_v3_ending_b_visual.json"
    )

    return plan_rebuild(previous, current)


def test_only_ending_b_visual_source_changed() -> None:
    plan = scenario_b_plan()

    assert plan["changed_sources"] == [
        "image.ending_b",
    ]

    assert plan["stale_assets"] == [
        "preview.ending_b",
        "thumbnail.ending_b",
    ]


def test_four_unaffected_assets_are_reused() -> None:
    plan = scenario_b_plan()

    assert plan["reused_assets"] == [
        "caption.opening",
        "preview.ending_a",
        "thumbnail.ending_a",
        "voice.opening",
    ]

    assert plan["affected_paths"] == [
        "ending_b",
    ]

    assert plan["unaffected_paths"] == [
        "ending_a",
    ]


def test_visual_source_is_resolved_from_story_data() -> None:
    story = load_story(
        "fixtures/main_story/story_v3_ending_b_visual.json"
    )

    visual = resolve_branch_visual(
        story,
        "ending_b",
    )

    assert visual["source_id"] == "image.ending_b"
    assert visual["asset_ref"] == (
        "original://night-platform-v2"
    )
    assert visual["background"] == (24, 61, 82)


def test_exact_scenario_b_plan_can_be_approved() -> None:
    plan = scenario_b_plan()

    approval = create_approval(
        plan,
        approved_by="project-owner",
    )

    assert validate_approval(plan, approval) is True
