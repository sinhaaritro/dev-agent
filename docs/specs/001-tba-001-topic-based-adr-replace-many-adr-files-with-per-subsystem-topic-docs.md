---
tags: [topic-adr, decision-record, revision, discovery, guardrail]
---

# TBA-001: Topic-Based ADR (replace many-ADR files with per-subsystem topic docs)

Status: APPROVED
Handoff: 2026-09-22

> Scope: **complete and check-passing (promotion-ready).** Sections 1-4 capture
> the design; Section 5 (Task DAG) is authored; Sections 6-7 are concrete.
> **Everything is in scope**, including updating the framework's own
> `docs/reference/` docs to describe topics-instead-of-ADRs. The engine change is
> **incremental**: add the topic way in Tasks 1-6, verify per task, then retire
> the old `adr` / `docs/decisions` way in Task 7 (last, separately-reversible).
> Splitting `promote_spec.py` into smaller scripts is a separate future change.

## 1. Goal & Context

Replace the many-ADR decision system (`docs/decisions/`, one file per decision)
with **Topic-Based ADRs**: one doc per subsystem that reads like a normal, current
livedoc, carries the decision history at its end, and can grow into a folder of
subtopic docs. Goal: fix (1) **revision** (reversing a decision is a cheap,
explicit, single-approval operation, incl. cross-topic) and (2) **discovery** (a
newcomer reads the Current State alone to understand the repo today; the Decision
Log stops you repeating failed decisions or re-researching). The anti-rogue
guardrail (no silent modification) is kept and lane-tied (section 2.5).

Motivating failures: 30+ ADRs before first release; provisional choices (e.g.
"start with JSON") calcifying into rules the agent won't move past; approve-then-
reverse oscillation where a reversal spawns a new ADR or a silent Lane C patch and
the same conflict recurs.

## 2. Design & Trade-offs

1. **One topic doc per subsystem, not one ADR per decision.** Alternative: keep
   `docs/decisions/`. Rejected: clutter, and each ADR's protected status turns
   decisions into locks (lock-in). A single livedoc per subsystem is one source of
   truth and revises in place. (consequence in section 3)

2. **A topic doc is a normal doc: `## Current State` + `## Decision Log`.**
   The Current State reads like a current-state doc (headers/subheaders) a newcomer
   can read alone. The Decision Log sits at the end; each entry is a subheading =
   its decision ID, so it is linkable. Alternative: a terse ID list as the "active"
   section. Rejected: it forces the reader to jump around (section 3, 8, 14, 21)
   and doesn't read as a doc.

3. **Decision IDs are kept: `<TOPIC>-D<nn>`** (e.g. `FILE-D04` = the 4th decision
    in the `file` topic; multi-word: `DATA-STORAGE-D02`). The namespace is the
    **full topic name, uppercased** (`data-storage` -> `DATA-STORAGE-`); keep topic
    names short (1-2 words) so it stays usable. The file's H1 title is a separate
    human display name and may be longer than the filename. For a folder topic the
    ID is **topic-global across all its sub-files** (the engine scans every file in
    the topic for the next number). IDs are subheadings in the Decision Log
    (linkable anchors for cross-refs), **not** the structure of the Current State.

4. **Per-file Decision Logs.** A topic is either one file `docs/<name>.md` or a
   folder `docs/<name>/`. Each file is self-contained: its Current State + its own
   `## Decision Log` at the end. A decision is stored in the file whose content it
   is about; if it changes the Current State described in *another* file of the
   same topic, it links to that heading.

5. **Links are plain markdown heading anchors.** Any heading is targetable — a
    Current State subheading or a Decision Log ID subheading — within a file
    (`#anchor`) or across files/topics (`other.md#anchor`). Cross-topic refs point
    at a heading in the other topic, not a deep path. Two cross-ref fields:
    **`Affects: <target>`** on a decision = an informational pointer to where its
    ripple is (no reciprocal entry required); **`Ref: <source>`** on a decision =
    the affected topic's own record of a change, pointing back to the primary
    decision (present only when that topic gains/changes a decision because of it).

