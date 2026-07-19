"""Cinematic, minimal story presentation for the Branchline cockpit."""

from __future__ import annotations

from typing import Any

from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
    phase_copy,
    primary_action_label,
    step_label,
)
from branchline.presentation.judge_view import (
    build_scenario_view,
)


SCENE_CONFIG = {
    "scenario_b": {
        "story_label": "LAST TRAIN · RELEASE 3",
        "route_label": "ENDING B",
        "chapter_label": "CHAPTER 04 · NIGHT PLATFORM",
        "dialogue_line": "Cross the illuminated night platform.",
        "accent": "cyan",
        "before_image": "/ui-art/ending_b_before.png",
        "after_image": "/ui-art/ending_b_after.png",
        "ready_title": "The final platform scene changed.",
        "ready_caption": (
            "A creator revised Ending B minutes before publication."
        ),
        "planned_title": "Only Ending B needs to move.",
        "planned_caption": (
            "The shared voice, captions, and complete Ending A route "
            "remain verified in Backblaze B2."
        ),
        "complete_title": "Ending B rebuilt. Ending A never moved.",
        "complete_caption": (
            "The revised route passed remote verification without "
            "regenerating unrelated media."
        ),
    },
    "scenario_a": {
        "story_label": "LAST TRAIN · SHARED SCENE",
        "route_label": "BOTH ROUTES",
        "chapter_label": "CHAPTER 03 · LAST DEPARTURE",
        "dialogue_line": "The last train leaves at eight.",
        "accent": "violet",
        "before_image": "/ui-art/shared_dialogue.png",
        "after_image": "/ui-art/shared_dialogue.png",
        "ready_title": "One line changed across the entire story.",
        "ready_caption": (
            "Shared dialogue now affects media in both reachable endings."
        ),
        "planned_title": "The change crosses both routes.",
        "planned_caption": (
            "Branchline identified four dependent assets while preserving "
            "both branch-specific route cards."
        ),
        "complete_title": "Both routes are synchronized again.",
        "complete_caption": (
            "All shared media was rebuilt and every reachable path verified."
        ),
    },
    "scenario_c": {
        "story_label": "LAST TRAIN · RELEASE SAFETY",
        "route_label": "ENDING B",
        "chapter_label": "FINAL CHECK · NIGHT PLATFORM",
        "dialogue_line": "Cross the illuminated night platform.",
        "accent": "rose",
        "before_image": "/ui-art/ending_b_after.png",
        "after_image": "/ui-art/ending_b_after.png",
        "ready_title": "Ending B looks ready—but one asset is missing.",
        "ready_caption": (
            "The candidate release references media that cannot be "
            "retrieved from Backblaze B2."
        ),
        "planned_title": "Remote verification required.",
        "planned_caption": (
            "Branchline must test every reachable route before publication."
        ),
        "complete_title": "The broken route was locked before release.",
        "complete_caption": (
            "Ending A remains healthy while Ending B is blocked from "
            "unsafe publication."
        ),
    },
}


def display_path_name(path_id: str) -> str:
    names = {
        "ending_a": "ENDING A",
        "ending_b": "ENDING B",
    }

    return names.get(
        path_id,
        path_id.replace("_", " ").upper(),
    )


def route_cards(
    scenario: dict[str, Any],
    *,
    phase: str,
) -> list[dict[str, str]]:
    affected_assets = set(
        scenario["rebuilt_assets"]
    ) | set(
        scenario["failed_assets"]
    )

    results: list[dict[str, str]] = []

    for path in scenario["paths"]:
        affected = any(
            asset_id in affected_assets
            for asset_id in path["required_assets"]
        )

        if phase == READY:
            if affected:
                status = "CHANGE PENDING"
                tone = "warning"
            else:
                status = "PROTECTED"
                tone = "quiet"

        elif phase == PLANNED:
            if affected:
                status = "REBUILD"
                tone = "warning"
            else:
                status = "PRESERVE"
                tone = "safe"

        else:
            status = path["status"]
            tone = (
                "safe"
                if path["verified"]
                else "blocked"
            )

        results.append(
            {
                "path_id": path["path_id"],
                "label": display_path_name(
                    path["path_id"]
                ),
                "status": status,
                "tone": tone,
            }
        )

    return results


