"""Phase-driven, creator-friendly focus experience for Branchline."""

from __future__ import annotations

from typing import Any

from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
)


DIRECTOR_OPTIONS: tuple[dict[str, str], ...] = (
    {
        "id": "scenario_b",
        "tag": "LIVE DEMO",
        "title": "Revise Ending B",
        "summary": (
            "Change one branch visual while preserving "
            "all unrelated generated media."
        ),
        "result": "2 rebuild · 4 preserve",
        "icon": "auto_stories",
    },
    {
        "id": "scenario_a",
        "tag": "GENBLAZE CASE",
        "title": "Revise shared dialogue",
        "summary": (
            "Change one shared line and rebuild every "
            "dependent voice, caption, and preview."
        ),
        "result": "4 rebuild · 2 preserve",
        "icon": "record_voice_over",
    },
    {
        "id": "scenario_c",
        "tag": "SAFETY CASE",
        "title": "Detect missing media",
        "summary": (
            "Verify a candidate release and isolate "
            "the exact branch that cannot publish."
        ),
        "result": "Ending A safe · Ending B blocked",
        "icon": "shield",
    },
)


WHY_EXPLANATIONS: dict[str, dict[str, Any]] = {
    "scenario_b": {
        "title": "Why only two assets?",
        "summary": (
            "Only the visual source for Ending B changed. "
            "Branchline followed that source through the story graph."
        ),
        "items": [
            {
                "label": "Ending B artwork",
                "reason": (
                    "Directly depends on image.ending_b."
                ),
                "action": "REBUILD",
            },
            {
                "label": "Ending B preview",
                "reason": (
                    "Depends on the Ending B artwork, so its "
                    "compiled video is now stale."
                ),
                "action": "REBUILD",
            },
            {
                "label": "Ending A route",
                "reason": (
                    "Has no dependency on image.ending_b."
                ),
                "action": "PRESERVE",
            },
            {
                "label": "Voice and caption",
                "reason": (
                    "The shared dialogue did not change."
                ),
                "action": "PRESERVE",
            },
        ],
    },
    "scenario_a": {
        "title": "Why four assets?",
        "summary": (
            "The shared opening dialogue changed. Every generated "
            "asset that contains that line must become current again."
        ),
        "items": [
            {
                "label": "Opening voice",
                "reason": (
                    "Contains the previous spoken dialogue."
                ),
                "action": "REBUILD",
            },
            {
                "label": "Opening caption",
                "reason": (
                    "Contains the previous written dialogue."
                ),
                "action": "REBUILD",
            },
            {
                "label": "Both route previews",
                "reason": (
                    "Each preview combines the shared voice "
                    "and caption with branch artwork."
                ),
                "action": "REBUILD",
            },
            {
                "label": "Both route artworks",
                "reason": (
                    "Their branch-specific image sources remain current."
                ),
                "action": "PRESERVE",
            },
        ],
    },
    "scenario_c": {
        "title": "Why is only Ending B blocked?",
        "summary": (
            "The unavailable object is required only by the "
            "Ending B route."
        ),
        "items": [
            {
                "label": "Ending B preview",
                "reason": (
                    "The required B2 object could not be retrieved."
                ),
                "action": "FAILED",
            },
            {
                "label": "Ending B route",
                "reason": (
                    "A reachable route cannot publish with "
                    "a missing required asset."
                ),
                "action": "BLOCK",
            },
            {
                "label": "Ending A route",
                "reason": (
                    "Every object required by Ending A still verifies."
                ),
                "action": "PRESERVE",
            },
        ],
    },
}


def director_options() -> list[dict[str, str]]:
    """Return real, selectable creator workflows."""
    return [
        dict(option)
        for option in DIRECTOR_OPTIONS
    ]


def _panel(
    *,
    css_class: str = "",
    badges: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "class": css_class,
        "badges": list(badges),
    }


