"""Tests for the verified Branchline baseline release."""

from __future__ import annotations

import json
from pathlib import Path


def load_release() -> dict:
    path = Path("evidence/release_baseline_v1.json")

    assert path.exists(), (
        "Run scripts/build_baseline_release.py first"
    )

    return json.loads(path.read_text())


def test_baseline_release_contains_all_six_assets() -> None:
    release = load_release()

    expected = {
        "voice.opening",
        "caption.opening",
        "thumbnail.ending_a",
        "thumbnail.ending_b",
        "preview.ending_a",
        "preview.ending_b",
    }

    assert set(release["assets"]) == expected
    assert release["metrics"]["assets_total"] == 6


def test_every_baseline_asset_is_remotely_verified() -> None:
    release = load_release()

    assert all(
        asset["remote_verified"]
        for asset in release["assets"].values()
    )

    assert (
        release["metrics"]["assets_remote_verified"]
        == 6
    )


def test_both_story_paths_are_verified() -> None:
    release = load_release()

    assert len(release["paths"]) == 2
    assert all(
        path_item["verified"]
        for path_item in release["paths"]
    )

    assert release["metrics"]["paths_verified"] == 2


def test_genblaze_provenance_is_verified() -> None:
    release = load_release()
    genblaze = release["genblaze"]

    assert genblaze["pipeline_manifest_verified"] is True
    assert genblaze["stored_manifest_verified"] is True
    assert genblaze["canonical_hashes_match"] is True


def test_baseline_release_is_publishable() -> None:
    release = load_release()

    assert (
        release["publication_status"]
        == "SAFE_TO_PUBLISH"
    )
    assert release["status"] == "BASELINE RELEASE VERIFIED"
