"""Human approval records bound to exact rebuild plans."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from branchline.domain.story_graph import canonical_hash


class ApprovalError(ValueError):
    """Raised when a rebuild plan lacks valid human approval."""


def plan_fingerprint(plan: dict[str, Any]) -> str:
    """Create a deterministic SHA-256 fingerprint for a rebuild plan."""
    return canonical_hash(plan)


def create_approval(
    plan: dict[str, Any],
    *,
    approved_by: str,
    note: str = "",
    decision: str = "approved",
) -> dict[str, Any]:
    """Create an approval or rejection bound to one exact plan."""
    actor = approved_by.strip()
    normalized_decision = decision.strip().lower()

    if not actor:
        raise ApprovalError("approved_by cannot be empty")

    if normalized_decision not in {"approved", "rejected"}:
        raise ApprovalError(
            "decision must be either 'approved' or 'rejected'"
        )

    project_id = str(plan.get("project_id", "")).strip()
    if not project_id:
        raise ApprovalError("plan is missing project_id")

    return {
        "approval_id": str(uuid4()),
        "project_id": project_id,
        "plan_sha256": plan_fingerprint(plan),
        "decision": normalized_decision,
        "approved_by": actor,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "note": note.strip(),
        "status": (
            "REBUILD APPROVED"
            if normalized_decision == "approved"
            else "REBUILD REJECTED"
        ),
    }


def validate_approval(
    plan: dict[str, Any],
    approval: dict[str, Any] | None,
) -> bool:
    """Require valid approval for the current, unmodified plan."""
    if approval is None:
        raise ApprovalError("No human approval was provided")

    if approval.get("decision") != "approved":
        raise ApprovalError(
            f"Rebuild was not approved: "
            f"{approval.get('decision', 'missing decision')}"
        )

    if approval.get("project_id") != plan.get("project_id"):
        raise ApprovalError(
            "Approval project does not match rebuild-plan project"
        )

    expected_hash = plan_fingerprint(plan)
    recorded_hash = approval.get("plan_sha256")

    if recorded_hash != expected_hash:
        raise ApprovalError(
            "Approval does not match the current rebuild plan. "
            "The plan may have changed after approval."
        )

    if not str(approval.get("approved_by", "")).strip():
        raise ApprovalError("Approval has no human approver")

    return True
