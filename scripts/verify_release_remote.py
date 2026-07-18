"""Independently verify a Branchline release and every asset stored in B2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import boto3
from dotenv import load_dotenv


REQUIRED_ENV_VARS = (
    "B2_BUCKET_NAME",
    "B2_KEY_ID",
    "B2_APP_KEY",
    "B2_REGION",
    "B2_ENDPOINT",
)


class ReleaseVerificationError(RuntimeError):
    """Raised when a stored release cannot be independently verified."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download a Branchline release and all referenced assets "
            "from B2, then independently verify their hashes."
        )
    )

    parser.add_argument(
        "release",
        type=Path,
        help="Local release evidence JSON used to locate the B2 manifest.",
    )

    return parser.parse_args()


def require_environment() -> dict[str, str]:
    """Load required B2 values without printing credentials."""
    load_dotenv()

    values: dict[str, str] = {}
    missing: list[str] = []

    for name in REQUIRED_ENV_VARS:
        value = os.getenv(name, "").strip()

        if value:
            values[name] = value
        else:
            missing.append(name)

    if missing:
        raise ReleaseVerificationError(
            "Missing environment variables: " + ", ".join(missing)
        )

    return values


def normalize_endpoint(raw_endpoint: str) -> str:
    """Return a validated Backblaze HTTPS S3 endpoint."""
    endpoint = raw_endpoint.strip().rstrip("/")

    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"https://{endpoint}"

    parsed = urlparse(endpoint)
    hostname = parsed.hostname or ""

    if (
        parsed.scheme != "https"
        or not hostname.startswith("s3.")
        or not hostname.endswith(".backblazeb2.com")
    ):
        raise ReleaseVerificationError(
            "B2_ENDPOINT must look like "
            "https://s3.us-west-004.backblazeb2.com"
        )

    return endpoint


def create_s3_client(env: dict[str, str]) -> Any:
    """Create an explicitly configured B2 S3 client."""
    return boto3.client(
        "s3",
        endpoint_url=normalize_endpoint(env["B2_ENDPOINT"]),
        aws_access_key_id=env["B2_KEY_ID"],
        aws_secret_access_key=env["B2_APP_KEY"],
        region_name=env["B2_REGION"],
    )


def canonical_bytes(value: Any) -> bytes:
    """Serialize JSON deterministically."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    """Return a SHA-256 digest for raw bytes."""
    return hashlib.sha256(content).hexdigest()


def verify_release_canonical_hash(
    release: dict[str, Any],
    *,
    label: str,
) -> str:
    """Verify the top-level canonical hash recorded by a release."""
    recorded = release.get("canonical_sha256")

    if not isinstance(recorded, str) or len(recorded) != 64:
        raise ReleaseVerificationError(
            f"{label} has no valid canonical_sha256"
        )

    without_hash = dict(release)
    without_hash.pop("canonical_sha256", None)

    calculated = sha256_bytes(
        canonical_bytes(without_hash)
    )

    if calculated != recorded:
        raise ReleaseVerificationError(
            f"{label} canonical hash mismatch: "
            f"{calculated} != {recorded}"
        )

    return calculated


def read_local_release(path: Path) -> dict[str, Any]:
    """Read the local release locator/evidence file."""
    if not path.exists():
        raise ReleaseVerificationError(
            f"Local release file does not exist: {path}"
        )

    try:
        release = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ReleaseVerificationError(
            f"Local release file is invalid JSON: {exc}"
        ) from exc

    if not isinstance(release, dict):
        raise ReleaseVerificationError(
            "Local release document must be a JSON object"
        )

    return release


def download_object(
    client: Any,
    *,
    bucket: str,
    object_key: str,
) -> bytes:
    """Download one B2 object or raise a useful verification error."""
    try:
        response = client.get_object(
            Bucket=bucket,
            Key=object_key,
        )
    except Exception as exc:
        raise ReleaseVerificationError(
            f"Could not download B2 object {object_key}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    return response["Body"].read()


def verify_assets(
    client: Any,
    *,
    bucket: str,
    release: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Download and verify every asset dynamically listed by the release."""
    assets = release.get("assets")

    if not isinstance(assets, dict) or not assets:
        raise ReleaseVerificationError(
            "Release contains no assets"
        )

    verified: dict[str, dict[str, Any]] = {}

    for logical_id, asset in sorted(assets.items()):
        if not isinstance(asset, dict):
            raise ReleaseVerificationError(
                f"Asset record is invalid: {logical_id}"
            )

        object_key = str(
            asset.get("object_key", "")
        ).strip()

        expected_sha256 = str(
            asset.get("sha256", "")
        ).strip()

        expected_size = asset.get("size_bytes")

        if not object_key:
            raise ReleaseVerificationError(
                f"{logical_id} has no B2 object key"
            )

        if len(expected_sha256) != 64:
            raise ReleaseVerificationError(
                f"{logical_id} has no valid SHA-256"
            )

        content = download_object(
            client,
            bucket=bucket,
            object_key=object_key,
        )

        actual_sha256 = sha256_bytes(content)
        actual_size = len(content)

        if actual_sha256 != expected_sha256:
            raise ReleaseVerificationError(
                f"{logical_id} SHA-256 mismatch: "
                f"{actual_sha256} != {expected_sha256}"
            )

        if (
            isinstance(expected_size, int)
            and actual_size != expected_size
        ):
            raise ReleaseVerificationError(
                f"{logical_id} size mismatch: "
                f"{actual_size} != {expected_size}"
            )

        verified[logical_id] = {
            "logical_id": logical_id,
            "object_key": object_key,
            "expected_sha256": expected_sha256,
            "actual_sha256": actual_sha256,
            "size_bytes": actual_size,
            "creation_action": asset.get(
                "creation_action",
                "unknown",
            ),
            "verified": True,
        }

        print(
            f"✓ {logical_id}: "
            f"{actual_size} bytes · "
            f"{actual_sha256[:12]}…"
        )

    return verified


