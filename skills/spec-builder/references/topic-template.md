# Topic Doc Template (format-of-truth)

The single source of format truth for Topic-Based decision docs. Every topic doc
filed under `docs/` must match this structure, which is why topic creation and
revision run through the spec-builder engine (`promote_spec.py topic`) instead of
judgment. One topic doc per subsystem, not one ADR per decision.

```text
---
tags: [lowercase-kebab, ...]
---

# <Display Title>

## Current State
A normal, current-state doc: prose with `###` subheadings a newcomer can read
alone to understand the repo today. Link decisions from here into the Decision
Log below (plain markdown heading anchors).

### <Subheading>
- ...

## Decision Log

### <TOPIC>-D<nn> - <Title>
- **Date:** YYYY-MM-DD
- **Why:** One or two sentences: the reason for the change.
- **Supersedes:** <TOPIC>-D<mm>   (optional)
- **Affects:** <other-topic>.md#<anchor>   (one-way pointer, optional)
- **Ref:** <other-topic>.md#<other-topic-dnn>   (reciprocal entry, optional)
```

Rules:

1. **YAML frontmatter holds `tags:`** — a curated keyword list the `sync-docs`
   index generator copies into the topic's `covers:` line (the source of the
   AI-routing keywords; stable, not re-derived). The H1 title is a separate human
   display name and may be longer than the filename.
2. `## Current State` is a normal doc — headers/subheaders, prose, links. A
   newcomer reading only this section understands the repo today.
3. `## Decision Log` is at the end; every entry is a subheading
   `### <TOPIC>-D<nn> - <title>` (linkable). Fields: `Date`, `Why`, and where
   relevant `Supersedes / Affects / Ref` (`Affects` = one-way pointer; `Ref` =
   reciprocal entry, present only when the affected topic gains/changes a
   decision because of it).
4. Decision IDs are `<TOPIC>-D<nn>`: the namespace is the full topic name
   uppercased (`data-storage` -> `DATA-STORAGE-`); keep topic names short (1-2
   words). For a folder topic the ID is topic-global across all its sub-files.
5. Failed/superseded decisions stay in the Log (marked), never deleted.
6. All log entries are equal — one format, no heavier tier for high-stakes
   decisions. The weight/justification for important choices lives in the Current
   State prose, not in a bigger log record.
7. Folder-growth rules: a topic is either one file `docs/<name>.md` or a folder
   `docs/<name>/`, never both. When a doc gets big, split it into subtopic files
   the way a developer maintains docs (e.g. `overview`, `implementation`,
   `gotchas`). Each file is self-contained: its Current State + its own Decision
   Log. No file is required to be the entry — a folder's files may be named
   `overview`, `index`, or anything. Promotion renames `<name>.md` -> `<name>/`.
8. A change that reverses a decision is a revision (named, human-authorized,
   cross-file/topic, one approval) — never "delete + recreate."

Usage: created and revised with `promote_spec.py topic` (Task 3). Pure research
(not implemented) is recorded only when the human says so.
