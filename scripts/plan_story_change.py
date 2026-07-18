"""Produce a minimum rebuild plan between two story versions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from branchline.domain.story_graph import load_story, plan_rebuild


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calculate stale and reusable story assets."
    )
    parser.add_argument("previous", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument(
        "--evidence",
        type=Path,
        required=True,
        help="Path where the resulting plan will be written.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    previous_story = load_story(args.previous)
    current_story = load_story(args.current)
    plan = plan_rebuild(previous_story, current_story)

    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(plan, indent=2) + "\n")

    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
