---
tags: [docs, spec, lifecycle, adr, scratchpad]
---

# 005 - Docs Architecture & Spec Lifecycle

The knowledge layer: the `docs/` folder structure, ID and tag conventions,
the spec-first lifecycle (draft → approval → promotion → ADRs → handoff →
build → review), and the scratchpad's garbage collection.

**Skills covered:** `spec-builder` (templates, promotion, ADRs, handoff, tag
governance, TOC), `task-cleaner` (scratchpad purging).

## 1. The `docs/` triad + scratchpad

| Folder | Role | Lifecycle |
| :--- | :--- | :--- |
| `docs/specs/` | What to build | Lifecycle: `Status: DRAFT` → `APPROVED` (or `PROVISIONAL - AUTONOMOUS DEFAULT`) |
| `docs/decisions/` | Why we chose | Immutable ADRs; backlinked to specs via `Source:` |
| `docs/reference/` | What is (this series) | Living; no lifecycle; optional `version_pin` / `fallback_pin` |
| `docs/temp/` | Ephemeral working memory | Gitignored (`*` except `.gitignore`); purged on acceptance |

Each committed folder has a `README.md` carrying a generated `## Index`
section between `<!-- TOC:START -->` / `<!-- TOC:END -->` markers;
`docs/README.md` is the human landing page. `docs/temp/` gets no TOC
(ephemeral — a generated index there is just churn).

## 2. ID conventions

- **`specs/`:** `NNN-<slug>.md`. Sub-IDs: `NNN-<letter><NN>` (e.g. `001-A01`),
  deeper `NNN-<letter><NN>-<letter><NN>` (e.g. `001-A01-B01`). Parent and
  child share the `NNN` prefix so a worktree can claim the subtree. A sub-ID
  child promotes as `NNN-<slug>.md` (the engine strips the `NNN-LNN:` title
  prefix).
- **`decisions/`:** `adr-<NNN>-<slug>.md` (flat; ADRs never nest — nesting is
  expressed by the backlink graph).
- **`reference/`:** `<slug>.md` (no numeric prefix — blueprints are few and
  named, not counted).

**Numbering is engine-derived.** `promote_spec.py` computes the next `NNN` by
scanning the folder; a hand-written number can silently overwrite a committed
record.

## 3. Tags contract

Every committed doc in `specs/`, `decisions/`, `reference/` carries a `tags`
field in its **YAML frontmatter block** at the top of the file:

```text
---
tags: [lowercase-kebab, ...]
---
```

2–30 chars per tag, max 7 per doc, no empty field. The **filename is the
single identity** — there is no `name:` field anywhere. Reference docs may
optionally add `version_pin: <git-tag>` or `fallback_pin: <commit-hash>` in
the same block.

Legacy tolerance: a bare `tags:` line outside frontmatter (pre-frontmatter
docs) is still read by every scan, and is normalized into frontmatter
automatically by the engine on `promote`, ADR filing, and `tag-rename` — so
old docs keep working and converge to the canonical form on their next write.

Governance subcommands of `promote_spec.py`:

| Subcommand | Behavior |
| :--- | :--- |
| `tag-list` | Read-only: sorted tag → files with counts |
| `tag-suggest` | Advisory near-dup candidates only — never blocks |
| `tag-lint` | Normative; exit 1 on violations; also runs inside `check` |
| `tag-rename <old> <new>` | The only writer; frontmatter tags only |
| `tag-index` | Writes the `<!-- TAG-INDEX:* -->` block into `docs/README.md` |

## 4. The spec-first lifecycle (two steps)

```text
Incoming requirement
        │
        ▼
 docs/temp/draft-plan.md          (Lane B: sections 1,3,4 / Lane A: all 6)
        │  validated: promote_spec.py check <draft> --lane <B|A>
        ▼
 [ Approval gate — human acceptance or compliant autonomous resolution ]
        │  promote_spec.py promote <draft> --lane <B|A> --status <APPROVED|PROVISIONAL>
        ├──► docs/specs/NNN-<slug>.md        (committed, the working contract)
        ├──► docs/decisions/adr-NNN-*.md     (one per architectural decision; APPROVED only)
        └──► task-cleaner purges docs/temp/  (preserves gate-log.md)
        ▼
 Phase 1.5 - HANDOFF (mandatory)
        │  promote_spec.py handoff docs/specs/NNN-<slug>.md --lane <B|A>
        ├──► docs/temp/handoff.md            (ephemeral)
        └──► spec header stamped Handoff: <YYYY-MM-DD>   (durable proof)
        ▼
 SESSION STOPS — no build in the spec-producing session
        ▼
 STEP 2: a NEW session reads the promoted spec (verified via the Handoff:
 marker), builds, ticks section-4 checkboxes, finalizes at Phase 3-Review
 (Phase: 3-Review, checkboxes synced to - [x] with green verification
 evidence), then task-cleaner purges the scratchpad on acceptance.
```

