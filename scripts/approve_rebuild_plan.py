"""Approve or reject an exact Branchline rebuild plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from branchline.domain.approval import (
    create_approval,
    validate_approval,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a human decision bound to a rebuild plan."
    )

    parser.add_argument("plan", type=Path)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--note", default="")

    decision = parser.add_mutually_exclusive_group()
    decision.add_argument(
        "--approve",
        action="store_true",
        help="Approve the rebuild plan.",
    )
    decision.add_argument(
        "--reject",
        action="store_true",
        help="Reject the rebuild plan.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.plan.exists():
        raise SystemExit(f"Plan file does not exist: {args.plan}")

    plan = json.loads(args.plan.read_text())
    chosen_decision = "rejected" if args.reject else "approved"

    approval = create_approval(
        plan,
        approved_by=args.approved_by,
        note=args.note,
        decision=chosen_decision,
    )

    if chosen_decision == "approved":
        validate_approval(plan, approval)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(approval, indent=2) + "\n")

    print(json.dumps(approval, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
