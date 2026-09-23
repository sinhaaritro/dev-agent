---
tags: [decision-records, adr, topic-docs, spec-lifecycle, framework]
---

# Decision Records

## Current State

Decision knowledge is recorded **Topic-Based**: one doc per subsystem under `docs/`
(a flat file `docs/<name>.md`, or a folder `docs/<name>/` once it grows), each
holding a `## Current State` a newcomer can read alone plus a `## Decision Log`
of equal-weight, linkable entries (`<TOPIC>-D<nn>`).

### How it works
- A topic doc is a normal doc — headers, prose, plain heading-anchor links —
  not a special artifact. It is created and revised only through the
  spec-builder engine (`promote_spec.py topic`), so numbering, format, and the
  no-silent-edits floor are enforced rather than left to judgment
  (DECISION-RECORDS-D01).
- Decision IDs are topic-global across a topic's files; a reversal is a
  *revision* — the next ID with `Supersedes:` — never "delete + recreate".
- `docs/_topics.md` is the generated AI-routing index (covers from `tags:`,
  sections/files from headings), rebuilt by `generate_map.py sync-docs`;
  humans land on `docs/README.md`.
- Lane-tied guardrail (system.md §3): Lanes A/B consult topic docs at plan
  time and surface a Conflict Surface when a plan reverses a Current State;
  Lanes C/D skip docs and escalate on pattern-breaks.

### Why this shape
The previous model — one file per decision (`docs/decisions/adr-NNN-*.md`) with
scattered backlinks — made decisions hard to find and the backlinks brittle.
Grouping decisions by subsystem puts "why is it like this?" one file away from
"how does it work?" (DECISION-RECORDS-D01).

## Decision Log

### DECISION-RECORDS-D01 - Adopt Topic-Based decision docs, retire the many-ADR model
- **Date:** 2026-09-23
- **Why:** Many small ADR files with scattered backlinks made decisions hard to
  find and the links brittle; one livedoc per subsystem keeps Current State and
  its decision history together, with a generated AI index and a lane-tied
  guardrail replacing per-file immutability.
- **Supersedes:** the many-ADR model (one `docs/decisions/adr-NNN-*.md` per decision, backlinked to specs)
- **Affects:** docs/005-docs-architecture-and-spec-lifecycle.md#topic-based-decision-records

### DECISION-RECORDS-D02 - Flatten knowledge layout: specs/ at root, reference series under docs/
- **Date:** 2026-09-23
- **Why:** Flatten the knowledge layout: specs live at repo-root specs/ (with specs/temp/ scratchpad), the 001-007 reference series lives directly under docs/ (no reference/ subfolder), and docs/ holds only the reference series + topic docs + README + _topics.md. Simpler, fewer nested dirs; the engine scans the repo root for specs/ and docs/.