6. **Revision is a named, human-authorized operation.** Never silent, never
   "delete + recreate." It updates the Current State in place, adds/updates the
   decision's Log subheading (Date / Why / Supersedes / Affects), and links across
   the affected files/topics. One decision, one reason, one approval, N files.

7. **Guardrail is lane-tied (no silent/unrequested topic edits), with the Conflict
    Surface as the reversal UX.** Lanes A/B consult topic docs during planning and
    emit the Conflict Surface (section 2.4) when a plan reverses a topic's Current
    State. Lanes C/D skip doc consultation (context savings); a pattern-break there
    is an escalation trigger, not a silent patch. A no-silent-edits floor still
    holds. Sync (align docs to code) is an explicit, user-initiated operation (2.6).
    Alternative: hard floor on every edit. Rejected: too heavy for fast lanes.

8. **Decision Log purpose (explicit).** Records when + why something changed, and
   **failed / superseded** decisions, so you don't repeat them or re-research (if
   the situation changed, a previously-rejected option may be viable — the log
   says why it was rejected before). Pure **research** (not implemented) is
   recorded **only when the human says so**.

9. **Growth = livedoc splitting, not a size rule.** When a doc gets big, split it
   into subtopic files the way a developer maintains docs (e.g. `overview`,
   `implementation`, `gotchas`). A **comparison doc** (full pro/con) is a valid
   folder artifact so the same comparison isn't re-discussed. Promotion renames
   `<name>.md` -> `<name>/`; a topic is never both a file and a folder.

10. **Incremental engine change.** Keep `promote_spec.py` as one file. ADD a
    `topic` operation now; KEEP `promote` (-> `docs/specs`), `check`, `handoff`.
    RETIRE the `adr` subcommand + old index/TOC logic **only after** the new way
    is verified. (Conflict detection becomes prose-based, not ID-matching —
    accepted.) Splitting the script is a separate future change.

### 2.1 Topic naming & location

- Live directly under `docs/`: `docs/auth.md` (file) or `docs/auth/` (folder).
  Distinct from `docs/reference/` (framework meta-docs), `docs/specs/` (feature
  specs), `docs/temp/` (scratchpad).
- Plain lowercase names, no numeric prefix (kebab for multi-word:
  `docs/data-storage.md`). The name is the ID namespace (`auth` -> `AUTH-`).
- Reserved names (a topic may not use them): `reference/`, `specs/`, `temp/`,
  `README.md`.
- **The topic index is not placed in `docs/README.md`; it is a generated file at
  `docs/_topics.md`** (underscore prefix = generated, excluded from the topic
  list). The existing `docs/README.md` **human folder-structure landing is kept**
  but reframed to describe topic docs instead of the `decisions/` ADR folder, and
  it points to `_topics.md` for the AI topic index. (A section in `.agents/MAP.md`
  is an acceptable alternative home for the index, but `docs/_topics.md` is the
  default.)
  It is rebuilt by scanning `docs/` (always the `docs/` folder from the repo root):
  copy each topic's `tags:` frontmatter into a `covers:` line, and derive key
  `sections` / `files` from its headings. The index is AI-optimized routing signal,
  not a human landing page (humans read the topic files). **`sync-docs` is a
  map-generator subcommand.** **Auto-trigger = agent behavior:** after editing a
  topic doc the AI runs it (a system.md rule), not a git hook. **Manual trigger:**
  the human runs `sync-docs` after hand-editing docs.

### 2.2 Topic doc format (the contract)

Each topic file (or each file in a topic folder) is a normal doc with one fixed
section at the end:

```markdown
---
tags: [file-structure, layout, package-x]
---

# File Structure

## Current State
We use package X for layout (see [FILE-D04](#file-d04---package-x-vs-package-y)).
Folder layout:

### Doc tree
- docs/t1, docs/t2

### Source tree
- src/y1, src/y2

This layout avoids the auth-header issue.

## Decision Log

### FILE-D04 - Package X vs Package Y
- **Date:** 2026-09-21
- **Why:** Package Y is generally better, but for our case (1, 2, 3) we need X.
- **Supersedes:** FILE-D03

### FILE-D03 - Initial layout (superseded)
- **Date:** 2026-08-15
- **Why:** First cut to unblock work; fell short because ...
```

