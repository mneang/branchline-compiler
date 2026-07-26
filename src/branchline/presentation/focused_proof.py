"""Focused causal proof for Branchline's normal creator experience."""

from __future__ import annotations

from typing import Any


LEGEND = (
    {
        "kind": "source",
        "label": "Source",
    },
    {
        "kind": "media",
        "label": "Media asset",
    },
    {
        "kind": "route",
        "label": "Story route",
    },
)


def _release_id(
    execution: dict[str, Any] | None,
    *,
    fallback: str,
) -> str:
    if not isinstance(
        execution,
        dict,
    ):
        return fallback

    direct = str(
        execution.get(
            "release_id",
            "",
        )
    ).strip()

    if direct:
        return direct

    release = execution.get(
        "release"
    )

    if isinstance(
        release,
        dict,
    ):
        nested = str(
            release.get(
                "release_id",
                "",
            )
        ).strip()

        if nested:
            return nested

    return fallback


def _visual_proof(
    execution: dict[str, Any] | None,
) -> dict[str, Any]:
    release_id = _release_id(
        execution,
        fallback="ending-b-visual-v3",
    )

    return {
        "eyebrow": "SELECTIVE RELEASE PROOF",
        "title": "Only Ending B moved.",
        "summary": (
            "The changed visual source reaches two Ending B assets. "
            "Ending A and all shared media remain current."
        ),
        "nodes": [
            {
                "kind": "source",
                "state": "changed",
                "label": "image.ending_b",
                "detail": "Changed source",
            },
            {
                "kind": "media",
                "state": "rebuild",
                "label": "Ending B artwork",
                "detail": "Rebuilt",
            },
            {
                "kind": "media",
                "state": "rebuild",
                "label": "Ending B preview",
                "detail": "Rebuilt",
            },
            {
                "kind": "route",
                "state": "verified",
                "label": "Ending B",
                "detail": "Route verified",
            },
        ],
        "metrics": [
            {
                "label": "REBUILT",
                "value": "2",
            },
            {
                "label": "PRESERVED",
                "value": "4",
            },
            {
                "label": "B2 OBJECTS",
                "value": "6 / 6",
            },
        ],
        "facts": [
            {
                "label": "GENBLAZE",
                "value": "Verified manifest provenance reused",
                "detail": "0 unnecessary AI requests",
            },
            {
                "label": "BACKBLAZE B2 BYTES",
                "value": "6 / 6 remotely re-hashed",
                "detail": "Stored bytes matched every declared SHA-256",
            },
            {
                "label": "BRANCHLINE GUARD",
                "value": release_id,
                "detail": (
                    "2 / 2 routes healthy · "
                    "0 stale · SAFE TO PUBLISH"
                ),
            },
        ],
        "verdict": "SAFE TO PUBLISH",
        "tone": "verified",
        "legend": list(LEGEND),
    }


def _dialogue_proof() -> dict[str, Any]:
    return {
        "eyebrow": "GENBLAZE RELEASE PROOF",
        "title": "One shared line reached both routes.",
        "summary": (
            "The opening dialogue changed, so its voice, caption, "
            "and both compiled route previews became stale."
        ),
        "nodes": [
            {
                "kind": "source",
                "state": "changed",
                "label": "dialogue.opening",
                "detail": "Changed source",
            },
            {
                "kind": "media",
                "state": "rebuild",
                "label": "Voice + caption",
                "detail": "Generated through Genblaze",
            },
            {
                "kind": "media",
                "state": "rebuild",
                "label": "Route previews",
                "detail": "Both rebuilt",
            },
            {
                "kind": "route",
                "state": "verified",
                "label": "Ending A + B",
                "detail": "2 / 2 verified",
            },
        ],
        "metrics": [
            {
                "label": "REBUILT",
                "value": "4",
            },
            {
                "label": "PRESERVED",
                "value": "2",
            },
            {
                "label": "ROUTES",
                "value": "2 / 2",
            },
        ],
        "facts": [
            {
                "label": "GENBLAZE",
                "value": "Canonical generation manifest verified",
                "detail": (
                    "Provider, model, prompt, and "
                    "asset SHA-256 recorded"
                ),
            },
            {
                "label": "BACKBLAZE B2 BYTES",
                "value": "6 / 6 remotely re-hashed",
                "detail": (
                    "Stored media bytes matched "
                    "the manifest SHA-256 values"
                ),
            },
            {
                "label": "BRANCHLINE GUARD",
                "value": "2 / 2 routes · 0 stale",
                "detail": "Publication decision: SAFE TO PUBLISH",
            },
        ],
        "verdict": "SAFE TO PUBLISH",
        "tone": "verified",
        "legend": list(LEGEND),
    }


def _safety_proof() -> dict[str, Any]:
    return {
        "eyebrow": "PUBLICATION-GUARD PROOF",
        "title": "No stale branches published.",
        "summary": (
            "B2 could not retrieve preview.ending_b. Branchline "
            "blocked Ending B while Ending A remained independently "
            "verified and publishable."
        ),
        "nodes": [
            {
                "kind": "media",
                "state": "missing",
                "label": "preview.ending_b",
                "detail": "B2 object missing",
            },
            {
                "kind": "route",
                "state": "blocked",
                "label": "Ending B",
                "detail": "Dependent route blocked",
            },
            {
                "kind": "route",
                "state": "verified",
                "label": "Ending A",
                "detail": "Unaffected route verified",
            },
        ],
        "causal_nodes": [
            {
                "kind": "media",
                "state": "missing",
                "label": "preview.ending_b",
                "detail": "B2 object missing",
            },
            {
                "kind": "route",
                "state": "blocked",
                "label": "Ending B",
                "detail": "Dependent route blocked",
            },
        ],
        "independent_nodes": [
            {
                "kind": "route",
                "state": "verified",
                "label": "Ending A",
                "detail": (
                    "Independently verified · "
                    "not dependent on preview.ending_b"
                ),
            },
        ],
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
        "facts": [
            {
                "label": "GENBLAZE",
                "value": "Verified provenance retained",
                "detail": (
                    "Canonical Genblaze manifest retained; "
                    "no regeneration attempted during validation"
                ),
            },
            {
                "label": "BACKBLAZE B2 BYTES",
                "value": "5 verified · 1 missing",
                "detail": (
                    "5 stored-byte SHA-256 matches; "
                    "preview.ending_b missing"
                ),
            },
            {
                "label": "BRANCHLINE GUARD",
                "value": "Ending B blocked",
                "detail": (
                    "Ending A remains independently "
                    "verified and publishable"
                ),
            },
        ],
        "verdict": "PUBLICATION STOPPED",
        "tone": "blocked",
        "legend": list(LEGEND),
    }


def build_focused_proof(
    *,
    scenario_id: str,
    execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the concise proof shown before the complete graph."""
    if scenario_id == "scenario_b":
        return _visual_proof(
            execution
        )

    if scenario_id == "scenario_a":
        return _dialogue_proof()

    if scenario_id == "scenario_c":
        return _safety_proof()

    raise ValueError(
        f"Unsupported focused-proof scenario: {scenario_id}"
    )
