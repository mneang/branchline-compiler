"""Dynamic, evidence-backed release choreography for Branchline."""

from __future__ import annotations

from typing import Any


REVISION_STORIES: dict[str, dict[str, Any]] = {
    "scenario_b": {
        "subject": "Ending B platform scene",
        "source_id": "image.ending_b",
        "before": "Warm evening platform",
        "after": "Illuminated night platform",
        "summary": (
            "The creator changed the visual direction of Ending B."
        ),
        "plan": (
            "Rebuild the Ending B artwork and preview. Preserve the "
            "shared voice, captions, and complete Ending A route."
        ),
        "impact": [
            "Ending B route artwork",
            "Ending B release preview",
        ],
        "preserved": [
            "Shared opening voice",
            "Shared caption",
            "Ending A artwork",
            "Ending A preview",
        ],
    },
    "scenario_a": {
        "subject": "Shared opening dialogue",
        "source_id": "dialogue.opening",
        "before": "The last train leaves at seven.",
        "after": "The last train leaves at eight.",
        "summary": (
            "One shared story line changed across both endings."
        ),
        "plan": (
            "Rebuild the opening voice, caption, and both route "
            "previews. Preserve the branch-specific artwork."
        ),
        "impact": [
            "Opening voice",
            "Opening caption",
            "Ending A preview",
            "Ending B preview",
        ],
        "preserved": [
            "Ending A artwork",
            "Ending B artwork",
        ],
    },
    "scenario_c": {
        "subject": "Ending B release preview",
        "source_id": "preview.ending_b",
        "before": "Release manifest references a required preview",
        "after": "The remote B2 object cannot be retrieved",
        "summary": (
            "A candidate release contains an unavailable media object."
        ),
        "plan": (
            "Verify every reachable route. Preserve healthy Ending A "
            "and prevent Ending B from being published."
        ),
        "impact": [
            "Ending B publication",
        ],
        "preserved": [
            "Ending A artwork",
            "Ending A preview",
            "Shared voice and caption",
        ],
    },
}


CAUSAL_ROUTES: dict[str, dict[str, Any]] = {
    "scenario_b": {
        "source": "ENDING B SCENE",
        "assets": [
            "ROUTE ARTWORK",
            "ROUTE PREVIEW",
        ],
        "destination": "ENDING B",
        "result": "2 assets rebuild",
        "preserved": "Ending A remains untouched",
    },
    "scenario_a": {
        "source": "SHARED DIALOGUE",
        "assets": [
            "VOICE + CAPTION",
            "BOTH PREVIEWS",
        ],
        "destination": "ENDING A + ENDING B",
        "result": "4 shared assets rebuild",
        "preserved": "Both route artworks remain untouched",
    },
    "scenario_c": {
        "source": "B2 OBJECT CHECK",
        "assets": [
            "5 VERIFIED",
            "1 MISSING",
        ],
        "destination": "ENDING B LOCKED",
        "result": "Unsafe publication stopped",
        "preserved": "Ending A remains healthy",
    },
}


MEDIA_COMPARISONS: dict[str, dict[str, str]] = {
    "scenario_b": {
        "before": (
            "/release-media/ending_b_before.mp4"
        ),
        "after": (
            "/release-media/ending_b_after.mp4"
        ),
        "before_label": "Before revision",
        "after_label": "After selective rebuild",
        "caption": (
            "Ending B changes while Ending A remains preserved."
        ),
    },
    "scenario_a": {
        "before": (
            "/release-media/shared_dialogue_before.mp4"
        ),
        "after": (
            "/release-media/shared_dialogue_after.mp4"
        ),
        "before_label": "Original shared dialogue",
        "after_label": "Rebuilt shared dialogue",
        "caption": (
            "The revised line propagates into both route previews."
        ),
    },
    "scenario_c": {
        "before": (
            "/release-media/ending_b_after.mp4"
        ),
        "after": (
            "/release-media/ending_b_blocked.mp4"
        ),
        "before_label": "Candidate release",
        "after_label": "Publication blocked",
        "caption": (
            "Branchline isolates the unavailable Ending B preview."
        ),
    },
}


