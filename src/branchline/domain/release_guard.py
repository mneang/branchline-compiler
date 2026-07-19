"""Dynamic remote-media checks that decide whether a release may publish."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

from branchline.domain.story_graph import (
    asset_dependency_fingerprint,
    canonical_hash,
    source_hashes,
)


FetchBytes = Callable[[str], bytes]


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def evaluate_release_candidate(
    *,
    story: dict[str, Any],
    release: dict[str, Any],
    fetch_bytes: FetchBytes,
) -> dict[str, Any]:
    """Verify every story asset and calculate affected paths dynamically."""
    asset_specs = {
        asset["id"]: asset
        for asset in story["assets"]
    }

    release_assets = release.get("assets", {})
    if not isinstance(release_assets, dict):
        release_assets = {}

    source_digests = source_hashes(story)
    memo: dict[str, str] = {}

    expected_fingerprints = {
        asset_id: asset_dependency_fingerprint(
            asset_id,
            story=story,
            source_digest_by_id=source_digests,
            memo=memo,
        )
        for asset_id in sorted(asset_specs)
    }

    blocking_issues: list[dict[str, Any]] = []
    asset_results: dict[str, dict[str, Any]] = {}

    story_hash_matches = (
        release.get("story_sha256")
        == canonical_hash(story)
    )

    if not story_hash_matches:
        blocking_issues.append(
            {
                "code": "story_hash_mismatch",
                "detail": (
                    "Release story hash does not match "
                    "the current story."
                ),
            }
        )

    for logical_id in sorted(asset_specs):
        record = release_assets.get(logical_id)
        issues: list[dict[str, Any]] = []

        if not isinstance(record, dict):
            record = {}
            issues.append(
                {
                    "code": "asset_record_missing",
                    "logical_id": logical_id,
                    "detail": "Required asset record is missing.",
                }
            )

        expected_fingerprint = expected_fingerprints[logical_id]

        if (
            record.get("dependency_fingerprint")
            != expected_fingerprint
        ):
            issues.append(
                {
                    "code": "stale_dependency_fingerprint",
                    "logical_id": logical_id,
                    "detail": (
                        "Asset dependencies are stale or different."
                    ),
                }
            )

        object_key = str(
            record.get("object_key", "")
        ).strip()

        expected_sha256 = str(
            record.get("sha256", "")
        ).strip()

        expected_size = record.get("size_bytes")
        actual_sha256 = None
        actual_size = None
        remote_retrieved = False

        if not object_key:
            issues.append(
                {
                    "code": "object_key_missing",
                    "logical_id": logical_id,
                    "detail": "Asset has no B2 object key.",
                }
            )

        if len(expected_sha256) != 64:
            issues.append(
                {
                    "code": "sha256_missing_or_invalid",
                    "logical_id": logical_id,
                    "detail": "Asset has no valid SHA-256.",
                }
            )

        if object_key and len(expected_sha256) == 64:
            try:
                content = fetch_bytes(object_key)
                remote_retrieved = True
                actual_size = len(content)
                actual_sha256 = sha256_bytes(content)

                if actual_sha256 != expected_sha256:
                    issues.append(
                        {
                            "code": "remote_hash_mismatch",
                            "logical_id": logical_id,
                            "detail": (
                                "Remote B2 bytes do not match "
                                "the recorded SHA-256."
                            ),
                        }
                    )

                if (
                    isinstance(expected_size, int)
                    and actual_size != expected_size
                ):
                    issues.append(
                        {
                            "code": "remote_size_mismatch",
                            "logical_id": logical_id,
                            "detail": (
                                "Remote B2 object size does not "
                                "match the release."
                            ),
                        }
                    )

            except FileNotFoundError:
                issues.append(
                    {
                        "code": "remote_object_missing",
                        "logical_id": logical_id,
                        "detail": (
                            "The required B2 object does not exist."
                        ),
                    }
                )

            except Exception as exc:
                issues.append(
                    {
                        "code": "remote_object_unavailable",
                        "logical_id": logical_id,
                        "detail": (
                            f"{type(exc).__name__}: {exc}"
                        ),
                    }
                )

        verified = not issues

        asset_results[logical_id] = {
            "logical_id": logical_id,
            "object_key": object_key or None,
            "expected_sha256": expected_sha256 or None,
            "actual_sha256": actual_sha256,
            "expected_size_bytes": expected_size,
            "actual_size_bytes": actual_size,
            "remote_retrieved": remote_retrieved,
            "issues": issues,
            "verified": verified,
        }

        blocking_issues.extend(issues)

    paths = []

    for path_spec in story["paths"]:
        required_assets = path_spec["required_assets"]

        blocked_assets = sorted(
            asset_id
            for asset_id in required_assets
            if not asset_results.get(
                asset_id,
                {},
            ).get("verified", False)
        )

        verified = (
            not blocked_assets
            and story_hash_matches
        )

        paths.append(
            {
                "path_id": path_spec["id"],
                "required_assets": required_assets,
                "blocked_assets": blocked_assets,
                "verified": verified,
                "status": (
                    "VERIFIED"
                    if verified
                    else "BLOCKED"
                ),
            }
        )

    failed_assets = sorted(
        asset_id
        for asset_id, result in asset_results.items()
        if not result["verified"]
    )

    verified_assets = sorted(
        asset_id
        for asset_id, result in asset_results.items()
        if result["verified"]
    )

    blocked_paths = sorted(
        path["path_id"]
        for path in paths
        if not path["verified"]
    )

    verified_paths = sorted(
        path["path_id"]
        for path in paths
        if path["verified"]
    )

    publication_status = (
        "BLOCKED"
        if blocking_issues
        else "SAFE_TO_PUBLISH"
    )

    return {
        "schema_version": 1,
        "project_id": story["project_id"],
        "release_id": release.get("release_id"),
        "assets": asset_results,
        "paths": paths,
        "blocking_issues": blocking_issues,
        "failed_assets": failed_assets,
        "verified_assets": verified_assets,
        "blocked_paths": blocked_paths,
        "verified_paths": verified_paths,
        "metrics": {
            "assets_total": len(asset_results),
            "assets_verified": len(verified_assets),
            "assets_failed": len(failed_assets),
            "paths_total": len(paths),
            "paths_verified": len(verified_paths),
            "paths_blocked": len(blocked_paths),
            "blocking_issues": len(blocking_issues),
        },
        "publication_status": publication_status,
        "status": (
            "PUBLICATION BLOCKED"
            if publication_status == "BLOCKED"
            else "PUBLICATION VERIFIED"
        ),
    }
