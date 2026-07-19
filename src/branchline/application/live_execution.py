"""Plan-bound live execution for Branchline Scenario B.

The adapter invokes the existing, proven Scenario B builder with:

- a fresh human approval
- a unique release ID and B2 object key
- isolated runtime evidence paths
- an independent remote publication guard

Canonical checked-in evidence is never overwritten.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from branchline.domain.approval import (
    create_approval,
    validate_approval,
)
from branchline.domain.release_guard import (
    evaluate_release_candidate,
)
from branchline.domain.story_graph import (
    canonical_hash,
    load_story,
)

import scripts.build_scenario_b_visual_release as scenario_b_builder


PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]

RUNTIME_ROOT = (
    PROJECT_ROOT
    / ".branchline"
    / "runtime"
)

_EXECUTION_LOCK = threading.Lock()

ProgressCallback = Callable[
    [dict[str, str]],
    None,
]


class LiveExecutionError(RuntimeError):
    """Raised when a real release action cannot complete safely."""


class LiveExecutionUnavailable(
    LiveExecutionError
):
    """Raised when the hosted runtime lacks required live configuration."""


def _write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )


def _emit(
    progress: ProgressCallback | None,
    *,
    stage: str,
    detail: str,
) -> None:
    if progress is None:
        return

    progress(
        {
            "stage": stage,
            "detail": detail,
        }
    )


def _safe_log_tail(
    output: str,
) -> str:
    lines = [
        line.strip()
        for line in output.splitlines()
        if line.strip()
    ]

    if not lines:
        return "The builder returned no diagnostic output."

    return lines[-1][:500]


def prepare_scenario_b_execution(
    analysis: dict[str, Any],
    *,
    approved_by: str,
    runtime_root: Path | None = None,
) -> dict[str, Any]:
    """Create a unique, plan-bound runtime execution package."""
    if analysis.get("scenario_id") != "scenario_b":
        raise LiveExecutionError(
            "Only Scenario B supports deterministic live execution."
        )

    plan = analysis.get("plan")

    if not isinstance(plan, dict):
        raise LiveExecutionError(
            "Live analysis contains no executable rebuild plan."
        )

    calculated_plan_hash = canonical_hash(
        plan
    )

    if (
        calculated_plan_hash
        != analysis.get("plan_sha256")
    ):
        raise LiveExecutionError(
            "The live analysis plan changed before approval."
        )

    approval = create_approval(
        plan,
        approved_by=approved_by,
        note=(
            "Approved through the interactive "
            "Branchline release studio."
        ),
    )

    validate_approval(
        plan,
        approval,
    )

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    release_id = (
        "ending-b-live-"
        f"{timestamp}-"
        f"{uuid4().hex[:8]}"
    )

    release_key = (
        "branchline/projects/"
        f"{plan['project_id']}/"
        f"releases/{release_id}/"
        "release.json"
    )

    base_directory = (
        runtime_root
        if runtime_root is not None
        else RUNTIME_ROOT
    )

    audit_directory = (
        base_directory
        / release_id
    )

    audit_directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    plan_path = (
        audit_directory
        / "plan.json"
    )

    approval_path = (
        audit_directory
        / "approval.json"
    )

    release_path = (
        audit_directory
        / "release.json"
    )

    guard_path = (
        audit_directory
        / "publication_guard.json"
    )

    _write_json(
        plan_path,
        plan,
    )

    _write_json(
        approval_path,
        approval,
    )

    return {
        "scenario_id": "scenario_b",
        "release_id": release_id,
        "release_key": release_key,
        "guard_key": (
            "branchline/projects/"
            f"{plan['project_id']}/"
            f"releases/{release_id}/"
            "publication-guard.json"
        ),
        "plan": plan,
        "plan_sha256": calculated_plan_hash,
        "approval": approval,
        "audit_directory": audit_directory,
        "plan_path": plan_path,
        "approval_path": approval_path,
        "release_path": release_path,
        "guard_path": guard_path,
    }


def validate_live_execution_contract(
    *,
    prepared: dict[str, Any],
    release: dict[str, Any],
    guard: dict[str, Any],
) -> dict[str, Any]:
    """Validate the exact product claim made by the live UI."""
    approval = prepared["approval"]
    plan = prepared["plan"]

    if (
        release.get("release_id")
        != prepared["release_id"]
    ):
        raise LiveExecutionError(
            "The returned release ID does not match "
            "the approved execution."
        )

    if (
        release.get("release_object_key")
        != prepared["release_key"]
    ):
        raise LiveExecutionError(
            "The release was stored under an unexpected B2 key."
        )

    release_approval = release.get(
        "approval",
        {},
    )

    if (
        release_approval.get(
            "approval_id"
        )
        != approval["approval_id"]
    ):
        raise LiveExecutionError(
            "The release does not contain the fresh approval."
        )

    if (
        release_approval.get(
            "plan_sha256"
        )
        != approval["plan_sha256"]
    ):
        raise LiveExecutionError(
            "The release approval is not bound "
            "to the current plan."
        )

    if set(
        release.get(
            "planned_stale_assets",
            [],
        )
    ) != set(
        plan["stale_assets"]
    ):
        raise LiveExecutionError(
            "The executed rebuild set differs "
            "from the approved plan."
        )

    if set(
        release.get(
            "planned_reused_assets",
            [],
        )
    ) != set(
        plan["reused_assets"]
    ):
        raise LiveExecutionError(
            "The executed reuse set differs "
            "from the approved plan."
        )

    metrics = release.get(
        "metrics",
        {},
    )

    expected_metrics = {
        "assets_rebuilt": 2,
        "assets_reused": 4,
        "assets_remote_verified": 6,
        "paths_verified": 2,
        "stale_assets_remaining": 0,
        "new_ai_requests": 0,
    }

    for name, expected in (
        expected_metrics.items()
    ):
        actual = metrics.get(name)

        if actual != expected:
            raise LiveExecutionError(
                "Unexpected live release metric "
                f"{name}: {actual!r} != {expected!r}"
            )

    if (
        release.get(
            "publication_status"
        )
        != "SAFE_TO_PUBLISH"
    ):
        raise LiveExecutionError(
            "The new release is not publishable."
        )

    if (
        guard.get(
            "publication_status"
        )
        != "SAFE_TO_PUBLISH"
    ):
        raise LiveExecutionError(
            "The independent publication guard "
            "did not approve the new release."
        )

    guard_metrics = guard.get(
        "metrics",
        {},
    )

    if guard_metrics.get(
        "assets_verified"
    ) != 6:
        raise LiveExecutionError(
            "The guard did not verify all six assets."
        )

    if guard_metrics.get(
        "paths_verified"
    ) != 2:
        raise LiveExecutionError(
            "The guard did not verify both reachable paths."
        )

    if guard.get(
        "failed_assets"
    ):
        raise LiveExecutionError(
            "The guard found failed assets."
        )

    return {
        "release_id": release[
            "release_id"
        ],
        "release_object_key": release[
            "release_object_key"
        ],
        "approval_id": approval[
            "approval_id"
        ],
        "plan_sha256": approval[
            "plan_sha256"
        ],
        "assets_rebuilt": 2,
        "assets_reused": 4,
        "assets_verified": 6,
        "paths_verified": 2,
        "stale_assets_remaining": 0,
        "new_ai_requests": 0,
        "publication_status": (
            "SAFE_TO_PUBLISH"
        ),
    }


def execute_scenario_b_release(
    *,
    analysis: dict[str, Any],
    approved_by: str,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Execute, store, independently verify, and record Scenario B."""
    prepared = prepare_scenario_b_execution(
        analysis,
        approved_by=approved_by,
    )

    _emit(
        progress,
        stage="approval",
        detail=(
            "Fresh human approval created and "
            "bound to the exact live plan."
        ),
    )

    with _EXECUTION_LOCK:
        original_directory = Path.cwd()

        global_names = (
            "RELEASE_ID",
            "RELEASE_KEY",
            "PLAN_PATH",
            "APPROVAL_PATH",
            "EVIDENCE_PATH",
        )

        original_globals = {
            name: getattr(
                scenario_b_builder,
                name,
            )
            for name in global_names
        }

        try:
            os.chdir(
                PROJECT_ROOT
            )

            try:
                environment = (
                    scenario_b_builder
                    .require_b2_environment()
                )

            except (
                scenario_b_builder
                .ScenarioBReleaseError
            ) as exc:
                raise LiveExecutionUnavailable(
                    str(exc)
                ) from exc

            scenario_b_builder.RELEASE_ID = (
                prepared["release_id"]
            )

            scenario_b_builder.RELEASE_KEY = (
                prepared["release_key"]
            )

            scenario_b_builder.PLAN_PATH = (
                prepared["plan_path"]
            )

            scenario_b_builder.APPROVAL_PATH = (
                prepared["approval_path"]
            )

            scenario_b_builder.EVIDENCE_PATH = (
                prepared["release_path"]
            )

            output = io.StringIO()

            _emit(
                progress,
                stage="build",
                detail=(
                    "Verifying the base release, rebuilding "
                    "two affected assets, and preserving four."
                ),
            )

            with (
                contextlib.redirect_stdout(
                    output
                ),
                contextlib.redirect_stderr(
                    output
                ),
            ):
                exit_code = (
                    scenario_b_builder.main()
                )

            builder_log = output.getvalue()

            (
                prepared[
                    "audit_directory"
                ]
                / "builder.log"
            ).write_text(
                builder_log
            )

            if exit_code != 0:
                raise LiveExecutionError(
                    "Scenario B builder failed: "
                    + _safe_log_tail(
                        builder_log
                    )
                )

            release_path = prepared[
                "release_path"
            ]

            if not release_path.exists():
                raise LiveExecutionError(
                    "The builder returned success "
                    "without producing release evidence."
                )

            local_release_bytes = (
                release_path.read_bytes()
            )

            release = json.loads(
                local_release_bytes.decode(
                    "utf-8"
                )
            )

            scenario_b_builder.verify_canonical_release(
                release,
                label=(
                    "Fresh live Scenario B release"
                ),
            )

            _emit(
                progress,
                stage="manifest",
                detail=(
                    "Unique release manifest stored in "
                    "Backblaze B2."
                ),
            )

            bucket = environment[
                "B2_BUCKET_NAME"
            ]

            client = (
                scenario_b_builder
                .create_s3_client(
                    environment
                )
            )

            remote_release_bytes = (
                client.get_object(
                    Bucket=bucket,
                    Key=prepared[
                        "release_key"
                    ],
                )["Body"].read()
            )

            if (
                remote_release_bytes
                != local_release_bytes
            ):
                raise LiveExecutionError(
                    "Remote B2 release bytes differ "
                    "from the local release record."
                )

            remote_release = json.loads(
                remote_release_bytes.decode(
                    "utf-8"
                )
            )

            scenario_b_builder.verify_canonical_release(
                remote_release,
                label=(
                    "Remote fresh Scenario B release"
                ),
            )

            current_story = load_story(
                str(
                    PROJECT_ROOT
                    / scenario_b_builder
                    .CURRENT_STORY_PATH
                )
            )

            def fetch_bytes(
                object_key: str,
            ) -> bytes:
                return client.get_object(
                    Bucket=bucket,
                    Key=object_key,
                )["Body"].read()

            _emit(
                progress,
                stage="guard",
                detail=(
                    "Independently retrieving all six "
                    "objects and checking both story routes."
                ),
            )

            guard = evaluate_release_candidate(
                story=current_story,
                release=remote_release,
                fetch_bytes=fetch_bytes,
            )

            guard_record = {
                **guard,
                "evaluated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "release_object_key": (
                    prepared[
                        "release_key"
                    ]
                ),
                "guard_report_object_key": (
                    prepared[
                        "guard_key"
                    ]
                ),
            }

            guard_record[
                "canonical_sha256"
            ] = canonical_hash(
                guard_record
            )

            guard_bytes = (
                json.dumps(
                    guard_record,
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n"
            ).encode("utf-8")

            client.put_object(
                Bucket=bucket,
                Key=prepared[
                    "guard_key"
                ],
                Body=guard_bytes,
                ContentType=(
                    "application/json"
                ),
            )

            downloaded_guard = (
                client.get_object(
                    Bucket=bucket,
                    Key=prepared[
                        "guard_key"
                    ],
                )["Body"].read()
            )

            if downloaded_guard != guard_bytes:
                raise LiveExecutionError(
                    "Remote publication-guard bytes "
                    "differ from the local audit record."
                )

            prepared[
                "guard_path"
            ].write_bytes(
                guard_bytes
            )

            summary = (
                validate_live_execution_contract(
                    prepared=prepared,
                    release=remote_release,
                    guard=guard_record,
                )
            )

            _emit(
                progress,
                stage="complete",
                detail=(
                    "Six objects and two reachable routes "
                    "verified. Release is safe to publish."
                ),
            )

            result = {
                "mode": "LIVE_EXECUTION",
                **summary,
                "guard_report_object_key": (
                    prepared[
                        "guard_key"
                    ]
                ),
                "audit_directory": str(
                    prepared[
                        "audit_directory"
                    ].relative_to(
                        PROJECT_ROOT
                    )
                ),
                "approval": prepared[
                    "approval"
                ],
                "release": remote_release,
                "guard": guard_record,
            }

            _write_json(
                prepared[
                    "audit_directory"
                ]
                / "result.json",
                result,
            )

            return result

        except (
            LiveExecutionError,
            LiveExecutionUnavailable,
        ):
            raise

        except Exception as exc:
            raise LiveExecutionError(
                "Live release execution failed: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        finally:
            for name, value in (
                original_globals.items()
            ):
                setattr(
                    scenario_b_builder,
                    name,
                    value,
                )

            os.chdir(
                original_directory
            )
