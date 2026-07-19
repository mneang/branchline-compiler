"""One-screen manga release presentation for Branchline."""

from __future__ import annotations

from typing import Any

from branchline.presentation.cinematic import (
    build_cinematic_view,
)
from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
)


VALID_PHASES = {
    READY,
    PLANNED,
    COMPLETE,
}


SCENARIO_COPY = {
    "scenario_b": {
        READY: {
            "eyebrow": "REVISION DETECTED",
            "title": "Ending B changed.",
            "body": (
                "Trace the revision through every generated asset "
                "before this branching story is published."
            ),
        },
        PLANNED: {
            "eyebrow": "MINIMAL REBUILD READY",
            "title": "Two assets move. Four stay.",
            "body": (
                "Rebuild the Ending B route card and preview. Preserve "
                "the shared voice, captions, and complete Ending A route."
            ),
        },
        COMPLETE: {
            "eyebrow": "RELEASE VERIFIED",
            "title": "Both endings are ready.",
            "body": (
                "Ending B was rebuilt while Ending A remained "
                "byte-identical in Backblaze B2."
            ),
        },
    },
    "scenario_a": {
        READY: {
            "eyebrow": "SHARED REVISION DETECTED",
            "title": "One line changed both routes.",
            "body": (
                "The revised dialogue appears in media shared by every "
                "reachable ending."
            ),
        },
        PLANNED: {
            "eyebrow": "CROSS-ROUTE PLAN READY",
            "title": "Four shared assets must move.",
            "body": (
                "Rebuild the voice, caption, and both route previews. "
                "Preserve the branch-specific artwork."
            ),
        },
        COMPLETE: {
            "eyebrow": "STORY SYNCHRONIZED",
            "title": "Both routes agree again.",
            "body": (
                "All affected shared media was rebuilt and every "
                "reachable route passed remote verification."
            ),
        },
    },
    "scenario_c": {
        READY: {
            "eyebrow": "RELEASE SAFETY CHECK",
            "title": "One route may be incomplete.",
            "body": (
                "Verify every required B2 object before this candidate "
                "release becomes public."
            ),
        },
        PLANNED: {
            "eyebrow": "REMOTE CHECK READY",
            "title": "Every route must prove itself.",
            "body": (
                "Branchline will independently retrieve the final media "
                "required by each reachable ending."
            ),
        },
        COMPLETE: {
            "eyebrow": "PUBLICATION STOPPED",
            "title": "Ending B is locked.",
            "body": (
                "The exact missing preview was isolated while Ending A "
                "remained healthy and verified."
            ),
        },
    },
}


def image_for_panel(
    scenario_id: str,
    phase: str,
    *,
    path_id: str,
) -> str:
    """Return the state-specific original manga panel."""
    if path_id == "ending_a":
        return "/manga-art/ending_a_manga.png"

    if scenario_id == "scenario_c" and phase == COMPLETE:
        return "/manga-art/ending_b_blocked_manga.png"

    if phase == COMPLETE:
        return "/manga-art/ending_b_verified_manga.png"

    if scenario_id == "scenario_a":
        return "/manga-art/shared_dialogue_manga.png"

    return "/manga-art/ending_b_ready_manga.png"


def action_label(
    scenario_id: str,
    phase: str,
) -> str:
    """Keep exactly one primary action at each state."""
    if phase == READY:
        return (
            "Verify release"
            if scenario_id == "scenario_c"
            else "Analyze revision"
        )

    if phase == PLANNED:
        return "Approve selective rebuild"

    return "Replay demonstration"


