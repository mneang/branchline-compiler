"""Dependency planning for branching generative-media stories."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


def canonical_hash(value: Any) -> str:
    """Hash a JSON-compatible value deterministically."""
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def load_story(path: str | Path) -> dict[str, Any]:
    """Load and validate a story graph."""
    story = json.loads(Path(path).read_text())

    source_ids = [item["id"] for item in story["sources"]]
    asset_ids = [item["id"] for item in story["assets"]]
    all_ids = set(source_ids + asset_ids)

    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Duplicate source IDs detected")

    if len(asset_ids) != len(set(asset_ids)):
        raise ValueError("Duplicate asset IDs detected")

    for asset in story["assets"]:
        missing = set(asset["depends_on"]) - all_ids
        if missing:
            raise ValueError(
                f"Asset {asset['id']} has unknown dependencies: "
                f"{sorted(missing)}"
            )

    for path_item in story["paths"]:
        missing = set(path_item["required_assets"]) - set(asset_ids)
        if missing:
            raise ValueError(
                f"Path {path_item['id']} references unknown assets: "
                f"{sorted(missing)}"
            )

    return story


def source_hashes(story: dict[str, Any]) -> dict[str, str]:
    """Return canonical hashes for all source nodes."""
    return {
        item["id"]: canonical_hash(
            {
                "type": item["type"],
                "value": item["value"],
            }
        )
        for item in story["sources"]
    }


def changed_sources(
    previous_story: dict[str, Any],
    current_story: dict[str, Any],
) -> list[str]:
    """Identify source nodes whose content changed."""
    previous = source_hashes(previous_story)
    current = source_hashes(current_story)

    source_ids = set(previous) | set(current)

    return sorted(
        source_id
        for source_id in source_ids
        if previous.get(source_id) != current.get(source_id)
    )


def reverse_dependencies(
    story: dict[str, Any],
) -> dict[str, set[str]]:
    """Build dependency-to-dependent adjacency."""
    reverse: dict[str, set[str]] = defaultdict(set)

    for asset in story["assets"]:
        for dependency in asset["depends_on"]:
            reverse[dependency].add(asset["id"])

    return reverse


def stale_assets(
    story: dict[str, Any],
    changed: list[str],
) -> list[str]:
    """Return every asset transitively invalidated by changed sources."""
    reverse = reverse_dependencies(story)
    queue = deque(changed)
    visited = set(changed)
    stale: set[str] = set()

    while queue:
        current = queue.popleft()

        for dependent in reverse.get(current, set()):
            if dependent in visited:
                continue

            visited.add(dependent)
            stale.add(dependent)
            queue.append(dependent)

    return sorted(stale)


def plan_rebuild(
    previous_story: dict[str, Any],
    current_story: dict[str, Any],
) -> dict[str, Any]:
    """Calculate the minimum rebuild plan and affected story paths."""
    changed = changed_sources(previous_story, current_story)
    stale = stale_assets(current_story, changed)

    all_assets = sorted(
        asset["id"]
        for asset in current_story["assets"]
    )

    reused = sorted(set(all_assets) - set(stale))

    affected_paths = sorted(
        path_item["id"]
        for path_item in current_story["paths"]
        if set(path_item["required_assets"]) & set(stale)
    )

    unaffected_paths = sorted(
        path_item["id"]
        for path_item in current_story["paths"]
        if path_item["id"] not in affected_paths
    )

    return {
        "project_id": current_story["project_id"],
        "changed_sources": changed,
        "stale_assets": stale,
        "reused_assets": reused,
        "affected_paths": affected_paths,
        "unaffected_paths": unaffected_paths,
        "metrics": {
            "source_changes": len(changed),
            "assets_to_rebuild": len(stale),
            "assets_to_reuse": len(reused),
            "paths_affected": len(affected_paths),
            "paths_total": len(current_story["paths"]),
        },
    }
