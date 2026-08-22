tags: [docs-architecture, id-conventions, tag-governance, toc, reference-rename]

# 010: Docs Architecture Rebuild - Reference Rename, ID Conventions, Tag Governance & TOC Roll-up

Status: APPROVED | Phase: 2-Build
Handoff: 2026-08-20

## 1. Goal & Context

Rebuild the `docs/` shared-space so the human and AI reader paths are equal-weight:
rename `docs/architecture/` to `docs/reference/` (living, version-pinable, generic
docs home), introduce explicit ID conventions for all three committed subfolders,
add a universal `tags` field to frontmatter across all three folders, add
deterministic per-folder TOC roll-ups (Python-generated, marker-block), and add
tag-governance functions to `promote_spec.py` (list / suggest-merge / lint /
rename / index) with lint wired into the existing `check` promotion gate. The
spec/ADR/handoff/verify-state contracts (file names, Status:/Phase:/Handoff:
headers, append-only rules) stay byte-identical; this task only adds to them.

## 2. Architectural Decisions & Trade-offs

- **D1 - Rename architecture to reference.** `docs/architecture/` becomes
  `docs/reference/`. Rationale: "reference" is the established word for the
  living, lookup, authoritative source of current system truth - distinct from
  `specs/` (what to build, lifecycle) and `decisions/` (why we chose, immutable,
  backlinked). The three-folder triad is now what-is / what-to-build / why.
  Alternatives considered: `blueprint/` (implies pre-build, static), `handbook/`
  (implies how-to), `docs-core/` (vague). "Reference" is precise, familiar, and
  version-pin friendly. Trade-off: every existing cross-reference to
  `docs/architecture/...` (READMEs, specs, ADRs, v7 master doc) must be updated in
  one pass - a mechanical global rename with a verification grep at the end.
- **D2 - No lifecycle on reference; version pin is opt-in.** Reference docs carry
  no DRAFT/APPROVED transition. They are *living*. Optional frontmatter
  `version_pin: <git-tag>` (primary, for repos that ship versioned docs) or
  `fallback_pin: <commit-hash>` (when no tag exists). Absent by default - small
  repos and this template use neither. A checker validates `version_pin` is a real
  tag and `fallback_pin` is a reachable commit only when the field is present.
  Trade-off: opt-in keeps the template lightweight; the versioned-repo case is
  supported without burdening the common case.
- **D3 - ID conventions per folder (not one scheme).** Numeric, ordered where
  things proliferate; slugs where things are few and named; flat counters where
  things are atomic:
  - `specs/`: `NNN-<slug>.md`, sub-IDs `NNN-<letter><NN>` (e.g. `001-A01`,
    `001-A02`, `001-B01`), deeper `NNN-<letter><NN>-<letter><NN>` (e.g.
    `001-A01-B01`). Hyphen separator (no dot) - `001A01` was ambiguous
    (A-01 vs A0-1). Parent and child share the `NNN` prefix so a worktree can
    claim the subtree. The engine's `next_number()` must learn to read sub-IDs:
    a child promotion under `001` increments that branch's letter-group counter,
    not the global max.
  - `decisions/`: `adr-NNN-<slug>.md` (unchanged, flat). ADRs never nest; nesting
    is expressed by the backlink graph (`Source:` points at spec, `Governed-by:`
    optional pointer to reference doc).
  - `reference/`: `<slug>.md` (human-readable, no numeric prefix - blueprints are
    few and named, not counted). Display title derived from filename or H1, never
    a `name:` field.
- **D4 - Universal `tags` field, filename = identity.** All three folders'
  frontmatter carry `tags: [lowercase-kebab, ...]`. No `name:` field anywhere -
  the filename is the single identity (kills the dual-source-of-truth trap).
  Controlled-vocabulary discipline is enforced by lint (normative) + suggest
  (advisory). Tags are the one structured field that pays off as the repo grows
  and feeds any future vector index as a structured filter layer.