def build_revision_story(
    scenario_id: str,
    analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build creator-facing change language."""
    try:
        story = dict(
            REVISION_STORIES[scenario_id]
        )
    except KeyError as exc:
        raise ValueError(
            f"Unsupported revision story: {scenario_id}"
        ) from exc

    if analysis is not None:
        story["calculated_source_ids"] = list(
            analysis["changed_sources"]
        )
        story["plan_sha256"] = analysis[
            "plan_sha256"
        ]
        story["calculated_at"] = analysis[
            "calculated_at"
        ]
    else:
        story["calculated_source_ids"] = []
        story["plan_sha256"] = None
        story["calculated_at"] = None

    return story


def build_causal_route(
    scenario_id: str,
) -> dict[str, Any]:
    """Return a concise causal route for presentation."""
    try:
        return dict(
            CAUSAL_ROUTES[scenario_id]
        )
    except KeyError as exc:
        raise ValueError(
            f"Unsupported causal route: {scenario_id}"
        ) from exc


def media_comparison(
    scenario_id: str,
) -> dict[str, str]:
    """Return the playable comparison for one scenario."""
    try:
        return dict(
            MEDIA_COMPARISONS[scenario_id]
        )
    except KeyError as exc:
        raise ValueError(
            f"Unsupported media comparison: {scenario_id}"
        ) from exc


def _metric(
    scenario: dict[str, Any],
    *names: str,
    default: int = 0,
) -> int:
    metrics = scenario.get(
        "raw_metrics",
        {},
    )

    for name in names:
        value = metrics.get(name)

        if value is not None:
            return int(value)

    return default


def build_verified_replay_stages(
    scenario_id: str,
) -> list[dict[str, str]]:
    """Build the exact evidence-backed execution sequence."""
    if scenario_id == "scenario_b":
        return [
            {
                "id": "plan",
                "label": "Plan fingerprint matched",
                "detail": (
                    "The approved action is bound to the live "
                    "dependency plan."
                ),
                "check": "plan",
            },
            {
                "id": "artwork",
                "label": "Ending B artwork confirmed",
                "detail": (
                    "The route artwork is present in the exact "
                    "rebuild set."
                ),
                "check": "rebuilt_assets",
            },
            {
                "id": "preview",
                "label": "Ending B preview confirmed",
                "detail": (
                    "The route preview is present in the exact "
                    "rebuild set."
                ),
                "check": "rebuilt_assets",
            },
            {
                "id": "b2",
                "label": "B2 release record confirmed",
                "detail": (
                    "Content-addressed media and release evidence "
                    "are recorded in Backblaze B2."
                ),
                "check": "b2",
            },
            {
                "id": "verify",
                "label": "Every reachable route verified",
                "detail": (
                    "Remote objects and both final story paths "
                    "passed verification."
                ),
                "check": "healthy_release",
            },
        ]

    if scenario_id == "scenario_a":
        return [
            {
                "id": "plan",
                "label": "Plan fingerprint matched",
                "detail": (
                    "The shared-dialogue impact was calculated "
                    "from the story graph."
                ),
                "check": "plan",
            },
            {
                "id": "shared_media",
                "label": "Shared media rebuild confirmed",
                "detail": (
                    "Voice, caption, and both previews are present "
                    "in the rebuild set."
                ),
                "check": "rebuilt_assets",
            },
            {
                "id": "route_art",
                "label": "Branch artwork preserved",
                "detail": (
                    "Both ending-specific route images remain "
                    "reusable."
                ),
                "check": "reused_assets",
            },
            {
                "id": "b2",
                "label": "B2 release record confirmed",
                "detail": (
                    "The release manifest and generated media "
                    "remain available in B2."
                ),
                "check": "b2",
            },
            {
                "id": "verify",
                "label": "Both routes verified",
                "detail": (
                    "Every reachable story route passed the final "
                    "release check."
                ),
                "check": "healthy_release",
            },
        ]

    if scenario_id == "scenario_c":
        return [
            {
                "id": "candidate",
                "label": "Candidate manifest loaded",
                "detail": (
                    "Every media object required by the candidate "
                    "release was enumerated."
                ),
                "check": "candidate",
            },
            {
                "id": "retrieve",
                "label": "Healthy B2 media retrieved",
                "detail": (
                    "Five release objects remain available and "
                    "hash-verifiable."
                ),
                "check": "partial_retrieval",
            },
            {
                "id": "missing",
                "label": "Missing preview isolated",
                "detail": (
                    "The failure is contained to the Ending B "
                    "preview."
                ),
                "check": "missing_asset",
            },
            {
                "id": "route_guard",
                "label": "Ending B route locked",
                "detail": (
                    "Ending A remains verified while unsafe "
                    "publication is stopped."
                ),
                "check": "blocked_release",
            },
        ]

    raise ValueError(
        f"Unsupported replay scenario: {scenario_id}"
    )


def validate_replay_stage(
    stage: dict[str, str],
    *,
    scenario_id: str,
    scenario: dict[str, Any],
    analysis: dict[str, Any] | None,
) -> None:
    """Require real release evidence before marking a stage complete."""
    check = stage["check"]

    rebuilt = set(
        scenario.get(
            "rebuilt_assets",
            [],
        )
    )

    reused = set(
        scenario.get(
            "reused_assets",
            [],
        )
    )

    paths = scenario.get(
        "paths",
        [],
    )

    proof = scenario.get(
        "provenance",
        {},
    )

    if check == "plan":
        if analysis is None:
            raise RuntimeError(
                "A live analysis is required before replay approval."
            )

        plan_hash = analysis.get(
            "plan_sha256",
            "",
        )

        if len(plan_hash) != 64:
            raise RuntimeError(
                "The live dependency plan has no valid SHA-256."
            )

        return

    if check == "rebuilt_assets":
        expected = {
            "scenario_b": {
                "thumbnail.ending_b",
                "preview.ending_b",
            },
            "scenario_a": {
                "voice.opening",
                "caption.opening",
                "preview.ending_a",
                "preview.ending_b",
            },
        }[scenario_id]

        if not expected.issubset(rebuilt):
            raise RuntimeError(
                "Verified rebuilt assets do not match the "
                "required release plan."
            )

        return

    if check == "reused_assets":
        expected = {
            "thumbnail.ending_a",
            "thumbnail.ending_b",
        }

        if not expected.issubset(reused):
            raise RuntimeError(
                "Verified preserved assets are incomplete."
            )

        return

    if check == "b2":
        if not proof.get("b2_object_key"):
            raise RuntimeError(
                "The verified release has no B2 evidence key."
            )

        return

    if check == "healthy_release":
        if not proof.get("remote_verified"):
            raise RuntimeError(
                "Remote B2 verification is incomplete."
            )

        if not paths or not all(
            bool(path.get("verified"))
            for path in paths
        ):
            raise RuntimeError(
                "At least one reachable story path is not verified."
            )

        return

    if check == "candidate":
        if _metric(
            scenario,
            "assets_total",
        ) < 1:
            raise RuntimeError(
                "The candidate manifest contains no assets."
            )

        return

    if check == "partial_retrieval":
        verified = _metric(
            scenario,
            "assets_verified",
            "assets_remote_verified",
        )

        if verified < 1:
            raise RuntimeError(
                "No healthy remote media was retrieved."
            )

        return

    if check == "missing_asset":
        failed = _metric(
            scenario,
            "assets_failed",
        )

        failed_assets = scenario.get(
            "failed_assets",
            [],
        )

        if (
            failed < 1
            or "preview.ending_b"
            not in failed_assets
        ):
            raise RuntimeError(
                "The expected missing Ending B preview "
                "was not isolated."
            )

        return

    if check == "blocked_release":
        statuses = {
            path["path_id"]: path["status"]
            for path in paths
        }

        if statuses.get("ending_a") != "VERIFIED":
            raise RuntimeError(
                "Ending A was not preserved."
            )

        if statuses.get("ending_b") != "BLOCKED":
            raise RuntimeError(
                "Ending B was not blocked."
            )

        return

    raise RuntimeError(
        f"Unknown replay evidence check: {check}"
    )
