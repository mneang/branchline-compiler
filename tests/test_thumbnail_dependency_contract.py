"""Verify that thumbnail rendering matches declared graph dependencies."""

from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

from branchline.domain.story_graph import load_story
from branchline.media.thumbnails import (
    create_branch_thumbnail,
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def test_thumbnail_renderer_has_no_dialogue_input() -> None:
    parameters = inspect.signature(
        create_branch_thumbnail
    ).parameters

    assert "dialogue" not in parameters
    assert "prompt" not in parameters
    assert "caption" not in parameters


def test_story_graph_declares_visual_only_thumbnail_dependencies() -> None:
    story = load_story(
        "fixtures/main_story/story_v2_shared_dialogue.json"
    )

    assets = {
        asset["id"]: asset
        for asset in story["assets"]
    }

    assert assets["thumbnail.ending_a"]["depends_on"] == [
        "image.ending_a",
    ]

    assert assets["thumbnail.ending_b"]["depends_on"] == [
        "image.ending_b",
    ]


def test_identical_branch_visuals_produce_identical_bytes(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"

    common = {
        "branch_label": "ENDING B",
        "destination": "Remain beneath the station lights",
        "background": (76, 27, 47),
    }

    create_branch_thumbnail(
        first,
        **common,
    )

    create_branch_thumbnail(
        second,
        **common,
    )

    assert file_sha256(first) == file_sha256(second)


def test_branch_visual_change_produces_new_thumbnail_bytes(
    tmp_path: Path,
) -> None:
    previous = tmp_path / "previous.png"
    current = tmp_path / "current.png"

    create_branch_thumbnail(
        previous,
        branch_label="ENDING B",
        destination="Remain beneath the station lights",
        background=(76, 27, 47),
    )

    create_branch_thumbnail(
        current,
        branch_label="ENDING B",
        destination="Cross the illuminated night platform",
        background=(24, 61, 82),
    )

    assert file_sha256(previous) != file_sha256(current)
