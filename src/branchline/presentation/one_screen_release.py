"""One-screen creator commands for Branchline's manga release room."""

from __future__ import annotations

from typing import Any

from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
)


WORKFLOWS: tuple[dict[str, str], ...] = (
    {
        "id": "scenario_a",
        "label": "Dialogue revision",
        "icon": "graphic_eq",
        "description": (
            "Refresh shared voice and captions."
        ),
    },
    {
        "id": "scenario_b",
        "label": "Visual revision",
        "icon": "palette",
        "description": (
            "Rebuild one changed branch visual."
        ),
    },
    {
        "id": "scenario_c",
        "label": "Safety check",
        "icon": "shield",
        "description": (
            "Stop a branch with missing media."
        ),
    },
)


def workflow_options() -> list[dict[str, str]]:
    """Return the three genuine Branchline creator workflows."""
    return [
        dict(item)
        for item in WORKFLOWS
    ]


def _analysis_counts(
    analysis: dict[str, Any] | None,
    *,
    rebuilt_default: int,
    reused_default: int,
) -> tuple[int, int]:
    if analysis is None:
        return (
            rebuilt_default,
            reused_default,
        )

    metrics = analysis.get(
        "metrics",
        {},
    )

    if not isinstance(metrics, dict):
        metrics = {}

    rebuilt = metrics.get(
        "assets_to_rebuild",
        metrics.get(
            "assets_rebuilt",
            rebuilt_default,
        ),
    )

    reused = metrics.get(
        "assets_to_reuse",
        metrics.get(
            "assets_reused",
            reused_default,
        ),
    )

    return (
        int(rebuilt),
        int(reused),
    )


def _execution_stage(
    active_stage: str | None,
) -> tuple[str, str]:
    stages = {
        "approval": (
            "Approval bound to the plan",
            "The creator authorized this exact selective rebuild.",
        ),
        "build": (
            "Rebuilding Ending B media",
            "Ending A and shared media remain untouched.",
        ),
        "manifest": (
            "Recording the new release",
            "The unique release manifest is being stored in B2.",
        ),
        "guard": (
            "Verifying every route",
            "All six objects are being retrieved and hashed.",
        ),
        "complete": (
            "Release verification complete",
            "Both reachable story routes passed.",
        ),
    }

    return stages.get(
        active_stage,
        (
            "Executing selective rebuild",
            "The previous healthy release remains untouched.",
        ),
    )


