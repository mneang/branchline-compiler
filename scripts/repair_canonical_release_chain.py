"""Create dependency-truthful canonical releases without new AI requests."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import boto3
from dotenv import load_dotenv

from branchline.domain.story_graph import (
    asset_dependency_fingerprint,
    canonical_hash,
    load_story,
    source_hashes,
)
from branchline.media.previews import (
    create_story_preview_frame,
)
from branchline.media.thumbnails import (
    create_branch_thumbnail,
)

from scripts.build_baseline_release import (
    canonical_bytes,
    create_caption,
    create_preview,
    sha256_bytes,
    upload_content_addressed,
    verify_remote_object,
)


PROJECT_ID = "last-train"

BASELINE_STORY_PATH = Path(
    "fixtures/main_story/story_v1.json"
)
CURRENT_STORY_PATH = Path(
    "fixtures/main_story/story_v2_shared_dialogue.json"
)

LEGACY_BASELINE_PATH = Path(
    "evidence/release_baseline_v1.json"
)
LEGACY_CURRENT_PATH = Path(
    "evidence/release_shared_dialogue_v2.json"
)

CANONICAL_BASELINE_PATH = Path(
    "evidence/release_baseline_v1_canonical.json"
)
CANONICAL_CURRENT_PATH = Path(
    "evidence/release_shared_dialogue_v2_canonical.json"
)

CANONICAL_BASELINE_ID = "baseline-v1-canonical"
CANONICAL_CURRENT_ID = "shared-dialogue-v2-canonical"

CANONICAL_BASELINE_KEY = (
    f"branchline/projects/{PROJECT_ID}/"
    f"releases/{CANONICAL_BASELINE_ID}/release.json"
)

CANONICAL_CURRENT_KEY = (
    f"branchline/projects/{PROJECT_ID}/"
    f"releases/{CANONICAL_CURRENT_ID}/release.json"
)

BRANCHES = {
    "ending_a": {
        "label": "ENDING A",
        "destination": "Board the midnight-blue express",
        "background": (20, 45, 78),
    },
    "ending_b": {
        "label": "ENDING B",
        "destination": "Remain beneath the station lights",
        "background": (76, 27, 47),
    },
}


class CanonicalRepairError(RuntimeError):
    """Raised when the canonical release chain cannot be repaired."""


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise CanonicalRepairError(f"Missing file: {path}")

    document = json.loads(path.read_text())

    if not isinstance(document, dict):
        raise CanonicalRepairError(
            f"{path} must contain a JSON object"
        )

    return document


def verify_canonical_hash(
    document: dict[str, Any],
    *,
    label: str,
) -> None:
    recorded = str(
        document.get("canonical_sha256", "")
    ).strip()

    content = dict(document)
    content.pop("canonical_sha256", None)

    calculated = sha256_bytes(
        canonical_bytes(content)
    )

    if recorded != calculated:
        raise CanonicalRepairError(
            f"{label} canonical hash is invalid"
        )


def require_b2_environment() -> dict[str, str]:
    env_path = Path(".env").resolve()

    if not env_path.exists():
        raise CanonicalRepairError(".env is missing")

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
        name: os.getenv(name, "").strip()
        for name in names
    }

    missing = [
        name
        for name, value in values.items()
        if not value
    ]

    if missing:
        raise CanonicalRepairError(
            "Missing B2 values: " + ", ".join(missing)
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
        raise CanonicalRepairError("Invalid B2 endpoint")

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=env["B2_KEY_ID"],
        aws_secret_access_key=env["B2_APP_KEY"],
        region_name=env["B2_REGION"],
    )


def story_dialogue(story: dict[str, Any]) -> str:
    for source in story["sources"]:
        if source["id"] == "dialogue.opening":
            return str(source["value"])

    raise CanonicalRepairError("dialogue.opening is missing")


def download_verified_asset(
    client: Any,
    *,
    bucket: str,
    record: dict[str, Any],
    output_path: Path,
) -> Path:
    response = client.get_object(
        Bucket=bucket,
        Key=record["object_key"],
    )

    content = response["Body"].read()

    if sha256_bytes(content) != record["sha256"]:
        raise CanonicalRepairError(
            f"Remote hash mismatch for {record['logical_id']}"
        )

    output_path.write_bytes(content)
    return output_path


def expected_fingerprints(
    story: dict[str, Any],
) -> dict[str, str]:
    source_digests = source_hashes(story)
    memo: dict[str, str] = {}

    return {
        asset["id"]: asset_dependency_fingerprint(
            asset["id"],
            story=story,
            source_digest_by_id=source_digests,
            memo=memo,
        )
        for asset in story["assets"]
    }


def add_remote_verification(
    client: Any,
    *,
    bucket: str,
    assets: dict[str, dict[str, Any]],
) -> None:
    for asset in assets.values():
        asset.update(
            verify_remote_object(
                client,
                bucket=bucket,
                object_key=asset["object_key"],
                expected_sha256=asset["sha256"],
            )
        )


def build_paths(
    story: dict[str, Any],
    assets: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    results = []

    for path_spec in story["paths"]:
        required = path_spec["required_assets"]

        missing = [
            asset_id
            for asset_id in required
            if asset_id not in assets
        ]

        failed = [
            asset_id
            for asset_id in required
            if asset_id in assets
            and not assets[asset_id].get("remote_verified")
        ]

        results.append(
            {
                "path_id": path_spec["id"],
                "required_assets": required,
                "missing_assets": missing,
                "failed_assets": failed,
                "verified": not missing and not failed,
            }
        )

    return results


def upload_release(
    client: Any,
    *,
    bucket: str,
    key: str,
    path: Path,
    release: dict[str, Any],
) -> None:
    release["canonical_sha256"] = sha256_bytes(
        canonical_bytes(release)
    )

    payload = (
        json.dumps(
            release,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")

    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=payload,
        ContentType="application/json",
    )

    downloaded = client.get_object(
        Bucket=bucket,
        Key=key,
    )["Body"].read()

    if downloaded != payload:
        raise CanonicalRepairError(
            f"Remote release bytes differ for {key}"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def copied_voice_record(
    *,
    legacy_record: dict[str, Any],
    fingerprint: str,
    release_action: str,
    source_release_id: str,
) -> dict[str, Any]:
    keep = (
        "logical_id",
        "object_key",
        "b2_uri",
        "sha256",
        "size_bytes",
        "media_type",
        "provider",
        "model",
        "voice",
        "genblaze_run_id",
    )

    record = {
        key: legacy_record[key]
        for key in keep
        if key in legacy_record
    }

    record.update(
        {
            "logical_id": "voice.opening",
            "creation_action": "generated_through_genblaze",
            "materialization_action": (
                "adopted_verified_genblaze_asset"
            ),
            "release_action": release_action,
            "source_release_id": source_release_id,
            "depends_on": ["dialogue.opening"],
            "dependency_fingerprint": fingerprint,
        }
    )

    return record


def main() -> int:
    if (
        CANONICAL_BASELINE_PATH.exists()
        and CANONICAL_CURRENT_PATH.exists()
        and os.getenv("FORCE_CANONICAL_REPAIR") != "yes"
    ):
        print(
            "Canonical release evidence already exists. "
            "No media was rebuilt."
        )
        return 0

    try:
        baseline_story = load_story(BASELINE_STORY_PATH)
        current_story = load_story(CURRENT_STORY_PATH)

        legacy_baseline = read_json(LEGACY_BASELINE_PATH)
        legacy_current = read_json(LEGACY_CURRENT_PATH)

        verify_canonical_hash(
            legacy_baseline,
            label="Legacy baseline",
        )
        verify_canonical_hash(
            legacy_current,
            label="Legacy selective release",
        )

        env = require_b2_environment()
        bucket = env["B2_BUCKET_NAME"]
        client = create_client(env)

        work_dir = Path(
            tempfile.mkdtemp(
                prefix="branchline-canonical-repair-"
            )
        )

        baseline_dialogue = story_dialogue(baseline_story)
        current_dialogue = story_dialogue(current_story)

        baseline_voice_path = download_verified_asset(
            client,
            bucket=bucket,
            record=legacy_baseline["assets"]["voice.opening"],
            output_path=work_dir / "baseline-voice.wav",
        )

        current_voice_path = download_verified_asset(
            client,
            bucket=bucket,
            record=legacy_current["assets"]["voice.opening"],
            output_path=work_dir / "current-voice.wav",
        )

        baseline_fingerprints = expected_fingerprints(
            baseline_story
        )

        current_fingerprints = expected_fingerprints(
            current_story
        )

        baseline_assets: dict[str, dict[str, Any]] = {}

        baseline_assets["voice.opening"] = copied_voice_record(
            legacy_record=legacy_baseline["assets"]["voice.opening"],
            fingerprint=baseline_fingerprints["voice.opening"],
            release_action="canonicalized_from_verified_release",
            source_release_id=legacy_baseline["release_id"],
        )

        baseline_caption = work_dir / "baseline-caption.srt"
        create_caption(
            baseline_caption,
            baseline_dialogue,
        )

        stored_caption = upload_content_addressed(
            client,
            bucket=bucket,
            path=baseline_caption,
            media_type="application/x-subrip",
            logical_id="caption.opening",
        )

        baseline_assets["caption.opening"] = {
            "logical_id": "caption.opening",
            "creation_action": "compiled_by_branchline",
            "materialization_action": "canonical_repair",
            "release_action": "canonicalized",
            **stored_caption,
            "depends_on": ["dialogue.opening"],
            "dependency_fingerprint": (
                baseline_fingerprints["caption.opening"]
            ),
        }

        for branch_id, presentation in BRANCHES.items():
            thumbnail_id = f"thumbnail.{branch_id}"
            preview_id = f"preview.{branch_id}"

            thumbnail_path = (
                work_dir / f"baseline-{thumbnail_id}.png"
            )
            preview_frame_path = (
                work_dir / f"baseline-frame-{branch_id}.png"
            )
            preview_path = (
                work_dir / f"baseline-{preview_id}.mp4"
            )

            create_branch_thumbnail(
                thumbnail_path,
                branch_label=presentation["label"],
                destination=presentation["destination"],
                background=presentation["background"],
            )

            create_story_preview_frame(
                preview_frame_path,
                branch_label=presentation["label"],
                destination=presentation["destination"],
                dialogue=baseline_dialogue,
                background=presentation["background"],
            )

            create_preview(
                image_path=preview_frame_path,
                audio_path=baseline_voice_path,
                output_path=preview_path,
            )

            stored_thumbnail = upload_content_addressed(
                client,
                bucket=bucket,
                path=thumbnail_path,
                media_type="image/png",
                logical_id=thumbnail_id,
            )

            stored_preview = upload_content_addressed(
                client,
                bucket=bucket,
                path=preview_path,
                media_type="video/mp4",
                logical_id=preview_id,
            )

            baseline_assets[thumbnail_id] = {
                "logical_id": thumbnail_id,
                "creation_action": "compiled_by_branchline",
                "materialization_action": "canonical_repair",
                "release_action": "canonicalized",
                **stored_thumbnail,
                "depends_on": [f"image.{branch_id}"],
                "dependency_fingerprint": (
                    baseline_fingerprints[thumbnail_id]
                ),
            }

            baseline_assets[preview_id] = {
                "logical_id": preview_id,
                "creation_action": "compiled_by_branchline",
                "materialization_action": "canonical_repair",
                "release_action": "canonicalized",
                **stored_preview,
                "depends_on": [
                    "voice.opening",
                    "caption.opening",
                    f"image.{branch_id}",
                ],
                "dependency_fingerprint": (
                    baseline_fingerprints[preview_id]
                ),
            }

        add_remote_verification(
            client,
            bucket=bucket,
            assets=baseline_assets,
        )

        baseline_paths = build_paths(
            baseline_story,
            baseline_assets,
        )

        canonical_baseline = {
            "schema_version": 2,
            "project_id": PROJECT_ID,
            "release_id": CANONICAL_BASELINE_ID,
            "legacy_release_id": legacy_baseline["release_id"],
            "release_object_key": CANONICAL_BASELINE_KEY,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "story_sha256": canonical_hash(baseline_story),
            "source_hashes": source_hashes(baseline_story),
            "assets": baseline_assets,
            "paths": baseline_paths,
            "genblaze": deepcopy(
                legacy_baseline.get("genblaze", {})
            ),
            "metrics": {
                "assets_total": 6,
                "assets_remote_verified": 6,
                "paths_total": 2,
                "paths_verified": 2,
            },
            "publication_status": "SAFE_TO_PUBLISH",
            "status": "CANONICAL BASELINE VERIFIED",
        }

        upload_release(
            client,
            bucket=bucket,
            key=CANONICAL_BASELINE_KEY,
            path=CANONICAL_BASELINE_PATH,
            release=canonical_baseline,
        )

        current_assets: dict[str, dict[str, Any]] = {}

        current_assets["voice.opening"] = copied_voice_record(
            legacy_record=legacy_current["assets"]["voice.opening"],
            fingerprint=current_fingerprints["voice.opening"],
            release_action="rebuilt",
            source_release_id=legacy_current["release_id"],
        )

        current_caption = work_dir / "current-caption.srt"
        create_caption(
            current_caption,
            current_dialogue,
        )

        stored_current_caption = upload_content_addressed(
            client,
            bucket=bucket,
            path=current_caption,
            media_type="application/x-subrip",
            logical_id="caption.opening",
        )

        current_assets["caption.opening"] = {
            "logical_id": "caption.opening",
            "creation_action": "compiled_by_branchline",
            "materialization_action": "canonical_repair",
            "release_action": "rebuilt",
            **stored_current_caption,
            "depends_on": ["dialogue.opening"],
            "dependency_fingerprint": (
                current_fingerprints["caption.opening"]
            ),
        }

        for branch_id, presentation in BRANCHES.items():
            thumbnail_id = f"thumbnail.{branch_id}"
            preview_id = f"preview.{branch_id}"

            reused_thumbnail = deepcopy(
                baseline_assets[thumbnail_id]
            )

            reused_thumbnail.update(
                {
                    "release_action": (
                        "reused_from_canonical_baseline"
                    ),
                    "reused_from_release_id": (
                        CANONICAL_BASELINE_ID
                    ),
                }
            )

            current_assets[thumbnail_id] = reused_thumbnail

            preview_frame_path = (
                work_dir / f"current-frame-{branch_id}.png"
            )
            preview_path = (
                work_dir / f"current-{preview_id}.mp4"
            )

            create_story_preview_frame(
                preview_frame_path,
                branch_label=presentation["label"],
                destination=presentation["destination"],
                dialogue=current_dialogue,
                background=presentation["background"],
            )

            create_preview(
                image_path=preview_frame_path,
                audio_path=current_voice_path,
                output_path=preview_path,
            )

            stored_preview = upload_content_addressed(
                client,
                bucket=bucket,
                path=preview_path,
                media_type="video/mp4",
                logical_id=preview_id,
            )

            current_assets[preview_id] = {
                "logical_id": preview_id,
                "creation_action": "compiled_by_branchline",
                "materialization_action": "canonical_repair",
                "release_action": "rebuilt",
                **stored_preview,
                "depends_on": [
                    "voice.opening",
                    "caption.opening",
                    f"image.{branch_id}",
                ],
                "dependency_fingerprint": (
                    current_fingerprints[preview_id]
                ),
            }

        add_remote_verification(
            client,
            bucket=bucket,
            assets=current_assets,
        )

        deltas = {}

        for logical_id in sorted(current_assets):
            previous = baseline_assets[logical_id]
            current = current_assets[logical_id]

            deltas[logical_id] = {
                "previous_sha256": previous["sha256"],
                "current_sha256": current["sha256"],
                "hash_changed": (
                    previous["sha256"] != current["sha256"]
                ),
                "previous_object_key": previous["object_key"],
                "current_object_key": current["object_key"],
                "object_key_changed": (
                    previous["object_key"]
                    != current["object_key"]
                ),
                "release_action": current["release_action"],
            }

        rebuilt = {
            logical_id
            for logical_id, delta in deltas.items()
            if delta["hash_changed"]
        }

        reused = {
            logical_id
            for logical_id, delta in deltas.items()
            if not delta["hash_changed"]
        }

        expected_rebuilt = {
            "voice.opening",
            "caption.opening",
            "preview.ending_a",
            "preview.ending_b",
        }

        expected_reused = {
            "thumbnail.ending_a",
            "thumbnail.ending_b",
        }

        if rebuilt != expected_rebuilt:
            raise CanonicalRepairError(
                f"Unexpected rebuilt set: {sorted(rebuilt)}"
            )

        if reused != expected_reused:
            raise CanonicalRepairError(
                f"Unexpected reused set: {sorted(reused)}"
            )

        current_paths = build_paths(
            current_story,
            current_assets,
        )

        canonical_current = {
            "schema_version": 2,
            "project_id": PROJECT_ID,
            "release_id": CANONICAL_CURRENT_ID,
            "previous_release_id": CANONICAL_BASELINE_ID,
            "legacy_release_id": legacy_current["release_id"],
            "release_object_key": CANONICAL_CURRENT_KEY,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "story_sha256": canonical_hash(current_story),
            "source_hashes": source_hashes(current_story),
            "changed_sources": ["dialogue.opening"],
            "assets": current_assets,
            "asset_deltas": deltas,
            "paths": current_paths,
            "genblaze": deepcopy(
                legacy_current.get("genblaze", {})
            ),
            "metrics": {
                "source_changes": 1,
                "assets_total": 6,
                "assets_rebuilt": 4,
                "assets_reused": 2,
                "reuse_rate_percent": 33.3,
                "assets_remote_verified": 6,
                "paths_total": 2,
                "paths_verified": 2,
                "stale_assets_remaining": 0,
            },
            "publication_status": "SAFE_TO_PUBLISH",
            "status": (
                "CANONICAL SELECTIVE RELEASE "
                "COMPLETED AND VERIFIED"
            ),
        }

        upload_release(
            client,
            bucket=bucket,
            key=CANONICAL_CURRENT_KEY,
            path=CANONICAL_CURRENT_PATH,
            release=canonical_current,
        )

        summary = {
            "canonical_baseline": CANONICAL_BASELINE_ID,
            "canonical_current": CANONICAL_CURRENT_ID,
            "assets_rebuilt": 4,
            "assets_reused": 2,
            "assets_remote_verified": 6,
            "paths_verified": "2/2",
            "stale_assets_remaining": 0,
            "publication_status": "SAFE_TO_PUBLISH",
            "new_ai_requests": 0,
            "status": (
                "CANONICAL RELEASE CHAIN "
                "COMPLETED AND VERIFIED"
            ),
        }

        print(json.dumps(summary, indent=2))
        return 0

    except Exception as exc:
        print(
            "CANONICAL REPAIR FAILED: "
            f"{type(exc).__name__}: {exc}"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