Rules:
- **YAML frontmatter holds `tags:`** — a curated keyword list the index generator
  copies into the topic's `covers:` line (the source of the AI-routing keywords;
  stable, not re-derived). The H1 title is a separate human display name and may be
  longer than the filename.
- `## Current State` is a normal doc — headers/subheaders, prose, links. A
  newcomer reading only this section understands the repo today.
- `## Decision Log` is at the end; every entry is a subheading
  `### <TOPIC>-D<nn> - <title>` (linkable). Fields: `Date`, `Why`, and where
  relevant `Supersedes` / `Affects` / `Ref` (`Affects` = one-way pointer, `Ref` =
  reciprocal entry — see decision 5).
- Failed/superseded decisions stay in the Log (marked), never deleted.
- **All log entries are equal** — one format, no heavier tier for high-stakes
  decisions. The weight/justification for important choices lives in the Current
  State prose, not in a bigger log record.

Default folder layout on growth (each file is self-contained per decision 4):

```text
docs/db/
  overview.md             # Current State (entry) + its Decision Log
  implementation.md       # high-level implementation + its Decision Log
  gotchas.md              # known pitfalls + its Decision Log
  compare-pg-vs-mongo.md  # (optional) pro/con research + its Decision Log
```

No file is required to be the entry — a folder's files may be named `overview`,
`index`, or anything; each is self-contained.

### 2.3 Cross-file / cross-topic revision (worked example: JWT to cookie)

One decision, one approval, two topics, linked by heading anchors:

- `docs/auth.md`: Current State updated to session cookies; Log subheading
  `AUTH-D03` added with `Why`, `Supersedes: AUTH-D02`, `Affects: api.md#api-auth`.
- `docs/api.md`: Current State heading `#api-auth` updated to "auth via cookie";
  its Log gets subheading `API-D01` with `Ref: auth.md#auth-d03`.

Both topics reflect the change in one revision, so it does not resurface as a new
conflict. This is the **reciprocal** case — `api`'s Current State actually changes, so it
gets its own entry (`API-D01`) with `Ref:` back to the primary. The **one-way** case:
if a decision's ripple reaches another topic but that topic's Current State does not
change, the primary just records `Affects:` and the other topic gains no entry.

### 2.4 Conflict Surface (guardrail interaction)

Emit when a planned change reverses the Current State of a topic.

**Lane-proportional conflict detection** (prose-based, not ID-matching):
- **Lane A** — full: consult every topic the plan touches.
- **Lane B** — scoped: consult only the topics the plan touches.
- **Lanes C/D** — none: no doc consultation (context savings); a pattern-break is an escalation trigger.

```text
[CONFLICT] Planned change reverses the current approach in docs/auth
  - Current State: session cookies for browser auth
  - Last change (auth.md#auth-d03, 2026-09-21): localStorage JWT was XSS-exposed
  - Your change (JWT bearer) reverses it

  (A) Explore the reversal - I'll show impact: code snippets, which files depend
      on the current approach, the existing changes involved. Then you explicitly
      authorize -> I run the cross-topic revision.
  (B) Keep the current approach - proceed within it.
   (C) Abandon - drop the change.
```

### 2.5 Guardrail (lane-tied, the "don't contradict / don't sneak" rule)

- **No silent / unrequested topic edits** — the floor holds in every lane.
- **Lanes A/B** consult topic docs during planning; on a reversal they emit the
  Conflict Surface (2.4) instead of proceeding.
