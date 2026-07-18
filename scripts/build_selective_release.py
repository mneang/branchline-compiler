"""Build Scenario A Release V2 by rebuilding only stale story assets."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from genblaze_core import (
    KeyStrategy,
    Modality,
    ObjectStorageSink,
    Pipeline,
)

from branchline.domain.approval import validate_approval
from branchline.domain.story_graph import (
    canonical_hash,
    load_story,
    plan_rebuild,
    source_hashes,
)

from scripts.build_baseline_release import (
    asset_dependency_fingerprint,
    canonical_bytes,
    create_caption,
    create_preview,
    create_s3_client,
    create_thumbnail,
    read_json,
    sha256_bytes,
    story_dialogue,
    upload_content_addressed,
    verify_remote_object,
)

from scripts.genblaze_gemini_b2_smoke import (
    GeminiTTSProvider,
    create_backend,
    require_environment,
)


PROJECT_ID = "last-train"
PREVIOUS_RELEASE_ID = "baseline-v1"
RELEASE_ID = "shared-dialogue-v2"

PREVIOUS_STORY_PATH = Path(
    "fixtures/main_story/story_v1.json"
)
CURRENT_STORY_PATH = Path(
    "fixtures/main_story/story_v2_shared_dialogue.json"
)

PLAN_PATH = Path(
    "evidence/story_graph_shared_dialogue.json"
)
APPROVAL_PATH = Path(
    "evidence/approval_shared_dialogue.json"
)
BASELINE_PATH = Path(
    "evidence/release_baseline_v1.json"
)
EVIDENCE_PATH = Path(
    "evidence/release_shared_dialogue_v2.json"
)

MODEL = "gemini-2.5-flash-preview-tts"
VOICE = "Kore"

GENBLAZE_PREFIX = "branchline/genblaze"
CAS_PREFIX = "branchline/cas/sha256"

RELEASE_KEY = (
    f"branchline/projects/{PROJECT_ID}/"
    f"releases/{RELEASE_ID}/release.json"
)


class SelectiveReleaseError(RuntimeError):
    """Raised when a selective release cannot be safely produced."""


def verify_release_canonical_hash(
    release: dict[str, Any],
    *,
    label: str,
) -> str:
    """Verify a Branchline release's canonical SHA-256."""
    recorded = str(
        release.get("canonical_sha256", "")
    ).strip()

    if len(recorded) != 64:
        raise SelectiveReleaseError(
            f"{label} has no valid canonical_sha256"
        )

    without_hash = dict(release)
    without_hash.pop("canonical_sha256", None)

    calculated = sha256_bytes(
        canonical_bytes(without_hash)
    )

    if calculated != recorded:
        raise SelectiveReleaseError(
            f"{label} canonical hash mismatch: "
            f"{calculated} != {recorded}"
        )

    return calculated


