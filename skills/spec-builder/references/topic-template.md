# Topic Doc Template (format-of-truth)

The single source of format truth for Topic-Based decision docs. Every topic doc
filed under `docs/` must match this structure, which is why topic creation and
revision run through the spec-builder engine (the runtime's `spec topic` command) instead of
judgment. One topic doc per subsystem; the Decision Log records the decisions the human
asks to keep.

```text
---
tags: [lowercase-kebab, ...]
---

# <Display Title>

<One short paragraph: what this subsystem is, so a newcomer can start here.>

## <Section>

Prose, lists, tables, links. A newcomer reading the body - everything before the
Decision Log - understands the repo today.

### <Sub-subheading>

- ...

## <Section>

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
2. **The body is a normal doc** — after the H1, free-form `##` sections (with
   `###` sub-subheadings where useful), prose, and links. There is **no
   `## Current State` wrapper**: a newcomer reads the body top to bottom, and the
   body's `##` headings are the sections the generated index lists. Headings
   inside fenced code blocks are not structure.
3. **`## Decision Log` is the last section** — nothing may follow it. Every entry
   is a subheading `### <TOPIC>-D<nn> - <title>` (linkable). Fields: `Date`,
   `Why`, and where relevant `Supersedes / Affects / Ref` (`Affects` = one-way
   pointer; `Ref` = reciprocal entry, present only when the affected topic
   gains/changes a decision because of it).
4. Decision IDs are `<TOPIC>-D<nn>`: the namespace is the full topic name
   uppercased (`data-storage` -> `DATA-STORAGE-`); keep topic names short (1-2
   words). For a folder topic the ID is topic-global across all its sub-files.
5. Failed/superseded decisions stay in the Log (marked), never deleted.
6. All log entries are equal — one format, no heavier tier for high-stakes
   decisions. The weight/justification for important choices lives in the body
   prose, not in a bigger log record.
7. Folder-growth rules: a topic is either one file `docs/<name>.md` or a folder
   `docs/<name>/`, never both. When a doc gets big, split it into subtopic files
   the way a developer maintains docs (e.g. `overview`, `implementation`,
   `gotchas`). Each file is self-contained: its body sections + its own Decision
   Log. No file is required to be the entry — a folder's files may be named
   `overview`, `index`, or anything. Promotion renames `<name>.md` -> `<name>/`.
8. A change that reverses a decision is a revision (named, human-authorized,
   cross-file/topic, one approval) — never "delete + recreate." `--body` replaces
   the whole body (everything after the H1, before the Decision Log) in one
   explicit operation; the log is never rewritten.
9. **One format only.** A legacy doc that still carries a `## Current State`
   wrapper is migrated by the engine on its next `spec topic`: the heading is
   removed and the headings inside it are promoted one level (`###` -> `##`,
   `####` -> `###`, ...). Never author the wrapper in a new doc.

Usage: created and revised with the runtime's `spec topic` command. Pure research
(not implemented) is recorded only when the human says so.
