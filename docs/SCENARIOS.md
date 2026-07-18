# Dynamic Scenarios

## Scenario A — Shared Dialogue Change

A line used before the story branch changes.

Expected behavior:
- Rebuild its voice
- Rebuild its caption
- Rebuild previews for both reachable endings
- Preserve unrelated images and branch-only media

Final state:
- Both paths pass verification
- Release is published

## Scenario B — Branch-Specific Visual Change

The background for Ending B changes.

Expected behavior:
- Rebuild Ending B scene render
- Rebuild Ending B thumbnail and preview
- Preserve the opening and Ending A

Final state:
- Only Ending B assets change
- Both paths pass verification
- Release is published

## Scenario C — Broken Reachable Path

A required current voice or caption asset is missing or has an outdated
source hash.

Expected behavior:
- Identify the exact broken path
- Block publication
- Report the missing or stale dependency

Final state:
- Verification fails
- Release remains blocked