def summary_metrics(
    scenario: dict[str, Any],
    *,
    phase: str,
) -> list[dict[str, str]]:
    metrics = scenario.get(
        "raw_metrics",
        {},
    )

    if phase == READY:
        return []

    if phase == PLANNED:
        total_assets = (
            len(scenario["rebuilt_assets"])
            + len(scenario["reused_assets"])
        )

        reuse_rate = (
            round(
                len(scenario["reused_assets"])
                / total_assets
                * 100,
                1,
            )
            if total_assets
            else 0.0
        )

        return [
            {
                "label": "REBUILD",
                "value": str(
                    len(
                        scenario[
                            "rebuilt_assets"
                        ]
                    )
                ),
                "detail": "affected media",
            },
            {
                "label": "PRESERVE",
                "value": str(
                    len(
                        scenario[
                            "reused_assets"
                        ]
                    )
                ),
                "detail": "verified B2 objects",
            },
            {
                "label": "REUSE",
                "value": f"{reuse_rate}%",
                "detail": "generation avoided",
            },
        ]

    if (
        scenario["publication_status"]
        == "BLOCKED"
    ):
        return [
            {
                "label": "HEALTHY",
                "value": str(
                    metrics.get(
                        "assets_verified",
                        0,
                    )
                ),
                "detail": "assets preserved",
            },
            {
                "label": "FAILED",
                "value": str(
                    metrics.get(
                        "assets_failed",
                        0,
                    )
                ),
                "detail": "exact asset isolated",
            },
            {
                "label": "SAFE ROUTES",
                "value": str(
                    metrics.get(
                        "paths_verified",
                        0,
                    )
                ),
                "detail": "unaffected path",
            },
        ]

    return [
        {
            "label": "VERIFIED",
            "value": (
                f"{metrics.get('assets_remote_verified', 0)}"
                f"/{metrics.get('assets_total', 0)}"
            ),
            "detail": "remote media objects",
        },
        {
            "label": "ROUTES",
            "value": (
                f"{metrics.get('paths_verified', 0)}"
                f"/{metrics.get('paths_total', 0)}"
            ),
            "detail": "reachable paths",
        },
        {
            "label": "STALE",
            "value": str(
                metrics.get(
                    "stale_assets_remaining",
                    0,
                )
            ),
            "detail": "assets remaining",
        },
    ]


def build_cinematic_view(
    scenario_id: str,
    phase: str,
) -> dict[str, Any]:
    if phase not in {
        READY,
        PLANNED,
        COMPLETE,
    }:
        raise ValueError(
            f"Unsupported cinematic phase: {phase}"
        )

    scenario = build_scenario_view(
        scenario_id
    )

    config = SCENE_CONFIG[
        scenario_id
    ]

    if phase == READY:
        scene_title = config[
            "ready_title"
        ]
        scene_caption = config[
            "ready_caption"
        ]

    elif phase == PLANNED:
        scene_title = config[
            "planned_title"
        ]
        scene_caption = config[
            "planned_caption"
        ]

    else:
        scene_title = config[
            "complete_title"
        ]
        scene_caption = config[
            "complete_caption"
        ]

    image = (
        config["after_image"]
        if phase == COMPLETE
        else config["before_image"]
    )

    blocked = (
        phase == COMPLETE
        and scenario[
            "publication_status"
        ]
        == "BLOCKED"
    )

    active_change = (
        scenario["changed_sources"][0]
        if scenario["changed_sources"]
        else "remote B2 media availability"
    )

    return {
        "scenario": scenario,
        "phase": phase,
        "step_label": step_label(
            scenario_id,
            phase,
        ),
        "primary_action": (
            primary_action_label(
                scenario_id,
                phase,
            )
        ),
        "copy": phase_copy(
            scenario,
            phase,
        ),
        "story_label": config[
            "story_label"
        ],
        "route_label": config[
            "route_label"
        ],
        "chapter_label": config[
            "chapter_label"
        ],
        "dialogue_line": config[
            "dialogue_line"
        ],
        "accent": config[
            "accent"
        ],
        "image": image,
        "scene_title": scene_title,
        "scene_caption": scene_caption,
        "active_change": active_change,
        "route_cards": route_cards(
            scenario,
            phase=phase,
        ),
        "summary_metrics": (
            summary_metrics(
                scenario,
                phase=phase,
            )
        ),
        "blocked": blocked,
    }
