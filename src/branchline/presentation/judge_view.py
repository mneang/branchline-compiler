"""Build judge-facing views from verified Branchline evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]


SCENARIO_CONFIG = {
    "scenario_b": {
        "short_name": "Scenario B",
        "title": "Ending B visual revision",
        "trigger": (
            "The creator changes only Ending B's visual "
            "before publication."
        ),
        "story_path": (
            "fixtures/main_story/"
            "story_v3_ending_b_visual.json"
        ),
        "evidence_path": (
            "evidence/release_ending_b_visual_v3.json"
        ),
        "kind": "release",
        "hero": True,
    },
    "scenario_a": {
        "short_name": "Scenario A",
        "title": "Shared dialogue revision",
        "trigger": (
            "The creator changes shared dialogue used by "
            "both reachable endings."
        ),
        "story_path": (
            "fixtures/main_story/"
            "story_v2_shared_dialogue.json"
        ),
        "evidence_path": (
            "evidence/"
            "release_shared_dialogue_v2_canonical.json"
        ),
        "kind": "release",
        "hero": False,
    },
    "scenario_c": {
        "short_name": "Scenario C",
        "title": "Missing reachable media",
        "trigger": (
            "A required Ending B preview cannot be retrieved "
            "from Backblaze B2."
        ),
        "story_path": (
            "fixtures/main_story/"
            "story_v2_shared_dialogue.json"
        ),
        "evidence_path": (
            "evidence/"
            "publication_guard_missing_preview_ending_b.json"
        ),
        "kind": "guard",
        "hero": False,
    },
}


STATUS_COLORS = {
    "changed": "#f59e0b",
    "rebuilt": "#fb7185",
    "reused": "#34d399",
    "verified": "#38bdf8",
    "blocked": "#ef4444",
    "neutral": "#64748b",
}


def read_json(
    relative_path: str,
    *,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Read one required JSON document."""
    path = root / relative_path

    if not path.exists():
        raise FileNotFoundError(
            f"Required Branchline evidence is missing: {path}"
        )

    document = json.loads(path.read_text())

    if not isinstance(document, dict):
        raise ValueError(
            f"{path} must contain a JSON object"
        )

    return document


def display_identifier(identifier: str) -> str:
    """Make a graph identifier readable without hiding its real ID."""
    if "." in identifier:
        prefix, remainder = identifier.split(".", 1)
        return f"{prefix}\n{remainder}"

    return identifier.replace("_", "\n")


def asset_action(
    logical_id: str,
    evidence: dict[str, Any],
    *,
    kind: str,
) -> str:
    """Normalize one asset's judge-facing state."""
    if kind == "guard":
        failed = set(evidence.get("failed_assets", []))

        return (
            "blocked"
            if logical_id in failed
            else "verified"
        )

    record = evidence.get(
        "assets",
        {},
    ).get(logical_id, {})

    action = str(
        record.get("release_action", "")
    ).lower()

    if "rebuilt" in action:
        return "rebuilt"

    if "reused" in action:
        return "reused"

    if record.get("remote_verified") is True:
        return "verified"

    return "neutral"