- **Lanes C/D** skip doc consultation (context savings); a pattern-break (a change
  that contradicts a topic's Current State) is an **escalation trigger**, not a
  silent patch.
- A change that reverses a decision is a **revision** (named, human-authorized,
  cross-file/topic, one approval) — never "delete + recreate."

### 2.6 Sync (explicit, user-initiated)

- **Sync = align docs to code.** The user says "align the docs" (or "sync docs");
  the agent re-reads the relevant code and updates the affected Current State +
  Decision Log entries. Never run implicitly.
- The **topic index** (`_topics.md`) is a lighter, separate rebuild: auto on any
  `docs/` change, or `sync-docs` after hand edits (section 2.1).

## 3. Risks & Open Questions

> [!IMPORTANT]
> **User Review Required**
> - Guardrail lane-tied (A/B consult docs + Conflict Surface (2.4) on reversal; C/D
>   skip, escalate on pattern-break; no-silent-edits floor holds). Conflict detection
>   lane-proportional (A full, B scoped, C/D none). (decision 7)
> - All decision-log entries are equal — one format, no heavier ADR tier for
>   high-stakes decisions; the weight/emphasis lives in the Current State prose.
> - `docs/README.md` **stays** as the human folder-structure landing (reframed:
>   the `decisions/` ADR row is replaced by the topic-doc framing + a pointer to
>   `_topics.md`); the **AI topic index** is the generated `docs/_topics.md`, not
>   placed in `docs/README.md`. (section 2.1)
> - `docs/decisions/` is currently **empty** (no filed ADRs), so Task 7 retires
>   the ADR *machinery* (engine `adr` op + the folder + the ADR-specific tests) —
>   there is no ADR content to migrate.

### Open Questions

- [x] Q1: IDs — **decided** keep `<TOPIC>-D<nn>`; they are linkable Decision Log
      subheadings, not the Current State structure.
- [x] Q2: Location/naming — **decided** `docs/<name>.md` (or `docs/<name>/`),
      plain lowercase, no prefix; no `docs/README.md` — the generated index
      (`docs/_topics.md` or a MAP.md section) is the discovery entry.
- [x] Q3: Engine home — **decided** keep `promote_spec.py` one file for now; ADD
      `topic`, KEEP promote/check/handoff, RETIRE `adr` + old index after
      verification. Splitting = separate future change.
- [x] Q4: Git-protection — **decided** lane-tied guardrail (A/B consult docs +
      Conflict Surface on reversal; C/D skip + escalate on pattern-break);
      no-silent-edits floor holds.
- [x] Q5: ID namespace — **decided** full topic name, uppercased; keep topic names
      short; H1 title is a separate (possibly longer) display name; folder IDs are
      topic-global across sub-files.
- [x] Q6: `covers` source — **decided** curated `tags:` frontmatter per topic file,
      copied by the generator (stable, not re-derived).
- [x] Q7: `Affects` vs `Ref` — **decided** `Affects` = informational one-way pointer;
      `Ref` = reciprocal entry only when the affected topic gains/changes a decision.
- [x] Q8: `sync-docs` home/trigger — **decided** map-generator subcommand; auto =
      agent behavior (system.md rule), not a git hook; index default `docs/_topics.md`.
- [x] Q9: Folder entry file — **decided** none required; files may be named anything.

### Risks

- Per-file logs scatter history; "have we tried X before" needs a grep across
  topic logs. Mitigate: logs are keyword-greppable; the index points to topics.
- A decision in file A that changes file B's Current State splits its story across
  two files. Mitigate: the decision links to B's heading (decisions 4/5).
- Prose-based conflict detection is judgment, not a mechanical match. Accepted
  (decision 10); the Conflict Surface still requires human approval.
- Removing ADRs loses per-decision Context/Consequences structure. Mitigate: each
  Log subheading keeps Date / Why / Supersedes / Affects — ADR-grade reasoning,
  ADR-free ceremony.

## 4. Affected Files & Contracts

> Incremental: add the new way, verify, then remove the old (ADR) way. Splitting
> the engine is a separate future change.

### [NEW] docs/_topics.md (generated) — or a section in .agents/MAP.md
Generated **AI context-routing index** — not a human landing page; humans read the
topic files directly. Per topic: name, `path`, a keyword `covers` list (for matching),
and either `files:` (folder sub-files, each with a short cover) or `sections:` (key
headings). Rebuilt by scanning `docs/` (loosely read files + headings -> `covers` +
sections/files); auto on docs change, or `sync-docs` for hand edits. No `docs/README.md`.

### [NEW] docs/<name>.md (or docs/<name>/ once grown)
One per subsystem (plain lowercase, e.g. `auth`, `db`, `file`). Contract: matches
section 2.2 — normal doc, `## Current State` + `## Decision Log` (ID subheadings)
at the end; a file or a folder, never both; each folder file is self-contained.

### [NEW] .agents/skills/spec-builder/references/topic-template.md
Format-of-truth for topic docs: `tags:` frontmatter, H1 title, `## Current State`,
`## Decision Log` (ID subheadings: Date / Why / Supersedes / Affects / Ref), +
per-file and folder-growth rules (no required entry file). Mirrors `adr-template.md`'s
role.

### [MODIFY] .agents/skills/spec-builder/scripts/promote_spec.py
Add a `topic` operation (single + cross-file/topic revision, heading-anchor links,
human-gated research entries). Keep `promote`/`check`/`handoff`. Retire the `adr`
subcommand + old `decisions`/`reference` index logic only after the new way is
verified. (One file for now; splitting is a separate change.)

### [MODIFY] .agents/skills/map-generator/scripts/generate_map.py
Add a `sync-docs` subcommand: scan `docs/`, copy each topic's `tags:` frontmatter
into `covers:`, derive `sections`/`files` from headings, write `docs/_topics.md`.
This is the index builder; the AI runs it after editing a topic doc (auto) or the
human runs it after hand edits.

### [MODIFY] .agents/rules/system.md
Guardrail (lane-tied): no silent/unrequested topic edits; Lanes A/B consult docs
and emit the Conflict Surface (2.4) on a reversal; Lanes C/D skip docs and escalate
on a pattern-break; Sync is an explicit op (2.6). Drop `docs/decisions/*` references.

### [MODIFY] docs/reference/005-*.md (+ any other framework docs touching decisions/ADRs)
Update the framework's own docs to describe topics-instead-of-ADRs. (In scope per
"everything.")

