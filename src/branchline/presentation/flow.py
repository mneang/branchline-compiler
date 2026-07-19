"""Minimal judge-facing interaction flow for Branchline."""

from __future__ import annotations

from typing import Any


READY = "ready"
PLANNED = "planned"
COMPLETE = "complete"

VALID_PHASES = {
    READY,
    PLANNED,
    COMPLETE,
}


def next_phase(
    scenario_id: str,
    phase: str,
) -> str:
    """Advance the smallest useful interaction sequence."""
    if phase not in VALID_PHASES:
        raise ValueError(f"Unknown phase: {phase}")

    if phase == READY:
        # Publication safety checks do not require an approval step.
        return (
            COMPLETE
            if scenario_id == "scenario_c"
            else PLANNED
        )

    if phase == PLANNED:
        return COMPLETE

    return READY


def primary_action_label(
    scenario_id: str,
    phase: str,
) -> str:
    """Return exactly one primary action for the current state."""
    if phase == READY:
        return (
            "Verify reachable media"
            if scenario_id == "scenario_c"
            else "Analyze impact"
        )

    if phase == PLANNED:
        return "Approve plan & replay verified release"

    return "Replay scenario"


def step_label(
    scenario_id: str,
    phase: str,
) -> str:
    """Provide concise progression without decorative steps."""
    if scenario_id == "scenario_c":
        return (
            "READY"
            if phase == READY
            else "VERIFIED"
        )

    labels = {
        READY: "1 OF 2 · CHANGE DETECTED",
        PLANNED: "2 OF 2 · PLAN READY",
        COMPLETE: "COMPLETED · RELEASE VERIFIED",
    }

    return labels[phase]


def phase_copy(
    scenario: dict[str, Any],
    phase: str,
) -> dict[str, str]:
    """Create focused copy for one scenario state."""
    blocked = (
        scenario["publication_status"]
        == "BLOCKED"
    )

    if phase == READY:
        return {
            "headline": scenario["title"],
            "supporting": scenario["trigger"],
        }

    if phase == PLANNED:
        rebuilt = len(
            scenario["rebuilt_assets"]
        )
        reused = len(
            scenario["reused_assets"]
        )

        return {
            "headline": (
                f"Rebuild {rebuilt}. Reuse {reused}."
            ),
            "supporting": (
                "Branchline isolated the smallest safe release plan. "
                "Unrelated media remains untouched in Backblaze B2."
            ),
        }

    return {
        "headline": (
            "Publication blocked"
            if blocked
            else "Release safe to publish"
        ),
        "supporting": (
            "The affected route failed remote verification while "
            "the healthy route remained intact."
            if blocked
            else
            "Every final B2 object and reachable story path "
            "was independently verified."
        ),
    }
