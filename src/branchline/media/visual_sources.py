"""Resolve branch visuals from story source data."""

from __future__ import annotations

from typing import Any


class VisualSourceError(ValueError):
    """Raised when a story visual source cannot be rendered safely."""


def find_source(
    story: dict[str, Any],
    source_id: str,
) -> dict[str, Any]:
    """Return one source record by ID."""
    for source in story["sources"]:
        if source["id"] == source_id:
            return source

    raise VisualSourceError(
        f"Story source does not exist: {source_id}"
    )


def resolve_branch_visual(
    story: dict[str, Any],
    branch_id: str,
) -> dict[str, Any]:
    """Resolve a renderable visual definition for one branch."""
    source_id = f"image.{branch_id}"
    source = find_source(story, source_id)
    value = source.get("value")

    if not isinstance(value, dict):
        raise VisualSourceError(
            f"{source_id} must contain a structured visual definition"
        )

    label = str(value.get("label", "")).strip()
    destination = str(
        value.get("destination", "")
    ).strip()
    asset_ref = str(
        value.get("asset_ref", "")
    ).strip()
    background = value.get("background")

    if not label:
        raise VisualSourceError(
            f"{source_id} is missing label"
        )

    if not destination:
        raise VisualSourceError(
            f"{source_id} is missing destination"
        )

    if not asset_ref:
        raise VisualSourceError(
            f"{source_id} is missing asset_ref"
        )

    if (
        not isinstance(background, list)
        or len(background) != 3
        or not all(
            isinstance(channel, int)
            and 0 <= channel <= 255
            for channel in background
        )
    ):
        raise VisualSourceError(
            f"{source_id}.background must contain "
            "three RGB integers from 0 through 255"
        )

    return {
        "source_id": source_id,
        "asset_ref": asset_ref,
        "label": label,
        "destination": destination,
        "background": tuple(background),
    }
