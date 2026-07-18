"""Tests for plan-bound Branchline human approval."""

from __future__ import annotations

from copy import deepcopy

import pytest

from branchline.domain.approval import (
    ApprovalError,
    create_approval,
    validate_approval,
)
from branchline.domain.story_graph import load_story, plan_rebuild


def scenario_a_plan() -> dict:
    previous = load_story(
        "fixtures/main_story/story_v1.json"
    )
    current = load_story(
        "fixtures/main_story/story_v2_shared_dialogue.json"
    )

    return plan_rebuild(previous, current)


def test_matching_approval_is_valid() -> None:
    plan = scenario_a_plan()

    approval = create_approval(
        plan,
        approved_by="project-owner",
    )

    assert validate_approval(plan, approval) is True


def test_missing_approval_blocks_execution() -> None:
    plan = scenario_a_plan()

    with pytest.raises(
        ApprovalError,
        match="No human approval",
    ):
        validate_approval(plan, None)


def test_rejection_blocks_execution() -> None:
    plan = scenario_a_plan()

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


def test_plan_mutation_invalidates_old_approval() -> None:
    original_plan = scenario_a_plan()

    approval = create_approval(
        original_plan,
        approved_by="project-owner",
    )

    modified_plan = deepcopy(original_plan)
    modified_plan["stale_assets"].append(
        "thumbnail.ending_a"
    )
    modified_plan["stale_assets"].sort()

    with pytest.raises(
        ApprovalError,
        match="does not match",
    ):
        validate_approval(modified_plan, approval)
