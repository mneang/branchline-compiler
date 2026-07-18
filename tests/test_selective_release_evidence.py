"""Tests for Branchline's verified selective Release V2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


BASELINE_PATH = Path(
    "evidence/release_baseline_v1.json"
)

RELEASE_PATH = Path(
    "evidence/release_shared_dialogue_v2.json"
)


def load_json(path: Path) -> dict:
    assert path.exists(), (
        f"Required evidence file is missing: {path}"
    )

    return json.loads(path.read_text())


def test_selective_release_rebuilds_exactly_four_assets() -> None:
    release = load_json(RELEASE_PATH)

    rebuilt = {
        logical_id
        for logical_id, asset
        in release["assets"].items()
        if asset["release_action"] == "rebuilt"
    }

    assert rebuilt == {
        "voice.opening",
        "caption.opening",
        "preview.ending_a",
        "preview.ending_b",
    }

    assert release["metrics"][
        "assets_rebuilt"
    ] == 4


def test_selective_release_reuses_exactly_two_assets() -> None:
    release = load_json(RELEASE_PATH)

    reused = {
        logical_id
        for logical_id, asset
        in release["assets"].items()
        if asset["release_action"]
        == "reused_from_baseline"
    }

    assert reused == {
        "thumbnail.ending_a",
        "thumbnail.ending_b",
    }

    assert release["metrics"][
        "assets_reused"
    ] == 2


def test_reused_assets_keep_baseline_bytes_and_keys() -> None:
    baseline = load_json(BASELINE_PATH)
    release = load_json(RELEASE_PATH)

    for logical_id in (
        "thumbnail.ending_a",
        "thumbnail.ending_b",
    ):
        assert (
            release["assets"][logical_id]["sha256"]
            == baseline["assets"][logical_id]["sha256"]
        )

        assert (
            release["assets"][logical_id]["object_key"]
            == baseline["assets"][logical_id]["object_key"]
        )


def test_rebuilt_assets_have_new_bytes() -> None:
    baseline = load_json(BASELINE_PATH)
    release = load_json(RELEASE_PATH)

    for logical_id in (
        "voice.opening",
        "caption.opening",
        "preview.ending_a",
        "preview.ending_b",
    ):
        assert (
            release["assets"][logical_id]["sha256"]
            != baseline["assets"][logical_id]["sha256"]
        )


def test_all_assets_and_paths_are_verified() -> None:
    release = load_json(RELEASE_PATH)

    assert len(release["assets"]) == 6

    assert all(
        asset["remote_verified"]
        for asset in release["assets"].values()
    )

    assert len(release["paths"]) == 2

    assert all(
        path_item["verified"]
        for path_item in release["paths"]
    )

    assert release["metrics"][
        "assets_remote_verified"
    ] == 6

    assert release["metrics"][
        "paths_verified"
    ] == 2

    assert release["metrics"][
        "stale_assets_remaining"
    ] == 0


def test_genblaze_provenance_is_verified() -> None:
    release = load_json(RELEASE_PATH)
    genblaze = release["genblaze"]

    assert genblaze[
        "pipeline_manifest_verified"
    ] is True

    assert genblaze[
        "stored_manifest_verified"
    ] is True

    assert genblaze[
        "canonical_hashes_match"
    ] is True


def test_selective_release_canonical_hash_is_valid() -> None:
    release = load_json(RELEASE_PATH)

    recorded = release.pop(
        "canonical_sha256"
    )

    canonical = json.dumps(
        release,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    calculated = hashlib.sha256(
        canonical
    ).hexdigest()

    assert calculated == recorded


def test_selective_release_is_safe_to_publish() -> None:
    release = load_json(RELEASE_PATH)

    assert (
        release["publication_status"]
        == "SAFE_TO_PUBLISH"
    )

    assert release["status"] == (
        "SELECTIVE RELEASE COMPLETED "
        "AND VERIFIED"
    )
