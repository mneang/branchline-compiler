"""Calculate a rebuild plan from two versions of a branching story."""

from __future__ import annotations

import json
from pathlib import Path

from branchline.domain.story_graph import load_story, plan_rebuild


PREVIOUS = Path("fixtures/main_story/story_v1.json")
CURRENT = Path("fixtures/main_story/story_v2_shared_dialogue.json")
EVIDENCE = Path("evidence/story_graph_shared_dialogue.json")


def main() -> int:
    previous_story = load_story(PREVIOUS)
    current_story = load_story(CURRENT)

    plan = plan_rebuild(previous_story, current_story)

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(plan, indent=2) + "\n")

    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
