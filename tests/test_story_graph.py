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