def verify_baseline_release(
    client: Any,
    *,
    bucket: str,
    baseline: dict[str, Any],
) -> None:
    """Re-download and verify the baseline before reusing any assets."""
    local_hash = verify_release_canonical_hash(
        baseline,
        label="Local baseline release",
    )

    release_key = str(
        baseline.get("release_object_key", "")
    ).strip()

    if not release_key:
        raise SelectiveReleaseError(
            "Baseline release has no release_object_key"
        )

    response = client.get_object(
        Bucket=bucket,
        Key=release_key,
    )

    remote_bytes = response["Body"].read()

    try:
        remote_baseline = json.loads(
            remote_bytes.decode("utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SelectiveReleaseError(
            "Remote baseline release is not valid JSON"
        ) from exc

    remote_hash = verify_release_canonical_hash(
        remote_baseline,
        label="Remote baseline release",
    )

    if local_hash != remote_hash:
        raise SelectiveReleaseError(
            "Local and remote baseline canonical hashes differ"
        )

    if baseline.get("release_id") != remote_baseline.get(
        "release_id"
    ):
        raise SelectiveReleaseError(
            "Local and remote baseline release IDs differ"
        )

    for logical_id, asset in sorted(
        remote_baseline["assets"].items()
    ):
        verification = verify_remote_object(
            client,
            bucket=bucket,
            object_key=asset["object_key"],
            expected_sha256=asset["sha256"],
        )

        if not verification["remote_verified"]:
            raise SelectiveReleaseError(
                f"Baseline asset failed verification: {logical_id}"
            )


def generate_updated_voice(
    *,
    env: dict[str, str],
    dialogue: str,
    work_dir: Path,
) -> dict[str, Any]:
    """Generate the changed voice through Genblaze and persist it to B2."""
    provider = GeminiTTSProvider(
        api_key=env["GEMINI_API_KEY"],
        output_dir=work_dir / "provider-output",
    )

    sink = ObjectStorageSink(
        create_backend(env),
        prefix=GENBLAZE_PREFIX,
        key_strategy=KeyStrategy.CONTENT_ADDRESSABLE,
    )

    result = None

    try:
        result = (
            Pipeline(
                "branchline-selective-shared-dialogue"
            )
            .step(
                provider,
                model=MODEL,
                prompt=(
                    "Read calmly and clearly. "
                    "Spoken dialogue begins now: "
                    f"{dialogue}"
                ),
                modality=Modality.AUDIO,
                params={"voice": VOICE},
                metadata={
                    "project_id": PROJECT_ID,
                    "release_id": RELEASE_ID,
                    "logical_asset": "voice.opening",
                    "rebuild_reason": (
                        "dialogue.opening changed"
                    ),
                },
            )
            .run(
                sink=sink,
                fail_fast=True,
                raise_on_failure=True,
                max_retries=0,
                timeout=90,
            )
        )
    finally:
        sink.close()

    if result is None:
        raise SelectiveReleaseError(
            "Genblaze returned no pipeline result"
        )

    if (
        not result.run.steps
        or not result.run.steps[0].assets
    ):
        raise SelectiveReleaseError(
            "Genblaze returned no voice asset"
        )

    asset = result.run.steps[0].assets[0]

    verification_backend = create_backend(env)

    verification_sink = ObjectStorageSink(
        verification_backend,
        prefix=GENBLAZE_PREFIX,
        key_strategy=KeyStrategy.CONTENT_ADDRESSABLE,
    )

    try:
        stored_manifest = verification_sink.read_manifest(
            result.run,
            verify=True,
        )

        object_key = verification_backend.key_from_url(
            asset.url
        )

        if not object_key:
            raise SelectiveReleaseError(
                "Could not derive the generated voice B2 key"
            )

        voice_bytes = verification_backend.get(
            object_key
        )
    finally:
        verification_sink.close()

    remote_sha256 = sha256_bytes(voice_bytes)

    if remote_sha256 != asset.sha256:
        raise SelectiveReleaseError(
            "Generated voice B2 bytes do not match "
            "the Genblaze asset SHA-256"
        )

    pipeline_manifest_verified = (
        result.manifest.verify()
    )
    stored_manifest_verified = (
        stored_manifest.verify()
    )
    canonical_hashes_match = (
        result.manifest.canonical_hash
        == stored_manifest.canonical_hash
    )

    if not all(
        (
            pipeline_manifest_verified,
            stored_manifest_verified,
            canonical_hashes_match,
        )
    ):
        raise SelectiveReleaseError(
            "Generated voice provenance verification failed"
        )

    local_path = work_dir / "voice.opening.wav"
    local_path.write_bytes(voice_bytes)

    return {
        "path": local_path,
        "object_key": object_key,
        "b2_uri": (
            f"b2://{env['B2_BUCKET_NAME']}/{object_key}"
        ),
        "sha256": asset.sha256,
        "size_bytes": len(voice_bytes),
        "media_type": "audio/wav",
        "provider": provider.name,
        "model": MODEL,
        "voice": VOICE,
        "run_id": result.run.run_id,
        "manifest_sha256": (
            result.manifest.canonical_hash
        ),
        "pipeline_manifest_verified": (
            pipeline_manifest_verified
        ),
        "stored_manifest_verified": (
            stored_manifest_verified
        ),
        "canonical_hashes_match": (
            canonical_hashes_match
        ),
        "remote_sha256": remote_sha256,
        "remote_verified": True,
    }


def create_preview_frame(
    path: Path,
    *,
    ending_id: str,
    dialogue: str,
) -> None:
    """Create an original frame for a rebuilt branch preview."""
    if ending_id == "ending_a":
        create_thumbnail(
            path,
            ending="ENDING A",
            dialogue=dialogue,
            background=(20, 45, 78),
            destination="Board the midnight-blue express",
        )
        return

    if ending_id == "ending_b":
        create_thumbnail(
            path,
            ending="ENDING B",
            dialogue=dialogue,
            background=(76, 27, 47),
            destination="Remain beneath the station lights",
        )
        return

    raise SelectiveReleaseError(
        f"Unsupported ending preview: {ending_id}"
    )


def main() -> int:
    if (
        EVIDENCE_PATH.exists()
        and os.getenv(
            "FORCE_SELECTIVE_RELEASE"
        ) != "yes"
    ):
        print(
            f"Selective release already exists: "
            f"{EVIDENCE_PATH}\n"
            "No Gemini request was made. Set "
            "FORCE_SELECTIVE_RELEASE=yes only for an "
            "intentional rebuild."
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
        baseline = read_json(BASELINE_PATH)

        recalculated_plan = plan_rebuild(
            previous_story,
            current_story,
        )

        if canonical_hash(
            recalculated_plan
        ) != canonical_hash(recorded_plan):
            raise SelectiveReleaseError(
                "Recorded rebuild plan no longer matches "
                "the current story versions"
            )

        # Approval validation occurs before any provider request.
        validate_approval(
            recorded_plan,
            approval,
        )

        if (
            baseline.get("project_id")
            != current_story.get("project_id")
        ):
            raise SelectiveReleaseError(
                "Baseline and current story project IDs differ"
            )

        env = require_environment()
        bucket = env["B2_BUCKET_NAME"]
        client = create_s3_client(env)

        # No provider request occurs before the entire baseline is verified.
        verify_baseline_release(
            client,
            bucket=bucket,
            baseline=baseline,
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
            raise SelectiveReleaseError(
                "An asset cannot be both stale and reusable"
            )

        if (
            stale_assets | reused_assets
        ) != all_asset_ids:
            raise SelectiveReleaseError(
                "The rebuild plan does not partition "
                "every current story asset"
            )

        supported_stale_assets = {
            "voice.opening",
            "caption.opening",
            "preview.ending_a",
            "preview.ending_b",
        }

        if stale_assets != supported_stale_assets:
            raise SelectiveReleaseError(
                "Scenario A produced an unexpected stale set: "
                f"{sorted(stale_assets)}"
            )

        if os.getenv(
            "ALLOW_LIVE_SELECTIVE_RELEASE"
        ) != "yes":
            print(
                "Live selective generation blocked. Run with "
                "ALLOW_LIVE_SELECTIVE_RELEASE=yes to authorize "
                "exactly one Gemini TTS request.",
                file=sys.stderr,
            )
            return 2

        work_dir = Path(
            tempfile.mkdtemp(
                prefix="branchline-release-v2-"
            )
        )

        dialogue = story_dialogue(
            current_story
        )

        source_digest_by_id = source_hashes(
            current_story
        )

        dependency_memo: dict[str, str] = {}

        expected_fingerprints = {
            logical_id: asset_dependency_fingerprint(
                logical_id,
                story=current_story,
                source_digest_by_id=source_digest_by_id,
                memo=dependency_memo,
            )
            for logical_id in sorted(all_asset_ids)
        }

        assets: dict[str, dict[str, Any]] = {}

        # Reuse only assets whose dependency fingerprints remain current.
        for logical_id in sorted(reused_assets):
            baseline_asset = baseline["assets"].get(
                logical_id
            )

            if baseline_asset is None:
                raise SelectiveReleaseError(
                    f"Reusable baseline asset is missing: "
                    f"{logical_id}"
                )

            expected_fingerprint = (
                expected_fingerprints[logical_id]
            )

            if (
                baseline_asset.get(
                    "dependency_fingerprint"
                )
                != expected_fingerprint
            ):
                raise SelectiveReleaseError(
                    f"Asset was marked reusable but its "
                    f"dependencies changed: {logical_id}"
                )

            reused_record = dict(
                baseline_asset
            )

            reused_record.update(
                {
                    "release_action": (
                        "reused_from_baseline"
                    ),
                    "reused_from_release_id": (
                        PREVIOUS_RELEASE_ID
                    ),
                    "original_creation_action": (
                        baseline_asset.get(
                            "creation_action"
                        )
                    ),
                    "dependency_fingerprint": (
                        expected_fingerprint
                    ),
                }
            )

            assets[logical_id] = reused_record

        # One load-bearing Genblaze generation step.
        voice = generate_updated_voice(
            env=env,
            dialogue=dialogue,
            work_dir=work_dir,
        )

        assets["voice.opening"] = {
            "logical_id": "voice.opening",
            "creation_action": (
                "generated_through_genblaze"
            ),
            "release_action": "rebuilt",
            "object_key": voice["object_key"],
            "b2_uri": voice["b2_uri"],
            "sha256": voice["sha256"],
            "size_bytes": voice["size_bytes"],
            "media_type": voice["media_type"],
            "depends_on": asset_specs[
                "voice.opening"
            ]["depends_on"],
            "dependency_fingerprint": (
                expected_fingerprints[
                    "voice.opening"
                ]
            ),
            "provider": voice["provider"],
            "model": voice["model"],
            "voice": voice["voice"],
            "genblaze_run_id": voice["run_id"],
            "remote_sha256": voice[
                "remote_sha256"
            ],
            "remote_verified": True,
        }

        caption_path = (
            work_dir / "caption.opening.srt"
        )

        create_caption(
            caption_path,
            dialogue,
        )

        caption_stored = upload_content_addressed(
            client,
            bucket=bucket,
            path=caption_path,
            media_type="application/x-subrip",
            logical_id="caption.opening",
        )

        assets["caption.opening"] = {
            "logical_id": "caption.opening",
            "creation_action": (
                "compiled_by_branchline"
            ),
            "release_action": "rebuilt",
            **caption_stored,
            "depends_on": asset_specs[
                "caption.opening"
            ]["depends_on"],
            "dependency_fingerprint": (
                expected_fingerprints[
                    "caption.opening"
                ]
            ),
        }

        for ending_id in (
            "ending_a",
            "ending_b",
        ):
            logical_id = (
                f"preview.{ending_id}"
            )

            frame_path = (
                work_dir
                / f"frame.{ending_id}.png"
            )

            preview_path = (
                work_dir
                / f"{logical_id}.mp4"
            )

            create_preview_frame(
                frame_path,
                ending_id=ending_id,
                dialogue=dialogue,
            )

            create_preview(
                image_path=frame_path,
                audio_path=voice["path"],
                output_path=preview_path,
            )

            preview_stored = (
                upload_content_addressed(
                    client,
                    bucket=bucket,
                    path=preview_path,
                    media_type="video/mp4",
                    logical_id=logical_id,
                )
            )

            assets[logical_id] = {
                "logical_id": logical_id,
                "creation_action": (
                    "compiled_by_branchline"
                ),
                "release_action": "rebuilt",
                **preview_stored,
                "depends_on": asset_specs[
                    logical_id
                ]["depends_on"],
                "dependency_fingerprint": (
                    expected_fingerprints[
                        logical_id
                    ]
                ),
            }

        if set(assets) != all_asset_ids:
            missing = sorted(
                all_asset_ids - set(assets)
            )

            raise SelectiveReleaseError(
                f"Release is missing assets: {missing}"
            )

        # Independently fetch and hash every final object.
        for logical_id, asset in sorted(
            assets.items()
        ):
            verification = verify_remote_object(
                client,
                bucket=bucket,
                object_key=asset["object_key"],
                expected_sha256=asset["sha256"],
            )

            asset.update(verification)

        asset_deltas: dict[
            str,
            dict[str, Any],
        ] = {}

        for logical_id in sorted(all_asset_ids):
            previous_asset = baseline["assets"][
                logical_id
            ]
            current_asset = assets[
                logical_id
            ]

            hash_changed = (
                previous_asset["sha256"]
                != current_asset["sha256"]
            )

            object_key_changed = (
                previous_asset["object_key"]
                != current_asset["object_key"]
            )

            if logical_id in stale_assets:
                if not hash_changed:
                    raise SelectiveReleaseError(
                        f"Stale asset was rebuilt but its "
                        f"bytes did not change: {logical_id}"
                    )

                expected_action = "rebuilt"
            else:
                if hash_changed:
                    raise SelectiveReleaseError(
                        f"Reusable asset bytes changed: "
                        f"{logical_id}"
                    )

                if object_key_changed:
                    raise SelectiveReleaseError(
                        f"Reusable asset B2 key changed: "
                        f"{logical_id}"
                    )

                expected_action = (
                    "reused_from_baseline"
                )

            if (
                current_asset["release_action"]
                != expected_action
            ):
                raise SelectiveReleaseError(
                    f"Incorrect release action for {logical_id}"
                )

            asset_deltas[logical_id] = {
                "logical_id": logical_id,
                "previous_sha256": (
                    previous_asset["sha256"]
                ),
                "current_sha256": (
                    current_asset["sha256"]
                ),
                "previous_object_key": (
                    previous_asset["object_key"]
                ),
                "current_object_key": (
                    current_asset["object_key"]
                ),
                "hash_changed": hash_changed,
                "object_key_changed": (
                    object_key_changed
                ),
                "release_action": (
                    current_asset[
                        "release_action"
                    ]
                ),
            }

        stale_remaining = sorted(
            logical_id
            for logical_id, asset in assets.items()
            if asset.get(
                "dependency_fingerprint"
            )
            != expected_fingerprints[
                logical_id
            ]
        )

        if stale_remaining:
            raise SelectiveReleaseError(
                "Release still contains stale assets: "
                f"{stale_remaining}"
            )

        paths: list[dict[str, Any]] = []

        for path_spec in current_story[
            "paths"
        ]:
            required_assets = path_spec[
                "required_assets"
            ]

            missing_assets = sorted(
                logical_id
                for logical_id in required_assets
                if logical_id not in assets
            )

            failed_assets = sorted(
                logical_id
                for logical_id in required_assets
                if logical_id in assets
                and not assets[
                    logical_id
                ].get("remote_verified")
            )

            verified = (
                not missing_assets
                and not failed_assets
            )

            paths.append(
                {
                    "path_id": path_spec["id"],
                    "required_assets": (
                        required_assets
                    ),
                    "missing_assets": (
                        missing_assets
                    ),
                    "failed_assets": (
                        failed_assets
                    ),
                    "verified": verified,
                }
            )

        if not all(
            path_item["verified"]
            for path_item in paths
        ):
            raise SelectiveReleaseError(
                "At least one reachable path failed"
            )

        rebuilt_count = sum(
            1
            for asset in assets.values()
            if asset["release_action"]
            == "rebuilt"
        )

        reused_count = sum(
            1
            for asset in assets.values()
            if asset["release_action"]
            == "reused_from_baseline"
        )

        release: dict[str, Any] = {
            "schema_version": 1,
            "project_id": PROJECT_ID,
            "release_id": RELEASE_ID,
            "previous_release_id": (
                PREVIOUS_RELEASE_ID
            ),
            "release_object_key": RELEASE_KEY,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "previous_story_file": str(
                PREVIOUS_STORY_PATH
            ),
            "current_story_file": str(
                CURRENT_STORY_PATH
            ),
            "story_sha256": canonical_hash(
                current_story
            ),
            "source_hashes": (
                source_digest_by_id
            ),
            "plan_sha256": approval[
                "plan_sha256"
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
                "decision": approval[
                    "decision"
                ],
            },
            "changed_sources": recorded_plan[
                "changed_sources"
            ],
            "planned_stale_assets": sorted(
                stale_assets
            ),
            "planned_reused_assets": sorted(
                reused_assets
            ),
            "assets": assets,
            "asset_deltas": asset_deltas,
            "paths": paths,
            "genblaze": {
                "run_id": voice["run_id"],
                "provider": voice["provider"],
                "model": voice["model"],
                "manifest_sha256": voice[
                    "manifest_sha256"
                ],
                "pipeline_manifest_verified": (
                    voice[
                        "pipeline_manifest_verified"
                    ]
                ),
                "stored_manifest_verified": (
                    voice[
                        "stored_manifest_verified"
                    ]
                ),
                "canonical_hashes_match": (
                    voice[
                        "canonical_hashes_match"
                    ]
                ),
            },
            "metrics": {
                "source_changes": len(
                    recorded_plan[
                        "changed_sources"
                    ]
                ),
                "assets_total": len(assets),
                "assets_rebuilt": (
                    rebuilt_count
                ),
                "assets_reused": reused_count,
                "reuse_rate_percent": round(
                    reused_count
                    / len(assets)
                    * 100,
                    1,
                ),
                "assets_remote_verified": sum(
                    1
                    for asset in assets.values()
                    if asset[
                        "remote_verified"
                    ]
                ),
                "paths_total": len(paths),
                "paths_verified": sum(
                    1
                    for path_item in paths
                    if path_item["verified"]
                ),
                "stale_assets_remaining": len(
                    stale_remaining
                ),
                "genblaze_generation_runs": 1,
            },
            "publication_status": (
                "SAFE_TO_PUBLISH"
            ),
            "status": (
                "SELECTIVE RELEASE COMPLETED "
                "AND VERIFIED"
            ),
        }

        release["canonical_sha256"] = (
            sha256_bytes(
                canonical_bytes(release)
            )
        )

        release_bytes = (
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
            Body=release_bytes,
            ContentType="application/json",
            Metadata={
                "project-id": PROJECT_ID,
                "release-id": RELEASE_ID,
                "previous-release-id": (
                    PREVIOUS_RELEASE_ID
                ),
                "canonical-sha256": (
                    release[
                        "canonical_sha256"
                    ]
                ),
            },
        )

        downloaded_release_bytes = (
            client.get_object(
                Bucket=bucket,
                Key=RELEASE_KEY,
            )["Body"].read()
        )

        if (
            downloaded_release_bytes
            != release_bytes
        ):
            raise SelectiveReleaseError(
                "Downloaded release bytes differ "
                "from uploaded release bytes"
            )

        downloaded_release = json.loads(
            downloaded_release_bytes.decode(
                "utf-8"
            )
        )

        verify_release_canonical_hash(
            downloaded_release,
            label="Downloaded selective release",
        )

        EVIDENCE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        EVIDENCE_PATH.write_bytes(
            release_bytes
        )

        summary = {
            "project_id": PROJECT_ID,
            "release_id": RELEASE_ID,
            "changed_sources": len(
                recorded_plan[
                    "changed_sources"
                ]
            ),
            "assets_rebuilt": rebuilt_count,
            "assets_reused": reused_count,
            "reuse_rate_percent": round(
                reused_count
                / len(assets)
                * 100,
                1,
            ),
            "assets_remote_verified": (
                len(assets)
            ),
            "paths_verified": (
                f"{len(paths)}/{len(paths)}"
            ),
            "stale_assets_remaining": 0,
            "publication_status": (
                "SAFE_TO_PUBLISH"
            ),
            "status": (
                "SELECTIVE RELEASE COMPLETED "
                "AND VERIFIED"
            ),
        }

        print(json.dumps(summary, indent=2))
        return 0

    except Exception as exc:
        print(
            "SELECTIVE RELEASE FAILED: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
