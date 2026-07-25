"""Tests for original playable release media."""

from __future__ import annotations

from pathlib import Path


MEDIA_DIRECTORY = Path(
    "assets/release_media"
)


def test_playable_media_files_exist() -> None:
    expected = {
        "ending_b_before.mp4",
        "ending_b_after.mp4",
        "shared_dialogue_before.mp4",
        "shared_dialogue_after.mp4",
        "ending_b_blocked.mp4",
    }

    actual = {
        path.name
        for path in MEDIA_DIRECTORY.glob(
            "*.mp4"
        )
    }

    assert actual >= expected

    for filename in expected:
        path = MEDIA_DIRECTORY / filename

        assert path.stat().st_size > 50_000

        header = path.read_bytes()[:64]

        assert b"ftyp" in header


def test_release_media_contains_no_external_assets() -> None:
    source = Path(
        "scripts/generate_release_media.py"
    ).read_text()

    assert "http://" not in source
    assert "https://" not in source
    assert "requests." not in source
