---
tags: [decision-records, docs, spec, lifecycle, topic-adr, scratchpad, framework]
---

# Decision Records & the Spec Lifecycle

The knowledge layer: how `docs/` is organized, how Topic-Based decision records work, the ID and tag conventions, the spec-first lifecycle (draft → vetting → compile → build → review → sign-off → done), the spec **group** file layout, and the scratchpad's garbage collection.

## Current State

Decision knowledge is recorded **Topic-Based**: one doc per subsystem under `docs/` (a flat file `docs/<name>.md`, or a folder `docs/<name>/` once it grows), each holding a `## Current State` a newcomer can read alone plus a `## Decision Log` of equal-weight, linkable entries (`<TOPIC>-D<nn>`). `docs/` is a **single layer** — there is no separate numbered reference series; every doc is a topic doc.

### How it works

- A topic doc is a normal doc — headers, prose, plain heading-anchor links — not a special artifact. It is created and revised only through the spec-builder engine (`promote_spec.py topic`), so numbering, format, and the no-silent-edits floor are enforced rather than left to judgment (DECISION-RECORDS-D01).
- Decision IDs are topic-global across a topic's files; a reversal is a *revision* — the next ID with `Supersedes:` — never "delete + recreate".
- `docs/_topics.md` is the generated AI-routing index (covers from `tags:`, sections/files from headings), rebuilt by `generate_map.py sync-docs`; humans start at `docs/README.md` and read the topic docs themselves.
- Lane-tied guardrail (dev-agent-framework.md section 3): Lanes A/B consult topic docs at plan time and surface a Conflict Surface when a plan reverses a Current State; Lanes C/D skip docs and escalate on pattern-breaks.

### Why this shape

The previous model — one file per decision (`docs/decisions/adr-NNN-*.md`) with scattered backlinks — made decisions hard to find and the backlinks brittle. Grouping decisions by subsystem puts "why is it like this?" one file away from "how does it work?" (DECISION-RECORDS-D01). A later numbered "what is" series duplicated the same subjects; the single-layer consolidation (DECISION-RECORDS-D05) keeps one doc per subsystem.

### The `docs/` layout

| Location | Role | Lifecycle |
| :--- | :--- | :--- |
| `docs/<name>.md` or `docs/<name>/` (topic docs) | Why we chose — one livedoc per subsystem: current state + decision history | Living; decisions are appended and revised in place |
| `docs/README.md` | Human landing page: the guided reading path | Maintained by hand (the engine never writes it) |
| `docs/_topics.md` | Generated AI routing index | Rebuilt by `sync-docs`; never hand-edit |
| `specs/` | What to build | A single `Status:` receipt per spec: `DRAFTED → COMPILED → BUILDING → BUILT → REVIEWED → COMPLETED` (failure states `ESCALATED` / `ABORTED`; gate-block states `PLAN_REVISION_REQUIRED` / `REVIEW_REVISION_REQUIRED`) |
| `specs/temp/` | Ephemeral working memory | Gitignored (`*` except `.gitignore`); purged by `task-cleaner` (default preserves `.gitignore` only) |

Topic docs live **directly** under `docs/` (never inside the committed folders), one per subsystem: `docs/auth.md`, or `docs/auth/` once grown. The AI routing index for them is the generated `docs/_topics.md` (underscore prefix = generated); humans read the topic docs directly, starting from `docs/README.md`.

`specs/README.md` is the only committed README carrying a generated `## Index` section, between `<!-- TOC:START -->` / `<!-- TOC:END -->` markers; `specs/temp/` gets no TOC (ephemeral — a generated index there is just churn).

### Topic doc format contract

Format-of-truth: `.agents/skills/spec-builder/references/topic-template.md`.

- YAML frontmatter `tags: [lowercase-kebab, ...]` — the curated keyword list `sync-docs` copies into the topic's `covers:` index line.
- H1 display title (separate from the filename; may be longer).
- `## Current State` — a normal doc (headers, prose, links) that a newcomer can read alone to understand the repo today.
- `## Decision Log` at the end — every entry a subheading `### <TOPIC>-D<nn> - <title>` (a linkable anchor), with fields `Date`, `Why`, and where relevant `Supersedes` / `Affects` / `Ref`. All entries are equal — one format, no heavier tier for high-stakes decisions (the weight lives in the Current State prose).

**ID namespace:** the full topic name, uppercased (`auth` → `AUTH-D01`, `data-storage` → `DATA-STORAGE-D02`); keep topic names short (1–2 words). For a folder topic the number is **topic-global across all its sub-files** (the engine scans every file of the topic for the next number). Each folder file is self-contained: its own Current State + its own Decision Log; a decision that changes another file's Current State links to that heading.

