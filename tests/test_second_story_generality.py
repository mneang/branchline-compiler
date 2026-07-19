"""Prove that Branchline operates on a different story without code changes."""

from __future__ import annotations

import inspect

from branchline.domain import story_graph
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


def generality_plan() -> dict:
    previous = load_story(PREVIOUS_PATH)
    current = load_story(CURRENT_PATH)

    return plan_rebuild(previous, current)


def test_second_story_has_different_shape() -> None:
    story = load_story(PREVIOUS_PATH)

    assert story["project_id"] == "midnight-signal"
    assert len(story["paths"]) == 3
    assert len(story["assets"]) == 8

    asset_ids = {
        asset["id"]
        for asset in story["assets"]
    }

    assert "voice.opening" not in asset_ids
    assert "preview.ending_a" not in asset_ids
    assert "thumbnail.ending_b" not in asset_ids


def test_tunnel_change_is_diagnosed_dynamically() -> None:
    plan = generality_plan()

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


def test_two_other_routes_remain_untouched() -> None:
    plan = generality_plan()

    assert plan["unaffected_paths"] == [
        "harbor_escape",
        "rooftop_escape",
    ]

    assert plan["reused_assets"] == [
        "card.harbor",
        "card.rooftop",
        "cut.harbor",
        "cut.rooftop",
        "narration.warning",
        "subtitle.warning",
    ]


def test_second_story_reuse_rate_is_seventy_five_percent() -> None:
    plan = generality_plan()

    assert plan["metrics"] == {
        "source_changes": 1,
        "assets_to_rebuild": 2,
        "assets_to_reuse": 6,
        "paths_affected": 1,
        "paths_total": 3,
    }

    reuse_rate = (
        plan["metrics"]["assets_to_reuse"]
        / (
            plan["metrics"]["assets_to_rebuild"]
            + plan["metrics"]["assets_to_reuse"]
        )
        * 100
    )

    assert reuse_rate == 75.0


def test_domain_planner_contains_no_fixture_specific_names() -> None:
    source = inspect.getsource(story_graph)

    forbidden = {
        "last-train",
        "midnight-signal",
        "ending_a",
        "ending_b",
        "tunnel_escape",
        "voice.opening",
    }

    assert not {
        value
        for value in forbidden
        if value in source
    }