def _visual_revision_command(
    *,
    phase: str,
    busy: bool,
    active_stage: str | None,
    analysis: dict[str, Any] | None,
    execution: dict[str, Any] | None,
) -> dict[str, Any]:
    if busy:
        headline, detail = _execution_stage(
            active_stage
        )

        return {
            "step": "04 · ACT",
            "headline": headline,
            "detail": detail,
            "metrics": [],
            "explanation": None,
            "lineage": None,
            "sponsor_line": None,
            "primary_label": "Executing selective rebuild…",
            "primary_kind": "disabled",
            "tone": "working",
            "verdict": None,
        }

    if phase == READY:
        return {
            "step": "01 · OBSERVE",
            "headline": "Ending B artwork changed.",
            "detail": (
                "Trace which generated media is now stale."
            ),
            "metrics": [],
            "explanation": (
                "Warm evening platform → illuminated night platform"
            ),
            "lineage": None,
            "sponsor_line": None,
            "primary_label": "Analyze impact",
            "primary_kind": "advance",
            "tone": "observe",
            "verdict": None,
        }

    if phase == PLANNED:
        rebuilt, reused = _analysis_counts(
            analysis,
            rebuilt_default=2,
            reused_default=4,
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

        return {
            "step": "02–03 · DIAGNOSE + PLAN",
            "headline": (
                f"Rebuild {rebuilt}. Preserve {reused}."
            ),
            "detail": (
                "Only Ending B depends on the changed image."
            ),
            "metrics": [
                {
                    "label": "REBUILD",
                    "value": str(rebuilt),
                },
                {
                    "label": "PRESERVE",
                    "value": str(reused),
                },
                {
                    "label": "REUSE",
                    "value": f"{reuse_rate:.1f}%",
                },
            ],
            "explanation": (
                "Ending B artwork and preview rebuild. "
                "The shared voice, caption, and Ending A "
                "remain current."
            ),
            "lineage": None,
            "sponsor_line": None,
            "primary_label": (
                f"Approve {rebuilt}-asset rebuild"
            ),
            "primary_kind": "advance",
            "tone": "planned",
            "verdict": None,
        }

    if phase == COMPLETE:
        release_id = "verified release"

        if execution is not None:
            release_id = str(
                execution.get(
                    "release_id",
                    release_id,
                )
            )

        return {
            "step": "05–06 · VERIFY + RECORD",
            "headline": "Both endings are current.",
            "detail": (
                "Ending B was rebuilt while Ending A "
                "remained byte-identical."
            ),
            "metrics": [
                {
                    "label": "OBJECTS",
                    "value": "6 / 6",
                },
                {
                    "label": "ROUTES",
                    "value": "2 / 2",
                },
                {
                    "label": "STALE",
                    "value": "0",
                },
            ],
            "explanation": None,
            "lineage": (
                "shared-dialogue-v2 → "
                "4 reused + 2 rebuilt → "
                f"{release_id}"
            ),
            "sponsor_line": (
                "Genblaze provenance reused · "
                "Backblaze B2 remotely verified · "
                "Publication guard passed"
            ),
            "primary_label": "Play verified release",
            "primary_kind": "media",
            "tone": "verified",
            "verdict": "SAFE TO PUBLISH",
        }

    raise ValueError(
        f"Unsupported visual-revision phase: {phase}"
    )


def _dialogue_revision_command(
    *,
    phase: str,
    busy: bool,
    active_stage: str | None,
) -> dict[str, Any]:
    if busy:
        headline, detail = _execution_stage(
            active_stage
        )

        return {
            "step": "04 · ACT",
            "headline": headline,
            "detail": detail,
            "metrics": [],
            "explanation": None,
            "lineage": None,
            "sponsor_line": None,
            "primary_label": "Verifying release evidence…",
            "primary_kind": "disabled",
            "tone": "working",
            "verdict": None,
        }

    if phase == READY:
        return {
            "step": "01 · OBSERVE",
            "headline": "The shared opening line changed.",
            "detail": (
                "Trace every voice, caption, and preview "
                "that contains the old dialogue."
            ),
            "metrics": [],
            "explanation": (
                "“The last train leaves at seven.” "
                "→ “The last train leaves at eight.”"
            ),
            "lineage": None,
            "sponsor_line": None,
            "primary_label": "Analyze impact",
            "primary_kind": "advance",
            "tone": "observe",
            "verdict": None,
        }

    if phase == PLANNED:
        return {
            "step": "02–03 · DIAGNOSE + PLAN",
            "headline": "Rebuild 4. Preserve 2.",
            "detail": (
                "Shared dialogue reaches both story routes."
            ),
            "metrics": [
                {
                    "label": "REBUILD",
                    "value": "4",
                },
                {
                    "label": "PRESERVE",
                    "value": "2",
                },
                {
                    "label": "GENBLAZE",
                    "value": "1 RUN",
                },
            ],
            "explanation": (
                "Voice, caption, and both previews rebuild. "
                "Both branch artworks remain current."
            ),
            "lineage": None,
            "sponsor_line": None,
            "primary_label": "Approve & rebuild 4 assets",
            "primary_kind": "advance",
            "tone": "planned",
            "verdict": None,
        }

    if phase == COMPLETE:
        return {
            "step": "05–06 · VERIFY + RECORD",
            "headline": "Both routes use the new dialogue.",
            "detail": (
                "Genblaze provenance and every remote object verify."
            ),
            "metrics": [
                {
                    "label": "OBJECTS",
                    "value": "6 / 6",
                },
                {
                    "label": "ROUTES",
                    "value": "2 / 2",
                },
                {
                    "label": "STALE",
                    "value": "0",
                },
            ],
            "explanation": None,
            "lineage": (
                "baseline-v1 → "
                "2 reused + 4 rebuilt → "
                "shared-dialogue-v2"
            ),
            "sponsor_line": (
                "Genblaze generation verified · "
                "Backblaze B2 remotely verified · "
                "Publication guard passed"
            ),
            "primary_label": "Play verified release",
            "primary_kind": "media",
            "tone": "verified",
            "verdict": "SAFE TO PUBLISH",
        }

    raise ValueError(
        f"Unsupported dialogue-revision phase: {phase}"
    )


def _safety_command(
    *,
    phase: str,
    busy: bool,
) -> dict[str, Any]:
    if busy:
        return {
            "step": "04 · ACT",
            "headline": "Checking required B2 media.",
            "detail": (
                "Every reachable route is being verified independently."
            ),
            "metrics": [],
            "explanation": None,
            "lineage": None,
            "sponsor_line": None,
            "primary_label": "Verifying candidate release…",
            "primary_kind": "disabled",
            "tone": "working-danger",
            "verdict": None,
        }

    if phase == READY:
        return {
            "step": "01 · OBSERVE",
            "headline": "One branch preview may be missing.",
            "detail": (
                "Verify the candidate before any route publishes."
            ),
            "metrics": [],
            "explanation": (
                "Candidate release references preview.ending_b."
            ),
            "lineage": None,
            "sponsor_line": None,
            "primary_label": "Run safety check",
            "primary_kind": "advance",
            "tone": "observe-danger",
            "verdict": None,
        }

    if phase == PLANNED:
        return {
            "step": "02–03 · DIAGNOSE + PLAN",
            "headline": "Verify every required object.",
            "detail": (
                "Publication remains locked until route health is known."
            ),
            "metrics": [
                {
                    "label": "OBJECTS",
                    "value": "6",
                },
                {
                    "label": "ROUTES",
                    "value": "2",
                },
                {
                    "label": "DECISION",
                    "value": "PENDING",
                },
            ],
            "explanation": (
                "Ending A and Ending B are evaluated separately, "
                "so one failure cannot hide inside a global status."
            ),
            "lineage": None,
            "sponsor_line": None,
            "primary_label": "Verify candidate",
            "primary_kind": "advance",
            "tone": "planned-danger",
            "verdict": None,
        }

    if phase == COMPLETE:
        return {
            "step": "05–06 · VERIFY + RECORD",
            "headline": "Ending B is locked.",
            "detail": (
                "Ending A remains publishable and remotely verified."
            ),
            "metrics": [
                {
                    "label": "VERIFIED",
                    "value": "5",
                },
                {
                    "label": "MISSING",
                    "value": "1",
                },
                {
                    "label": "SAFE ROUTES",
                    "value": "1",
                },
            ],
            "explanation": (
                "preview.ending_b could not be retrieved, "
                "so only the dependent route is blocked."
            ),
            "lineage": (
                "preview.ending_b missing → "
                "Ending B blocked"
            ),
            "sponsor_line": (
                "Genblaze provenance retained · "
                "Backblaze B2 isolated the missing object · "
                "Publication guard stopped Ending B"
            ),
            "primary_label": "Inspect failure evidence",
            "primary_kind": "proof",
            "tone": "blocked",
            "verdict": "PUBLICATION STOPPED",
        }

    raise ValueError(
        f"Unsupported safety phase: {phase}"
    )


def build_one_screen_command(
    *,
    scenario_id: str,
    phase: str,
    busy: bool,
    active_stage: str | None = None,
    analysis: dict[str, Any] | None = None,
    execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one clear command bar for the current release phase."""
    if scenario_id == "scenario_b":
        return _visual_revision_command(
            phase=phase,
            busy=busy,
            active_stage=active_stage,
            analysis=analysis,
            execution=execution,
        )

    if scenario_id == "scenario_a":
        return _dialogue_revision_command(
            phase=phase,
            busy=busy,
            active_stage=active_stage,
        )

    if scenario_id == "scenario_c":
        return _safety_command(
            phase=phase,
            busy=busy,
        )

    raise ValueError(
        f"Unsupported one-screen scenario: {scenario_id}"
    )