**Cross-topic links** are plain heading anchors. `Affects: <target>` on a decision is a one-way informational pointer to where its ripple is (no reciprocal entry required); `Ref: <source>` appears only when the affected topic itself gains/changes a decision because of it, pointing back at the primary decision.

**Revision** (reversing a decision) is a named, human-authorized operation — never silent, never "delete + recreate": it updates the Current State in place, appends the log entry with the **next** ID (the reversed one is marked `(superseded)` and stays), and links across the affected files/topics. One decision, one reason, one approval, N files.

**Guardrail (lane-tied, dev-agent-framework.md section 3):** no silent / unrequested topic edits in any lane; Lanes A/B consult the topic docs during planning and emit the Conflict Surface when a plan reverses a topic's Current State; Lanes C/D skip doc consultation and treat a pattern-break as an **escalation trigger**, not a silent patch. **Sync** (aligning docs to code) is an explicit, user-initiated operation.

**Growth = livedoc splitting, not a size rule:** when a doc gets big, split it into subtopic files the way a developer maintains docs (`overview`, `implementation`, `gotchas`; a full pro/con comparison doc is a valid folder artifact so the same comparison is not re-discussed). Promotion renames `<name>.md` → `<name>/`; a topic is never both a file and a folder.

**Purpose of the Log:** records when + why something changed, and **failed / superseded** decisions, so a later session does not repeat them or re-research (if the situation changed, a previously-rejected option may be viable — the log says why it was rejected before). Pure research (not implemented) is recorded only when the human says so.

**Engine:**

```text
# create / revise (single + cross-topic), human-gated via the approval step
python .agents/skills/spec-builder/scripts/promote_spec.py topic <name> \
    --why <text> [--title <t>] [--file <sub>] [--state <text>] \
    [--supersedes <ID>] [--affects <target>] \
    [--reciprocal <topic>] [--reciprocal-file <sub>] [--reciprocal-why <text>]

# rebuild the AI routing index after editing a topic doc
python .agents/skills/map-generator/scripts/generate_map.py sync-docs
```

### ID conventions

- **Topic docs:** `docs/<name>.md` (or `docs/<name>/`), plain lowercase, no numeric prefix (kebab for multi-word: `docs/data-storage.md`). The name is the decision-ID namespace. Reserved names a topic may not use: `README.md` and anything underscore-prefixed (generated files, e.g. `_topics.md`).
- **`specs/`:** a **group** of companions sharing one `NNN` prefix: `NNN-SPEC-<slug>.md` (the spec), `NNN-TASK-<NN>-<slug>.md` (one per section 5 task), `NNN-APPROVALS-<slug>.json` (gitignored; pre-approved verify fingerprints), `NNN-REPORT-<slug>.md` (the review report, `verify.py report`), and `NNN-ESCALATION-<slug>.md` (the consolidated failure record, when a run parks the spec `ESCALATED`). Sub-IDs `NNN-<letter><NN>` (e.g. `001-A01`), deeper `NNN-<letter><NN>-<letter><NN>` (e.g. `001-A01-B01`); a sub-ID child compiles into the parent group (the engine strips the `NNN-LNN:` title prefix).

**Numbering is engine-derived.** `promote_spec.py` computes the next `NNN` by scanning the specs folder, and the next `<TOPIC>-D<nn>` by scanning every file of the topic; a hand-written number can silently collide with a committed record.

### Tags contract

Every committed doc in `specs/` and every topic doc carries a `tags` field in its **YAML frontmatter block** at the top of the file:

```text
---
tags: [lowercase-kebab, ...]
---
```

2–30 chars per tag, max 7 per doc, no empty field. The **filename is the single identity** — there is no `name:` field anywhere. A topic doc may optionally add `version_pin: <git-tag>` or `fallback_pin: <commit-hash>` in the same block.

For topic docs the `tags:` list is the source of the `covers:` line in `docs/_topics.md` (the AI-routing keywords). `tag-lint` (also run inside `check`) lints the `specs/` docs; the governance subcommands are:

| Subcommand | Behavior |
| :--- | :--- |
| `tag-list` | Read-only: sorted tag → files with counts |
| `tag-suggest` | Advisory near-dup candidates only — never blocks |
| `tag-lint` | Normative; exit 1 on violations; also runs inside `check` |
| `tag-rename <old> <new>` | The only writer; frontmatter tags only |

Legacy tolerance: a bare `tags:` line outside frontmatter (pre-frontmatter docs) is still read by every scan, and is normalized into frontmatter automatically by the engine on `promote`, topic creation, and `tag-rename` — so old docs keep working and converge to the canonical form on their next write.

### The spec-first lifecycle (two steps)

