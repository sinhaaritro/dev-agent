---
name: spec-builder
description: Spec lifecycle - drafts implementation plans in specs/temp/, enforces templates, promotes approved specs to specs/ at approval, records architectural decisions as topic log entries, records Phase 1.5 handoffs
tags:
  - spec
  - plan draft
  - promote
  - implementation plan
  - template
metadata:
  version: 1.0.0
  author: AI Agent
---

# Spec Builder

## Overview

You own plan drafting, spec promotion, topic decision recording, and handoff recording. The templates in `references/` are the format truth — every draft, promoted spec, and topic doc must match them, which is why validation and promotion run through your engine instead of judgment. In system.md step 4 you are the on-demand plan authority: phase-protocol `plan.md` routes Lane B/A planning and its approval step (section 5) to you; `review.md` routes spec finalization.

## When to Use

- Lane B or A planning (`plan.md` section 2): draft the implementation plan into `specs/temp/draft-plan.md` under the enforced template.
- Approval-step promotion (`plan.md` section 5): on plan approval, promote `specs/temp/draft-plan.md` to `specs/`, record a topic log entry for every architectural decision, then record the Phase 1.5 handoff — before implementation starts (spec-first, two-step lifecycle).
- Review finalization (`review.md` section 3): confirm the build matches the promoted spec and sync its checkboxes.
- Any request to "draft a plan", "write a spec", "promote", "record a decision", or check an implementation plan's format — even if the user does not name the skill.

## Instructions

1. **Draft per lane into the running plan.** Lane B: sections **1 (Goal & Context), 4 (Affected Files & Contracts), 5 (Task DAG)** of `references/implementation-plan-template.md` only. Lane A: all seven sections — 1 Goal & Context, 2 Architectural Decisions & Trade-offs, 3 Risks & Open Questions, 4 Affected Files & Contracts, 5 Task DAG, 6 Verification Commands, 7 Rollback Strategy. Write to `specs/temp/draft-plan.md` and reuse that one running file — never multiple plan files per task. Drafts live in `specs/temp/` (gitignored), never committed.
2. **Validate before presenting** (never show or promote a half-formed plan):
   `python .agents/skills/spec-builder/scripts/promote_spec.py check specs/temp/draft-plan.md --lane <B|A>`
    Exit 0 = the lane's required sections are present, the section-5 Task DAG passes the structure + static-oracle lint, AND the tag lint found no violations; exit 1 prints the missing section numbers and/or the structure violations and/or the tag violations — fix them before continuing.
