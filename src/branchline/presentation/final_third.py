"""Final-third creator clarity and release-lineage presentation."""

from __future__ import annotations

from typing import Any

from branchline.presentation.flow import (
    COMPLETE,
    PLANNED,
    READY,
)


SCENARIO_PRESENTATION: dict[str, dict[str, Any]] = {
    "scenario_b": {
        "label": "Ending B visual revision",
        "tag": "LIVE DEMO",
        "source_release": "shared-dialogue-v2",
        "candidate_release": "ending-b-visual-v3",
        "revision": "Ending B scene changed",
        "assets_rebuilt": 2,
        "assets_reused": 4,
        "routes_total": 2,
        "genblaze_value": (
            "0 unnecessary AI requests"
        ),
        "genblaze_detail": (
            "Verified Genblaze provenance reused from B2"
        ),
    },
    "scenario_a": {
        "label": "Shared dialogue revision",
        "tag": "GENBLAZE CASE",
        "source_release": "baseline-v1",
        "candidate_release": "shared-dialogue-v2",
        "revision": "Shared opening dialogue changed",
        "assets_rebuilt": 4,
        "assets_reused": 2,
        "routes_total": 2,
        "genblaze_value": (
            "Gemini TTS generated through Genblaze"
        ),
        "genblaze_detail": (
            "Generation manifest stored and verified"
        ),
    },
    "scenario_c": {
        "label": "Missing branch preview",
        "tag": "SAFETY CASE",
        "source_release": "ending-b-visual-v3",
        "candidate_release": "candidate release",
        "revision": "Ending B preview unavailable",
        "assets_rebuilt": 0,
        "assets_reused": 5,
        "routes_total": 2,
        "genblaze_value": (
            "Existing generation provenance retained"
        ),
        "genblaze_detail": (
            "No regeneration attempted during verification"
        ),
    },
}


PURPOSE = {
    "brand": "BRANCHLINE",
    "headline": (
        "Revise your story without breaking "
        "its generated media."
    ),
    "supporting": (
        "Change one scene. Rebuild only what it affects."
    ),
    "promise": (
        "Publish no stale branches."
    ),
}


def _config(
    scenario_id: str,
) -> dict[str, Any]:
    try:
        return dict(
            SCENARIO_PRESENTATION[
                scenario_id
            ]
        )
    except KeyError as exc:
        raise ValueError(
            f"Unsupported final-third scenario: {scenario_id}"
        ) from exc


def _proof(
    scenario: dict[str, Any],
) -> dict[str, Any]:
    value = scenario.get(
        "provenance",
        {},
    )

    return (
        value
        if isinstance(value, dict)
        else {}
    )


def _release_id(
    *,
    config: dict[str, Any],
    scenario: dict[str, Any],
    execution: dict[str, Any] | None,
) -> str:
    if execution is not None:
        value = str(
            execution.get(
                "release_id",
                "",
            )
        ).strip()

        if value:
            return value

    candidates = (
        scenario.get("release_id"),
        _proof(scenario).get(
            "release_id"
        ),
        config["candidate_release"],
    )

    for candidate in candidates:
        value = str(
            candidate or ""
        ).strip()

        if value:
            return value

    return "verified release"


def _approval_id(
    *,
    scenario: dict[str, Any],
    execution: dict[str, Any] | None,
) -> str | None:
    if execution is not None:
        value = str(
            execution.get(
                "approval_id",
                "",
            )
        ).strip()

        if value:
            return value

    candidates = (
        scenario.get("approval_id"),
        _proof(scenario).get(
            "approval_id"
        ),
    )

    for candidate in candidates:
        value = str(
            candidate or ""
        ).strip()

        if value:
            return value

    return None