```text
Incoming requirement
        │
        ▼
 specs/temp/draft-plan.md          (Lane B: sections 1,4,5 / Lane A: sections 0-8)
        │  validated: promote_spec.py check <draft> --lane <B|A>
        ▼
 [ Vetting gate — optional, when the spec's vetting: on ]
        │  a block drops the spec to PLAN_REVISION_REQUIRED (re-plan)
        ▼
 [ "approve draft" gate — human acceptance or compliant autonomous resolution ]
        │  promote_spec.py compile <spec> --lane <B|A>
        ├──► specs/NNN-SPEC-<slug>.md          (committed, Status: COMPILED)
        ├──► specs/NNN-TASK-<NN>-<slug>.md     (one per section 5 task, the coder's briefing)
        ├──► specs/NNN-APPROVALS-<slug>.json   (pre-approved verify fingerprints)
        └──► topic log entries in docs/<topic>.md (one per architectural decision)
        ▼
 SESSION STOPS — no build in the spec-producing session
        ▼
 STEP 2: an explicit RUN (a new session / lead agent) reads the COMPILED spec
 group (verified via Status: COMPILED), runs
 verify.py doctor (PRECONDITIONS OK), creates one branch per spec off main,
 dispatches unblocked tasks to coders (each ticks its own task file, Verify +
 Expect with content-hash evidence), runs verify.py report at review,
 commits on the branch at the run's stop point (commit → COMPLETED,
 pre-commit → stop at REVIEWED), then task-cleaner purges the scratchpad on
 acceptance. A failure parks the spec ESCALATED (NNN-ESCALATION-<slug>.md)
 and the batch continues to the next spec.
```

Rules that make the split real:

- **Compile happens at "approve draft", never during review** and never before implementation. The engine is mechanics only, so never compile without the gate having passed.
- `COMPILED` is the **only** state a run may start from — it is unreachable without passing the compile gate. A spec compiled under an autonomous resolution keeps its `Gates:` record marked **autonomous** and records **no topic decisions** until a human clears that mark.
- Topic log entries are triggered by **the decision, not the lane**: any architectural decision at any lane (schema, public API, auth/security, new dependency) gets a permanent entry in its topic. Lane A: one per section 2 decision; Lane B: only when one surfaces.
- The compile step validates plan-readiness (the `check` oracles pass). Idempotent; `--dry-run` prints without writing.
- Lanes C/D have no plan or approval step, so **no compile applies** — never look for or create a compiled spec for C/D tasks.
- A session that compiled a spec MUST NOT start a build in the same session — a run is an explicit, separately-triggered execution.

### Templates (format truth)

In `.agents/skills/spec-builder/references/`:

- **`implementation-plan-template.md`** — the plan, sections 0–8: 0 Frontmatter (`tags`, `vetting`, `signoff`, `review_revision`), 1 Goal & Context, 2 The Change (thematic subsections), 3 Risks & Open Questions, 4 Affected Files & Contracts, 5 Tasks & Outcomes (each `Task N` carries `Depends On:`, `Outcomes: R#`, and a `Verify:`/`Expect:` pair; subtasks live in the task file, not the spec), 6 Gates, 7 Verification Commands, 8 Rollback Strategy. Lane B uses a single task (`Depends On: None`). `promote_spec.py check` validates the section 5 structure and statically lints the oracles (rejects no-op `Verify`, empty `Expect`, and a trivially-satisfied `Expect` — the whole command or a bare `echo`/`printf`; a marker the command emits from real state is allowed).
- **`task-file-format.md`** — the task-file contract: a self-contained briefing (Role & rules, Project overview, Owns, Reads / Context, a `### Progress` subtask checklist) generated per task at compile; the `verify.py` evidence block is appended on a green verify (see `task-files.md`).
- **`todo-checklist-format.md`** — subtasks are the **coder's own checklist** (`- [ ]` → `- [/]` → `- [x]`), not a second verification gate: the task's task-level `Verify` decides pass/fail. Task state is **derived**, not asserted — `MET` (evidence green + owned-file hashes still match) / `NOT MET` / `STALE` (an owned file drifted) / `NO-EVIDENCE` (via `verify.py status`); a task that exhausts its 3 attempts parks `ESCALATED`.
- **`topic-template.md`** — the topic doc contract: `tags:` frontmatter, H1 display title, `## Current State`, `## Decision Log` with `### <TOPIC>-D<nn> - <title>` subheadings (`Date` / `Why` / `Supersedes` / `Affects` / `Ref`) and the per-file / folder-growth rules.

### Deterministic TOC rollup + topic index

