"""Prove that missing reachable media blocks publication."""

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from branchline.domain.release_guard import (
    evaluate_release_candidate,
)
from branchline.domain.story_graph import load_story


PROJECT_ID = "last-train"
CANDIDATE_ID = "missing-preview-ending-b-v3"

STORY_PATH = Path(
    "fixtures/main_story/story_v2_shared_dialogue.json"
)

SOURCE_RELEASE_PATH = Path(
    "evidence/release_shared_dialogue_v2.json"
)

CANDIDATE_PATH = Path(
    "evidence/candidate_missing_preview_ending_b.json"
)

REPORT_PATH = Path(
    "evidence/publication_guard_missing_preview_ending_b.json"
)

ROOT_KEY = (
    f"branchline/projects/{PROJECT_ID}/"
    f"candidates/{CANDIDATE_ID}"
)

CANDIDATE_KEY = f"{ROOT_KEY}/candidate.json"
REPORT_KEY = f"{ROOT_KEY}/publication-guard.json"

MISSING_KEY = (
    f"{ROOT_KEY}/intentionally-missing/"
    "preview.ending_b.mp4"
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def add_canonical_hash(
    document: dict[str, Any],
) -> dict[str, Any]:
    result = dict(document)
    result.pop("canonical_sha256", None)

    result["canonical_sha256"] = sha256_bytes(
        canonical_bytes(result)
    )

    return result


def canonical_valid(document: dict[str, Any]) -> bool:
    recorded = document.get("canonical_sha256")

    content = dict(document)
    content.pop("canonical_sha256", None)

    return recorded == sha256_bytes(
        canonical_bytes(content)
    )


def json_bytes(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            document,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def require_b2_environment() -> dict[str, str]:
    load_dotenv()

    names = (
        "B2_BUCKET_NAME",
        "B2_KEY_ID",
        "B2_APP_KEY",
        "B2_REGION",
        "B2_ENDPOINT",
    )

    values = {
        name: os.getenv(name, "").strip()
        for name in names
    }

    missing = [
        name
        for name, value in values.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Missing B2 environment variables: "
            + ", ".join(missing)
        )

    return values


def create_client(env: dict[str, str]) -> Any:
    endpoint = env["B2_ENDPOINT"].rstrip("/")

    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"https://{endpoint}"

    parsed = urlparse(endpoint)

    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".backblazeb2.com")
    ):
        raise RuntimeError("Invalid B2 endpoint")

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=env["B2_KEY_ID"],
        aws_secret_access_key=env["B2_APP_KEY"],
        region_name=env["B2_REGION"],
    )


def object_exists(
    client: Any,
    *,
    bucket: str,
    key: str,
) -> bool:
    try:
        client.head_object(
            Bucket=bucket,
            Key=key,
        )
        return True

    except ClientError as exc:
        status = exc.response.get(
            "ResponseMetadata",
            {},
        ).get("HTTPStatusCode")

        code = exc.response.get(
            "Error",
            {},
        ).get("Code", "")

        if status == 404 or code in {
            "404",
            "NoSuchKey",
            "NotFound",
        }:
            return False

        raise


def fetch_bytes(
    client: Any,
    *,
    bucket: str,
    key: str,
) -> bytes:
    try:
        return client.get_object(
            Bucket=bucket,
            Key=key,
        )["Body"].read()

    except ClientError as exc:
        status = exc.response.get(
            "ResponseMetadata",
            {},
        ).get("HTTPStatusCode")

        code = exc.response.get(
            "Error",
            {},
        ).get("Code", "")

        if status == 404 or code in {
            "404",
            "NoSuchKey",
            "NotFound",
        }:
            raise FileNotFoundError(key) from exc

        raise