3. **Maintain the Task DAG state in real time** per `references/todo-checklist-format.md`: state lives on subtasks, `- [ ]` pending → `- [/]` in progress → `- [x]` done. Mark a subtask `[x]` only when its `Verify` exits 0 AND the output matches `Expect`, with evidence recorded in `specs/temp/verify-state.json` — a checkbox without evidence is unmet — and only after the four passes; an impossible subtask is never deleted, it gets `ABANDON: <non-empty reason>`. Revert to `[ ]` when a subtask fails 3 consecutive times (circuit breaker per phase-protocol `build.md`).
4. **Promote through the approval gate.** Promotion happens at the end of planning, on plan approval — never during review, never before implementation. It requires human acceptance or a compliant autonomous resolution (which leaves `specs/temp/gate-log.md` audit entries and marks the spec provisional). Run with the status matching the gate that actually passed:
   `python .agents/skills/spec-builder/scripts/promote_spec.py promote specs/temp/draft-plan.md --lane <B|A> --status <APPROVED|PROVISIONAL>`
   The engine validates the draft, computes the next sequential number by scanning `specs/` (never guess), derives the slug from the title, and refuses to overwrite. `APPROVED` = human acceptance; `PROVISIONAL` renders `PROVISIONAL - AUTONOMOUS DEFAULT`, which stays until a human clears the tag. The engine is mechanics only — the gate is asserted by the status you pass, so never promote without the gate. Both lanes promote (B: sections 1/4/5).
 5. **Topic decisions are triggered by the decision, not the lane.** Any architectural decision at any lane (schema, public API, auth/security, new dependency) gets a permanent entry in its topic doc directly under `docs/` (one doc per subsystem — format truth: `references/topic-template.md`). Lane A: one per section-2 decision; Lane B: only when a decision surfaces (no section 2). At approval, file it via:
    `python .agents/skills/spec-builder/scripts/promote_spec.py topic <name> --why <text> [--title <t>] [--file <sub>] [--tags a,b] [--state <text>]`
    The engine creates the topic doc from the template when missing, allocates the next `<TOPIC>-D<nn>` by scanning every file of the topic (topic-global), and appends the Decision Log entry (`Date` / `Why` / `Supersedes` / `Affects` / `Ref`). Reversing a decision is a **revision**, never "delete + recreate": `--supersedes <ID>` marks the old entry `(superseded)` and the new entry takes the next ID; `--affects <target>` records a one-way ripple pointer; `--reciprocal <topic>` writes the terse `Ref` entry in the affected topic. Entries are recorded only alongside `APPROVED`; autonomous resolutions record none until a human clears the tag. No silent / unrequested topic edits in any lane (system.md §3). After any topic-doc edit, rebuild the index:
    `python .agents/skills/map-generator/scripts/generate_map.py sync-docs`
 6. **Record the handoff — then stop.** After promotion and decision recording (Phase 1.5):
    `python .agents/skills/spec-builder/scripts/promote_spec.py handoff specs/<NNN>-<slug>.md --lane <B|A> [--handoff-dir <sandbox>] [--dry-run]`
     The engine validates `Status: APPROVED`, writes `specs/temp/handoff.md` (ephemeral; task-cleaner purges it at review), and stamps `Handoff: <YYYY-MM-DD>` on the spec header (durable). Idempotent; `--dry-run` prints without writing. Lanes C/D have no approval step, so no handoff. A session that recorded a handoff MUST NOT open `references/build.md` in the same session.
  7. **ID conventions.** `specs/`: `NNN-<slug>.md`; sub-IDs `NNN-<letter><NN>` (e.g. `001-A01`), deeper `NNN-<letter><NN>-<letter><NN>` (e.g. `001-A01-B01`) — parent and child share the `NNN` prefix so a worktree can claim the subtree; a sub-ID child promotes as `NNN-<slug>.md` (the engine strips the `NNN-LNN:` title prefix). The reference series lives at `docs/NNN-<slug>.md` (numbered, living, no lifecycle). Topic docs: `docs/<name>.md` (or `docs/<name>/` once grown), plain lowercase kebab, no numeric prefix — the name is the decision-ID namespace (`<TOPIC>-D<nn>`, topic-global across sub-files); reserved names a topic may not use: the `NNN-` numbered reference series, `README.md`, anything underscore-prefixed.
  8. **Tags contract.** Every committed doc in `specs/` and the reference series (`docs/NNN-*.md`) — and every topic doc — carries a `tags` field in its YAML frontmatter block at the top of the file: `---\ntags: [lowercase-kebab, ...]\n---` (2-30 chars per tag, max 7/doc, no empty field) — the filename is the single identity, never a `name:` field. For topic docs the `tags:` list is also the source of the `covers:` line in `docs/_topics.md`. A bare `tags:` line outside frontmatter is still read (pre-frontmatter docs keep scanning) and is normalized into frontmatter automatically on promote, topic creation, and tag-rename. Reference-series docs may optionally add `version_pin: <git-tag>` or `fallback_pin: <commit-hash>` in the same block. Governance subcommands (all `--root <repo-root>` defaults to the repo root):
    `python .agents/skills/spec-builder/scripts/promote_spec.py tag-list` (read-only report), `tag-suggest` (advisory near-dups only - never blocks), `tag-lint` (normative; also runs inside `check`), `tag-rename <old> <new>` (the only writer; frontmatter only), `tag-index` (writes the `<!-- TAG-INDEX:* -->` block into docs/README.md).
  9. **Deterministic TOC + topic index.** The `docs/README.md` landing README and `specs/README.md` each carry a `## Index` section between `<!-- TOC:START -->`/`<!-- TOC:END -->` markers, regenerated by the engine on every promote/topic/handoff:
      `python .agents/skills/spec-builder/scripts/promote_spec.py toc [--root <repo-root>]`
      The topic docs get their own lighter index: `python .agents/skills/map-generator/scripts/generate_map.py sync-docs` writes `docs/_topics.md` (covers from `tags:`, sections/files from headings). `--root` is the **repo root** (`<repo>`) — the engine scans `<root>/specs` and `<root>/docs`. A misused nested path (e.g. `<repo>/docs`) is auto-corrected up to the repo root, so stray folders are never created. This normalization applies to every `--root` subcommand (`toc`, `tag-index`, `tag-list`, `tag-suggest`, `tag-lint`, `tag-rename`, `check`, `promote`). Never hand-edit a marker block — run `toc`. `specs/temp/` gets no TOC (ephemeral). `--dry-run` prints without writing.

## Output Contract

- Plan: the validated draft at `specs/temp/draft-plan.md` (abbreviated for B, full for A), real-time TODO markers.
- Approval: the promoted spec path and status, e.g. `promoted: specs/004-<slug>.md` with `Status: APPROVED` (or `PROVISIONAL - AUTONOMOUS DEFAULT`), plus `topic: docs/<name>.md` / `decision: <TOPIC>-D<nn>` per decision (Lane A always; Lane B when a decision surfaced).
- Handoff: `handoff: specs/temp/handoff.md` written, `Handoff: <YYYY-MM-DD>` stamped; the session then stops.
- Review: the finalized spec — `Phase: 3-Review`, section-5 Task DAG subtasks synced to `- [x]` with re-measured verification evidence (fresh Phase-Gate re-run); no new promotion.

## Notes

- **Never promote without the gate** — the status argument is your assertion of which gate passed; the gate-log is the audit record.
- **Numbering is engine-derived** for specs (`specs/`) and topic decision IDs (scanned across every file of the topic) — a hand-written number can silently collide with a committed record.
- **`--specs-dir` / `--docs-dir` / `--handoff-dir` are for tests only** — real promotions target `specs/`, real topics target `docs/`, real handoffs target `specs/temp/`.
- **Drafts are ephemeral**; `task-cleaner` purges them after approval — the promoted spec and its topic decision entries are the durable record.
- **The handoff record closes the loop:** `specs/temp/handoff.md` is ephemeral; the `Handoff:` header stamp is the durable proof of the split, and `build.md` refuses to build without it.
