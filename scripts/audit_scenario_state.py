"""Audit local and Backblaze B2 state for every Branchline scenario."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


PROJECT_ID = "last-train"

BASELINE_RELEASE_KEY = (
    "branchline/projects/last-train/"
    "releases/baseline-v1/release.json"
)

SELECTIVE_RELEASE_KEY = (
    "branchline/projects/last-train/"
    "releases/shared-dialogue-v2/release.json"
)

SCENARIO_C_CANDIDATE_KEY = (
    "branchline/projects/last-train/"
    "candidates/missing-preview-ending-b-v3/"
    "candidate.json"
)

SCENARIO_C_REPORT_KEY = (
    "branchline/projects/last-train/"
    "candidates/missing-preview-ending-b-v3/"
    "publication-guard.json"
)

SCENARIO_C_MISSING_KEY = (
    "branchline/projects/last-train/"
    "candidates/missing-preview-ending-b-v3/"
    "intentionally-missing/preview.ending_b.mp4"
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def canonical_valid(document: dict[str, Any]) -> bool:
    recorded = document.get("canonical_sha256")

    if not isinstance(recorded, str) or len(recorded) != 64:
        return False

    content = dict(document)
    content.pop("canonical_sha256", None)

    calculated = hashlib.sha256(
        canonical_bytes(content)
    ).hexdigest()

    return recorded == calculated


def load_local_json(path: str) -> dict[str, Any] | None:
    file_path = Path(path)

    if not file_path.exists():
        return None

    try:
        result = json.loads(file_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None

    return result if isinstance(result, dict) else None


def normalized_endpoint(raw: str) -> str:
    endpoint = raw.strip().rstrip("/")

    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"https://{endpoint}"

    parsed = urlparse(endpoint)

    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".backblazeb2.com")
    ):
        raise RuntimeError("Invalid B2_ENDPOINT")

    return endpoint


def create_client() -> tuple[Any, str]:
    load_dotenv()

    required = (
        "B2_BUCKET_NAME",
        "B2_KEY_ID",
        "B2_APP_KEY",
        "B2_REGION",
        "B2_ENDPOINT",
    )

    missing = [
        name
        for name in required
        if not os.getenv(name, "").strip()
    ]

    if missing:
        raise RuntimeError(
            "Missing environment variables: " + ", ".join(missing)
        )

    client = boto3.client(
        "s3",
        endpoint_url=normalized_endpoint(
            os.environ["B2_ENDPOINT"]
        ),
        aws_access_key_id=os.environ["B2_KEY_ID"],
        aws_secret_access_key=os.environ["B2_APP_KEY"],
        region_name=os.environ["B2_REGION"],
    )

    return client, os.environ["B2_BUCKET_NAME"]


def object_state(
    client: Any,
    bucket: str,
    key: str,
) -> str:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return "EXISTS"

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
            return "MISSING"

        return f"ERROR:{code or status}"

    except Exception as exc:
        return f"ERROR:{type(exc).__name__}"


def remote_json(
    client: Any,
    bucket: str,
    key: str,
) -> dict[str, Any] | None:
    try:
        content = client.get_object(
            Bucket=bucket,
            Key=key,
        )["Body"].read()

        result = json.loads(content.decode("utf-8"))

        return result if isinstance(result, dict) else None

    except Exception:
        return None


def inspect_release(
    *,
    client: Any,
    bucket: str,
    local_path: str,
    expected_remote_key: str,
) -> dict[str, Any]:
    local = load_local_json(local_path)
    remote = remote_json(
        client,
        bucket,
        expected_remote_key,
    )

    manifest_state = object_state(
        client,
        bucket,
        expected_remote_key,
    )

    document = remote or local
    asset_states: dict[str, str] = {}

    if document:
        assets = document.get("assets", {})

        if isinstance(assets, dict):
            for logical_id, record in sorted(assets.items()):
                if not isinstance(record, dict):
                    asset_states[logical_id] = "INVALID_RECORD"
                    continue

                object_key = str(
                    record.get("object_key", "")
                ).strip()

                asset_states[logical_id] = (
                    object_state(client, bucket, object_key)
                    if object_key
                    else "NO_OBJECT_KEY"
                )

    assets_existing = sum(
        1
        for state in asset_states.values()
        if state == "EXISTS"
    )

    assets_total = len(asset_states)

    if (
        local is not None
        and remote is not None
        and manifest_state == "EXISTS"
        and assets_total > 0
        and assets_existing == assets_total
    ):
        overall = "UPLOADED"
    elif local is not None and remote is None:
        overall = "LOCAL_ONLY"
    elif local is None and remote is not None:
        overall = "REMOTE_ONLY"
    else:
        overall = "NOT_COMPLETE"

    return {
        "overall": overall,
        "local_file": local_path,
        "local_exists": local is not None,
        "local_canonical_valid": (
            canonical_valid(local)
            if local and "canonical_sha256" in local
            else None
        ),
        "remote_object_key": expected_remote_key,
        "remote_manifest_state": manifest_state,
        "remote_canonical_valid": (
            canonical_valid(remote)
            if remote and "canonical_sha256" in remote
            else None
        ),
        "release_id": (
            document.get("release_id")
            if document
            else None
        ),
        "publication_status": (
            document.get("publication_status")
            if document
            else None
        ),
        "assets_existing": assets_existing,
        "assets_total": assets_total,
        "asset_states": asset_states,
    }


def main() -> int:
    try:
        client, bucket = create_client()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "audit_status": "B2_CONNECTION_FAILED",
                    "error": f"{type(exc).__name__}: {exc}",
                },
                indent=2,
            )
        )
        return 0

    scenario_a_plan = load_local_json(
        "evidence/story_graph_shared_dialogue.json"
    )

    scenario_a_approval = load_local_json(
        "evidence/approval_shared_dialogue.json"
    )

    scenario_b_plan = load_local_json(
        "evidence/story_graph_ending_b_image.json"
    )

    candidate_local = load_local_json(
        "evidence/candidate_missing_preview_ending_b.json"
    )

    report_local = load_local_json(
        "evidence/publication_guard_missing_preview_ending_b.json"
    )

    candidate_remote = remote_json(
        client,
        bucket,
        SCENARIO_C_CANDIDATE_KEY,
    )

    report_remote = remote_json(
        client,
        bucket,
        SCENARIO_C_REPORT_KEY,
    )

    missing_state = object_state(
        client,
        bucket,
        SCENARIO_C_MISSING_KEY,
    )

    scenario_c_uploaded = (
        candidate_remote is not None
        and report_remote is not None
        and missing_state == "MISSING"
    )

    result = {
        "audit_status": "COMPLETED",
        "bucket": bucket,
        "scenario_a_shared_dialogue": {
            "plan_local": scenario_a_plan is not None,
            "approval_local": scenario_a_approval is not None,
            "baseline": inspect_release(
                client=client,
                bucket=bucket,
                local_path="evidence/release_baseline_v1.json",
                expected_remote_key=BASELINE_RELEASE_KEY,
            ),
            "selective_release_v2": inspect_release(
                client=client,
                bucket=bucket,
                local_path=(
                    "evidence/release_shared_dialogue_v2.json"
                ),
                expected_remote_key=SELECTIVE_RELEASE_KEY,
            ),
        },
        "scenario_b_ending_b_image": {
            "plan_local": scenario_b_plan is not None,
            "execution_status": (
                "PLANNER_ONLY"
                if scenario_b_plan is not None
                else "NOT_STARTED"
            ),
            "b2_release_expected_at_this_stage": False,
        },
        "scenario_c_publication_blocker": {
            "local_candidate_exists": candidate_local is not None,
            "local_report_exists": report_local is not None,
            "remote_candidate_state": object_state(
                client,
                bucket,
                SCENARIO_C_CANDIDATE_KEY,
            ),
            "remote_report_state": object_state(
                client,
                bucket,
                SCENARIO_C_REPORT_KEY,
            ),
            "deliberately_missing_asset_state": missing_state,
            "publication_status": (
                report_remote.get("publication_status")
                if report_remote
                else (
                    report_local.get("publication_status")
                    if report_local
                    else None
                )
            ),
            "uploaded_and_verified": scenario_c_uploaded,
        },
    }

    baseline = result[
        "scenario_a_shared_dialogue"
    ]["baseline"]

    release_v2 = result[
        "scenario_a_shared_dialogue"
    ]["selective_release_v2"]

    if baseline["overall"] != "UPLOADED":
        next_action = "BUILD_BASELINE_V1"
    elif release_v2["overall"] != "UPLOADED":
        next_action = "BUILD_SELECTIVE_RELEASE_V2"
    elif not scenario_c_uploaded:
        next_action = "RUN_SCENARIO_C"
    else:
        next_action = "ALL_CURRENT_SCENARIOS_PRESENT"

    result["recommended_next_action"] = next_action

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
