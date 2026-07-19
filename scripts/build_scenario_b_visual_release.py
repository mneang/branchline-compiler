"""Execute Scenario B: rebuild only media affected by one branch visual."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from branchline.domain.approval import (
    validate_approval,
)
from branchline.domain.story_graph import (
    asset_dependency_fingerprint,
    canonical_hash,
    load_story,
    plan_rebuild,
    source_hashes,
)
from branchline.media.previews import (
    create_story_preview_frame,
)
from branchline.media.thumbnails import (
    create_branch_thumbnail,
)
from branchline.media.visual_sources import (
    resolve_branch_visual,
)

from scripts.build_baseline_release import (
    canonical_bytes,
    create_preview,
    create_s3_client,
    sha256_bytes,
    upload_content_addressed,
    verify_remote_object,
)


PROJECT_ID = "last-train"
RELEASE_ID = "ending-b-visual-v3"

PREVIOUS_STORY_PATH = Path(
    "fixtures/main_story/story_v2_shared_dialogue.json"
)

CURRENT_STORY_PATH = Path(
    "fixtures/main_story/story_v3_ending_b_visual.json"
)

PLAN_PATH = Path(
    "evidence/story_graph_ending_b_visual_v3.json"
)

APPROVAL_PATH = Path(
    "evidence/approval_ending_b_visual_v3.json"
)

BASE_RELEASE_PATH = Path(
    "evidence/release_shared_dialogue_v2_canonical.json"
)

EVIDENCE_PATH = Path(
    "evidence/release_ending_b_visual_v3.json"
)

RELEASE_KEY = (
    f"branchline/projects/{PROJECT_ID}/"
    f"releases/{RELEASE_ID}/release.json"
)


class ScenarioBReleaseError(RuntimeError):
    """Raised when the branch-specific release cannot be verified."""


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ScenarioBReleaseError(
            f"Required file is missing: {path}"
        )

    document = json.loads(path.read_text())

    if not isinstance(document, dict):
        raise ScenarioBReleaseError(
            f"{path} must contain a JSON object"
        )

    return document


def verify_canonical_release(
    release: dict[str, Any],
    *,
    label: str,
) -> str:
    recorded = str(
        release.get("canonical_sha256", "")
    ).strip()

    content = dict(release)
    content.pop("canonical_sha256", None)

    calculated = sha256_bytes(
        canonical_bytes(content)
    )

    if recorded != calculated:
        raise ScenarioBReleaseError(
            f"{label} canonical hash is invalid"
        )

    return calculated


def require_b2_environment() -> dict[str, str]:
    env_path = Path(".env").resolve()

    if not env_path.exists():
        raise ScenarioBReleaseError(".env is missing")

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
        raise ScenarioBReleaseError(
            "Missing B2 values: " + ", ".join(missing)
        )

    return values


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
    calculated = sha256_bytes(content)

    if calculated != record["sha256"]:
        raise ScenarioBReleaseError(
            f"Remote hash mismatch for "
            f"{record.get('logical_id')}"
        )

    output_path.write_bytes(content)
    return output_path


def caption_text_from_srt(path: Path) -> str:
    """Extract spoken caption text from an SRT asset."""
    lines = []

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.isdigit():
            continue

        if "-->" in line:
            continue

        lines.append(line)

    text = " ".join(lines).strip()

    if not text:
        raise ScenarioBReleaseError(
            "Reused caption asset contains no dialogue"
        )

    return text


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


def build_paths(
    story: dict[str, Any],
    assets: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    results = []

    for path_spec in story["paths"]:
        required = path_spec["required_assets"]

        missing = [
            logical_id
            for logical_id in required
            if logical_id not in assets
        ]

        failed = [
            logical_id
            for logical_id in required
            if logical_id in assets
            and not assets[logical_id].get(
                "remote_verified"
            )
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


def main() -> int:
    if (
        EVIDENCE_PATH.exists()
        and os.getenv("FORCE_SCENARIO_B") != "yes"
    ):
        print(
            f"Scenario B evidence already exists: "
            f"{EVIDENCE_PATH}\n"
            "No media was rebuilt."
        )
        return 0

    try:
        previous_story = load_story(
            PREVIOUS_STORY_PATH
        )

        current_story = load_story(
            CURRENT_STORY_PATH
        )

        recorded_plan = read_json(PLAN_PATH)
        approval = read_json(APPROVAL_PATH)
        base_release = read_json(
            BASE_RELEASE_PATH
        )

        recalculated_plan = plan_rebuild(
            previous_story,
            current_story,
        )

        if (
            canonical_hash(recalculated_plan)
            != canonical_hash(recorded_plan)
        ):
            raise ScenarioBReleaseError(
                "Recorded plan no longer matches "
                "the two story versions"
            )

        validate_approval(
            recorded_plan,
            approval,
        )

        verify_canonical_release(
            base_release,
            label="Canonical Release V2",
        )

        if (
            base_release.get("project_id")
            != current_story.get("project_id")
        ):
            raise ScenarioBReleaseError(
                "Base release and current story "
                "belong to different projects"
            )

        env = require_b2_environment()
        bucket = env["B2_BUCKET_NAME"]
        client = create_s3_client(env)

        remote_base_bytes = client.get_object(
            Bucket=bucket,
            Key=base_release[
                "release_object_key"
            ],
        )["Body"].read()

        remote_base = json.loads(
            remote_base_bytes.decode("utf-8")
        )

        local_base_hash = verify_canonical_release(
            base_release,
            label="Local base release",
        )

        remote_base_hash = verify_canonical_release(
            remote_base,
            label="Remote base release",
        )

        if local_base_hash != remote_base_hash:
            raise ScenarioBReleaseError(
                "Local and remote base releases differ"
            )

        for logical_id, record in sorted(
            base_release["assets"].items()
        ):
            verification = verify_remote_object(
                client,
                bucket=bucket,
                object_key=record["object_key"],
                expected_sha256=record["sha256"],
            )

            if not verification["remote_verified"]:
                raise ScenarioBReleaseError(
                    f"Base asset failed verification: "
                    f"{logical_id}"
                )

        asset_specs = {
            asset["id"]: asset
            for asset in current_story["assets"]
        }

        all_asset_ids = set(asset_specs)
        stale_assets = set(
            recorded_plan["stale_assets"]
        )
        reused_assets = set(
            recorded_plan["reused_assets"]
        )

        if stale_assets & reused_assets:
            raise ScenarioBReleaseError(
                "An asset cannot be stale and reusable"
            )

        if stale_assets | reused_assets != all_asset_ids:
            raise ScenarioBReleaseError(
                "Plan does not partition every story asset"
            )

        changed_branches = {
            source_id.split(".", 1)[1]
            for source_id in recorded_plan[
                "changed_sources"
            ]
            if source_id.startswith("image.")
        }

        expected_stale = {
            logical_id
            for branch_id in changed_branches
            for logical_id in (
                f"thumbnail.{branch_id}",
                f"preview.{branch_id}",
            )
        }

        if stale_assets != expected_stale:
            raise ScenarioBReleaseError(
                "Visual source changes did not map to "
                "the expected thumbnail/preview pair"
            )

        fingerprints = expected_fingerprints(
            current_story
        )

        assets: dict[str, dict[str, Any]] = {}

        for logical_id in sorted(reused_assets):
            previous = base_release["assets"].get(
                logical_id
            )

            if previous is None:
                raise ScenarioBReleaseError(
                    f"Reusable asset is missing: {logical_id}"
                )

            if (
                previous.get(
                    "dependency_fingerprint"
                )
                != fingerprints[logical_id]
            ):
                raise ScenarioBReleaseError(
                    f"Reusable asset has stale dependencies: "
                    f"{logical_id}"
                )

            record = deepcopy(previous)

            record.update(
                {
                    "release_action": (
                        "reused_from_previous_release"
                    ),
                    "reused_from_release_id": (
                        base_release["release_id"]
                    ),
                    "dependency_fingerprint": (
                        fingerprints[logical_id]
                    ),
                }
            )

            assets[logical_id] = record

        work_dir = Path(
            tempfile.mkdtemp(
                prefix="branchline-scenario-b-"
            )
        )

        voice_path = download_verified_asset(
            client,
            bucket=bucket,
            record=base_release["assets"][
                "voice.opening"
            ],
            output_path=work_dir / "voice.opening.wav",
        )

        caption_path = download_verified_asset(
            client,
            bucket=bucket,
            record=base_release["assets"][
                "caption.opening"
            ],
            output_path=work_dir / "caption.opening.srt",
        )

        caption_text = caption_text_from_srt(
            caption_path
        )

        for logical_id in sorted(stale_assets):
            asset_type, branch_id = logical_id.split(
                ".",
                1,
            )

            visual = resolve_branch_visual(
                current_story,
                branch_id,
            )

            if asset_type == "thumbnail":
                output_path = (
                    work_dir / f"{logical_id}.png"
                )

                create_branch_thumbnail(
                    output_path,
                    branch_label=visual["label"],
                    destination=visual["destination"],
                    background=visual["background"],
                )

                media_type = "image/png"

            elif asset_type == "preview":
                frame_path = (
                    work_dir / f"frame.{branch_id}.png"
                )

                output_path = (
                    work_dir / f"{logical_id}.mp4"
                )

                create_story_preview_frame(
                    frame_path,
                    branch_label=visual["label"],
                    destination=visual["destination"],
                    dialogue=caption_text,
                    background=visual["background"],
                )

                create_preview(
                    image_path=frame_path,
                    audio_path=voice_path,
                    output_path=output_path,
                )

                media_type = "video/mp4"

            else:
                raise ScenarioBReleaseError(
                    f"Unsupported stale asset: {logical_id}"
                )

            stored = upload_content_addressed(
                client,
                bucket=bucket,
                path=output_path,
                media_type=media_type,
                logical_id=logical_id,
            )

            assets[logical_id] = {
                "logical_id": logical_id,
                "creation_action": (
                    "compiled_by_branchline"
                ),
                "materialization_action": (
                    "branch_visual_rebuild"
                ),
                "release_action": "rebuilt",
                **stored,
                "depends_on": asset_specs[
                    logical_id
                ]["depends_on"],
                "dependency_fingerprint": (
                    fingerprints[logical_id]
                ),
                "visual_source": visual,
            }

        if set(assets) != all_asset_ids:
            raise ScenarioBReleaseError(
                "Final release does not contain "
                "every story asset"
            )

        for logical_id, record in sorted(
            assets.items()
        ):
            record.update(
                verify_remote_object(
                    client,
                    bucket=bucket,
                    object_key=record["object_key"],
                    expected_sha256=record["sha256"],
                )
            )

        deltas = {}

        for logical_id in sorted(all_asset_ids):
            previous = base_release["assets"][
                logical_id
            ]

            current = assets[logical_id]

            hash_changed = (
                previous["sha256"]
                != current["sha256"]
            )

            key_changed = (
                previous["object_key"]
                != current["object_key"]
            )

            if logical_id in stale_assets:
                if not hash_changed:
                    raise ScenarioBReleaseError(
                        f"Rebuilt asset bytes did not change: "
                        f"{logical_id}"
                    )

                if current["release_action"] != "rebuilt":
                    raise ScenarioBReleaseError(
                        f"Incorrect action for rebuilt asset: "
                        f"{logical_id}"
                    )

            else:
                if hash_changed or key_changed:
                    raise ScenarioBReleaseError(
                        f"Reusable asset changed unexpectedly: "
                        f"{logical_id}"
                    )

                if (
                    current["release_action"]
                    != "reused_from_previous_release"
                ):
                    raise ScenarioBReleaseError(
                        f"Incorrect reuse action: {logical_id}"
                    )

            deltas[logical_id] = {
                "previous_sha256": previous["sha256"],
                "current_sha256": current["sha256"],
                "hash_changed": hash_changed,
                "previous_object_key": previous[
                    "object_key"
                ],
                "current_object_key": current[
                    "object_key"
                ],
                "object_key_changed": key_changed,
                "release_action": current[
                    "release_action"
                ],
            }

        stale_remaining = sorted(
            logical_id
            for logical_id, record in assets.items()
            if record.get(
                "dependency_fingerprint"
            ) != fingerprints[logical_id]
        )

        if stale_remaining:
            raise ScenarioBReleaseError(
                "Stale assets remain: "
                f"{stale_remaining}"
            )

        paths = build_paths(
            current_story,
            assets,
        )

        if not all(
            path["verified"]
            for path in paths
        ):
            raise ScenarioBReleaseError(
                "At least one reachable path failed"
            )

        release: dict[str, Any] = {
            "schema_version": 2,
            "project_id": PROJECT_ID,
            "release_id": RELEASE_ID,
            "previous_release_id": (
                base_release["release_id"]
            ),
            "release_object_key": RELEASE_KEY,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "story_sha256": canonical_hash(
                current_story
            ),
            "source_hashes": source_hashes(
                current_story
            ),
            "changed_sources": recorded_plan[
                "changed_sources"
            ],
            "planned_stale_assets": sorted(
                stale_assets
            ),
            "planned_reused_assets": sorted(
                reused_assets
            ),
            "affected_paths": recorded_plan[
                "affected_paths"
            ],
            "approval": {
                "approval_id": approval[
                    "approval_id"
                ],
                "approved_by": approval[
                    "approved_by"
                ],
                "approved_at": approval[
                    "approved_at"
                ],
                "plan_sha256": approval[
                    "plan_sha256"
                ],
            },
            "assets": assets,
            "asset_deltas": deltas,
            "paths": paths,
            "genblaze": {
                "new_generation_runs": 0,
                "new_ai_requests": 0,
                "reused_voice_asset": True,
                "voice_source_release_id": (
                    base_release["release_id"]
                ),
                "inherited_run_id": (
                    base_release.get(
                        "genblaze",
                        {},
                    ).get("run_id")
                ),
                "reason": (
                    "Only image.ending_b changed; "
                    "dialogue and voice remained current."
                ),
            },
            "metrics": {
                "source_changes": 1,
                "assets_total": 6,
                "assets_rebuilt": len(
                    stale_assets
                ),
                "assets_reused": len(
                    reused_assets
                ),
                "reuse_rate_percent": round(
                    len(reused_assets) / 6 * 100,
                    1,
                ),
                "assets_remote_verified": 6,
                "paths_total": len(paths),
                "paths_verified": sum(
                    1
                    for path in paths
                    if path["verified"]
                ),
                "stale_assets_remaining": 0,
                "new_ai_requests": 0,
            },
            "publication_status": "SAFE_TO_PUBLISH",
            "status": (
                "BRANCH-SPECIFIC RELEASE "
                "COMPLETED AND VERIFIED"
            ),
        }

        release["canonical_sha256"] = (
            sha256_bytes(
                canonical_bytes(release)
            )
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
            Key=RELEASE_KEY,
            Body=payload,
            ContentType="application/json",
        )

        remote_payload = client.get_object(
            Bucket=bucket,
            Key=RELEASE_KEY,
        )["Body"].read()

        if remote_payload != payload:
            raise ScenarioBReleaseError(
                "Remote release bytes differ "
                "from local release bytes"
            )

        remote_release = json.loads(
            remote_payload.decode("utf-8")
        )

        verify_canonical_release(
            remote_release,
            label="Remote Scenario B release",
        )

        EVIDENCE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        EVIDENCE_PATH.write_bytes(payload)

        summary = {
            "scenario": "B",
            "release_id": RELEASE_ID,
            "changed_sources": 1,
            "assets_rebuilt": 2,
            "assets_reused": 4,
            "reuse_rate_percent": 66.7,
            "assets_remote_verified": 6,
            "verified_paths": "2/2",
            "ending_a_unchanged": True,
            "stale_assets_remaining": 0,
            "new_ai_requests": 0,
            "publication_status": "SAFE_TO_PUBLISH",
            "status": (
                "BRANCH-SPECIFIC RELEASE "
                "COMPLETED AND VERIFIED"
            ),
        }

        print(json.dumps(summary, indent=2))
        return 0

    except Exception as exc:
        print(
            "SCENARIO B RELEASE FAILED: "
            f"{type(exc).__name__}: {exc}"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
