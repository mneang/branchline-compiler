"""Director's Cut presentation model for Branchline's creator workflow."""

from __future__ import annotations

from typing import Any

from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
)


AUDIENCE = (
    "FOR VISUAL NOVEL & INTERACTIVE COMIC TEAMS"
)

STAGE_LABELS = (
    "CHANGE",
    "DIAGNOSE",
    "PLAN",
    "APPROVE",
    "VERIFY",
    "PUBLISH",
)


CHANGE_RECEIPTS: dict[
    str,
    dict[str, str],
] = {
    "scenario_b": {
        "eyebrow": "ENDING B VISUAL CHANGE",
        "subject": "Ending B artwork",
        "before_label": "BEFORE",
        "before": (
            "Remain beneath the station lights"
        ),
        "after_label": "VERIFIED",
        "after": (
            "Cross the illuminated night platform"
        ),
        "impact": (
            "2 rebuild · 4 preserve · "
            "Ending A remains byte-identical"
        ),
    },
    "scenario_a": {
        "eyebrow": "SHARED DIALOGUE CHANGE",
        "subject": "dialogue.opening",
        "before_label": "BEFORE",
        "before": (
            "“The last train leaves at seven.”"
        ),
        "after_label": "VERIFIED",
        "after": (
            "“The last train leaves at eight.”"
        ),
        "impact": (
            "4 rebuild · 2 preserve · "
            "1 linked Genblaze run"
        ),
    },
    "scenario_c": {
        "eyebrow": "RELEASE CANDIDATE CHECK",
        "subject": "Ending B route",
        "before_label": "REQUIRED",
        "before": "6 B2 objects",
        "after_label": "OBSERVED",
        "after": (
            "preview.ending_b unavailable"
        ),
        "impact": (
            "Verify both routes independently "
            "before publication"
        ),
    },
}



NEXT_WORKFLOW_ACTIONS: dict[
    str,
    dict[str, str],
] = {
    "scenario_a": {
        "label": (
            "Next: See selective B2 reuse"
        ),
        "scenario_id": "scenario_b",
        "detail": (
            "Change only Ending B and preserve "
            "every unaffected verified object"
        ),
    },
    "scenario_b": {
        "label": (
            "Next: Test publication safety"
        ),
        "scenario_id": "scenario_c",
        "detail": (
            "Remove one required B2 object and "
            "verify fault isolation"
        ),
    },
}


def build_change_receipt(
    scenario_id: str,
) -> dict[str, str]:
    """Describe the exact creator-visible change."""
    try:
        return dict(
            CHANGE_RECEIPTS[
                scenario_id
            ]
        )
    except KeyError as exc:
        raise ValueError(
            "Unsupported Director's Cut scenario: "
            f"{scenario_id}"
        ) from exc


def _stage_statuses(
    *,
    scenario_id: str,
    phase: str,
    busy: bool,
    active_stage: str | None,
) -> tuple[str, ...]:
    """Return one semantic state for every release stage."""
    if phase == COMPLETE:
        if scenario_id == "scenario_c":
            return (
                "done",
                "done",
                "done",
                "skipped",
                "done",
                "blocked",
            )

        return (
            "done",
            "done",
            "done",
            "done",
            "done",
            "done",
        )

    if busy:
        active = (
            active_stage
            or ""
        ).lower()

        publish_active = any(
            token in active
            for token in (
                "publish",
                "record",
                "release",
            )
        )

        verify_active = any(
            token in active
            for token in (
                "verify",
                "remote",
                "hash",
                "guard",
                "manifest",
                "object",
                "route",
            )
        )

        if publish_active:
            return (
                "done",
                "done",
                "done",
                "done",
                "done",
                "active",
            )

        if verify_active:
            return (
                "done",
                "done",
                "done",
                "done",
                "active",
                "pending",
            )

        return (
            "done",
            "done",
            "done",
            "active",
            "pending",
            "pending",
        )

    if phase == PLANNED:
        return (
            "done",
            "done",
            "done",
            "active",
            "pending",
            "pending",
        )

    if phase == READY:
        return (
            "active",
            "pending",
            "pending",
            "pending",
            "pending",
            "pending",
        )

    raise ValueError(
        f"Unsupported release phase: {phase}"
    )


def build_release_rail(
    *,
    scenario_id: str,
    phase: str,
    busy: bool,
    active_stage: str | None = None,
) -> list[dict[str, str]]:
    """Build the six-step creator release progression."""
    statuses = _stage_statuses(
        scenario_id=scenario_id,
        phase=phase,
        busy=busy,
        active_stage=active_stage,
    )

    return [
        {
            "label": label,
            "status": status,
        }
        for label, status in zip(
            STAGE_LABELS,
            statuses,
            strict=True,
        )
    ]


