"""Prove that Branchline handles a structurally different story graph."""

from __future__ import annotations

import inspect

from branchline.domain.story_graph import (
    load_story,
    plan_rebuild,
)


PREVIOUS_PATH = (
    "fixtures/midnight_signal/story_v1.json"
)

CURRENT_PATH = (
    "fixtures/midnight_signal/story_v2_tunnel_art.json"
)


def calculate_plan() -> dict:
    previous = load_story(PREVIOUS_PATH)
    current = load_story(CURRENT_PATH)

    return plan_rebuild(previous, current)


def test_second_story_has_different_structure() -> None:
    story = load_story(PREVIOUS_PATH)

    assert story["project_id"] == "midnight-signal"
    assert len(story["sources"]) == 4
    assert len(story["assets"]) == 8
    assert len(story["paths"]) == 3

    asset_ids = {
        asset["id"]
        for asset in story["assets"]
    }

    original_fixture_names = {
        "voice.opening",
        "caption.opening",
        "preview.ending_a",
        "preview.ending_b",
        "thumbnail.ending_a",
        "thumbnail.ending_b",
    }

    assert asset_ids.isdisjoint(
        original_fixture_names
    )


def test_tunnel_change_is_isolated_dynamically() -> None:
    plan = calculate_plan()

    assert plan["changed_sources"] == [
        "art.tunnel",
    ]

    assert plan["stale_assets"] == [
        "card.tunnel",
        "cut.tunnel",
    ]

    assert plan["affected_paths"] == [
        "tunnel_escape",
    ]


def test_other_routes_and_assets_remain_reusable() -> None:
    plan = calculate_plan()

    assert plan["reused_assets"] == [
        "card.harbor",
        "card.rooftop",
        "cut.harbor",
        "cut.rooftop",
        "narration.warning",
        "subtitle.warning",
    ]

    assert plan["unaffected_paths"] == [
        "harbor_escape",
        "rooftop_escape",
    ]


def test_reuse_rate_is_seventy_five_percent() -> None:
    plan = calculate_plan()

    total_assets = (
        len(plan["stale_assets"])
        + len(plan["reused_assets"])
    )

    reuse_rate = round(
        len(plan["reused_assets"])
        / total_assets
        * 100,
        1,
    )

    assert total_assets == 8
    assert reuse_rate == 75.0


def test_planner_contains_no_story_specific_names() -> None:
    planner_source = inspect.getsource(
        plan_rebuild
    )

    forbidden_names = {
        "last-train",
        "midnight-signal",
        "ending_a",
        "ending_b",
        "tunnel_escape",
        "voice.opening",
        "preview.ending_a",
    }

    discovered = {
        name
        for name in forbidden_names
        if name in planner_source
    }

    assert discovered == set()
