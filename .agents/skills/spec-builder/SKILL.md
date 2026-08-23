---
name: spec-builder
description: Spec lifecycle - drafts implementation plans in docs/temp/, enforces templates, promotes approved specs to docs/specs/ at approval, files ADRs for architectural decisions, records Phase 1.5 handoffs
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

You own plan drafting, spec promotion, ADR filing, and handoff recording. The templates in `references/` are the format truth — every draft, promoted spec, and ADR must match them, which is why validation and promotion run through your engine instead of judgment. In system.md step 4 you are the on-demand plan authority: phase-protocol `plan.md` routes Lane B/A planning and its approval step (section 5) to you; `review.md` routes spec finalization.

## When to Use

- Lane B or A planning (`plan.md` section 2): draft the implementation plan into `docs/temp/draft-plan.md` under the enforced template.
- Approval-step promotion (`plan.md` section 5): on plan approval, promote `docs/temp/draft-plan.md` to `docs/specs/`, file ADRs for every architectural decision, then record the Phase 1.5 handoff — before implementation starts (spec-first, two-step lifecycle).
- Review finalization (`review.md` section 3): confirm the build matches the promoted spec and sync its checkboxes.
- Any request to "draft a plan", "write a spec", "promote", "write an ADR", or check an implementation plan's format — even if the user does not name the skill.

## Instructions

1. **Draft per lane into the running plan.** Lane B: sections **1 (Goal), 3 (Affected Files), 4 (TODO)** of `references/implementation-plan-template.md` only. Lane A: all six sections including 2 (Architectural Decisions & Trade-offs), 5 (Verification Commands), 6 (Rollback Strategy). Write to `docs/temp/draft-plan.md` and reuse that one running file — never multiple plan files per task. Drafts live in `docs/temp/` (gitignored), never committed.
2. **Validate before presenting** (never show or promote a half-formed plan):
   `python .agents/skills/spec-builder/scripts/promote_spec.py check docs/temp/draft-plan.md --lane <B|A>`
    Exit 0 = the lane's required sections are present AND the tag lint (spec 010 D7) found no violations; exit 1 prints the missing section numbers and/or the tag violations — fix them before continuing.
3. **Maintain the TODO checklist in real time** per `references/todo-checklist-format.md`: `- [ ]` pending → `- [/]` in progress → `- [x]` completed. Mark `[x]` only after that step's local verification passed — never with blank verification; revert to `[ ]` when a step fails 3 consecutive times (circuit breaker per phase-protocol `build.md`).
4. **Promote through the approval gate.** Promotion happens at the end of planning, on plan approval — never during review, never before implementation. It requires human acceptance or a compliant autonomous resolution (which leaves `docs/temp/gate-log.md` audit entries and marks the spec provisional). Run with the status matching the gate that actually passed:
   `python .agents/skills/spec-builder/scripts/promote_spec.py promote docs/temp/draft-plan.md --lane <B|A> --status <APPROVED|PROVISIONAL>`
   The engine validates the draft, computes the next sequential number by scanning `docs/specs/` (never guess), derives the slug from the title, and refuses to overwrite. `APPROVED` = human acceptance; `PROVISIONAL` renders `PROVISIONAL - AUTONOMOUS DEFAULT`, which stays until a human clears the tag. The engine is mechanics only — the gate is asserted by the status you pass, so never promote without the gate. Both lanes promote (B: sections 1/3/4).
5. **ADRs are triggered by the decision, not the lane.** Any architectural decision at any lane (schema, public API, auth/security, new dependency) gets a permanent ADR in `docs/decisions/`. Lane A: one per section-2 decision; Lane B: only when a decision surfaces (no section 2). At approval, draft each against `references/adr-template.md` in `docs/temp/` and file it:
   `python .agents/skills/spec-builder/scripts/promote_spec.py adr docs/temp/adr-draft-<topic>.md --source <promoted-spec>`
   The engine validates template sections, derives the next `NNN` from `docs/decisions/`, and refuses to overwrite. ADRs are written only alongside `APPROVED`; autonomous resolutions file none until a human clears the tag. Never edit an existing ADR — protected (system.md §3).