def normalized_paths(
    story: dict[str, Any],
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Normalize release and guard path evidence."""
    evidence_by_id = {
        item["path_id"]: item
        for item in evidence.get("paths", [])
        if isinstance(item, dict)
        and "path_id" in item
    }

    normalized = []

    for path_spec in story["paths"]:
        path_id = path_spec["id"]
        result = evidence_by_id.get(path_id, {})

        verified = bool(
            result.get("verified", False)
        )

        normalized.append(
            {
                "path_id": path_id,
                "required_assets": (
                    path_spec["required_assets"]
                ),
                "verified": verified,
                "blocked_assets": result.get(
                    "blocked_assets",
                    result.get(
                        "failed_assets",
                        [],
                    ),
                ),
                "status": (
                    "VERIFIED"
                    if verified
                    else "BLOCKED"
                ),
            }
        )

    return normalized


def build_graph_options(
    story: dict[str, Any],
    evidence: dict[str, Any],
    *,
    kind: str,
) -> dict[str, Any]:
    """Create a stable ECharts dependency graph."""
    changed_sources = set(
        evidence.get("changed_sources", [])
    )

    failed_assets = set(
        evidence.get("failed_assets", [])
    )

    paths = normalized_paths(
        story,
        evidence,
    )

    path_by_id = {
        item["path_id"]: item
        for item in paths
    }

    sources = sorted(
        story["sources"],
        key=lambda item: item["id"],
    )

    assets = sorted(
        story["assets"],
        key=lambda item: item["id"],
    )

    path_specs = sorted(
        story["paths"],
        key=lambda item: item["id"],
    )

    nodes: list[dict[str, Any]] = []
    links: list[dict[str, str]] = []

    def y_position(
        index: int,
        count: int,
    ) -> int:
        if count <= 1:
            return 300

        return int(
            60 + index * (500 / (count - 1))
        )

    for index, source in enumerate(sources):
        source_id = source["id"]
        state = (
            "changed"
            if source_id in changed_sources
            else "neutral"
        )

        nodes.append(
            {
                "id": source_id,
                "name": display_identifier(
                    source_id
                ),
                "x": 70,
                "y": y_position(
                    index,
                    len(sources),
                ),
                "symbolSize": 62,
                "category": 0,
                "value": state,
                "itemStyle": {
                    "color": STATUS_COLORS[state],
                },
            }
        )

    known_source_ids = {
        source["id"]
        for source in sources
    }

    known_asset_ids = {
        asset["id"]
        for asset in assets
    }

    for index, asset in enumerate(assets):
        logical_id = asset["id"]
        state = asset_action(
            logical_id,
            evidence,
            kind=kind,
        )

        if logical_id in failed_assets:
            state = "blocked"

        nodes.append(
            {
                "id": logical_id,
                "name": display_identifier(
                    logical_id
                ),
                "x": 470,
                "y": y_position(
                    index,
                    len(assets),
                ),
                "symbolSize": 68,
                "category": 1,
                "value": state,
                "itemStyle": {
                    "color": STATUS_COLORS[state],
                },
            }
        )

        for dependency in asset["depends_on"]:
            if (
                dependency in known_source_ids
                or dependency in known_asset_ids
            ):
                links.append(
                    {
                        "source": dependency,
                        "target": logical_id,
                    }
                )

    for index, path_spec in enumerate(path_specs):
        path_id = path_spec["id"]
        path_state = path_by_id[path_id]

        state = (
            "verified"
            if path_state["verified"]
            else "blocked"
        )

        nodes.append(
            {
                "id": path_id,
                "name": display_identifier(
                    path_id
                ),
                "x": 880,
                "y": y_position(
                    index,
                    len(path_specs),
                ),
                "symbolSize": 82,
                "category": 2,
                "value": state,
                "itemStyle": {
                    "color": STATUS_COLORS[state],
                },
            }
        )

        for logical_id in path_spec[
            "required_assets"
        ]:
            links.append(
                {
                    "source": logical_id,
                    "target": path_id,
                }
            )

    return {
        "animationDuration": 650,
        "animationDurationUpdate": 500,
        "tooltip": {
            "trigger": "item",
        },
        "legend": [
            {
                "data": [
                    "Source",
                    "Media asset",
                    "Story path",
                ],
                "textStyle": {
                    "color": "#cbd5e1",
                },
            }
        ],
        "series": [
            {
                "type": "graph",
                "layout": "none",
                "roam": True,
                "data": nodes,
                "links": links,
                "categories": [
                    {"name": "Source"},
                    {"name": "Media asset"},
                    {"name": "Story path"},
                ],
                "label": {
                    "show": True,
                    "position": "inside",
                    "fontSize": 10,
                    "color": "#ffffff",
                    "fontWeight": 600,
                },
                "lineStyle": {
                    "color": "#64748b",
                    "width": 2,
                    "curveness": 0.08,
                    "opacity": 0.72,
                },
                "emphasis": {
                    "focus": "adjacency",
                    "lineStyle": {
                        "width": 4,
                    },
                },
            }
        ],
    }


def provenance_view(
    evidence: dict[str, Any],
    *,
    kind: str,
) -> dict[str, Any]:
    """Extract concise B2 and Genblaze evidence."""
    assets = evidence.get("assets", {})
    voice = assets.get("voice.opening", {})
    genblaze = evidence.get("genblaze", {})

    if kind == "guard":
        return {
            "generation_engine": (
                "Inherited verified Genblaze release"
            ),
            "provider": "No new generation",
            "model": "No new generation",
            "run_id": "Not applicable",
            "b2_object_key": evidence.get(
                "guard_report_object_key",
                "Stored publication-guard report",
            ),
            "remote_verified": True,
        }

    return {
        "generation_engine": "Genblaze",
        "provider": (
            voice.get("provider")
            or genblaze.get("provider")
            or "Recorded in release provenance"
        ),
        "model": (
            voice.get("model")
            or genblaze.get("model")
            or "Recorded in release provenance"
        ),
        "run_id": (
            voice.get("genblaze_run_id")
            or genblaze.get("run_id")
            or genblaze.get("inherited_run_id")
            or "Inherited verified run"
        ),
        "b2_object_key": (
            evidence.get("release_object_key")
            or "Stored release manifest"
        ),
        "remote_verified": all(
            bool(asset.get("remote_verified"))
            for asset in assets.values()
        ),
    }


def metric_view(
    evidence: dict[str, Any],
    *,
    kind: str,
) -> list[dict[str, str]]:
    """Create four prominent scoreboard metrics."""
    metrics = evidence.get("metrics", {})

    if kind == "guard":
        return [
            {
                "label": "Failed assets",
                "value": str(
                    metrics.get("assets_failed", 0)
                ),
                "detail": "Exact failure isolated",
            },
            {
                "label": "Healthy assets",
                "value": str(
                    metrics.get("assets_verified", 0)
                ),
                "detail": "Remote media verified",
            },
            {
                "label": "Paths blocked",
                "value": str(
                    metrics.get("paths_blocked", 0)
                ),
                "detail": "Unsafe route stopped",
            },
            {
                "label": "Paths verified",
                "value": str(
                    metrics.get("paths_verified", 0)
                ),
                "detail": "Healthy route preserved",
            },
        ]

    reuse_rate = metrics.get(
        "reuse_rate_percent",
        0,
    )

    return [
        {
            "label": "Assets rebuilt",
            "value": str(
                metrics.get("assets_rebuilt", 0)
            ),
            "detail": "Only stale media",
        },
        {
            "label": "Assets reused",
            "value": str(
                metrics.get("assets_reused", 0)
            ),
            "detail": "Verified B2 objects",
        },
        {
            "label": "Reuse rate",
            "value": f"{reuse_rate}%",
            "detail": "Generation avoided",
        },
        {
            "label": "Paths verified",
            "value": (
                f"{metrics.get('paths_verified', 0)}"
                f"/{metrics.get('paths_total', 0)}"
            ),
            "detail": "Reachable routes healthy",
        },
    ]


def build_scenario_view(
    scenario_id: str,
    *,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Build one complete judge-facing scenario."""
    config = SCENARIO_CONFIG[scenario_id]

    story = read_json(
        config["story_path"],
        root=root,
    )

    evidence = read_json(
        config["evidence_path"],
        root=root,
    )

    kind = config["kind"]
    paths = normalized_paths(
        story,
        evidence,
    )

    rebuilt_assets = sorted(
        logical_id
        for logical_id in evidence.get(
            "assets",
            {},
        )
        if asset_action(
            logical_id,
            evidence,
            kind=kind,
        )
        == "rebuilt"
    )

    reused_assets = sorted(
        logical_id
        for logical_id in evidence.get(
            "assets",
            {},
        )
        if asset_action(
            logical_id,
            evidence,
            kind=kind,
        )
        == "reused"
    )

    failed_assets = sorted(
        evidence.get("failed_assets", [])
    )

    publication_status = str(
        evidence.get(
            "publication_status",
            "UNKNOWN",
        )
    )

    return {
        "scenario_id": scenario_id,
        "short_name": config["short_name"],
        "title": config["title"],
        "trigger": config["trigger"],
        "hero": config["hero"],
        "mode": "VERIFIED REPLAY",
        "project_id": story["project_id"],
        "changed_sources": sorted(
            evidence.get("changed_sources", [])
        ),
        "rebuilt_assets": rebuilt_assets,
        "reused_assets": reused_assets,
        "failed_assets": failed_assets,
        "paths": paths,
        "metrics": metric_view(
            evidence,
            kind=kind,
        ),
        "provenance": provenance_view(
            evidence,
            kind=kind,
        ),
        "publication_status": publication_status,
        "status_message": str(
            evidence.get("status", "")
        ),
        "graph_options": build_graph_options(
            story,
            evidence,
            kind=kind,
        ),
    }


def load_scenarios(
    *,
    root: Path = PROJECT_ROOT,
) -> dict[str, dict[str, Any]]:
    """Load every supported judge scenario."""
    return {
        scenario_id: build_scenario_view(
            scenario_id,
            root=root,
        )
        for scenario_id in SCENARIO_CONFIG
    }