def build_proof_cells(
    *,
    scenario_id: str,
    phase: str,
    busy: bool,
) -> list[dict[str, str]]:
    """Assign visible proof to Genblaze, B2, and Branchline."""
    if busy:
        return [
            {
                "label": "GENBLAZE",
                "value": "Execution active",
                "detail": (
                    "Provider and manifest evidence "
                    "are being recorded"
                ),
                "tone": "working",
            },
            {
                "label": "B2 BYTES",
                "value": "Verification active",
                "detail": (
                    "Remote objects are being "
                    "retrieved and hashed"
                ),
                "tone": "working",
            },
            {
                "label": "BRANCHLINE GUARD",
                "value": "Decision pending",
                "detail": (
                    "No route publishes before "
                    "verification completes"
                ),
                "tone": "working",
            },
        ]

    if phase != COMPLETE:
        return [
            {
                "label": "GENBLAZE",
                "value": "Plan pending",
                "detail": (
                    "Generation work is calculated "
                    "before execution"
                ),
                "tone": "pending",
            },
            {
                "label": "B2 BYTES",
                "value": "Reuse pending",
                "detail": (
                    "Verified objects remain eligible "
                    "for preservation"
                ),
                "tone": "pending",
            },
            {
                "label": "BRANCHLINE GUARD",
                "value": "Publication locked",
                "detail": (
                    "The release decision remains "
                    "unresolved"
                ),
                "tone": "pending",
            },
        ]

    if scenario_id == "scenario_a":
        return [
            {
                "label": "GENBLAZE",
                "value": "1 linked run",
                "detail": (
                    "Canonical Gemini TTS generation "
                    "lineage verified"
                ),
                "tone": "verified",
            },
            {
                "label": "B2 BYTES",
                "value": "6 / 6 matches",
                "detail": (
                    "Every stored object matched its "
                    "declared SHA-256"
                ),
                "tone": "verified",
            },
            {
                "label": "BRANCHLINE GUARD",
                "value": "2 / 2 routes safe",
                "detail": (
                    "0 stale assets · safe to publish"
                ),
                "tone": "verified",
            },
        ]

    if scenario_id == "scenario_b":
        return [
            {
                "label": "GENBLAZE",
                "value": "0 new AI requests",
                "detail": (
                    "Verified generation provenance "
                    "was reused"
                ),
                "tone": "verified",
            },
            {
                "label": "B2 BYTES",
                "value": "6 / 6 matches",
                "detail": (
                    "Rebuilt and preserved objects "
                    "were remotely re-hashed"
                ),
                "tone": "verified",
            },
            {
                "label": "BRANCHLINE GUARD",
                "value": "2 / 2 routes · 0 stale",
                "detail": (
                    "Only Ending B moved"
                ),
                "tone": "verified",
            },
        ]

    if scenario_id == "scenario_c":
        return [
            {
                "label": "GENBLAZE",
                "value": "Provenance retained",
                "detail": (
                    "No regeneration was attempted "
                    "during validation"
                ),
                "tone": "verified",
            },
            {
                "label": "B2 BYTES",
                "value": "5 matches · 1 missing",
                "detail": (
                    "preview.ending_b could not "
                    "be retrieved"
                ),
                "tone": "blocked",
            },
            {
                "label": "BRANCHLINE GUARD",
                "value": "Ending B blocked",
                "detail": (
                    "Ending A remains independently "
                    "verified"
                ),
                "tone": "blocked",
            },
        ]

    raise ValueError(
        "Unsupported Director's Cut scenario: "
        f"{scenario_id}"
    )



def next_workflow_action(
    *,
    scenario_id: str,
    phase: str,
) -> dict[str, str] | None:
    """Guide a user through Branchline's three proof stories."""
    if phase != COMPLETE:
        return None

    action = NEXT_WORKFLOW_ACTIONS.get(
        scenario_id
    )

    return (
        dict(action)
        if action is not None
        else None
    )


def replay_action(
    phase: str,
) -> dict[str, str] | None:
    """Expose the existing COMPLETE → READY reset as a replay action."""
    if phase != COMPLETE:
        return None

    return {
        "label": "Replay workflow",
        "kind": "replay",
        "detail": (
            "Return to the original change request "
            "and run the release flow again"
        ),
    }


def build_director_cut(
    *,
    scenario_id: str,
    phase: str,
    busy: bool,
    active_stage: str | None = None,
) -> dict[str, Any]:
    """Build all Director's Cut creator-facing presentation data."""
    return {
        "audience": AUDIENCE,
        "change": build_change_receipt(
            scenario_id
        ),
        "rail": build_release_rail(
            scenario_id=scenario_id,
            phase=phase,
            busy=busy,
            active_stage=active_stage,
        ),
        "proof_cells": build_proof_cells(
            scenario_id=scenario_id,
            phase=phase,
            busy=busy,
        ),
        "next_workflow": next_workflow_action(
            scenario_id=scenario_id,
            phase=phase,
        ),
        "replay": replay_action(
            phase
        ),
    }
