"""Generate one small synthetic WAV file through Gemini's free TTS tier."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import wave
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


MODEL = "gemini-2.5-flash-preview-tts"
VOICE = "Kore"
OUTPUT_PATH = Path("artifacts/smoke/gemini-tts.wav")

# Keep this tiny to protect quota and make the test deterministic in scope.
SYNTHETIC_TEXT = (
    "Read calmly and clearly: "
    "The last train leaves at eight. Choose your path carefully."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def save_pcm_as_wav(
    path: Path,
    pcm: bytes,
    channels: int = 1,
    sample_rate: int = 24_000,
    sample_width: int = 2,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)


def main() -> int:
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("✗ GEMINI_API_KEY is missing from .env", file=sys.stderr)
        return 1

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=MODEL,
            contents=SYNTHETIC_TEXT,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=VOICE,
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

        save_pcm_as_wav(OUTPUT_PATH, pcm)

        result = {
            "provider": "Google Gemini",
            "model": MODEL,
            "voice": VOICE,
            "output_path": str(OUTPUT_PATH),
            "size_bytes": OUTPUT_PATH.stat().st_size,
            "sha256": sha256_file(OUTPUT_PATH),
            "status": "GEMINI TTS SMOKE VERIFIED",
        }

        print(json.dumps(result, indent=2))
        return 0

    except Exception as exc:
        print(
            f"✗ Gemini TTS smoke test failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