### [DELETE] docs/decisions/ (and docs/decisions/README.md)
Removed **after** the new way is verified; superseded by the topic docs.

## 5. Task DAG

Build order follows `Depends On`. **Incremental**: add the topic way (Tasks 1-6),
verify per task, then remove the old ADR way (Task 7) as the last,
separately-reversible step. No engine splitting (each script stays one file).
Dictated contracts (function/subcommand names, test counts) are pinned so the
`Verify`/`Expect` oracles are deterministic.

### Task 1: Topic doc template (format-of-truth)

- Target Files: [NEW] `.agents/skills/spec-builder/references/topic-template.md`
- Depends On: None
- Subtasks:
  - [ ] 1.1 Author the template body: YAML frontmatter `tags:`, an H1 display title, `## Current State` (prose + `###` subheadings), and `## Decision Log` with a `### <TOPIC>-D<nn> - <title>` subheading and one complete example entry.
    - Input: design sections 2.2 (format contract) + 2.3 (worked example).
    - Output: `topic-template.md` with frontmatter, the two H2 sections, and a sample log entry.
    - Verify: `grep -cE "^## (Current State|Decision Log)$" .agents/skills/spec-builder/references/topic-template.md`
    - Expect: 2
  - [ ] 1.2 Add a "Rules" section: the per-entry field set (`Date` / `Why` / `Supersedes` / `Affects` / `Ref`) and the folder-growth rules (no required entry file; promotion renames `<name>.md` -> `<name>/`; a topic is never both a file and a folder).
    - Input: 1.1 output.
    - Output: template with the field set + folder-growth rules documented.
    - Verify: `grep -cE "(Supersedes / Affects / Ref|No file is required to be the entry)" .agents/skills/spec-builder/references/topic-template.md`
    - Expect: 2
