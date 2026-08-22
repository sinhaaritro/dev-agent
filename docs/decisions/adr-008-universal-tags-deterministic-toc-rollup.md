tags: [tag-governance, toc]

# ADR-008: Universal Tags & Deterministic TOC Roll-up

Status: Accepted
Date: 2026-08-20
Source: docs/specs/010-docs-architecture-rebuild-reference-rename-id-conventions-tag-governance-toc-roll-up.md

## Context

As the `reference/` folder broadens into the generic docs home, filename-grep
alone gets painful for cross-cutting questions ("every doc about auth?"). There is
no single structured field that serves human search, AI retrieval, and any future
vector index. The folder READMEs also have no index, so the human path has no
table of contents, and nothing enforces it.

## Decision

- D4: A universal `tags: [lowercase-kebab, ...]` frontmatter field on all three
  committed folders (`reference/`, `specs/`, `decisions/`). No `name:` field
  - the filename is the single identity (kills the dual-source-of-truth trap).
  Tags are the one structured field that pays off as the repo grows and feeds a
  future vector index as a structured filter layer. Controlled-vocabulary
  discipline is normative (lint) + advisory (suggest), not freeform.
- D5: Five tag-governance functions in `promote_spec.py` (not a new script), each
  a CLI subcommand wrapping a private function; `check` internally calls
  `_tag_lint()` as one validation step (two entry points, one function - no
  logic duplication): `tag-list` (read, no state), `tag-suggest` (read,
  advisory), `tag-lint` (normative, exit 1 on violations, in check), `tag-rename`
  (the only writer, frontmatter only), `tag-index` (writes the Tag index marker
  block). Lint exit code is identical standalone and in-check; no `--warn-only`.
- D6: A `toc` subcommand of `promote_spec.py` (human-confirmed Option A) emits a
  `## Index` section between `<!-- TOC:START -->` and `<!-- TOC:END -->` markers
  in each folder's README. Deterministic, sorted by each folder's ID scheme,
  idempotent (rewrites only the marker block). Hooked into promote/adr/handoff so
  it never drifts. `docs/temp/` gets no TOC. The `toc` and `tag-index` subcommands
  share one `_scan_docs()` helper since both scan the same folders and write the
  same READMEs.

## Consequences

- Positive: "find everything about X" is one tag query across all three folders;
  the promotion gate now also gates tag hygiene; the human path gains a
  deterministic, always-current TOC; the tag vocabulary is prunable (lint flags
  near-dups via the suggest output + index tag-universe report).
- Negative: `promote_spec.py` grows by ~150 LOC (557 -> ~770) - two new
  subcommand groups co-located by shared scan logic. The marker-block pattern
  means the generated index lives inside committed README files - safe only
  because the generator never touches text outside the markers.
- Follow-up: a future `suggest --semantic` mode (embedding-based near-dup detection)
  is explicitly out of scope here; it would be an optional extension skill to keep
  the base engine zero-dep and harness-agnostic.
