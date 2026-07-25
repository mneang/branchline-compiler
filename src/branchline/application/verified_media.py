"""Verified Backblaze B2 media playback for Branchline.

The service retrieves both release preview objects, verifies their
recorded hashes and sizes, and only then creates short-lived signed
playback URLs.

Long-lived B2 application credentials never leave the server.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from scripts.build_baseline_release import (
    create_s3_client,
)
from scripts.build_scenario_b_visual_release import (
    verify_canonical_release,
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]

PREVIOUS_RELEASE_PATH = (
    PROJECT_ROOT
    / "evidence"
    / "release_shared_dialogue_v2_canonical.json"
)

CURRENT_RELEASE_PATH = (
    PROJECT_ROOT
    / "evidence"
    / "release_ending_b_visual_v3.json"
)

PREVIEW_ID = "preview.ending_b"

DEFAULT_EXPIRY_SECONDS = 300
MIN_EXPIRY_SECONDS = 60
MAX_EXPIRY_SECONDS = 900


class VerifiedMediaError(RuntimeError):
    """Raised when B2 media cannot be proven safe for playback."""


def _read_release(
    path: Path,
) -> dict[str, Any]:
    if not path.exists():
        raise VerifiedMediaError(
            f"Required release evidence is missing: {path.name}"
        )

    try:
        document = json.loads(
            path.read_text()
        )
    except Exception as exc:
        raise VerifiedMediaError(
            f"Release evidence is invalid: {path.name}"
        ) from exc

    if not isinstance(document, dict):
        raise VerifiedMediaError(
            f"Release evidence must be an object: {path.name}"
        )

    try:
        verify_canonical_release(
            document,
            label=path.name,
        )
    except Exception as exc:
        raise VerifiedMediaError(
            f"Release evidence failed canonical verification: "
            f"{path.name}"
        ) from exc

    return document


def _require_environment() -> dict[str, str]:
    env_path = PROJECT_ROOT / ".env"

    if env_path.exists():
        load_dotenv(
            dotenv_path=env_path,
            override=False,
        )

    names = (
        "B2_BUCKET_NAME",
        "B2_KEY_ID",
        "B2_APP_KEY",
        "B2_REGION",
        "B2_ENDPOINT",
    )

    values = {
        name: os.getenv(
            name,
            "",
        ).strip()
        for name in names
    }

    missing = [
        name
        for name, value in values.items()
        if not value
    ]

    if missing:
        raise VerifiedMediaError(
            "Verified B2 playback is unavailable because "
            "the hosted environment is incomplete."
        )

    return values


def _preview_record(
    release: dict[str, Any],
    *,
    label: str,
) -> dict[str, Any]:
    assets = release.get(
        "assets",
        {},
    )

    if not isinstance(assets, dict):
        raise VerifiedMediaError(
            f"{label} has no valid asset collection."
        )

    record = assets.get(
        PREVIEW_ID
    )

    if not isinstance(record, dict):
        raise VerifiedMediaError(
            f"{label} does not contain {PREVIEW_ID}."
        )

    object_key = str(
        record.get(
            "object_key",
            "",
        )
    ).strip()

    sha256 = str(
        record.get(
            "sha256",
            "",
        )
    ).strip()

    size_bytes = record.get(
        "size_bytes"
    )

    media_type = str(
        record.get(
            "media_type",
            "",
        )
    ).strip()

    if not object_key:
        raise VerifiedMediaError(
            f"{label} preview has no B2 object key."
        )

    if len(sha256) != 64:
        raise VerifiedMediaError(
            f"{label} preview has no valid SHA-256."
        )

    if not isinstance(
        size_bytes,
        int,
    ) or size_bytes <= 0:
        raise VerifiedMediaError(
            f"{label} preview has no valid byte size."
        )

    if media_type != "video/mp4":
        raise VerifiedMediaError(
            f"{label} preview is not an MP4 video."
        )

    return {
        **record,
        "object_key": object_key,
        "sha256": sha256,
        "size_bytes": size_bytes,
        "media_type": media_type,
    }


def _retrieve_verified_object(
    client: Any,
    *,
    bucket: str,
    record: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    try:
        response = client.get_object(
            Bucket=bucket,
            Key=record[
                "object_key"
            ],
        )

        content = response[
            "Body"
        ].read()

    except Exception as exc:
        raise VerifiedMediaError(
            f"{label} could not be retrieved from B2."
        ) from exc

    actual_sha256 = hashlib.sha256(
        content
    ).hexdigest()

    actual_size = len(content)

    if (
        actual_sha256
        != record["sha256"]
    ):
        raise VerifiedMediaError(
            f"{label} failed remote SHA-256 verification."
        )

    if (
        actual_size
        != record["size_bytes"]
    ):
        raise VerifiedMediaError(
            f"{label} failed remote size verification."
        )

    return {
        "logical_id": PREVIEW_ID,
        "object_key": record[
            "object_key"
        ],
        "sha256": actual_sha256,
        "size_bytes": actual_size,
        "media_type": record[
            "media_type"
        ],
        "remote_verified": True,
    }


def _signed_url(
    client: Any,
    *,
    bucket: str,
    object_key: str,
    expires_in_seconds: int,
) -> str:
    try:
        url = client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": bucket,
                "Key": object_key,
            },
            ExpiresIn=expires_in_seconds,
        )
    except Exception as exc:
        raise VerifiedMediaError(
            "A short-lived B2 playback URL "
            "could not be created."
        ) from exc

    if not isinstance(
        url,
        str,
    ) or not url.strip():
        raise VerifiedMediaError(
            "B2 returned no playable signed URL."
        )

    return url


def build_verified_media_bundle(
    *,
    previous_release: dict[str, Any],
    current_release: dict[str, Any],
    client: Any,
    bucket: str,
    expires_in_seconds: int = DEFAULT_EXPIRY_SECONDS,
) -> dict[str, Any]:
    """Verify both B2 videos before creating playback URLs."""
    expiry = int(
        expires_in_seconds
    )

    if not (
        MIN_EXPIRY_SECONDS
        <= expiry
        <= MAX_EXPIRY_SECONDS
    ):
        raise VerifiedMediaError(
            "Signed playback expiry must be "
            "between 60 and 900 seconds."
        )

    previous_id = str(
        previous_release.get(
            "release_id",
            "",
        )
    ).strip()

    current_id = str(
        current_release.get(
            "release_id",
            "",
        )
    ).strip()

    parent_id = str(
        current_release.get(
            "previous_release_id",
            "",
        )
    ).strip()

    if not previous_id or not current_id:
        raise VerifiedMediaError(
            "Release lineage is incomplete."
        )

    if parent_id != previous_id:
        raise VerifiedMediaError(
            "The current release does not derive "
            "from the expected previous release."
        )

    if (
        previous_release.get(
            "project_id"
        )
        != current_release.get(
            "project_id"
        )
    ):
        raise VerifiedMediaError(
            "The two releases belong to different projects."
        )

    previous_record = _preview_record(
        previous_release,
        label="Previous release",
    )

    current_record = _preview_record(
        current_release,
        label="Current release",
    )

    if (
        previous_record["sha256"]
        == current_record["sha256"]
    ):
        raise VerifiedMediaError(
            "The rebuilt Ending B preview "
            "is byte-identical to the previous preview."
        )

    # Verify both objects completely before signing either URL.
    previous_verified = (
        _retrieve_verified_object(
            client,
            bucket=bucket,
            record=previous_record,
            label="Previous Ending B preview",
        )
    )

    current_verified = (
        _retrieve_verified_object(
            client,
            bucket=bucket,
            record=current_record,
            label="Current Ending B preview",
        )
    )

    previous_url = _signed_url(
        client,
        bucket=bucket,
        object_key=previous_record[
            "object_key"
        ],
        expires_in_seconds=expiry,
    )

    current_url = _signed_url(
        client,
        bucket=bucket,
        object_key=current_record[
            "object_key"
        ],
        expires_in_seconds=expiry,
    )

    return {
        "mode": "VERIFIED_B2_PLAYBACK",
        "status": (
            "B2 MEDIA RETRIEVED AND VERIFIED"
        ),
        "project_id": current_release[
            "project_id"
        ],
        "previous_release_id": previous_id,
        "release_id": current_id,
        "expires_in_seconds": expiry,
        "previous": {
            **previous_verified,
            "label": "Before revision",
            "url": previous_url,
        },
        "current": {
            **current_verified,
            "label": "Verified release",
            "url": current_url,
        },
    }


def load_verified_media_bundle(
    *,
    current_release: dict[str, Any] | None = None,
    expires_in_seconds: int = DEFAULT_EXPIRY_SECONDS,
) -> dict[str, Any]:
    """Load release evidence, verify B2 bytes, and sign playback."""
    previous_release = _read_release(
        PREVIOUS_RELEASE_PATH
    )

    if current_release is None:
        resolved_current = _read_release(
            CURRENT_RELEASE_PATH
        )
    else:
        resolved_current = dict(
            current_release
        )

        try:
            verify_canonical_release(
                resolved_current,
                label=(
                    "Current live release"
                ),
            )
        except Exception as exc:
            raise VerifiedMediaError(
                "The live release failed "
                "canonical verification."
            ) from exc

    environment = _require_environment()

    try:
        client = create_s3_client(
            environment
        )

        return build_verified_media_bundle(
            previous_release=previous_release,
            current_release=resolved_current,
            client=client,
            bucket=environment[
                "B2_BUCKET_NAME"
            ],
            expires_in_seconds=(
                expires_in_seconds
            ),
        )

    except VerifiedMediaError:
        raise

    except Exception as exc:
        raise VerifiedMediaError(
            "Verified B2 media playback failed."
        ) from exc


def local_presentation_fallback(
    *,
    reason: str,
) -> dict[str, Any]:
    """Return an explicitly labelled local presentation fallback."""
    safe_reason = (
        reason.strip()
        or "Remote B2 playback is unavailable."
    )

    return {
        "mode": (
            "LOCAL_PRESENTATION_FALLBACK"
        ),
        "status": (
            "LOCAL FALLBACK · NOT B2 PLAYBACK"
        ),
        "reason": safe_reason,
        "expires_in_seconds": None,
        "previous_release_id": (
            "shared-dialogue-v2"
        ),
        "release_id": (
            "presentation-fallback"
        ),
        "previous": {
            "label": "Before revision",
            "url": (
                "/release-media/"
                "ending_b_before.mp4"
            ),
            "sha256": None,
            "size_bytes": None,
            "media_type": "video/mp4",
            "remote_verified": False,
            "object_key": None,
        },
        "current": {
            "label": (
                "Local presentation fallback"
            ),
            "url": (
                "/release-media/"
                "ending_b_after.mp4"
            ),
            "sha256": None,
            "size_bytes": None,
            "media_type": "video/mp4",
            "remote_verified": False,
            "object_key": None,
        },
    }