- **D5 - Tag functions live in promote_spec.py, not a new script.** Five new
  subcommands dispatched by the existing CLI, each a thin wrapper around a
  private function; `check` internally calls `_tag_lint()` as one validation step
  (two entry points, one function - no logic duplication):
  - `tag-list`  -> `_tag_list()`       read-only, prints sorted tag->files w/ counts, no state
  - `tag-suggest` -> `_tag_suggest()`  read-only, prints near-dup candidates
  - `tag-lint`    -> `_tag_lint()`     normative, exit 1 on violations; wired into `check`
  - `tag-rename`  -> `_tag_rename()`   the only writer; rewrites frontmatter tags in matched files
  - `tag-index`   -> `_tag_index()`    writes Tag index block into folder README marker
  Trade-off: keeps the one-engine-per-concern pattern (promote_spec.py already has
  promote/adr/handoff/check subcommands); no second script file.
- **D6 - Deterministic TOC in folder READMEs, marker-block pattern, subcommand
  placement (RESOLVED: Option A).** The TOC is a `toc` subcommand of
  `promote_spec.py` (human-confirmed). Rationale: `toc` and `tag-index` both scan
  the three committed folders and write marker blocks into the same READMEs, so
  they share one `_scan_docs()` helper and live in one file - no duplicated
  frontmatter parsing, no cross-script drift risk. It emits a `## Index` section
  between `<!-- TOC:START -->` and `<!-- TOC:END -->` markers in each folder's
  README.md. Deterministic, sorted by each folder's ID scheme (specs by NNN/sub-ID,
  decisions by adr-NNN, reference by slug), shows name + status + version-pin +
  backlinks. Idempotent - only rewrites the marker block, never surrounding prose.
  Hooked into `promote`/`adr`/`handoff` so the TOC never drifts. `docs/temp/` gets
  NO TOC (ephemeral, gitignored, purged by task-cleaner - a generated index there
  is just churn). Trade-off: promote_spec.py grows by ~150 LOC (557 -> ~700);
  accepted in exchange for a single engine and shared scan logic.
- **D7 - Tag lint rules (normative, in check).** Lowercase-kebab only (catches
  `AuthToken`, `data model`); length bounds (2-30 chars); max 7 tags per doc
  (prevents noise); no empty tag field. Advisory `suggest` is NOT part of check
  (a suggestion should never block promotion). Lint exit code is identical in
  standalone and in-check (always 1 on violation) so the exit code is trustworthy
  in both contexts; no `--warn-only` flag.

## 3. Affected Files & Scope

- Renamed: docs/architecture/ -> docs/reference/ (git mv, preserves history)
- Modified: docs/README.md (NEW - human landing page: TOC, status board, folder
  descriptions; the single highest-leverage fix for the human reader path)
- Modified: docs/reference/README.md (was architecture/README.md; reworded for
  the reference role, version-pin note, TOC marker block)
- Modified: docs/reference/000-modular-agent-orchestration-v7.md (master doc:
  add tags frontmatter, update internal doc-tree to say reference/ not
  architecture/, note D2 version-pin)
