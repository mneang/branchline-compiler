"""Validate the committed sponsor-native vertical-slice evidence."""

from __future__ import annotations

import json
from pathlib import Path


def test_genblaze_b2_vertical_slice_is_verified() -> None:
    evidence_path = Path("evidence/genblaze_b2_vertical_slice.json")

    assert evidence_path.exists(), "Vertical-slice evidence is missing"

    evidence = json.loads(evidence_path.read_text())

    assert evidence["pipeline_manifest_verified"] is True
    assert evidence["stored_manifest_verified"] is True
    assert evidence["canonical_hashes_match"] is True
    assert evidence["remote_hash_matches_asset"] is True

    assert evidence["asset_sha256"] == evidence["remote_sha256"]
    assert evidence["media_type"] == "audio/wav"
    assert evidence["size_bytes"] > 0
    assert evidence["duration_seconds"] > 0

    assert evidence["status"] == "GENBLAZE B2 VERTICAL SLICE VERIFIED"