6. **Record the handoff — then stop.** After promotion and ADR filing (Phase 1.5):
   `python .agents/skills/spec-builder/scripts/promote_spec.py handoff docs/specs/<NNN>-<slug>.md --lane <B|A> [--handoff-dir <sandbox>] [--dry-run]`
    The engine validates `Status: APPROVED` (Lane A also requires ≥1 ADR with `Source:` pointing at the spec; Lane B allows zero), writes `docs/temp/handoff.md` (ephemeral; task-cleaner purges it at review), and stamps `Handoff: <YYYY-MM-DD>` on the spec header (durable). Idempotent; `--dry-run` prints without writing. Lanes C/D have no approval step, so no handoff (spec 008 D3). A session that recorded a handoff MUST NOT open `references/build.md` in the same session.
7. **ID conventions (spec 010 D3).** `specs/`: `NNN-<slug>.md`; sub-IDs `NNN-<letter><NN>` (e.g. `001-A01`), deeper `NNN-<letter><NN>-<letter><NN>` (e.g. `001-A01-B01`) — parent and child share the `NNN` prefix so a worktree can claim the subtree; a sub-ID child promotes as `NNN-<slug>.md` (the engine strips the `NNN-LNN:` title prefix). `decisions/`: `adr-<NNN>-<slug>.md` (flat; ADRs never nest — nesting is the backlink graph). `reference/`: `<slug>.md` (no numeric prefix).
8. **Tags contract (spec 010 D4/D7).** Every committed doc in `specs/`, `decisions/`, `reference/` carries a `tags` field in its YAML frontmatter block at the top of the file: `---\ntags: [lowercase-kebab, ...]\n---` (2-30 chars per tag, max 7/doc, no empty field) — the filename is the single identity, never a `name:` field. A bare `tags:` line outside frontmatter is still read (pre-frontmatter docs keep scanning) and is normalized into frontmatter automatically on promote, adr filing, and tag-rename. `reference/` docs may optionally add `version_pin: <git-tag>` or `fallback_pin: <commit-hash>` in the same block. Governance subcommands (all `--root <docs-dir>` defaults to the repo docs/):
    `python .agents/skills/spec-builder/scripts/promote_spec.py tag-list` (read-only report), `tag-suggest` (advisory near-dups only - never blocks), `tag-lint` (normative; also runs inside `check`), `tag-rename <old> <new>` (the only writer; frontmatter only), `tag-index` (writes the `<!-- TAG-INDEX:* -->` block into docs/README.md).
9. **Deterministic TOC (spec 010 D6).** Each folder README (+ the docs/ landing README) carries a `## Index` section between `<!-- TOC:START -->`/`<!-- TOC:END -->` markers, regenerated by the engine on every promote/adr/handoff:
    `python .agents/skills/spec-builder/scripts/promote_spec.py toc [--root <docs-dir>]`
    Never hand-edit a marker block — run `toc`. `docs/temp/` gets no TOC (ephemeral). `--dry-run` prints without writing.

## Output Contract

- Plan: the validated draft at `docs/temp/draft-plan.md` (abbreviated for B, full for A), real-time TODO markers.
- Approval: the promoted spec path and status, e.g. `promoted: docs/specs/004-<slug>.md` with `Status: APPROVED` (or `PROVISIONAL - AUTONOMOUS DEFAULT`), plus `adr: docs/decisions/adr-<NNN>-<slug>.md` per decision (Lane A always; Lane B when a decision surfaced).
- Handoff: `handoff: docs/temp/handoff.md` written, `Handoff: <YYYY-MM-DD>` stamped; the session then stops.
- Review: the finalized spec — `Phase: 3-Review`, section-4 checkboxes synced to `- [x]` with green verification evidence; no new promotion.

## Notes

- **Never promote without the gate** — the status argument is your assertion of which gate passed; the gate-log is the audit record.
- **Numbering is engine-derived** for specs (`docs/specs/`) and ADRs (`docs/decisions/`) — a hand-written number can silently overwrite a committed record.
- **`--specs-dir` / `--decisions-dir` are for tests only** — real promotions target `docs/specs/`, real ADRs target `docs/decisions/`.
- **Drafts are ephemeral**; `task-cleaner` purges them after approval — the promoted spec and its ADRs are the durable record.
- **The handoff record closes the loop:** `docs/temp/handoff.md` is ephemeral; the `Handoff:` header stamp is the durable proof of the split, and `build.md` refuses to build without it (spec 008).