def verify_paths(
    release: dict[str, Any],
    verified_assets: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Recalculate reachable-path health from verified assets."""
    paths = release.get("paths")

    if not isinstance(paths, list) or not paths:
        raise ReleaseVerificationError(
            "Release contains no reachable paths"
        )

    results: list[dict[str, Any]] = []

    for path_record in paths:
        path_id = str(
            path_record.get("path_id", "")
        ).strip()

        required_assets = path_record.get(
            "required_assets",
            [],
        )

        if not path_id:
            raise ReleaseVerificationError(
                "A path is missing path_id"
            )

        if not isinstance(required_assets, list):
            raise ReleaseVerificationError(
                f"Path {path_id} has invalid required_assets"
            )

        missing = sorted(
            asset_id
            for asset_id in required_assets
            if asset_id not in verified_assets
        )

        failed = sorted(
            asset_id
            for asset_id in required_assets
            if asset_id in verified_assets
            and not verified_assets[asset_id]["verified"]
        )

        path_verified = not missing and not failed

        results.append(
            {
                "path_id": path_id,
                "required_assets": required_assets,
                "missing_assets": missing,
                "failed_assets": failed,
                "verified": path_verified,
            }
        )

        if not path_verified:
            raise ReleaseVerificationError(
                f"Path {path_id} failed verification. "
                f"Missing={missing}, failed={failed}"
            )

        print(
            f"✓ Path {path_id}: "
            f"{len(required_assets)} required assets verified"
        )

    return results


def verify_recorded_metrics(
    release: dict[str, Any],
    *,
    assets_verified: int,
    paths_verified: int,
) -> None:
    """Ensure release metrics match independently calculated totals."""
    metrics = release.get("metrics", {})

    expected_metrics = {
        "assets_total": assets_verified,
        "assets_remote_verified": assets_verified,
        "paths_total": paths_verified,
        "paths_verified": paths_verified,
    }

    for field, calculated in expected_metrics.items():
        recorded = metrics.get(field)

        if recorded != calculated:
            raise ReleaseVerificationError(
                f"Release metric mismatch for {field}: "
                f"recorded={recorded!r}, "
                f"calculated={calculated!r}"
            )


def main() -> int:
    args = parse_args()

    try:
        env = require_environment()
        local_release = read_local_release(args.release)

        local_hash = verify_release_canonical_hash(
            local_release,
            label="Local release",
        )

        release_object_key = str(
            local_release.get(
                "release_object_key",
                "",
            )
        ).strip()

        if not release_object_key:
            raise ReleaseVerificationError(
                "Local release has no release_object_key"
            )

        bucket = env["B2_BUCKET_NAME"]
        client = create_s3_client(env)

        print("=== REMOTE RELEASE MANIFEST ===")

        remote_bytes = download_object(
            client,
            bucket=bucket,
            object_key=release_object_key,
        )

        try:
            remote_release = json.loads(
                remote_bytes.decode("utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReleaseVerificationError(
                "Remote release manifest is not valid UTF-8 JSON"
            ) from exc

        remote_hash = verify_release_canonical_hash(
            remote_release,
            label="Remote release",
        )

        identity_fields = (
            "schema_version",
            "project_id",
            "release_id",
            "story_sha256",
        )

        for field in identity_fields:
            local_value = local_release.get(field)
            remote_value = remote_release.get(field)

            if local_value != remote_value:
                raise ReleaseVerificationError(
                    f"Local/remote release mismatch for {field}: "
                    f"{local_value!r} != {remote_value!r}"
                )

        if local_hash != remote_hash:
            raise ReleaseVerificationError(
                "Local and remote canonical release hashes differ"
            )

        print(
            f"✓ Remote release manifest: "
            f"{remote_release['release_id']}"
        )
        print(f"✓ Canonical SHA-256: {remote_hash}")

        print("\n=== REMOTE ASSETS ===")

        verified_assets = verify_assets(
            client,
            bucket=bucket,
            release=remote_release,
        )

        print("\n=== REACHABLE PATHS ===")

        verified_paths = verify_paths(
            remote_release,
            verified_assets,
        )

        verify_recorded_metrics(
            remote_release,
            assets_verified=len(verified_assets),
            paths_verified=len(verified_paths),
        )

        publication_status = remote_release.get(
            "publication_status"
        )

        if publication_status != "SAFE_TO_PUBLISH":
            raise ReleaseVerificationError(
                "Release is not publishable: "
                f"{publication_status!r}"
            )

        action_counts: dict[str, int] = {}

        for asset in verified_assets.values():
            action = str(asset["creation_action"])
            action_counts[action] = (
                action_counts.get(action, 0) + 1
            )

        summary = {
            "project_id": remote_release["project_id"],
            "release_id": remote_release["release_id"],
            "release_object_key": release_object_key,
            "release_canonical_sha256": remote_hash,
            "assets_verified": len(verified_assets),
            "paths_verified": len(verified_paths),
            "creation_actions": action_counts,
            "publication_status": publication_status,
            "status": (
                "REMOTE RELEASE COMPLETED AND VERIFIED"
            ),
        }

        print("\n=== VERIFICATION RESULT ===")
        print(json.dumps(summary, indent=2))

        return 0

    except Exception as exc:
        print(
            f"REMOTE RELEASE VERIFICATION FAILED: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
