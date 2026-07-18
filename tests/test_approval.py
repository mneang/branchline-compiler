"""Tests for plan-bound human rebuild approval."""

from __future__ import annotations

from copy import deepcopy

import pytest

from branchline.domain.approval import (
    ApprovalError,
    create_approval,
    validate_approval,
)
from branchline.domain.story_graph import load_story, plan_rebuild


def scenario_b_plan() -> dict:
    previous = load_story("fixtures/main_story/story_v1.json")
    current = load_story(
        "fixtures/main_story/story_v2_ending_b_image.json"
    )
    return plan_rebuild(previous, current)


def test_matching_human_approval_is_valid() -> None:
    plan = scenario_b_plan()

    approval = create_approval(
        plan,
        approved_by="project-owner",
        note="Approve Ending B minimum rebuild.",
    )

    assert validate_approval(plan, approval) is True


def test_execution_without_approval_is_blocked() -> None:
    plan = scenario_b_plan()

    with pytest.raises(
        ApprovalError,
        match="No human approval",
    ):
        validate_approval(plan, None)


def test_rejected_plan_is_blocked() -> None:
    plan = scenario_b_plan()

    rejection = create_approval(
        plan,
        approved_by="project-owner",
        decision="rejected",
    )

    with pytest.raises(
        ApprovalError,
        match="not approved",
    ):
        validate_approval(plan, rejection)


def test_plan_change_after_approval_invalidates_decision() -> None:
    original_plan = scenario_b_plan()

    approval = create_approval(
        original_plan,
        approved_by="project-owner",
    )

    modified_plan = deepcopy(original_plan)
    modified_plan["stale_assets"].append("preview.ending_a")

    with pytest.raises(
        ApprovalError,
        match="does not match",
    ):
        validate_approval(modified_plan, approval)
