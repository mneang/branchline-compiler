# ADR 0001: Thumbnail Dependency Contract

## Status

Accepted.

## Context

Branchline determines whether generated and compiled media can be reused by
comparing source hashes and dependency fingerprints.

The story graph declares:

- `thumbnail.ending_a` depends on `image.ending_a`
- `thumbnail.ending_b` depends on `image.ending_b`

Therefore, shared dialogue must not be rendered into either thumbnail.
Otherwise, a dialogue change could leave visually outdated text inside an
asset that the dependency planner correctly considers visually unchanged.

## Decision

Branch thumbnails may include only branch-visual information:

- branch label
- branch destination or outcome
- branch visual theme
- release or provenance label

They must not include:

- shared dialogue
- narration
- captions
- unrelated branch content

Dialogue remains valid inside branch previews because previews explicitly
depend on the shared voice and caption assets.

## Consequences

A shared dialogue edit can truthfully:

- rebuild the voice
- rebuild the caption
- rebuild both previews
- reuse both thumbnails

A branch-visual edit can truthfully:

- rebuild only that branch's thumbnail
- rebuild only that branch's preview
- preserve all unrelated assets
