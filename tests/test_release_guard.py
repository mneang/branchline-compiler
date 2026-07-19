"""Tests for Branchline's dynamic publication guard."""

from __future__ import annotations

import hashlib
from copy import deepcopy

from branchline.domain.release_guard import (
    evaluate_release_candidate,
)
from branchline.domain.story_graph import (
    asset_dependency_fingerprint,
    canonical_hash,
    source_hashes,
)


def make_story() -> dict:
    return {
        "project_id": "guard-test",
        "sources": [
            {
                "id": "source.shared",
                "type": "dialogue",
                "value": "Shared dialogue",
            },
            {
                "id": "source.ending_b",
                "type": "image",
                "value": "ending-b-v1",
            },
        ],
        "assets": [
            {
                "id": "asset.shared",
                "type": "audio",
                "depends_on": ["source.shared"],
            },
            {
                "id": "asset.ending_b",
                "type": "video",
                "depends_on": ["source.ending_b"],
            },
        ],
        "paths": [
            {
                "id": "ending_a",
                "required_assets": ["asset.shared"],
            },
            {
                "id": "ending_b",
                "required_assets": [
                    "asset.shared",
                    "asset.ending_b",
                ],
            },
        ],
    }


def make_release(
    story: dict,
) -> tuple[dict, dict[str, bytes]]:
    content_by_key = {
        "objects/shared.wav": b"shared-audio",
        "objects/ending-b.mp4": b"ending-b-video",
    }

    logical_to_key = {
        "asset.shared": "objects/shared.wav",
        "asset.ending_b": "objects/ending-b.mp4",
    }

    source_digests = source_hashes(story)
    memo: dict[str, str] = {}

    assets = {}

    for logical_id, object_key in logical_to_key.items():
        content = content_by_key[object_key]

        assets[logical_id] = {
            "logical_id": logical_id,
            "object_key": object_key,
            "sha256": hashlib.sha256(
                content
            ).hexdigest(),
            "size_bytes": len(content),
            "dependency_fingerprint": (
                asset_dependency_fingerprint(
                    logical_id,
                    story=story,
                    source_digest_by_id=source_digests,
                    memo=memo,
                )
            ),
        }

    release = {
        "project_id": story["project_id"],
        "release_id": "release-1",
        "story_sha256": canonical_hash(story),
        "assets": assets,
    }

    return release, content_by_key


def test_valid_release_is_publishable() -> None:
    story = make_story()
    release, content_by_key = make_release(story)

    report = evaluate_release_candidate(
        story=story,
        release=release,
        fetch_bytes=lambda key: content_by_key[key],
    )

    assert (
        report["publication_status"]
        == "SAFE_TO_PUBLISH"
    )
    assert report["failed_assets"] == []
    assert report["blocked_paths"] == []
    assert report["verified_paths"] == [
        "ending_a",
        "ending_b",
    ]


def test_missing_branch_asset_blocks_only_its_path() -> None:
    story = make_story()
    release, content_by_key = make_release(story)

    def fetch(key: str) -> bytes:
        if key == "objects/ending-b.mp4":
            raise FileNotFoundError(key)

        return content_by_key[key]

    report = evaluate_release_candidate(
        story=story,
        release=release,
        fetch_bytes=fetch,
    )

    assert report["publication_status"] == "BLOCKED"
    assert report["failed_assets"] == [
        "asset.ending_b",
    ]
    assert report["verified_paths"] == [
        "ending_a",
    ]
    assert report["blocked_paths"] == [
        "ending_b",
    ]

    assert {
        item["code"]
        for item in report["blocking_issues"]
    } == {
        "remote_object_missing",
    }


def test_stale_shared_asset_blocks_every_dependent_path() -> None:
    story = make_story()
    release, content_by_key = make_release(story)

    stale_release = deepcopy(release)

    stale_release["assets"]["asset.shared"][
        "dependency_fingerprint"
    ] = "0" * 64

    report = evaluate_release_candidate(
        story=story,
        release=stale_release,
        fetch_bytes=lambda key: content_by_key[key],
    )

    assert report["publication_status"] == "BLOCKED"
    assert report["failed_assets"] == [
        "asset.shared",
    ]
    assert report["blocked_paths"] == [
        "ending_a",
        "ending_b",
    ]

    assert {
        item["code"]
        for item in report["blocking_issues"]
    } == {
        "stale_dependency_fingerprint",
    }
