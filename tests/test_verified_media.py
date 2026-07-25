"""Tests for hash-gated B2 media playback."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from io import BytesIO
from typing import Any

import pytest

from branchline.application.verified_media import (
    VerifiedMediaError,
    build_verified_media_bundle,
    local_presentation_fallback,
)


PREVIOUS_BYTES = b"previous-ending-b-preview"
CURRENT_BYTES = b"current-ending-b-preview"


def asset_record(
    content: bytes,
    *,
    key: str,
) -> dict[str, Any]:
    return {
        "logical_id": "preview.ending_b",
        "object_key": key,
        "sha256": hashlib.sha256(
            content
        ).hexdigest(),
        "size_bytes": len(content),
        "media_type": "video/mp4",
    }


def releases() -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    previous = {
        "project_id": "last-train",
        "release_id": "shared-dialogue-v2",
        "assets": {
            "preview.ending_b": asset_record(
                PREVIOUS_BYTES,
                key="objects/previous.mp4",
            ),
        },
    }

    current = {
        "project_id": "last-train",
        "release_id": "ending-b-live-test",
        "previous_release_id": (
            "shared-dialogue-v2"
        ),
        "assets": {
            "preview.ending_b": asset_record(
                CURRENT_BYTES,
                key="objects/current.mp4",
            ),
        },
    }

    return previous, current


class FakeClient:
    def __init__(
        self,
        objects: dict[str, bytes],
    ) -> None:
        self.objects = objects
        self.signed_keys: list[str] = []

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> dict[str, Any]:
        del Bucket

        if Key not in self.objects:
            raise RuntimeError(
                "missing fake object"
            )

        return {
            "Body": BytesIO(
                self.objects[Key]
            ),
        }

    def generate_presigned_url(
        self,
        *,
        ClientMethod: str,
        Params: dict[str, str],
        ExpiresIn: int,
    ) -> str:
        assert ClientMethod == "get_object"
        assert ExpiresIn == 300

        key = Params["Key"]
        self.signed_keys.append(key)

        return (
            "https://signed.example.invalid/"
            + key
        )


def fake_client() -> FakeClient:
    return FakeClient(
        {
            "objects/previous.mp4": (
                PREVIOUS_BYTES
            ),
            "objects/current.mp4": (
                CURRENT_BYTES
            ),
        }
    )


def test_both_objects_verify_before_signing() -> None:
    previous, current = releases()
    client = fake_client()

    bundle = build_verified_media_bundle(
        previous_release=previous,
        current_release=current,
        client=client,
        bucket="test-bucket",
    )

    assert bundle["mode"] == (
        "VERIFIED_B2_PLAYBACK"
    )

    assert bundle[
        "previous"
    ]["remote_verified"] is True

    assert bundle[
        "current"
    ]["remote_verified"] is True

    assert client.signed_keys == [
        "objects/previous.mp4",
        "objects/current.mp4",
    ]


def test_tampered_object_blocks_all_signed_urls() -> None:
    previous, current = releases()

    client = FakeClient(
        {
            "objects/previous.mp4": (
                PREVIOUS_BYTES
            ),
            "objects/current.mp4": (
                b"tampered"
            ),
        }
    )

    with pytest.raises(
        VerifiedMediaError,
        match="SHA-256",
    ):
        build_verified_media_bundle(
            previous_release=previous,
            current_release=current,
            client=client,
            bucket="test-bucket",
        )

    assert client.signed_keys == []


def test_release_lineage_must_match() -> None:
    previous, current = releases()

    current[
        "previous_release_id"
    ] = "unrelated-release"

    with pytest.raises(
        VerifiedMediaError,
        match="does not derive",
    ):
        build_verified_media_bundle(
            previous_release=previous,
            current_release=current,
            client=fake_client(),
            bucket="test-bucket",
        )


def test_rebuilt_preview_must_have_new_bytes() -> None:
    previous, current = releases()

    current[
        "assets"
    ]["preview.ending_b"] = deepcopy(
        previous[
            "assets"
        ]["preview.ending_b"]
    )

    with pytest.raises(
        VerifiedMediaError,
        match="byte-identical",
    ):
        build_verified_media_bundle(
            previous_release=previous,
            current_release=current,
            client=fake_client(),
            bucket="test-bucket",
        )


def test_signed_url_expiry_is_bounded() -> None:
    previous, current = releases()

    with pytest.raises(
        VerifiedMediaError,
        match="between 60 and 900",
    ):
        build_verified_media_bundle(
            previous_release=previous,
            current_release=current,
            client=fake_client(),
            bucket="test-bucket",
            expires_in_seconds=3600,
        )


def test_local_fallback_is_explicit() -> None:
    fallback = (
        local_presentation_fallback(
            reason=(
                "Hosted B2 configuration unavailable."
            )
        )
    )

    assert fallback["mode"] == (
        "LOCAL_PRESENTATION_FALLBACK"
    )

    assert fallback[
        "current"
    ]["remote_verified"] is False

    assert fallback["status"] == (
        "LOCAL FALLBACK · NOT B2 PLAYBACK"
    )
