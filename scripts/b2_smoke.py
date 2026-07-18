"""Upload, retrieve, and independently verify one object in Backblaze B2."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv


REQUIRED_ENV_VARS = (
    "B2_BUCKET_NAME",
    "B2_KEY_ID",
    "B2_APP_KEY",
    "B2_REGION",
    "B2_ENDPOINT",
)


def require_environment() -> dict[str, str]:
    """Return required environment variables or fail with a clear message."""
    load_dotenv()

    values: dict[str, str] = {}
    missing: list[str] = []

    for name in REQUIRED_ENV_VARS:
        value = os.getenv(name, "").strip()
        if not value:
            missing.append(name)
        else:
            values[name] = value

    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    return values


def sha256_bytes(content: bytes) -> str:
    """Calculate a SHA-256 digest."""
    return hashlib.sha256(content).hexdigest()



def normalize_endpoint(raw_endpoint: str) -> str:
    """Normalize and validate a Backblaze B2 HTTPS endpoint."""
    endpoint = raw_endpoint.strip().rstrip("/")

    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"https://{endpoint}"

    parsed = urlparse(endpoint)

    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError(
            "B2_ENDPOINT must be a valid HTTPS URL, for example: "
            "https://s3.us-west-004.backblazeb2.com"
        )

    return endpoint

def main() -> int:
    try:
        env = require_environment()
        env["B2_ENDPOINT"] = normalize_endpoint(env["B2_ENDPOINT"])

        client = boto3.client(
            "s3",
            endpoint_url=env["B2_ENDPOINT"],
            aws_access_key_id=env["B2_KEY_ID"],
            aws_secret_access_key=env["B2_APP_KEY"],
            region_name=env["B2_REGION"],
            config=Config(signature_version="s3v4"),
        )

        object_key = "smoke-tests/b2-handshake.json"

        payload = {
            "project": "branchline-compiler",
            "test": "b2-handshake",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "uploaded",
        }

        original_bytes = json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        ).encode("utf-8")

        original_hash = sha256_bytes(original_bytes)

        client.put_object(
            Bucket=env["B2_BUCKET_NAME"],
            Key=object_key,
            Body=original_bytes,
            ContentType="application/json",
            Metadata={"sha256": original_hash},
        )

        response = client.get_object(
            Bucket=env["B2_BUCKET_NAME"],
            Key=object_key,
        )

        retrieved_bytes = response["Body"].read()
        retrieved_hash = sha256_bytes(retrieved_bytes)

        if retrieved_hash != original_hash:
            raise RuntimeError(
                "Verification failed: retrieved object hash does not match."
            )

        print(
            json.dumps(
                {
                    "bucket": env["B2_BUCKET_NAME"],
                    "object_key": object_key,
                    "uploaded_sha256": original_hash,
                    "retrieved_sha256": retrieved_hash,
                    "hashes_match": True,
                    "status": "B2 HANDSHAKE VERIFIED",
                },
                indent=2,
            )
        )

        return 0

    except (RuntimeError, ValueError, BotoCoreError, ClientError) as exc:
        print(f"B2 smoke test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