Rules that make the split real:

- Promotion happens **at approval, never during review** and never before
  implementation. The `--status` argument is the agent's assertion of which
  gate passed — the engine is mechanics only, so never promote without the
  gate.
- `APPROVED` = human acceptance. `PROVISIONAL` renders
  `PROVISIONAL - AUTONOMOUS DEFAULT` and stays until a human clears the tag;
  autonomous resolutions file **no ADRs** until cleared.
- ADRs are triggered by **the decision, not the lane**: any architectural
  decision at any lane (schema, public API, auth/security, new dependency)
  gets a permanent ADR. Lane A: one per section-2 decision; Lane B: only when
  one surfaces.
- The handoff engine validates `Status: APPROVED` (Lane A additionally
  requires ≥1 ADR whose `Source:` points at the spec; Lane B allows zero).
  Exit 1 = fix the gap first. Idempotent; `--dry-run` prints without writing.
- Lanes C/D have no plan or approval step, so **no handoff applies** — never
  look for or create a handoff record for C/D tasks.
- A session that recorded a handoff MUST NOT open `build.md` in the same
  session.

## 5. Templates (format truth)

In `.agents/skills/spec-builder/references/`:

- **`implementation-plan-template.md`** — the 6-section plan: 1 Goal &
  Context, 2 Architectural Decisions & Trade-offs, 3 Affected Files & Scope,
  4 Actionable TODO Checklist, 5 Verification Commands, 6 Rollback Strategy.
  Lane B uses sections 1, 3, 4 only.
- **`adr-template.md`** — Context / Decision / Consequences, with `Status:`,
  `Date:`, `Source:` headers.
- **`todo-checklist-format.md`** — real-time markers: `- [ ]` pending →
  `- [/]` in progress → `- [x]` completed (only after that step's local
  verification passed; revert to `[ ]` when a step fails 3 consecutive times).

## 6. Deterministic TOC rollup

`python .agents/skills/spec-builder/scripts/promote_spec.py toc [--root
<docs-dir>]` regenerates each folder README's `## Index` marker block, sorted
by each folder's ID scheme (specs by NNN/sub-ID, decisions by adr-NNN,
reference by slug), showing name + status + version-pin + backlinks. It is
hooked into `promote` / `adr` / `handoff` so the TOC never drifts, is
idempotent (rewrites only the marker block, never surrounding prose), and
`--dry-run` prints without writing. **Never hand-edit a marker block** —
prose outside the markers (like the 000 NOT-IMPLEMENTED note in
`reference/README.md`) is safe from regeneration.

## 7. Scratchpad lifecycle & garbage collection

`docs/temp/` holds the session's working state: `active-task.md` (working
memory), `draft-plan.md` (the one running plan per task), `escalation.md`
(circuit-breaker report), `gate-log.md` (append-only audit), `handoff.md`
(Phase 1.5 record), `verify-state.json` (verification ledger), plus per-task
workspaces.

`task-cleaner` purges it on human acceptance (the final step of Review):

```text
python .agents/skills/task-cleaner/scripts/clean.py clean
```

- Default: everything purged **except** `gate-log.md` and `.gitignore`;
  report is `purged: N, preserved: M`.
- `clean --dry-run` / `status` classify without deleting — use in doubt.
- `gate-log.md` is purged **only** after an explicit human review via
  `clean --preserve ""` — a hand-deleted gate-log is a policy violation with
  no audit trail.
- Scope is the scratchpad and nothing else: the committed folders are never
  touched; the engine refuses targets at or above the repo root.
- The engine restores no template stubs — the next task's Plan phase creates
  scratchpad files on demand.
