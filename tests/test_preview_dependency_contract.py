"""Verify that previews respond to every declared content dependency."""

from __future__ import annotations

import hashlib
from pathlib import Path

from branchline.media.previews import (
    create_story_preview_frame,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_identical_preview_inputs_are_deterministic(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"

    parameters = {
        "branch_label": "ENDING A",
        "destination": "Board the midnight-blue express",
        "dialogue": "The last train leaves at seven.",
        "background": (20, 45, 78),
    }

    create_story_preview_frame(first, **parameters)
    create_story_preview_frame(second, **parameters)

    assert digest(first) == digest(second)


def test_dialogue_change_changes_preview_bytes(
    tmp_path: Path,
) -> None:
    previous = tmp_path / "previous.png"
    current = tmp_path / "current.png"

    common = {
        "branch_label": "ENDING A",
        "destination": "Board the midnight-blue express",
        "background": (20, 45, 78),
    }

    create_story_preview_frame(
        previous,
        dialogue="The last train leaves at seven.",
        **common,
    )

    create_story_preview_frame(
        current,
        dialogue="The last train leaves at eight.",
        **common,
    )

    assert digest(previous) != digest(current)


def test_branch_visual_change_changes_preview_bytes(
    tmp_path: Path,
) -> None:
    previous = tmp_path / "previous.png"
    current = tmp_path / "current.png"

    create_story_preview_frame(
        previous,
        branch_label="ENDING B",
        destination="Remain beneath the station lights",
        dialogue="The last train leaves at eight.",
        background=(76, 27, 47),
    )

    create_story_preview_frame(
        current,
        branch_label="ENDING B",
        destination="Cross the illuminated night platform",
        dialogue="The last train leaves at eight.",
        background=(24, 61, 82),
    )

    assert digest(previous) != digest(current)
