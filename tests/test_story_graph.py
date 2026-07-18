from branchline.domain.story_graph import load_story, plan_rebuild


def test_shared_dialogue_change_rebuilds_both_branches() -> None:
    previous = load_story("fixtures/main_story/story_v1.json")
    current = load_story(
        "fixtures/main_story/story_v2_shared_dialogue.json"
    )

    plan = plan_rebuild(previous, current)

    assert plan["changed_sources"] == ["dialogue.opening"]

    assert plan["stale_assets"] == [
        "caption.opening",
        "preview.ending_a",
        "preview.ending_b",
        "voice.opening",
    ]

    assert plan["reused_assets"] == [
        "thumbnail.ending_a",
        "thumbnail.ending_b",
    ]

    assert plan["affected_paths"] == [
        "ending_a",
        "ending_b",
    ]

    assert plan["metrics"]["source_changes"] == 1
    assert plan["metrics"]["assets_to_rebuild"] == 4
    assert plan["metrics"]["assets_to_reuse"] == 2
    assert plan["metrics"]["paths_affected"] == 2


def test_ending_b_image_change_is_branch_specific() -> None:
    previous = load_story("fixtures/main_story/story_v1.json")
    current = load_story(
        "fixtures/main_story/story_v2_ending_b_image.json"
    )

    plan = plan_rebuild(previous, current)

    assert plan["changed_sources"] == [
        "image.ending_b",
    ]

    assert plan["stale_assets"] == [
        "preview.ending_b",
        "thumbnail.ending_b",
    ]

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

    assert plan["metrics"] == {
        "source_changes": 1,
        "assets_to_rebuild": 2,
        "assets_to_reuse": 4,
        "paths_affected": 1,
        "paths_total": 2,
    }