`python .agents/skills/spec-builder/scripts/promote_spec.py toc [--root <root>]` regenerates the `specs/README.md` `## Index` marker block, sorted by NNN/sub-ID, showing name + status + version-pin + backlinks. It is hooked into `compile` / `topic` / `accept` so the TOC never drifts, is idempotent (rewrites only the marker block, never surrounding prose), and `--dry-run` prints without writing. **Never hand-edit a marker block** — prose outside the markers is safe from regeneration.

The topic index is a separate, lighter rebuild: `python .agents/skills/map-generator/scripts/generate_map.py sync-docs` scans `docs/`, copies each topic's `tags:` frontmatter into a `covers:` line, derives `sections` (file topics) / `files` (folder topics) from headings, and writes `docs/_topics.md`. The agent runs it after editing a topic doc; a human runs it after hand edits. Every `docs/` file and folder is a topic, and the only thing skipped is the generated `_topics.md` itself (it would otherwise index itself).

### Scratchpad lifecycle & garbage collection

`specs/temp/` holds only **draft-stage** working state: `draft-plan.md` (the one running plan being authored), `active-task.md` (working memory), and any draft-stage notes. The durable records that used to live here are now committed with the spec group: gate decisions in the spec's `Gates:` section, the Review report as `NNN-REPORT-<slug>.md`, the failure record as `NNN-ESCALATION-<slug>.md`, and per-task evidence inside each `NNN-TASK` file.

`task-cleaner` purges it (default preserves `.gitignore` only; a human may pass `--preserve` to keep specific files):

```text
python .agents/skills/task-cleaner/scripts/clean.py clean
```

- Default: everything purged **except** `.gitignore`; retired scratch artifacts (the old `gate-log.md`, `verify-state.json`, `approvals.json`) are purged when present. Report is `purged: N, preserved: M`.
- **No auto-purge** — the engine only deletes when explicitly invoked; it never sweeps the scratchpad as a side effect of a status transition.
- `clean --dry-run` / `status` classify without deleting — use in doubt.
- Scope is the scratchpad and nothing else: the committed folders (including the spec group) are never touched; the engine refuses targets at or above the repo root.
- The engine restores no template stubs — the next task's planning status (`DRAFTED`) creates scratchpad files on demand.

## Decision Log

### DECISION-RECORDS-D01 - Adopt Topic-Based decision docs, retire the many-ADR model
- **Date:** 2026-09-23
- **Why:** Many small ADR files with scattered backlinks made decisions hard to find and the links brittle; one livedoc per subsystem keeps Current State and its decision history together, with a generated AI index and a lane-tied guardrail replacing per-file immutability.
- **Supersedes:** the many-ADR model (one `docs/decisions/adr-NNN-*.md` per decision, backlinked to specs)

### DECISION-RECORDS-D02 - Flatten knowledge layout: specs/ at root, reference series under docs/ (superseded)
- **Date:** 2026-09-23
- **Why:** Flatten the knowledge layout: specs live at repo-root specs/ (with specs/temp/ scratchpad), the 001-007 reference series lives directly under docs/ (no reference/ subfolder), and docs/ holds only the reference series + topic docs + README + _topics.md. Simpler, fewer nested dirs; the engine scans the repo root for specs/ and docs/.

### DECISION-RECORDS-D03 - sync-docs indexes all docs/ topics; only _topics.md is skipped
- **Date:** 2026-09-23
- **Why:** sync-docs indexes every docs/ file and folder as a topic - the reference series, the landing README, and all topic docs - and skips ONLY the generated _topics.md itself. The earlier reservation of the numbered series / README / underscore files was over-broad; the reference docs are legitimate routing topics.

### DECISION-RECORDS-D04 - The engine (promote_spec.py) should not know about docs/README.md at all
- **Date:** 2026-09-27
- **Why:** The engine (promote_spec.py) should not know about docs/README.md at all. The file stays as a plain human-maintained file (no engine-generated TOC/TAG-INDEX blocks; the AI may read it, and a human can explicitly ask the AI to write it), but no engine/script creates, writes, or updates it. The tag-index subcommand (whose only output was that file) is removed; specs/README.md keeps its generated TOC.
- **Supersedes:** DECISION-RECORDS-D02

### DECISION-RECORDS-D05 - Retire the numbered reference series; docs/ is one topic-doc layer
- **Date:** 2026-10-18
- **Why:** The `NNN-` reference series and the topic docs explained the same subsystems in two places, so a reader had to jump between a "what is" doc and a "why we chose" doc to understand one thing. Consolidating everything into flat, prefix-free topic docs (each `## Current State` + `## Decision Log`) with `docs/README.md` as a guided reading path gives a newcomer one place to start and removes the engine's special-cased "reference" series.
- **Supersedes:** the numbered reference series and the `NNN-` docs naming convention (the reference-series half of DECISION-RECORDS-D02)
- **Affects:** overview.md, skill-discovery.md, routing.md
