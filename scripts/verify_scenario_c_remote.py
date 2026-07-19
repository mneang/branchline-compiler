"""Independently verify Scenario C evidence and its remote B2 state."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


CANDIDATE_PATH = Path(
    "evidence/candidate_missing_preview_ending_b.json"
)

REPORT_PATH = Path(
    "evidence/publication_guard_missing_preview_ending_b.json"
)


class ScenarioCVerificationError(RuntimeError):
    """Raised when Scenario C evidence cannot be independently verified."""


def canonical_bytes(document: dict[str, Any]) -> bytes:
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def verify_canonical(
    document: dict[str, Any],
    *,
    label: str,
) -> str:
    recorded = str(
        document.get("canonical_sha256", "")
    ).strip()

    if len(recorded) != 64:
        raise ScenarioCVerificationError(
            f"{label} has no valid canonical SHA-256"
        )

    content = dict(document)
    content.pop("canonical_sha256", None)

    calculated = hashlib.sha256(
        canonical_bytes(content)
    ).hexdigest()

    if calculated != recorded:
        raise ScenarioCVerificationError(
            f"{label} canonical SHA-256 mismatch"
        )

    return calculated


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ScenarioCVerificationError(
            f"Required evidence file is missing: {path}"
        )

    document = json.loads(path.read_text())

    if not isinstance(document, dict):
        raise ScenarioCVerificationError(
            f"{path} must contain a JSON object"
        )

    return document


def require_environment() -> dict[str, str]:
    env_path = Path(".env").resolve()

    if not env_path.exists():
        raise ScenarioCVerificationError(
            f".env was not found at {env_path}"
        )

    # Explicit path prevents python-dotenv stdin/frame discovery problems.
    load_dotenv(
        dotenv_path=env_path,
        override=False,
    )

    required = (
        "B2_BUCKET_NAME",
        "B2_KEY_ID",
        "B2_APP_KEY",
        "B2_REGION",
        "B2_ENDPOINT",
    )

    values = {
        name: os.getenv(name, "").strip()
        for name in required
    }

    missing = [
        name
        for name, value in values.items()
        if not value
    ]

    if missing:
        raise ScenarioCVerificationError(
            "Missing environment variables: "
            + ", ".join(missing)
        )

    return values


def create_client(env: dict[str, str]) -> Any:
    endpoint = env["B2_ENDPOINT"].rstrip("/")

    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"https://{endpoint}"

    parsed = urlparse(endpoint)
    hostname = parsed.hostname or ""

    if (
        parsed.scheme != "https"
        or not hostname.startswith("s3.")
        or not hostname.endswith(".backblazeb2.com")
    ):
        raise ScenarioCVerificationError(
            "B2_ENDPOINT is not a valid Backblaze endpoint"
        )

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=env["B2_KEY_ID"],
        aws_secret_access_key=env["B2_APP_KEY"],
        region_name=env["B2_REGION"],
    )


def download(
    client: Any,
    *,
    bucket: str,
    key: str,
) -> bytes:
    response = client.get_object(
        Bucket=bucket,
        Key=key,
    )

    return response["Body"].read()


def verify_missing(
    client: Any,
    *,
    bucket: str,
    key: str,
) -> None:
    try:
        client.head_object(
            Bucket=bucket,
            Key=key,
        )

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
            return

        raise

    raise ScenarioCVerificationError(
        "The intentionally missing B2 object unexpectedly exists"
    )


def main() -> int:
    try:
        candidate = read_json(CANDIDATE_PATH)
        report = read_json(REPORT_PATH)

        candidate_hash = verify_canonical(
            candidate,
            label="Candidate manifest",
        )

        report_hash = verify_canonical(
            report,
            label="Publication-guard report",
        )

        if report.get("publication_status") != "BLOCKED":
            raise ScenarioCVerificationError(
                "Publication status is not BLOCKED"
            )

        if report.get("failed_assets") != [
            "preview.ending_b"
        ]:
            raise ScenarioCVerificationError(
                "Scenario C did not isolate preview.ending_b"
            )

        if report.get("verified_paths") != [
            "ending_a"
        ]:
            raise ScenarioCVerificationError(
                "Ending A is not the sole verified path"
            )

        if report.get("blocked_paths") != [
            "ending_b"
        ]:
            raise ScenarioCVerificationError(
                "Ending B is not the sole blocked path"
            )

        issue_codes = {
            issue["code"]
            for issue in report.get(
                "blocking_issues",
                [],
            )
        }

        if issue_codes != {
            "remote_object_missing"
        }:
            raise ScenarioCVerificationError(
                f"Unexpected blocking issues: {sorted(issue_codes)}"
            )

        env = require_environment()
        bucket = env["B2_BUCKET_NAME"]
        client = create_client(env)

        remote_candidate = download(
            client,
            bucket=bucket,
            key=report[
                "candidate_manifest_object_key"
            ],
        )

        remote_report = download(
            client,
            bucket=bucket,
            key=report[
                "guard_report_object_key"
            ],
        )

        if remote_candidate != CANDIDATE_PATH.read_bytes():
            raise ScenarioCVerificationError(
                "Remote candidate differs from local evidence"
            )

        if remote_report != REPORT_PATH.read_bytes():
            raise ScenarioCVerificationError(
                "Remote guard report differs from local evidence"
            )

        verify_missing(
            client,
            bucket=bucket,
            key=report[
                "missing_asset_object_key"
            ],
        )

        summary = {
            "scenario": "C",
            "candidate_canonical_sha256": candidate_hash,
            "guard_report_canonical_sha256": report_hash,
            "assets_verified": report["metrics"][
                "assets_verified"
            ],
            "assets_failed": report["metrics"][
                "assets_failed"
            ],
            "failed_asset": "preview.ending_b",
            "verified_paths": ["ending_a"],
            "blocked_paths": ["ending_b"],
            "remote_candidate_verified": True,
            "remote_guard_report_verified": True,
            "missing_object_absence_verified": True,
            "publication_status": "BLOCKED",
            "status": (
                "SCENARIO C INDEPENDENTLY VERIFIED"
            ),
        }

        print(json.dumps(summary, indent=2))
        return 0

    except Exception as exc:
        print(
            "SCENARIO C VERIFICATION FAILED: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
