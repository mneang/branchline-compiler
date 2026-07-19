"""Tests for plan-bound live Scenario B execution."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from branchline.application.live_analysis import (
    analyze_story_revision,
)
from branchline.application.live_execution import (
    LiveExecutionError,
    prepare_scenario_b_execution,
    validate_live_execution_contract,
)
from branchline.domain.approval import (
    validate_approval,
)


def test_execution_package_uses_unique_runtime_release(
    tmp_path: Path,
) -> None:
    analysis = analyze_story_revision(
        "scenario_b"
    )

    prepared = (
        prepare_scenario_b_execution(
            analysis,
            approved_by=(
                "interactive-release-operator"
            ),
            runtime_root=tmp_path,
        )
    )

    assert prepared[
        "release_id"
    ].startswith(
        "ending-b-live-"
    )

    assert prepared[
        "release_key"
    ].endswith(
        "/release.json"
    )

    assert (
        prepared["release_id"]
        in prepared["release_key"]
    )

    assert prepared[
        "release_path"
    ].parent == prepared[
        "audit_directory"
    ]

    assert validate_approval(
        prepared["plan"],
        prepared["approval"],
    )


def test_runtime_approval_matches_live_plan(
    tmp_path: Path,
) -> None:
    analysis = analyze_story_revision(
        "scenario_b"
    )

    prepared = (
        prepare_scenario_b_execution(
            analysis,
            approved_by="creator",
            runtime_root=tmp_path,
        )
    )

    assert (
        prepared["approval"][
            "plan_sha256"
        ]
        == analysis["plan_sha256"]
    )


def test_mutated_analysis_cannot_be_approved(
    tmp_path: Path,
) -> None:
    analysis = analyze_story_revision(
        "scenario_b"
    )

    corrupted = deepcopy(
        analysis
    )

    corrupted["plan"][
        "stale_assets"
    ].append(
        "voice.opening"
    )

    with pytest.raises(
        LiveExecutionError,
        match="changed before approval",
    ):
        prepare_scenario_b_execution(
            corrupted,
            approved_by="creator",
            runtime_root=tmp_path,
        )


def test_live_result_contract_proves_final_state(
    tmp_path: Path,
) -> None:
    analysis = analyze_story_revision(
        "scenario_b"
    )

    prepared = (
        prepare_scenario_b_execution(
            analysis,
            approved_by="creator",
            runtime_root=tmp_path,
        )
    )

    release = {
        "release_id": prepared[
            "release_id"
        ],
        "release_object_key": prepared[
            "release_key"
        ],
        "approval": {
            "approval_id": prepared[
                "approval"
            ]["approval_id"],
            "plan_sha256": prepared[
                "approval"
            ]["plan_sha256"],
        },
        "planned_stale_assets": (
            prepared["plan"][
                "stale_assets"
            ]
        ),
        "planned_reused_assets": (
            prepared["plan"][
                "reused_assets"
            ]
        ),
        "metrics": {
            "assets_rebuilt": 2,
            "assets_reused": 4,
            "assets_remote_verified": 6,
            "paths_verified": 2,
            "stale_assets_remaining": 0,
            "new_ai_requests": 0,
        },
        "publication_status": (
            "SAFE_TO_PUBLISH"
        ),
    }

    guard = {
        "publication_status": (
            "SAFE_TO_PUBLISH"
        ),
        "failed_assets": [],
        "metrics": {
            "assets_verified": 6,
            "paths_verified": 2,
        },
    }

    summary = (
        validate_live_execution_contract(
            prepared=prepared,
            release=release,
            guard=guard,
        )
    )

    assert summary[
        "assets_rebuilt"
    ] == 2

    assert summary[
        "assets_reused"
    ] == 4

    assert summary[
        "publication_status"
    ] == "SAFE_TO_PUBLISH"


def test_application_reuses_existing_builder() -> None:
    source = Path(
        "src/branchline/application/"
        "live_execution.py"
    ).read_text()

    assert (
        "scenario_b_builder.main()"
        in source
    )

    assert (
        "evaluate_release_candidate("
        in source
    )

    assert (
        "scenario_b_builder.RELEASE_ID"
        in source
    )

    assert (
        "scenario_b_builder.RELEASE_KEY"
        in source
    )


def test_runtime_evidence_is_ignored() -> None:
    ignore = Path(
        ".gitignore"
    ).read_text()

    assert (
        ".branchline/runtime/"
        in ignore
    )

    assert (
        "branchline_iniesta_lane.txt"
        in ignore
    )