- Phase Gate: `grep -q '^tags:' .agents/skills/spec-builder/references/topic-template.md && grep -q '^## Current State$' .agents/skills/spec-builder/references/topic-template.md && grep -q '^## Decision Log$' .agents/skills/spec-builder/references/topic-template.md`

### Task 2: `sync-docs` index builder

- Target Files: [MODIFY] `.agents/skills/map-generator/scripts/generate_map.py`, [NEW] `tests/test_sync_docs.py`
- Depends On: None
- Subtasks:
  - [ ] 2.1 Add a `sync-docs` subcommand: a `def sync_docs(root)` handler + argv dispatch on `"sync-docs"` that scans `docs/` for topic files/folders, copies each topic's `tags:` frontmatter into a `covers:` line, derives `sections` (file topics) / `files` (folder topics, union of sub-file `tags:`) from headings, and writes `docs/_topics.md`.
    - Input: the `docs/` topic layout + design 2.1 (index format).
    - Output: `generate_map.py` with a working `sync-docs` subcommand (handler `sync_docs`).
    - Verify: `grep -c "def sync_docs(" .agents/skills/map-generator/scripts/generate_map.py`
    - Expect: 1
  - [ ] 2.2 Write `tests/test_sync_docs.py` with exactly 4 tests: (a) file topic -> `covers:` from `tags:` + `sections:` from headings; (b) folder topic -> `covers:` = union of sub-file `tags:` + a `files:` list; (c) output is written to `docs/_topics.md`; (d) a hand-edited `docs/README.md` is not overwritten.
    - Input: 2.1 output.
    - Output: `tests/test_sync_docs.py` (4 tests).
    - Verify: `grep -c "def test_" tests/test_sync_docs.py`
    - Expect: 4
  - [ ] 2.3 Run the new tests to GREEN.
    - Input: 2.1 + 2.2 output.
    - Output: all 4 `sync-docs` tests passing.
    - Verify: `python -m unittest tests.test_sync_docs -v`
    - Expect: Ran 4 tests
- Phase Gate: `python -m unittest tests.test_sync_docs -v`

### Task 3: Engine `topic` operation

- Target Files: [MODIFY] `.agents/skills/spec-builder/scripts/promote_spec.py`, [NEW] `tests/test_topic_op.py`
- Depends On: Task 1
- Subtasks:
  - [ ] 3.1 Add a `topic` subcommand (`def cmd_topic(args)` + `sub.add_parser("topic", ...)`): create a topic (file or folder) and allocate the next `<TOPIC>-D<nn>` by scanning **all** files of the topic for the max ID (topic-global), writing a Decision Log entry (Date / Why / Supersedes / Affects / Ref).
    - Input: the template (Task 1) = format-of-truth.
    - Output: `promote_spec.py` with a working `topic` create path (handler `cmd_topic`).
    - Verify: `grep -c "def cmd_topic(" .agents/skills/spec-builder/scripts/promote_spec.py`
    - Expect: 1
  - [ ] 3.2 Add revision + cross-file/topic behavior in `def _revise_topic(`: a revision updates the Current State in place + the log entry (never delete+recreate); a cross-file/topic revision writes the primary entry with `Affects` and, only when the affected topic gains/changes a decision, a terse `Ref` entry in the other file/topic; links are plain heading anchors.
    - Input: 3.1 output + design 2.3 (worked example).
    - Output: `topic` op supports single-file and cross-file/topic revision.
    - Verify: `grep -c "def _revise_topic(" .agents/skills/spec-builder/scripts/promote_spec.py`
    - Expect: 1
  - [ ] 3.3 Write `tests/test_topic_op.py` with exactly 5 tests: (a) create allocates the next ID scanning the whole topic (folder sub-files); (b) create a single-file topic; (c) a revision supersedes without reusing the ID; (d) a cross-topic revision writes `Affects` (primary) + `Ref` (affected); (e) a topic-based full lifecycle (promote -> topic -> handoff) leaves the project root clean.
    - Input: 3.1 + 3.2 output.
    - Output: `tests/test_topic_op.py` (5 tests).
    - Verify: `grep -c "def test_" tests/test_topic_op.py`
    - Expect: 5
  - [ ] 3.4 Run the new tests to GREEN (existing suite stays green).
    - Input: 3.1-3.3 output.
    - Output: all 5 `topic`-op tests passing.
    - Verify: `python -m unittest tests.test_topic_op -v`
    - Expect: Ran 5 tests
