"""Live story-revision analysis for Branchline.

This module performs fresh dependency analysis from source story files.
It does not claim that stored release execution is happening live.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from branchline.domain.story_graph import (
    canonical_hash,
    load_story,
    plan_rebuild,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]


SCENARIOS = {
    "scenario_a": {
        "previous_story": (
            "fixtures/main_story/story_v1.json"
        ),
        "current_story": (
            "fixtures/main_story/"
            "story_v2_shared_dialogue.json"
        ),
    },
    "scenario_b": {
        "previous_story": (
            "fixtures/main_story/"
            "story_v2_shared_dialogue.json"
        ),
        "current_story": (
            "fixtures/main_story/"
            "story_v3_ending_b_visual.json"
        ),
    },
}


class LiveAnalysisError(RuntimeError):
    """Raised when live revision analysis cannot be trusted."""


def _resolve_path(
    relative_path: str,
    *,
    root: Path,
) -> Path:
    path = root / relative_path

    if not path.exists():
        raise LiveAnalysisError(
            f"Required story fixture is missing: {path}"
        )

    return path


def analyze_story_revision(
    scenario_id: str,
    *,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Calculate a fresh rebuild plan from two story versions."""
    try:
        config = SCENARIOS[scenario_id]
    except KeyError as exc:
        raise LiveAnalysisError(
            f"Scenario does not support live analysis: {scenario_id}"
        ) from exc

    previous_path = _resolve_path(
        config["previous_story"],
        root=root,
    )

    current_path = _resolve_path(
        config["current_story"],
        root=root,
    )

    previous_story = load_story(
        str(previous_path)
    )

    current_story = load_story(
        str(current_path)
    )

    plan = plan_rebuild(
        previous_story,
        current_story,
    )

    changed_sources = sorted(
        plan.get("changed_sources", [])
    )

    stale_assets = sorted(
        plan.get("stale_assets", [])
    )

    reused_assets = sorted(
        plan.get("reused_assets", [])
    )

    affected_paths = sorted(
        plan.get("affected_paths", [])
    )

    unaffected_paths = sorted(
        plan.get("unaffected_paths", [])
    )

    if not changed_sources:
        raise LiveAnalysisError(
            "The selected story versions contain no source change."
        )

    total_assets = (
        len(stale_assets)
        + len(reused_assets)
    )

    if total_assets == 0:
        raise LiveAnalysisError(
            "The calculated plan contains no media assets."
        )

    reuse_rate = round(
        len(reused_assets)
        / total_assets
        * 100,
        1,
    )

    return {
        "mode": "LIVE_ANALYSIS",
        "scenario_id": scenario_id,
        "project_id": plan["project_id"],
        "previous_story": config[
            "previous_story"
        ],
        "current_story": config[
            "current_story"
        ],
        "calculated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "plan": deepcopy(plan),
        "plan_sha256": canonical_hash(plan),
        "changed_sources": changed_sources,
        "stale_assets": stale_assets,
        "reused_assets": reused_assets,
        "affected_paths": affected_paths,
        "unaffected_paths": unaffected_paths,
        "metrics": {
            "source_changes": len(
                changed_sources
            ),
            "assets_to_rebuild": len(
                stale_assets
            ),
            "assets_to_reuse": len(
                reused_assets
            ),
            "assets_total": total_assets,
            "reuse_rate_percent": reuse_rate,
            "paths_affected": len(
                affected_paths
            ),
            "paths_unaffected": len(
                unaffected_paths
            ),
        },
    }


def validate_analysis_against_release(
    analysis: dict[str, Any],
    scenario_view: dict[str, Any],
) -> None:
    """Stop the UI if its stored evidence disagrees with fresh analysis."""
    expected_rebuilt = sorted(
        scenario_view.get(
            "rebuilt_assets",
            [],
        )
    )

    expected_reused = sorted(
        scenario_view.get(
            "reused_assets",
            [],
        )
    )

    actual_rebuilt = sorted(
        analysis["stale_assets"]
    )

    actual_reused = sorted(
        analysis["reused_assets"]
    )

    mismatches = []

    if actual_rebuilt != expected_rebuilt:
        mismatches.append(
            "rebuilt-assets mismatch: "
            f"live={actual_rebuilt}, "
            f"evidence={expected_rebuilt}"
        )

    if actual_reused != expected_reused:
        mismatches.append(
            "reused-assets mismatch: "
            f"live={actual_reused}, "
            f"evidence={expected_reused}"
        )

    if mismatches:
        raise LiveAnalysisError(
            "Live analysis disagrees with the verified release: "
            + "; ".join(mismatches)
        )


def analysis_metrics(
    analysis: dict[str, Any],
) -> list[dict[str, str]]:
    """Create exactly three creator-facing metrics."""
    metrics = analysis["metrics"]

    return [
        {
            "label": "REBUILD",
            "value": str(
                metrics["assets_to_rebuild"]
            ),
            "detail": "affected assets",
        },
        {
            "label": "PRESERVE",
            "value": str(
                metrics["assets_to_reuse"]
            ),
            "detail": "verified B2 objects",
        },
        {
            "label": "REUSE",
            "value": (
                f"{metrics['reuse_rate_percent']}%"
            ),
            "detail": "generation avoided",
        },
    ]