- Modified: docs/specs/README.md (add TOC marker block + sub-ID convention note)
- Modified: docs/decisions/README.md (add TOC marker block + "never nest, use
  backlinks" note)
- Modified: docs/specs/001..009 (add tags frontmatter to each; 001-008 stay
  APPROVED/PROVISIONAL byte-identical otherwise per spec 009 D4 protection)
- Modified: docs/decisions/adr-001..adr-006 (add tags frontmatter; protected,
  byte-identical otherwise)
- Modified: .agents/skills/spec-builder/scripts/promote_spec.py (5 new tag
  subcommands + _tag_* functions; next_number() learns sub-IDs; check calls
  _tag_lint; promote/adr/handoff call build_toc at the end)
- Modified: .agents/skills/spec-builder/SKILL.md (document new subcommands, new
  ID conventions, tags contract)
- Modified: .agents/skills/spec-builder/references/implementation-plan-template.md
  (add optional tags frontmatter to the template)
- Modified: .agents/skills/spec-builder/references/adr-template.md (add optional
  tags frontmatter)
- Modified: .agents/rules/system.md (update any docs/architecture/ ->
  docs/reference/ references; note tag-lint-in-check and TOC hooks)
- Modified: AGENTS.md (repo-map line docs/architecture -> docs/reference)
- Created: none new files (the TOC is a `toc` subcommand of promote_spec.py per D6)
- ADRs to file: adr-007-docs-reference-rename-and-id-conventions (D1+D3),
  adr-008-universal-tags-and-toc-rollup (D4+D5+D6)
- Deleted: none
- Untouched: .agents/skills/skill-creator/**, docs/temp/.gitignore, every other
  docs/temp/** working file, .agents/MAP.md (regenerated by map-generator, not
  hand-edited)

## 4. Actionable TODO Checklist

- [x] Step 1: git mv docs/architecture/ to docs/reference/; update its README and
        the v7 master doc's internal tree; add tags frontmatter to all reference
        docs (only 000 master for now).
- [x] Step 3: Add tags frontmatter to docs/specs/001-009 and
        docs/decisions/adr-001-006 (protected files - byte-identical otherwise,
        add tags line only, with explicit human confirmation for the protected
        edit per system.md 3).
- [x] Step 4: Create docs/README.md landing page (TOC + status board + folder
        descriptions) and add TOC marker blocks to the three folder READMEs.
- [x] Step 5: Implement the five _tag_* functions in promote_spec.py (list,
        suggest, lint, rename, index) + CLI subparsers; wire _tag_lint into check.
- [x] Step 6: Implement next_number() sub-ID support (read NNN-letter-NN,
        increment branch counter) + slug_from_title handling of sub-ID titles
        (strip `NNN-LNN:` prefix).
- [x] Step 7: Implement the `toc` subcommand (_toc_list, _write_toc_block, shared
        _scan_docs helper) in promote_spec.py + hook into promote/adr/handoff so
        the TOC regenerates on every lifecycle event.
- [x] Step 8: Update specs 001-008, ADRs 001-006, v7 master doc, system.md,
        SKILL.md, templates, AGENTS.md for all doc-tree / ID / tags references.
- [x] Step 9: File adr-007 (D1+D3) and adr-008 (D4+D5+D6) via promote_spec.py adr
        --source <this spec>.
- [x] Step 10: Verify (see section 5).

## 5. Verification Commands

- Build Command: none (no build system for this repo)
- Test Command:
  - ID convention: `python .agents/skills/spec-builder/scripts/promote_spec.py
    promote <test-draft> --lane B --dry-run --specs-dir <sandbox>` for each ID
    shape (NNN, NNN-A01, NNN-A01-B01) and assert the computed number/slug is
    correct (a sandbox specs-dir, never the real docs/specs/).
  - Tag functions: a sandbox docs tree with 3-4 seeded files carrying tags, then
    `tag-list` (stdout sorted, no writes), `tag-lint` (seed one bad tag, assert
    exit 1 + violation named; fix, assert exit 0), `tag-suggest` (seed
    `data-model` + `datamodel`, assert the pair is flagged, no writes),
    `tag-rename` (assert only frontmatter changed, prose intact), `tag-index`
    (assert README marker block present, surrounding prose byte-identical).
  - check-wiring: a draft with a malformed tag must fail `check` with the tag
    lint violation in the output (proves _tag_lint is in the gate).
  - TOC: seed a sandbox folder, run promote/adr/handoff, assert the README
    `<!-- TOC:START/END -->` block updated and the surrounding markdown is
    unchanged (diff outside markers is empty).
  - No-dup-identity: promote two drafts with the same title in different lanes -
    the second must be refused (find_existing_by_title still works with sub-IDs).
- Lint Command: none (no linter configured)

## 6. Rollback Strategy

All edits are text-only and additive in intent; the one destructive op is the
folder rename. On circuit-breaker trip (3 consecutive verification failures):
`git checkout -- docs .agents AGENTS.md` restores every pre-task file; the rename
is a `git mv` so `git checkout` reverts it cleanly (history preserved either
way). The scratchpad (draft-plan.md) is gitignored and unaffected. ADRs 007/008
and the promoted spec remain the durable record of what was attempted. AGENTS.md
is modified, so the template consumer would re-derive on next init - no other
consumer state.

---
Usage: drafted at `docs/temp/draft-plan.md` during Phase 1-Plan; validated with
`promote_spec.py check <draft> --lane A`; on acceptance promoted to
`docs/specs/[010]-docs-architecture-rebuild-reference-rename-id-conventions-
tag-governance-toc-rollup.md`; two ADRs filed (007, 008) covering the
architectural decisions; Phase 1.5 handoff recorded; session stops (spec 008 D1).