def main() -> int:
    try:
        story = load_story(STORY_PATH)

        source_release = json.loads(
            SOURCE_RELEASE_PATH.read_text()
        )

        if not canonical_valid(source_release):
            raise RuntimeError(
                "Release V2 canonical hash is invalid"
            )

        if (
            source_release.get("publication_status")
            != "SAFE_TO_PUBLISH"
        ):
            raise RuntimeError(
                "Release V2 is not currently publishable"
            )

        env = require_b2_environment()
        bucket = env["B2_BUCKET_NAME"]
        client = create_client(env)

        if object_exists(
            client,
            bucket=bucket,
            key=MISSING_KEY,
        ):
            raise RuntimeError(
                "The deliberately missing test key already exists"
            )

        candidate = deepcopy(source_release)

        candidate.update(
            {
                "release_id": CANDIDATE_ID,
                "previous_release_id": source_release["release_id"],
                "release_object_key": CANDIDATE_KEY,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "candidate_kind": (
                    "DELIBERATE SAFETY TEST FIXTURE"
                ),
                "publication_status": "PENDING_VERIFICATION",
                "status": "CANDIDATE REQUIRES VERIFICATION",
            }
        )

        target = candidate["assets"]["preview.ending_b"]

        target["object_key"] = MISSING_KEY
        target["b2_uri"] = f"b2://{bucket}/{MISSING_KEY}"
        target["remote_verified"] = False
        target["release_action"] = "candidate_reference"

        candidate = add_canonical_hash(candidate)

        report = evaluate_release_candidate(
            story=story,
            release=candidate,
            fetch_bytes=lambda key: fetch_bytes(
                client,
                bucket=bucket,
                key=key,
            ),
        )

        issue_codes = {
            issue["code"]
            for issue in report["blocking_issues"]
        }

        if report["publication_status"] != "BLOCKED":
            raise RuntimeError(
                "Scenario C failed to block publication"
            )

        if report["failed_assets"] != [
            "preview.ending_b"
        ]:
            raise RuntimeError(
                f"Unexpected failed assets: "
                f"{report['failed_assets']}"
            )

        if report["blocked_paths"] != ["ending_b"]:
            raise RuntimeError(
                f"Unexpected blocked paths: "
                f"{report['blocked_paths']}"
            )

        if report["verified_paths"] != ["ending_a"]:
            raise RuntimeError(
                f"Unexpected verified paths: "
                f"{report['verified_paths']}"
            )

        if issue_codes != {"remote_object_missing"}:
            raise RuntimeError(
                f"Unexpected issue codes: {sorted(issue_codes)}"
            )

        report.update(
            {
                "scenario": "C",
                "scenario_type": "missing_remote_object",
                "source_release_id": source_release["release_id"],
                "candidate_manifest_object_key": CANDIDATE_KEY,
                "guard_report_object_key": REPORT_KEY,
                "missing_asset_object_key": MISSING_KEY,
                "missing_asset_absence_verified": True,
            }
        )

        report = add_canonical_hash(report)

        candidate_payload = json_bytes(candidate)
        report_payload = json_bytes(report)

        client.put_object(
            Bucket=bucket,
            Key=CANDIDATE_KEY,
            Body=candidate_payload,
            ContentType="application/json",
        )

        client.put_object(
            Bucket=bucket,
            Key=REPORT_KEY,
            Body=report_payload,
            ContentType="application/json",
        )

        remote_candidate = fetch_bytes(
            client,
            bucket=bucket,
            key=CANDIDATE_KEY,
        )

        remote_report = fetch_bytes(
            client,
            bucket=bucket,
            key=REPORT_KEY,
        )

        if remote_candidate != candidate_payload:
            raise RuntimeError(
                "Remote candidate bytes differ"
            )

        if remote_report != report_payload:
            raise RuntimeError(
                "Remote guard report bytes differ"
            )

        if object_exists(
            client,
            bucket=bucket,
            key=MISSING_KEY,
        ):
            raise RuntimeError(
                "Missing-object fixture unexpectedly exists"
            )

        CANDIDATE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        CANDIDATE_PATH.write_bytes(candidate_payload)
        REPORT_PATH.write_bytes(report_payload)

        summary = {
            "scenario": "C",
            "failed_asset": "preview.ending_b",
            "assets_verified": report["metrics"]["assets_verified"],
            "assets_failed": report["metrics"]["assets_failed"],
            "verified_paths": report["verified_paths"],
            "blocked_paths": report["blocked_paths"],
            "blocking_issue": "remote_object_missing",
            "candidate_manifest_stored": True,
            "guard_report_stored": True,
            "publication_status": "BLOCKED",
            "status": (
                "PUBLICATION BLOCKER COMPLETED AND VERIFIED"
            ),
        }

        print(json.dumps(summary, indent=2))
        return 0

    except Exception as exc:
        print(
            "SCENARIO C FAILED: "
            f"{type(exc).__name__}: {exc}"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