- Phase Gate: `python -m unittest tests.test_topic_op -v`

### Task 4: Lane-tied guardrail in system.md

- Target Files: [MODIFY] `.agents/rules/system.md`
- Depends On: None
- Subtasks:
  - [ ] 4.1 Replace the ADR guardrail with a "Topic guardrail" rule: no silent/unrequested topic edits; Lanes A/B consult topic docs during planning and emit the Conflict Surface on a reversal; Lanes C/D skip docs and escalate on a pattern-break; Sync is an explicit, user-initiated op.
    - Input: design 2.4 (Conflict Surface) + 2.5 (guardrail) + 2.6 (sync).
    - Output: `system.md` with a "Topic guardrail" rule.
    - Verify: `grep -c "Topic guardrail" .agents/rules/system.md`
    - Expect: 1
  - [ ] 4.2 Add the C/D escalation wording: a pattern-break (a change contradicting a topic's Current State) is an **escalation trigger**, not a silent patch.
    - Input: 4.1 output.
    - Output: `system.md` with the C/D escalation-trigger wording.
    - Verify: `grep -c "escalation trigger" .agents/rules/system.md`
    - Expect: 1
- Phase Gate: `grep -q "Topic guardrail" .agents/rules/system.md && grep -q "escalation trigger" .agents/rules/system.md`

### Task 5: Framework docs describe topics-instead-of-ADRs

- Target Files: [MODIFY] `docs/reference/005-docs-architecture-and-spec-lifecycle.md`, [MODIFY] `docs/README.md`
- Depends On: Task 3, Task 4
- Subtasks:
  - [ ] 5.1 Update `docs/reference/005-*.md` to describe the Topic-Based ADR system (topic docs, `## Current State` + `## Decision Log`, `sync-docs`, lane-tied guardrail) instead of the many-ADR model; add a `## Topic-Based Decision Records` section.
    - Input: design sections 1-4.
    - Output: reference 005 rewritten to describe topic docs.
    - Verify: `grep -c "## Topic-Based Decision Records" docs/reference/005-docs-architecture-and-spec-lifecycle.md`
    - Expect: 1
  - [ ] 5.2 Update the `docs/README.md` folder table + index prose so decision knowledge is framed as topic docs (the `decisions/` ADR row is replaced by the topic-doc framing) and points to `docs/_topics.md` for the AI topic index.
    - Input: 5.1 output.
    - Output: `docs/README.md` reframed (decisions -> topic docs; pointer to `_topics.md`).
    - Verify: `grep -c "Topic-Based" docs/README.md`
    - Expect: 1
- Phase Gate: `grep -q "## Topic-Based Decision Records" docs/reference/005-docs-architecture-and-spec-lifecycle.md && grep -q "Topic-Based" docs/README.md`

### Task 6: Seed the first real topic + generate the index

- Target Files: [NEW] `docs/decision-records.md`, [NEW] `docs/_topics.md` (generated)
- Depends On: Task 2, Task 3
- Subtasks:
  - [ ] 6.1 Create the first real topic doc `docs/decision-records.md` (the topic-based decision system itself) matching the template: frontmatter `tags:`, `## Current State`, `## Decision Log` with `DECISION-RECORDS-D01` (the decision to adopt Topic-Based ADRs, superseding the many-ADR approach).
    - Input: template (Task 1) + this spec.
    - Output: `docs/decision-records.md` (a real, seeded topic doc).
    - Verify: `grep -cE "^## (Current State|Decision Log)$" docs/decision-records.md`
    - Expect: 2
  - [ ] 6.2 Run `sync-docs` to generate `docs/_topics.md` from `docs/` (the seeded topic appears with a `covers:` line derived from its `tags:`).
    - Input: 6.1 output + `sync-docs` (Task 2).
    - Output: `docs/_topics.md` listing the seeded topic.
    - Verify: `grep -cE "^  covers:" docs/_topics.md`
    - Expect: 1
- Phase Gate: `test -f docs/decision-records.md && test -f docs/_topics.md`

### Task 7: Retire the old ADR way (last, separately-reversible)

- Target Files: [MODIFY] `.agents/skills/spec-builder/scripts/promote_spec.py`, [MODIFY] `tests/test_promote_spec_docs_root.py`, [DELETE] `docs/decisions/`
- Depends On: Task 3, Task 5, Task 6
- Subtasks:
  - [ ] 7.1 Remove the `adr` subcommand: delete `cmd_adr` + its `sub.add_parser("adr", ...)` registration from `promote_spec.py` (the `topic` op is the decision path now).
    - Input: verified `topic` op (Task 3).
    - Output: `promote_spec.py` with the `adr` subcommand removed.
    - Verify: `grep -c "def cmd_adr(" .agents/skills/spec-builder/scripts/promote_spec.py || true`
    - Expect: 0
  - [ ] 7.2 Update `tests/test_promote_spec_docs_root.py` so it no longer calls `adr`: remove the ADR-specific tests (the `adr` filing + unnumbered-`adr`-slug cases) and rewrite the full-lifecycle test to use the `topic` op; keep the toc + tag-index root-clean tests. Leave exactly 2 tests in this file.
    - Input: 7.1 output + `topic` op (Task 3).
    - Output: `test_promote_spec_docs_root.py` with 2 tests (no `adr` calls).
    - Verify: `grep -c "def test_" tests/test_promote_spec_docs_root.py`
    - Expect: 2
  - [ ] 7.3 Delete the now-empty ADR folder `docs/decisions/` (its README too).
    - Input: 7.1 output.
    - Output: `docs/decisions/` removed from the repo.
    - Verify: `ls -d docs/decisions 2>/dev/null | grep -c "docs/decisions" || true`
    - Expect: 0
  - [ ] 7.4 Run the full suite to GREEN at the final pinned inventory (2 + 4 + 5 = 11 tests).
    - Input: 7.1-7.3 output.
    - Output: the whole suite green with exactly 11 tests.
    - Verify: `python -m unittest discover -s tests -v`
    - Expect: Ran 11 tests
- Phase Gate: `python -m unittest discover -s tests -v`

## 6. Verification Commands

- Build Command: `python -m py_compile .agents/skills/spec-builder/scripts/promote_spec.py .agents/skills/map-generator/scripts/generate_map.py`
- Test Command: `python -m unittest discover -s tests -v`
- Lint Command: `python -m py_compile .agents/skills/spec-builder/scripts/promote_spec.py .agents/skills/map-generator/scripts/generate_map.py` (no dedicated linter is configured; `py_compile` is the syntax gate)
- Draft gate: `python .agents/skills/spec-builder/scripts/promote_spec.py check docs/temp/draft-plan.md --lane A` (this spec; passes now that Section 5 is authored)

## 7. Rollback Strategy

Revert in reverse Task DAG order: Task 7 (retire `adr` / `docs/decisions`) ->
Task 6 (seed topic + index) -> Task 5 (framework docs) -> Task 4 (system.md
guardrail) -> Task 3 (engine `topic` op) -> Task 2 (`sync-docs`) -> Task 1
(template).

Tasks 1-6 are additive (new files + new engine ops); each is independently
revertible by `git revert` of its task's commit. **Task 7 is the only destructive
step** (removes the `adr` subcommand, `docs/decisions/`, and the ADR-specific
tests) and is deliberately last so it can be reverted on its own without touching
the new topic machinery. If any subtask fails verification 3 consecutive times
the circuit breaker fires (phase-protocol `build.md`): dirty edits are reverted
and the subtask reverts to `[ ]`.
