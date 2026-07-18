"""One live Gemini TTS generation orchestrated by Genblaze and stored in B2."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import uuid
import wave
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from google import genai
from google.genai import types

from genblaze_core import (
    Asset,
    AudioMetadata,
    KeyStrategy,
    Modality,
    ObjectStorageSink,
    Pipeline,
    Step,
)
from genblaze_core.providers import BaseProvider, RetryPolicy
from genblaze_s3 import S3StorageBackend


MODEL = "gemini-2.5-flash-preview-tts"
VOICE = "Kore"
PIPELINE_NAME = "branchline-gemini-tts-b2-smoke"
STORAGE_PREFIX = "branchline/smoke"
OUTPUT_DIR = Path(tempfile.gettempdir()) / "branchline-genblaze"
EVIDENCE_PATH = Path("evidence/genblaze_b2_vertical_slice.json")

PROMPT = (
    "Read calmly and clearly: "
    "The last train leaves at eight. Choose your path carefully."
)

REQUIRED_ENV_VARS = (
    "GEMINI_API_KEY",
    "B2_BUCKET_NAME",
    "B2_KEY_ID",
    "B2_APP_KEY",
    "B2_REGION",
    "B2_ENDPOINT",
)


def require_environment() -> dict[str, str]:
    """Load and validate required credentials without printing them."""
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
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    return values


def sha256_bytes(content: bytes) -> str:
    """Return the SHA-256 digest of bytes."""
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a local file."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def save_pcm_as_wav(
    path: Path,
    pcm: bytes,
    *,
    channels: int = 1,
    sample_rate: int = 24_000,
    sample_width: int = 2,
) -> None:
    """Wrap raw Gemini PCM audio in a valid WAV container."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)