def _execution_context(
    execution_mode: str | None,
) -> tuple[str, str]:
    if execution_mode == "LIVE_EXECUTION":
        return (
            "LIVE SELECTIVE RELEASE",
            "Real assets are being rebuilt, stored, and verified.",
        )

    if execution_mode == "VERIFIED_REPLAY_FALLBACK":
        return (
            "VERIFIED EVIDENCE REPLAY",
            "Stored remote evidence is being validated.",
        )

    return (
        "RELEASE EXECUTION",
        "The approved plan is being processed.",
    )


def build_focus_experience(
    *,
    scenario_id: str,
    phase: str,
    busy: bool,
    proof_mode: bool,
    execution_mode: str | None,
    active_stage: str | None = None,
) -> dict[str, Any]:
    """Determine exactly what the user should see at this moment."""
    if scenario_id not in {
        "scenario_a",
        "scenario_b",
        "scenario_c",
    }:
        raise ValueError(
            f"Unsupported focus scenario: {scenario_id}"
        )

    why = WHY_EXPLANATIONS[
        scenario_id
    ]

    if busy:
        title, detail = _execution_context(
            execution_mode
        )

        if scenario_id == "scenario_b":
            panels = {
                "left": _panel(
                    css_class="panel-preserved",
                    badges=(
                        "PRESERVED FROM B2",
                    ),
                ),
                "right": _panel(
                    css_class="panel-working",
                    badges=(
                        "REBUILDING ARTWORK",
                        "REBUILDING PREVIEW",
                    ),
                ),
            }

        elif scenario_id == "scenario_a":
            panels = {
                "left": _panel(
                    css_class="panel-working",
                    badges=(
                        "PREVIEW REBUILD",
                    ),
                ),
                "right": _panel(
                    css_class="panel-working",
                    badges=(
                        "PREVIEW REBUILD",
                    ),
                ),
            }

        else:
            panels = {
                "left": _panel(
                    css_class="panel-preserved",
                    badges=(
                        "ROUTE VERIFIED",
                    ),
                ),
                "right": _panel(
                    css_class="panel-working-danger",
                    badges=(
                        "CHECKING REQUIRED MEDIA",
                    ),
                ),
            }

        return {
            "stage": "ACT",
            "stage_number": "04",
            "title": title,
            "detail": detail,
            "active_stage": active_stage,
            "panels": panels,
            "show_lineage": proof_mode,
            "show_sponsor_strip": proof_mode,
            "compact_shell": not proof_mode,
            "why": why,
            "context_bar": {
                "label": "ACTION",
                "value": title,
                "detail": detail,
                "tone": "working",
            },
        }

    if phase == READY:
        return {
            "stage": "OBSERVE",
            "stage_number": "01",
            "title": "See the story revision",
            "detail": (
                "Choose a real creator change, then let Branchline "
                "trace its media impact."
            ),
            "active_stage": None,
            "panels": {
                "left": _panel(),
                "right": _panel(
                    css_class=(
                        "panel-observed"
                        if scenario_id
                        in {
                            "scenario_b",
                            "scenario_c",
                        }
                        else ""
                    ),
                    badges=(
                        (
                            "REVISION DETECTED"
                            if scenario_id == "scenario_b"
                            else "MEDIA CHECK REQUIRED"
                        ),
                    )
                    if scenario_id
                    in {
                        "scenario_b",
                        "scenario_c",
                    }
                    else (),
                ),
            },
            "show_lineage": proof_mode,
            "show_sponsor_strip": proof_mode,
            "compact_shell": not proof_mode,
            "why": why,
            "context_bar": {
                "label": "OBSERVE",
                "value": "Story revision ready",
                "detail": (
                    "No rebuild begins until its impact is understood."
                ),
                "tone": "observe",
            },
        }

    if phase == PLANNED:
        if scenario_id == "scenario_b":
            panels = {
                "left": _panel(
                    css_class="panel-preserved",
                    badges=(
                        "PRESERVED FROM B2",
                    ),
                ),
                "right": _panel(
                    css_class="panel-affected",
                    badges=(
                        "ROUTE ARTWORK · REBUILD",
                        "ROUTE PREVIEW · REBUILD",
                    ),
                ),
            }

        elif scenario_id == "scenario_a":
            panels = {
                "left": _panel(
                    css_class="panel-affected",
                    badges=(
                        "PREVIEW · REBUILD",
                        "ARTWORK · PRESERVE",
                    ),
                ),
                "right": _panel(
                    css_class="panel-affected",
                    badges=(
                        "PREVIEW · REBUILD",
                        "ARTWORK · PRESERVE",
                    ),
                ),
            }

        else:
            panels = {
                "left": _panel(
                    css_class="panel-preserved",
                    badges=(
                        "ENDING A · HEALTHY",
                    ),
                ),
                "right": _panel(
                    css_class="panel-affected-danger",
                    badges=(
                        "ENDING B · VERIFY",
                    ),
                ),
            }

        return {
            "stage": "DIAGNOSE + PLAN",
            "stage_number": "02–03",
            "title": "Minimum safe rebuild",
            "detail": (
                "Only media reached through changed dependencies "
                "enters the plan."
            ),
            "active_stage": None,
            "panels": panels,
            "show_lineage": proof_mode,
            "show_sponsor_strip": proof_mode,
            "compact_shell": not proof_mode,
            "why": why,
            "context_bar": {
                "label": "PLAN",
                "value": (
                    "2 rebuild · 4 preserve"
                    if scenario_id == "scenario_b"
                    else (
                        "4 rebuild · 2 preserve"
                        if scenario_id == "scenario_a"
                        else "Verify every required object"
                    )
                ),
                "detail": (
                    "Execution remains locked until creator approval."
                ),
                "tone": "planned",
            },
        }

    if phase == COMPLETE:
        if scenario_id == "scenario_b":
            panels = {
                "left": _panel(
                    css_class="panel-verified",
                    badges=(
                        "PRESERVED · VERIFIED",
                    ),
                ),
                "right": _panel(
                    css_class="panel-verified",
                    badges=(
                        "REBUILT · VERIFIED",
                    ),
                ),
            }

        elif scenario_id == "scenario_a":
            panels = {
                "left": _panel(
                    css_class="panel-verified",
                    badges=(
                        "ROUTE VERIFIED",
                    ),
                ),
                "right": _panel(
                    css_class="panel-verified",
                    badges=(
                        "ROUTE VERIFIED",
                    ),
                ),
            }

        else:
            panels = {
                "left": _panel(
                    css_class="panel-verified",
                    badges=(
                        "REQUIRED OBJECTS VERIFIED",
                    ),
                ),
                "right": _panel(
                    css_class="panel-blocked-focus",
                    badges=(
                        "MISSING · preview.ending_b",
                    ),
                ),
            }

        return {
            "stage": "VERIFY + RECORD",
            "stage_number": "05–06",
            "title": (
                "Release verified"
                if scenario_id != "scenario_c"
                else "Unsafe branch contained"
            ),
            "detail": (
                "The changed state is proven by remote objects, "
                "route checks, and an auditable release record."
            ),
            "active_stage": None,
            "panels": panels,
            "show_lineage": True,
            "show_sponsor_strip": True,
            "compact_shell": False,
            "why": why,
            "context_bar": {
                "label": "VERIFIED",
                "value": (
                    "SAFE TO PUBLISH"
                    if scenario_id != "scenario_c"
                    else "ENDING B BLOCKED"
                ),
                "detail": (
                    "6 / 6 objects · 2 / 2 routes · 0 stale"
                    if scenario_id != "scenario_c"
                    else "Healthy route preserved · unsafe route stopped"
                ),
                "tone": (
                    "verified"
                    if scenario_id != "scenario_c"
                    else "blocked"
                ),
            },
        }

    raise ValueError(
        f"Unsupported focus phase: {phase}"
    )
