"""Tests for the judge-facing Branchline presentation model."""

from __future__ import annotations

from branchline.presentation.judge_view import (
    build_scenario_view,
    load_scenarios,
)


def test_all_three_scenarios_load() -> None:
    scenarios = load_scenarios()

    assert set(scenarios) == {
        "scenario_a",
        "scenario_b",
        "scenario_c",
    }


def test_scenario_b_is_the_hero_flow() -> None:
    view = build_scenario_view(
        "scenario_b"
    )

    assert view["hero"] is True
    assert view["mode"] == "VERIFIED REPLAY"

    assert view["changed_sources"] == [
        "image.ending_b",
    ]

    assert view["rebuilt_assets"] == [
        "preview.ending_b",
        "thumbnail.ending_b",
    ]

    assert view["reused_assets"] == [
        "caption.opening",
        "preview.ending_a",
        "thumbnail.ending_a",
        "voice.opening",
    ]

    assert (
        view["publication_status"]
        == "SAFE_TO_PUBLISH"
    )


def test_scenario_c_exposes_exact_failure() -> None:
    view = build_scenario_view(
        "scenario_c"
    )

    assert view["failed_assets"] == [
        "preview.ending_b",
    ]

    verified = [
        item["path_id"]
        for item in view["paths"]
        if item["verified"]
    ]

    blocked = [
        item["path_id"]
        for item in view["paths"]
        if not item["verified"]
    ]

    assert verified == ["ending_a"]
    assert blocked == ["ending_b"]

    assert (
        view["publication_status"]
        == "BLOCKED"
    )


def test_dependency_graph_contains_all_node_types() -> None:
    view = build_scenario_view(
        "scenario_b"
    )

    series = view[
        "graph_options"
    ]["series"][0]

    categories = {
        item["category"]
        for item in series["data"]
    }

    assert categories == {0, 1, 2}
    assert len(series["links"]) > 0


def test_every_scenario_has_four_metrics() -> None:
    for view in load_scenarios().values():
        assert len(view["metrics"]) == 4