def decision_metrics(
    scenario: dict[str, Any],
    phase: str,
) -> list[dict[str, str]]:
    """Expose no more than three decision-relevant metrics."""
    if phase == READY:
        return []

    metrics = scenario.get(
        "raw_metrics",
        {},
    )

    if phase == PLANNED:
        rebuilt = len(
            scenario["rebuilt_assets"]
        )
        reused = len(
            scenario["reused_assets"]
        )
        total = rebuilt + reused

        reuse_rate = (
            round(
                reused / total * 100,
                1,
            )
            if total
            else 0.0
        )

        return [
            {
                "label": "REBUILD",
                "value": str(rebuilt),
                "detail": "affected assets",
            },
            {
                "label": "PRESERVE",
                "value": str(reused),
                "detail": "verified B2 objects",
            },
            {
                "label": "REUSE",
                "value": f"{reuse_rate}%",
                "detail": "generation avoided",
            },
        ]

    if scenario["publication_status"] == "BLOCKED":
        return [
            {
                "label": "HEALTHY",
                "value": str(
                    metrics.get(
                        "assets_verified",
                        0,
                    )
                ),
                "detail": "assets verified",
            },
            {
                "label": "MISSING",
                "value": str(
                    metrics.get(
                        "assets_failed",
                        0,
                    )
                ),
                "detail": "exact failure",
            },
            {
                "label": "SAFE ROUTES",
                "value": str(
                    metrics.get(
                        "paths_verified",
                        0,
                    )
                ),
                "detail": "preserved",
            },
        ]

    return [
        {
            "label": "OBJECTS",
            "value": (
                f"{metrics.get('assets_remote_verified', 0)}"
                f"/{metrics.get('assets_total', 0)}"
            ),
            "detail": "remote verified",
        },
        {
            "label": "ROUTES",
            "value": (
                f"{metrics.get('paths_verified', 0)}"
                f"/{metrics.get('paths_total', 0)}"
            ),
            "detail": "release healthy",
        },
        {
            "label": "STALE",
            "value": str(
                metrics.get(
                    "stale_assets_remaining",
                    0,
                )
            ),
            "detail": "remaining",
        },
    ]


def sponsor_strip(
    scenario: dict[str, Any],
    phase: str,
) -> list[dict[str, str]]:
    """Keep sponsor necessity visible without exposing raw infrastructure."""
    proof = scenario["provenance"]
    metrics = scenario.get(
        "raw_metrics",
        {},
    )

    if phase == READY:
        b2_value = "Verified media memory"
        release_value = "Awaiting analysis"

    elif phase == PLANNED:
        b2_value = (
            f"{len(scenario['reused_assets'])} "
            "objects preserved"
        )
        release_value = (
            f"{len(scenario['rebuilt_assets'])} "
            "assets in exact plan"
        )

    elif scenario["publication_status"] == "BLOCKED":
        b2_value = (
            f"{metrics.get('assets_verified', 0)} verified · "
            f"{metrics.get('assets_failed', 0)} missing"
        )
        release_value = "Unsafe publication blocked"

    else:
        b2_value = (
            f"{metrics.get('assets_remote_verified', 0)}/"
            f"{metrics.get('assets_total', 0)} "
            "objects verified"
        )
        release_value = "Safe to publish"

    return [
        {
            "label": "GENBLAZE",
            "value": proof["generation_engine"],
            "detail": (
                f"{proof['provider']} · "
                f"{proof['model']}"
            ),
        },
        {
            "label": "BACKBLAZE B2",
            "value": b2_value,
            "detail": "Durable media and release evidence",
        },
        {
            "label": "RELEASE CHECK",
            "value": release_value,
            "detail": "Every reachable path evaluated",
        },
    ]


def build_release_spread(
    scenario_id: str,
    phase: str,
) -> dict[str, Any]:
    """Build one complete manga-spread state."""
    if phase not in VALID_PHASES:
        raise ValueError(
            f"Unsupported release phase: {phase}"
        )

    experience = build_cinematic_view(
        scenario_id,
        phase,
    )

    scenario = experience["scenario"]

    route_by_id = {
        route["path_id"]: route
        for route in experience["route_cards"]
    }

    panels = []

    for path_id in (
        "ending_a",
        "ending_b",
    ):
        route = route_by_id[path_id]

        panels.append(
            {
                "path_id": path_id,
                "label": route["label"],
                "status": route["status"],
                "tone": route["tone"],
                "image": image_for_panel(
                    scenario_id,
                    phase,
                    path_id=path_id,
                ),
            }
        )

    active_change = (
        scenario["changed_sources"][0]
        if scenario["changed_sources"]
        else "remote B2 object availability"
    )

    blocked = (
        phase == COMPLETE
        and scenario["publication_status"]
        == "BLOCKED"
    )

    return {
        "scenario_id": scenario_id,
        "phase": phase,
        "scenario": scenario,
        "copy": SCENARIO_COPY[
            scenario_id
        ][phase],
        "story_label": experience[
            "story_label"
        ],
        "chapter_label": experience[
            "chapter_label"
        ],
        "dialogue_line": experience[
            "dialogue_line"
        ],
        "active_change": active_change,
        "panels": panels,
        "metrics": decision_metrics(
            scenario,
            phase,
        ),
        "sponsor_strip": sponsor_strip(
            scenario,
            phase,
        ),
        "action_label": action_label(
            scenario_id,
            phase,
        ),
        "publication_status": scenario[
            "publication_status"
        ],
        "blocked": blocked,
    }
