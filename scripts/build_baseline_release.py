"""Build and verify Branchline's real baseline story release."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import boto3
import imageio_ffmpeg
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

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
    source_hashes,
)

# Reuse the exact provider and B2 configuration that already passed.
from scripts.genblaze_gemini_b2_smoke import (
    GeminiTTSProvider,
    create_backend,
    require_environment,
)


PROJECT_ID = "last-train"
RELEASE_ID = "baseline-v1"

STORY_PATH = Path("fixtures/main_story/story_v1.json")
PLAN_PATH = Path("evidence/story_graph_shared_dialogue.json")
APPROVAL_PATH = Path("evidence/approval_shared_dialogue.json")
EVIDENCE_PATH = Path("evidence/release_baseline_v1.json")

MODEL = "gemini-2.5-flash-preview-tts"
VOICE = "Kore"

GENBLAZE_PREFIX = "branchline/genblaze"
CAS_PREFIX = "branchline/cas/sha256"

RELEASE_KEY = (
    f"branchline/projects/{PROJECT_ID}/"
    f"releases/{RELEASE_ID}/release.json"
)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Required file is missing: {path}")

    return json.loads(path.read_text())


def normalized_endpoint(value: str) -> str:
    endpoint = value.strip().rstrip("/")

    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"https://{endpoint}"

    parsed = urlparse(endpoint)

    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".backblazeb2.com")
    ):
        raise RuntimeError(
            "B2_ENDPOINT is not a valid Backblaze HTTPS endpoint"
        )

    return endpoint


def create_s3_client(env: dict[str, str]) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=normalized_endpoint(env["B2_ENDPOINT"]),
        aws_access_key_id=env["B2_KEY_ID"],
        aws_secret_access_key=env["B2_APP_KEY"],
        region_name=env["B2_REGION"],
    )


def object_exists(client: Any, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        status = exc.response.get("ResponseMetadata", {}).get(
            "HTTPStatusCode"
        )
        code = exc.response.get("Error", {}).get("Code", "")

        if status == 404 or code in {
            "404",
            "NoSuchKey",
            "NotFound",
        }:
            return False

        raise


def upload_content_addressed(
    client: Any,
    *,
    bucket: str,
    path: Path,
    media_type: str,
    logical_id: str,
) -> dict[str, Any]:
    content = path.read_bytes()
    digest = sha256_bytes(content)
    extension = path.suffix.lower().lstrip(".")

    key = (
        f"{CAS_PREFIX}/{digest[:2]}/"
        f"{digest}.{extension}"
    )

    reused_existing_object = object_exists(client, bucket, key)

    if not reused_existing_object:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType=media_type,
            Metadata={
                "sha256": digest,
                "logical-id": logical_id,
                "project-id": PROJECT_ID,
            },
        )

    return {
        "object_key": key,
        "b2_uri": f"b2://{bucket}/{key}",
        "sha256": digest,
        "size_bytes": len(content),
        "media_type": media_type,
        "storage_action": (
            "reused_existing_cas_object"
            if reused_existing_object
            else "uploaded_new_cas_object"
        ),
    }


def verify_remote_object(
    client: Any,
    *,
    bucket: str,
    object_key: str,
    expected_sha256: str,
) -> dict[str, Any]:
    response = client.get_object(
        Bucket=bucket,
        Key=object_key,
    )

    content = response["Body"].read()
    remote_sha256 = sha256_bytes(content)

    if remote_sha256 != expected_sha256:
        raise RuntimeError(
            f"Remote hash mismatch for {object_key}: "
            f"{remote_sha256} != {expected_sha256}"
        )

    return {
        "remote_sha256": remote_sha256,
        "remote_size_bytes": len(content),
        "remote_verified": True,
    }


def load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        (
            "/usr/share/fonts/truetype/dejavu/"
            f"DejaVuSans{'-Bold' if bold else ''}.ttf"
        ),
        (
            "/usr/share/fonts/truetype/liberation2/"
            f"LiberationSans-{'Bold' if bold else 'Regular'}.ttf"
        ),
    ]

    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)

    return ImageFont.load_default()


def story_dialogue(story: dict[str, Any]) -> str:
    for source in story["sources"]:
        if source["id"] == "dialogue.opening":
            return str(source["value"])

    raise RuntimeError("dialogue.opening is missing")


def create_caption(path: Path, dialogue: str) -> None:
    content = (
        "1\n"
        "00:00:00,000 --> 00:00:08,000\n"
        f"{dialogue}\n"
    )

    path.write_text(content)


def create_thumbnail(
    path: Path,
    *,
    ending: str,
    dialogue: str,
    background: tuple[int, int, int],
    destination: str,
) -> None:
    image = Image.new(
        "RGB",
        (1280, 720),
        background,
    )

    draw = ImageDraw.Draw(image)

    small = load_font(24, bold=True)
    heading = load_font(64, bold=True)
    body = load_font(38)
    footer = load_font(28, bold=True)

    draw.rounded_rectangle(
        (54, 48, 1226, 672),
        radius=34,
        fill=(12, 16, 28),
        outline=(218, 224, 238),
        width=3,
    )

    draw.text(
        (96, 88),
        "BRANCHLINE  •  VERIFIED BASELINE",
        font=small,
        fill=(192, 202, 220),
    )

    draw.text(
        (96, 160),
        ending,
        font=heading,
        fill=(255, 255, 255),
    )

    y = 285
    for line in textwrap.wrap(dialogue, width=42):
        draw.text(
            (96, y),
            line,
            font=body,
            fill=(229, 233, 242),
        )
        y += 52

    draw.text(
        (96, 555),
        destination,
        font=footer,
        fill=(255, 225, 145),
    )

    draw.text(
        (96, 610),
        "Release v1 • All required media verified",
        font=small,
        fill=(154, 166, 188),
    )

    image.save(path, format="PNG", optimize=True)


def create_preview(
    *,
    image_path: Path,
    audio_path: Path,
    output_path: Path,
) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    command = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-framerate",
        "30",
        "-i",
        str(image_path),
        "-i",
        str(audio_path),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-pix_fmt",
        "yuv420p",
        "-shortest",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            "FFmpeg preview compilation failed:\n"
            + completed.stderr[-2000:]
        )

    if not output_path.exists() or output_path.stat().st_size <= 0:
        raise RuntimeError(
            f"FFmpeg produced no valid output: {output_path}"
        )


def asset_dependency_fingerprint(
    asset_id: str,
    *,
    story: dict[str, Any],
    source_digest_by_id: dict[str, str],
    memo: dict[str, str],
) -> str:
    if asset_id in memo:
        return memo[asset_id]

    assets = {
        asset["id"]: asset
        for asset in story["assets"]
    }

    asset = assets[asset_id]
    dependencies: list[dict[str, str]] = []

    for dependency in sorted(asset["depends_on"]):
        if dependency in source_digest_by_id:
            dependency_hash = source_digest_by_id[dependency]
        elif dependency in assets:
            dependency_hash = asset_dependency_fingerprint(
                dependency,
                story=story,
                source_digest_by_id=source_digest_by_id,
                memo=memo,
            )
        else:
            raise RuntimeError(
                f"Unknown dependency {dependency} for {asset_id}"
            )

        dependencies.append(
            {
                "id": dependency,
                "sha256": dependency_hash,
            }
        )

    fingerprint = canonical_hash(
        {
            "asset_id": asset_id,
            "dependencies": dependencies,
        }
    )

    memo[asset_id] = fingerprint
    return fingerprint


def generate_baseline_voice(
    *,
    env: dict[str, str],
    dialogue: str,
    work_dir: Path,
) -> dict[str, Any]:
    provider = GeminiTTSProvider(
        api_key=env["GEMINI_API_KEY"],
        output_dir=work_dir / "provider-output",
    )

    sink = ObjectStorageSink(
        create_backend(env),
        prefix=GENBLAZE_PREFIX,
        key_strategy=KeyStrategy.CONTENT_ADDRESSABLE,
    )

    try:
        result = (
            Pipeline("branchline-baseline-voice")
            .step(
                provider,
                model=MODEL,
                prompt=(
                    "Read calmly and clearly: "
                    f"{dialogue}"
                ),
                modality=Modality.AUDIO,
                params={"voice": VOICE},
                metadata={
                    "project_id": PROJECT_ID,
                    "release_id": RELEASE_ID,
                    "logical_asset": "voice.opening",
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

    if not result.run.steps or not result.run.steps[0].assets:
        raise RuntimeError("Genblaze returned no baseline voice asset")

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

        object_key = verification_backend.key_from_url(asset.url)

        if not object_key:
            raise RuntimeError(
                "Could not derive the voice B2 object key"
            )

        voice_bytes = verification_backend.get(object_key)
    finally:
        verification_sink.close()

    remote_sha256 = sha256_bytes(voice_bytes)

    if remote_sha256 != asset.sha256:
        raise RuntimeError(
            "Baseline voice remote hash does not match "
            "the Genblaze asset hash"
        )

    local_path = work_dir / "voice.opening.wav"
    local_path.write_bytes(voice_bytes)

    pipeline_verified = result.manifest.verify()
    stored_verified = stored_manifest.verify()
    canonical_match = (
        result.manifest.canonical_hash
        == stored_manifest.canonical_hash
    )

    if not all(
        [
            pipeline_verified,
            stored_verified,
            canonical_match,
        ]
    ):
        raise RuntimeError(
            "Genblaze baseline voice provenance verification failed"
        )

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
        "genblaze_run_id": result.run.run_id,
        "genblaze_manifest_sha256": (
            result.manifest.canonical_hash
        ),
        "pipeline_manifest_verified": pipeline_verified,
        "stored_manifest_verified": stored_verified,
        "canonical_hashes_match": canonical_match,
        "remote_verified": True,
    }


def main() -> int:
    if EVIDENCE_PATH.exists() and os.getenv(
        "FORCE_REBUILD_BASELINE"
    ) != "yes":
        print(
            f"Baseline evidence already exists: {EVIDENCE_PATH}\n"
            "No API request was made. Set "
            "FORCE_REBUILD_BASELINE=yes only to rebuild deliberately."
        )
        return 0

    if os.getenv("ALLOW_LIVE_BASELINE") != "yes":
        print(
            "Live baseline generation blocked. Run with "
            "ALLOW_LIVE_BASELINE=yes to authorize one TTS request.",
            file=sys.stderr,
        )
        return 2

    load_dotenv()

    try:
        story = load_story(STORY_PATH)
        plan = read_json(PLAN_PATH)
        approval = read_json(APPROVAL_PATH)

        # No provider request occurs unless approval integrity passes first.
        validate_approval(plan, approval)

        env = require_environment()
        bucket = env["B2_BUCKET_NAME"]
        client = create_s3_client(env)

        work_dir = Path(
            tempfile.mkdtemp(
                prefix="branchline-baseline-"
            )
        )

        dialogue = story_dialogue(story)

        voice = generate_baseline_voice(
            env=env,
            dialogue=dialogue,
            work_dir=work_dir,
        )

        caption_path = work_dir / "caption.opening.srt"
        thumbnail_a_path = (
            work_dir / "thumbnail.ending_a.png"
        )
        thumbnail_b_path = (
            work_dir / "thumbnail.ending_b.png"
        )
        preview_a_path = (
            work_dir / "preview.ending_a.mp4"
        )
        preview_b_path = (
            work_dir / "preview.ending_b.mp4"
        )

        create_caption(caption_path, dialogue)

        create_thumbnail(
            thumbnail_a_path,
            ending="ENDING A",
            dialogue=dialogue,
            background=(20, 45, 78),
            destination="Board the midnight-blue express",
        )

        create_thumbnail(
            thumbnail_b_path,
            ending="ENDING B",
            dialogue=dialogue,
            background=(76, 27, 47),
            destination="Remain beneath the station lights",
        )

        create_preview(
            image_path=thumbnail_a_path,
            audio_path=voice["path"],
            output_path=preview_a_path,
        )

        create_preview(
            image_path=thumbnail_b_path,
            audio_path=voice["path"],
            output_path=preview_b_path,
        )

        compiled_paths = {
            "caption.opening": (
                caption_path,
                "application/x-subrip",
            ),
            "thumbnail.ending_a": (
                thumbnail_a_path,
                "image/png",
            ),
            "thumbnail.ending_b": (
                thumbnail_b_path,
                "image/png",
            ),
            "preview.ending_a": (
                preview_a_path,
                "video/mp4",
            ),
            "preview.ending_b": (
                preview_b_path,
                "video/mp4",
            ),
        }

        asset_specs = {
            asset["id"]: asset
            for asset in story["assets"]
        }

        source_digest_by_id = source_hashes(story)
        dependency_memo: dict[str, str] = {}

        assets: dict[str, dict[str, Any]] = {
            "voice.opening": {
                "logical_id": "voice.opening",
                "creation_action": "generated_through_genblaze",
                "object_key": voice["object_key"],
                "b2_uri": voice["b2_uri"],
                "sha256": voice["sha256"],
                "size_bytes": voice["size_bytes"],
                "media_type": voice["media_type"],
                "depends_on": asset_specs[
                    "voice.opening"
                ]["depends_on"],
                "dependency_fingerprint": (
                    asset_dependency_fingerprint(
                        "voice.opening",
                        story=story,
                        source_digest_by_id=(
                            source_digest_by_id
                        ),
                        memo=dependency_memo,
                    )
                ),
                "provider": voice["provider"],
                "model": voice["model"],
                "remote_verified": True,
            }
        }

        for logical_id, (
            local_path,
            media_type,
        ) in compiled_paths.items():
            stored = upload_content_addressed(
                client,
                bucket=bucket,
                path=local_path,
                media_type=media_type,
                logical_id=logical_id,
            )

            assets[logical_id] = {
                "logical_id": logical_id,
                "creation_action": (
                    "compiled_by_branchline"
                ),
                **stored,
                "depends_on": asset_specs[
                    logical_id
                ]["depends_on"],
                "dependency_fingerprint": (
                    asset_dependency_fingerprint(
                        logical_id,
                        story=story,
                        source_digest_by_id=(
                            source_digest_by_id
                        ),
                        memo=dependency_memo,
                    )
                ),
            }

        for logical_id, asset in assets.items():
            verification = verify_remote_object(
                client,
                bucket=bucket,
                object_key=asset["object_key"],
                expected_sha256=asset["sha256"],
            )

            asset.update(verification)

        paths: list[dict[str, Any]] = []

        for path_spec in story["paths"]:
            required = path_spec["required_assets"]
            missing = [
                asset_id
                for asset_id in required
                if asset_id not in assets
            ]

            unverified = [
                asset_id
                for asset_id in required
                if asset_id in assets
                and not assets[asset_id].get(
                    "remote_verified"
                )
            ]

            verified = not missing and not unverified

            paths.append(
                {
                    "path_id": path_spec["id"],
                    "required_assets": required,
                    "missing_assets": missing,
                    "unverified_assets": unverified,
                    "verified": verified,
                }
            )

        all_paths_verified = all(
            path_item["verified"]
            for path_item in paths
        )

        all_assets_verified = all(
            asset["remote_verified"]
            for asset in assets.values()
        )

        if len(assets) != 6:
            raise RuntimeError(
                f"Expected six baseline assets, got {len(assets)}"
            )

        if not all_assets_verified:
            raise RuntimeError(
                "At least one baseline asset failed remote verification"
            )

        if not all_paths_verified:
            raise RuntimeError(
                "At least one baseline path failed verification"
            )

        release: dict[str, Any] = {
            "schema_version": 1,
            "project_id": PROJECT_ID,
            "release_id": RELEASE_ID,
            "release_object_key": RELEASE_KEY,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "story_file": str(STORY_PATH),
            "story_sha256": canonical_hash(story),
            "source_hashes": source_digest_by_id,
            "prepared_for_plan_sha256": approval[
                "plan_sha256"
            ],
            "assets": assets,
            "paths": paths,
            "genblaze": {
                "run_id": voice["genblaze_run_id"],
                "manifest_sha256": voice[
                    "genblaze_manifest_sha256"
                ],
                "pipeline_manifest_verified": voice[
                    "pipeline_manifest_verified"
                ],
                "stored_manifest_verified": voice[
                    "stored_manifest_verified"
                ],
                "canonical_hashes_match": voice[
                    "canonical_hashes_match"
                ],
            },
            "metrics": {
                "assets_total": len(assets),
                "assets_generated_through_genblaze": 1,
                "assets_compiled_by_branchline": 5,
                "assets_remote_verified": sum(
                    1
                    for asset in assets.values()
                    if asset["remote_verified"]
                ),
                "paths_total": len(paths),
                "paths_verified": sum(
                    1
                    for path_item in paths
                    if path_item["verified"]
                ),
            },
            "publication_status": "SAFE_TO_PUBLISH",
            "status": "BASELINE RELEASE VERIFIED",
        }

        release["canonical_sha256"] = sha256_bytes(
            canonical_bytes(release)
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
                "canonical-sha256": release[
                    "canonical_sha256"
                ],
            },
        )

        downloaded_release = client.get_object(
            Bucket=bucket,
            Key=RELEASE_KEY,
        )["Body"].read()

        if downloaded_release != release_bytes:
            raise RuntimeError(
                "Stored release manifest bytes differ "
                "from the local release manifest"
            )

        downloaded_json = json.loads(
            downloaded_release.decode("utf-8")
        )

        recorded_canonical = downloaded_json.pop(
            "canonical_sha256"
        )

        recalculated_canonical = sha256_bytes(
            canonical_bytes(downloaded_json)
        )

        if recorded_canonical != recalculated_canonical:
            raise RuntimeError(
                "Stored release canonical hash verification failed"
            )

        EVIDENCE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        EVIDENCE_PATH.write_bytes(release_bytes)

        summary = {
            "project_id": PROJECT_ID,
            "release_id": RELEASE_ID,
            "assets_total": 6,
            "assets_remote_verified": 6,
            "paths_verified": "2/2",
            "genblaze_voice_verified": True,
            "release_manifest_verified": True,
            "publication_status": "SAFE_TO_PUBLISH",
            "status": "BASELINE RELEASE VERIFIED",
        }

        print(json.dumps(summary, indent=2))
        return 0

    except Exception as exc:
        print(
            f"Baseline release failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