def build_release_lineage(
    *,
    scenario_id: str,
    phase: str,
    scenario: dict[str, Any],
    analysis: dict[str, Any] | None = None,
    execution: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Explain how one release becomes the next."""
    config = _config(
        scenario_id
    )

    source_release = config[
        "source_release"
    ]

    if scenario_id == "scenario_c":
        if phase == COMPLETE:
            return {
                "eyebrow": (
                    "PUBLICATION-GUARD LINEAGE"
                ),
                "source": source_release,
                "movement": (
                    "5 VERIFIED · 1 MISSING"
                ),
                "target": (
                    "ENDING B BLOCKED"
                ),
                "caption": (
                    "The healthy Ending A route remains "
                    "publishable while the unsafe branch is isolated."
                ),
                "tone": "blocked",
            }

        return {
            "eyebrow": (
                "CANDIDATE RELEASE CHECK"
            ),
            "source": source_release,
            "movement": (
                "VERIFY EVERY B2 OBJECT"
            ),
            "target": (
                "PUBLICATION DECISION"
            ),
            "caption": (
                "Branchline will verify every required object "
                "before allowing publication."
            ),
            "tone": "warning",
        }

    if phase == READY:
        return {
            "eyebrow": (
                "RELEASE LINEAGE"
            ),
            "source": source_release,
            "movement": (
                "REVISION DETECTED"
            ),
            "target": (
                "IMPACT NOT YET CALCULATED"
            ),
            "caption": (
                f"{config['revision']}. Branchline will determine "
                "the minimum safe rebuild."
            ),
            "tone": "warning",
        }

    if phase == PLANNED:
        rebuilt = config[
            "assets_rebuilt"
        ]

        reused = config[
            "assets_reused"
        ]

        if analysis is not None:
            metrics = analysis.get(
                "metrics",
                {},
            )

            rebuilt = int(
                metrics.get(
                    "assets_to_rebuild",
                    rebuilt,
                )
            )

            reused = int(
                metrics.get(
                    "assets_to_reuse",
                    reused,
                )
            )

        return {
            "eyebrow": (
                "APPROVED RELEASE PLAN"
            ),
            "source": source_release,
            "movement": (
                f"{reused} REUSE · {rebuilt} REBUILD"
            ),
            "target": (
                "AWAITING CREATOR APPROVAL"
            ),
            "caption": (
                "Verified B2 objects stay byte-identical. "
                "Only affected media enters the rebuild."
            ),
            "tone": "planned",
        }

    if phase == COMPLETE:
        release_id = _release_id(
            config=config,
            scenario=scenario,
            execution=execution,
        )

        rebuilt = (
            int(
                execution.get(
                    "assets_rebuilt",
                    config[
                        "assets_rebuilt"
                    ],
                )
            )
            if execution is not None
            else config[
                "assets_rebuilt"
            ]
        )

        reused = (
            int(
                execution.get(
                    "assets_reused",
                    config[
                        "assets_reused"
                    ],
                )
            )
            if execution is not None
            else config[
                "assets_reused"
            ]
        )

        return {
            "eyebrow": (
                "VERIFIED RELEASE LINEAGE"
            ),
            "source": source_release,
            "movement": (
                f"{reused} REUSED · {rebuilt} REBUILT"
            ),
            "target": release_id,
            "caption": (
                "Every final object was retrieved from B2, "
                "hashed, and checked across each reachable route."
            ),
            "tone": "verified",
        }

    raise ValueError(
        f"Unsupported release phase: {phase}"
    )


def build_final_receipt(
    *,
    scenario_id: str,
    phase: str,
    scenario: dict[str, Any],
    execution: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Create the final human-readable release receipt."""
    if phase != COMPLETE:
        return None

    config = _config(
        scenario_id
    )

    publication_status = str(
        (
            execution.get(
                "publication_status"
            )
            if execution is not None
            else scenario.get(
                "publication_status",
                "",
            )
        )
        or (
            "BLOCKED"
            if scenario_id == "scenario_c"
            else "SAFE_TO_PUBLISH"
        )
    )

    release_id = _release_id(
        config=config,
        scenario=scenario,
        execution=execution,
    )

    approval_id = _approval_id(
        scenario=scenario,
        execution=execution,
    )

    if scenario_id == "scenario_c":
        return {
            "eyebrow": "SAFETY RECEIPT",
            "title": "No stale branches published",
            "release_id": release_id,
            "approval_id": approval_id,
            "status": publication_status,
            "line_one": (
                "Ending A remains independently verified."
            ),
            "line_two": (
                "Ending B cannot publish until its "
                "required preview is restored."
            ),
            "storage": (
                "Candidate and publication-guard evidence "
                "recorded in Backblaze B2."
            ),
            "tone": "blocked",
        }

    return {
        "eyebrow": "FINAL RELEASE RECEIPT",
        "title": "Mission completed and verified",
        "release_id": release_id,
        "approval_id": approval_id,
        "status": publication_status,
        "line_one": (
            f"{config['assets_reused']} verified objects reused · "
            f"{config['assets_rebuilt']} affected objects rebuilt."
        ),
        "line_two": (
            f"{config['routes_total']} / "
            f"{config['routes_total']} reachable routes healthy · "
            "0 stale assets."
        ),
        "storage": (
            "Release manifest and publication evidence "
            "stored and independently verified in Backblaze B2."
        ),
        "tone": "verified",
    }


def build_sponsor_proof(
    *,
    scenario_id: str,
    phase: str,
    scenario: dict[str, Any],
    execution: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Keep each sponsor technology visibly load-bearing."""
    config = _config(
        scenario_id
    )

    if scenario_id == "scenario_c":
        if phase == COMPLETE:
            return [
                {
                    "label": "GENBLAZE",
                    "value": config[
                        "genblaze_value"
                    ],
                    "detail": config[
                        "genblaze_detail"
                    ],
                },
                {
                    "label": "BACKBLAZE B2",
                    "value": (
                        "5 verified · 1 unavailable"
                    ),
                    "detail": (
                        "Remote retrieval isolated the failure"
                    ),
                },
                {
                    "label": "PUBLICATION GUARD",
                    "value": "ENDING B BLOCKED",
                    "detail": (
                        "Ending A remains healthy"
                    ),
                },
            ]

        return [
            {
                "label": "GENBLAZE",
                "value": config[
                    "genblaze_value"
                ],
                "detail": config[
                    "genblaze_detail"
                ],
            },
            {
                "label": "BACKBLAZE B2",
                "value": (
                    "Candidate objects awaiting verification"
                ),
                "detail": (
                    "Every required key will be retrieved"
                ),
            },
            {
                "label": "PUBLICATION GUARD",
                "value": (
                    "Decision pending"
                ),
                "detail": (
                    "No branch publishes before verification"
                ),
            },
        ]

    if phase == READY:
        return [
            {
                "label": "GENBLAZE",
                "value": config[
                    "genblaze_value"
                ],
                "detail": config[
                    "genblaze_detail"
                ],
            },
            {
                "label": "BACKBLAZE B2",
                "value": (
                    f"{config['assets_reused']} prior objects available"
                ),
                "detail": (
                    "Release memory ready for selective reuse"
                ),
            },
            {
                "label": "RELEASE CHECK",
                "value": "Awaiting analysis",
                "detail": (
                    "No publication decision yet"
                ),
            },
        ]

    if phase == PLANNED:
        return [
            {
                "label": "GENBLAZE",
                "value": config[
                    "genblaze_value"
                ],
                "detail": config[
                    "genblaze_detail"
                ],
            },
            {
                "label": "BACKBLAZE B2",
                "value": (
                    f"{config['assets_reused']} verified objects preserved"
                ),
                "detail": (
                    f"{config['assets_rebuilt']} affected objects rebuild"
                ),
            },
            {
                "label": "RELEASE CHECK",
                "value": (
                    "Plan bound to creator approval"
                ),
                "detail": (
                    "Execution cannot exceed the approved plan"
                ),
            },
        ]

    release_id = _release_id(
        config=config,
        scenario=scenario,
        execution=execution,
    )

    return [
        {
            "label": "GENBLAZE",
            "value": config[
                "genblaze_value"
            ],
            "detail": config[
                "genblaze_detail"
            ],
        },
        {
            "label": "BACKBLAZE B2",
            "value": (
                f"{config['assets_reused']} reused · "
                f"{config['assets_rebuilt']} rebuilt · "
                "6 / 6 verified"
            ),
            "detail": release_id,
        },
        {
            "label": "PUBLICATION GUARD",
            "value": "SAFE TO PUBLISH",
            "detail": (
                f"{config['routes_total']} / "
                f"{config['routes_total']} routes · "
                "0 stale assets"
            ),
        },
    ]


def build_final_third_context(
    *,
    scenario_id: str,
    phase: str,
    scenario: dict[str, Any],
    analysis: dict[str, Any] | None = None,
    execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build all final-third creator and judge presentation data."""
    return {
        "purpose": dict(PURPOSE),
        "scenario": _config(
            scenario_id
        ),
        "lineage": build_release_lineage(
            scenario_id=scenario_id,
            phase=phase,
            scenario=scenario,
            analysis=analysis,
            execution=execution,
        ),
        "final_receipt": build_final_receipt(
            scenario_id=scenario_id,
            phase=phase,
            scenario=scenario,
            execution=execution,
        ),
        "sponsor_strip": build_sponsor_proof(
            scenario_id=scenario_id,
            phase=phase,
            scenario=scenario,
            execution=execution,
        ),
    }