class GeminiTTSProvider(BaseProvider):
    """Minimal Gemini TTS adapter implementing Genblaze's provider lifecycle."""

    name = "google-gemini-tts"

    def __init__(self, api_key: str, output_dir: Path) -> None:
        # Disabled retry policy protects free-tier quota from duplicate calls.
        super().__init__(retry_policy=RetryPolicy.disabled())

        self.client = genai.Client(api_key=api_key)

        temp_root = Path(tempfile.gettempdir()).resolve()
        resolved_output = output_dir.resolve()

        if (
            resolved_output != temp_root
            and temp_root not in resolved_output.parents
        ):
            raise RuntimeError(
                "Gemini temporary output must remain beneath "
                f"{temp_root}; received {resolved_output}"
            )

        self.output_dir = resolved_output
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._completed_outputs: dict[str, Path] = {}

    def submit(self, step: Step, config: Any | None = None) -> str:
        """Generate audio synchronously and return an internal prediction ID."""
        del config

        if step.modality is not Modality.AUDIO:
            raise ValueError(
                f"GeminiTTSProvider requires audio modality, received {step.modality}"
            )

        prompt = str(step.prompt or "").strip()
        if not prompt:
            raise ValueError("TTS prompt cannot be empty")

        voice = str(step.params.get("voice", VOICE))

        response = self.client.models.generate_content(
            model=step.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice,
                        )
                    )
                ),
            ),
        )

        candidates = getattr(response, "candidates", None)
        if not candidates:
            raise RuntimeError("Gemini returned no candidates")

        parts = candidates[0].content.parts
        if not parts or not parts[0].inline_data:
            raise RuntimeError("Gemini returned no inline audio data")

        pcm = parts[0].inline_data.data
        if not pcm:
            raise RuntimeError("Gemini returned an empty audio payload")

        prediction_id = uuid.uuid4().hex
        output_path = self.output_dir / f"{prediction_id}.wav"

        save_pcm_as_wav(output_path, pcm)
        self._completed_outputs[prediction_id] = output_path

        return prediction_id

    def poll(self, prediction_id: Any, config: Any | None = None) -> bool:
        """Gemini completed synchronously during submit()."""
        del config
        return str(prediction_id) in self._completed_outputs

    def fetch_output(self, prediction_id: Any, step: Step) -> Step:
        """Attach the generated WAV as a native Genblaze Asset."""
        output_path = self._completed_outputs.get(str(prediction_id))

        if output_path is None or not output_path.exists():
            raise RuntimeError(
                f"Generated output was not found for prediction {prediction_id}"
            )

        with wave.open(str(output_path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_rate = wav_file.getframerate()
            sample_width_bits = wav_file.getsampwidth() * 8
            frames = wav_file.getnframes()
            duration = frames / sample_rate

        asset = Asset(
            url=output_path.resolve().as_uri(),
            media_type="audio/wav",
            sha256=sha256_file(output_path),
            size_bytes=output_path.stat().st_size,
            duration=duration,
            audio=AudioMetadata(
                codec=f"pcm_s{sample_width_bits}le",
                channels=channels,
                sample_rate=sample_rate,
            ),
            metadata={
                "voice": str(step.params.get("voice", VOICE)),
                "source": "live-gemini-free-tier-smoke",
            },
        )

        step.assets = [asset]
        return step


def b2_region_from_endpoint(raw_endpoint: str) -> str:
    """Extract the exact Backblaze cluster region from its HTTPS endpoint."""
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
        raise RuntimeError(
            "B2_ENDPOINT must look like "
            "https://s3.us-west-004.backblazeb2.com"
        )

    parts = hostname.split(".")

    if len(parts) < 4:
        raise RuntimeError(
            f"Could not extract an exact B2 region from {hostname}"
        )

    return parts[1]


def create_backend(env: dict[str, str]) -> S3StorageBackend:
    """Create B2 storage only when endpoint and region agree."""
    endpoint_region = b2_region_from_endpoint(env["B2_ENDPOINT"])
    configured_region = env["B2_REGION"].strip()

    if configured_region != endpoint_region:
        raise RuntimeError(
            "Backblaze configuration mismatch: "
            f"B2_REGION={configured_region!r}, but "
            f"B2_ENDPOINT belongs to {endpoint_region!r}."
        )

    return S3StorageBackend.for_backblaze(
        env["B2_BUCKET_NAME"],
        region=endpoint_region,
        key_id=env["B2_KEY_ID"],
        app_key=env["B2_APP_KEY"],
        preflight=True,
    )


def main() -> int:
    if os.getenv("ALLOW_LIVE_GENBLAZE_SMOKE") != "yes":
        print(
            "Live generation blocked. Run with "
            "ALLOW_LIVE_GENBLAZE_SMOKE=yes to authorize exactly one request.",
            file=sys.stderr,
        )
        return 2

    try:
        env = require_environment()

        provider = GeminiTTSProvider(
            api_key=env["GEMINI_API_KEY"],
            output_dir=OUTPUT_DIR,
        )

        sink = ObjectStorageSink(
            create_backend(env),
            prefix=STORAGE_PREFIX,
            key_strategy=KeyStrategy.HIERARCHICAL,
        )

        result = (
            Pipeline(PIPELINE_NAME)
            .step(
                provider,
                model=MODEL,
                prompt=PROMPT,
                modality=Modality.AUDIO,
                params={"voice": VOICE},
                metadata={
                    "project": "branchline-compiler",
                    "test": "sponsor-native-vertical-slice",
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

        if not result.run.steps:
            raise RuntimeError("Genblaze returned no pipeline steps")

        step = result.run.steps[0]

        if not step.assets:
            raise RuntimeError("Genblaze returned no output assets")

        stored_asset = step.assets[0]

        # Verification uses a fresh B2 connection rather than trusting the
        # generation process or its local output.
        verification_backend = create_backend(env)
        verification_sink = ObjectStorageSink(
            verification_backend,
            prefix=STORAGE_PREFIX,
            key_strategy=KeyStrategy.HIERARCHICAL,
        )

        try:
            stored_manifest = verification_sink.read_manifest(
                result.run,
                verify=True,
            )

            storage_key = verification_backend.key_from_url(stored_asset.url)
            if not storage_key:
                raise RuntimeError(
                    f"Could not derive a B2 object key from {stored_asset.url}"
                )

            remote_bytes = verification_backend.get(storage_key)
            remote_sha256 = sha256_bytes(remote_bytes)

            pipeline_manifest_verified = result.manifest.verify()
            stored_manifest_verified = stored_manifest.verify()
            canonical_hashes_match = (
                result.manifest.canonical_hash
                == stored_manifest.canonical_hash
            )
            remote_hash_matches_asset = (
                remote_sha256 == stored_asset.sha256
            )

            if not pipeline_manifest_verified:
                raise RuntimeError("Pipeline manifest verification failed")

            if not stored_manifest_verified:
                raise RuntimeError("Stored B2 manifest verification failed")

            if not canonical_hashes_match:
                raise RuntimeError(
                    "Local and stored manifest canonical hashes differ"
                )

            if not remote_hash_matches_asset:
                raise RuntimeError(
                    "Downloaded B2 object hash differs from the Genblaze asset hash"
                )

            evidence = {
                "pipeline": PIPELINE_NAME,
                "provider": provider.name,
                "model": MODEL,
                "voice": VOICE,
                "run_id": result.run.run_id,
                "asset_url": stored_asset.url,
                "b2_object_key": storage_key,
                "media_type": stored_asset.media_type,
                "size_bytes": stored_asset.size_bytes,
                "duration_seconds": stored_asset.duration,
                "asset_sha256": stored_asset.sha256,
                "remote_sha256": remote_sha256,
                "pipeline_manifest_verified": pipeline_manifest_verified,
                "stored_manifest_verified": stored_manifest_verified,
                "canonical_hashes_match": canonical_hashes_match,
                "remote_hash_matches_asset": remote_hash_matches_asset,
                "status": "GENBLAZE B2 VERTICAL SLICE VERIFIED",
            }

            EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
            EVIDENCE_PATH.write_text(
                json.dumps(evidence, indent=2) + "\n"
            )

            print(json.dumps(evidence, indent=2))
            return 0

        finally:
            verification_sink.close()

    except Exception as exc:
        print(
            f"Genblaze B2 smoke test failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
