"""Human approvals bound to exact Branchline rebuild plans."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from branchline.domain.story_graph import canonical_hash


class ApprovalError(ValueError):
    """Raised when execution lacks valid human authorization."""


def plan_fingerprint(plan: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 fingerprint of a rebuild plan."""
    return canonical_hash(plan)


def create_approval(
    plan: dict[str, Any],
    *,
    approved_by: str,
    note: str = "",
    decision: str = "approved",
) -> dict[str, Any]:
    """Create a decision tied to the exact current plan."""
    actor = approved_by.strip()
    normalized_decision = decision.strip().lower()
    project_id = str(plan.get("project_id", "")).strip()

    if not actor:
        raise ApprovalError("approved_by cannot be empty")

    if not project_id:
        raise ApprovalError("plan is missing project_id")

    if normalized_decision not in {"approved", "rejected"}:
        raise ApprovalError(
            "decision must be either 'approved' or 'rejected'"
        )

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
    """Permit execution only for an approved, unmodified plan."""
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
            "The plan changed after approval."
        )

    if not str(approval.get("approved_by", "")).strip():
        raise ApprovalError("Approval has no human approver")

    return True
