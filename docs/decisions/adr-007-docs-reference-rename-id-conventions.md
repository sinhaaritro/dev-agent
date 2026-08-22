tags: [docs-architecture, id-conventions, reference-rename]

# ADR-007: Docs Reference Rename & ID Conventions

Status: Accepted
Date: 2026-08-20
Source: docs/specs/010-docs-architecture-rebuild-reference-rename-id-conventions-tag-governance-toc-roll-up.md

## Context

The `docs/` shared-space had grown three committed subfolders (`specs/`,
`decisions/`, `architecture/`) with no agreed identity scheme and no human-facing
landing page. `architecture/` was being repurposed as the generic, living,
version-pinable docs home, but the name read as a narrow planning artifact.
Sub-documents under a spec could not be expressed in the filename, and the
human-vs-AI reader weight was skewed (the AI path had engines + MAP.md; the human
path had only per-folder READMEs).

## Decision

- D1: Rename `docs/architecture/` to `docs/reference/`. "Reference" is the
  established word for the living, lookup, authoritative source of current system
  truth, distinct from `specs/` (what to build, lifecycle) and `decisions/` (why
  we chose, immutable, backlinked). The three-folder triad is what-is /
  what-to-build / why.
- D3: ID conventions per folder, not one scheme - numeric where things
  proliferate, slugs where few and named, flat counters where atomic.
  - `specs/`: `NNN-<slug>.md`; sub-IDs `NNN-<letter><NN>` (e.g. `001-A01`),
    deeper `NNN-<letter><NN>-<letter><NN>` (e.g. `001-A01-B01`). Hyphen
    separator (no dot) - `001A01` is ambiguous (A-01 vs A0-1). Parent and child
    share the `NNN` prefix so a worktree can claim the subtree.
  - `decisions/`: `adr-NNN-<slug>.md` (flat, unchanged). ADRs never nest; nesting
    is the backlink graph (`Source:` at the spec, optional `Governed-by:` at the
    reference doc).
  - `reference/`: `<slug>.md` (no numeric prefix; display title from filename or
    H1, never a `name:` field).
- D2: Reference docs have no lifecycle. Optional opt-in frontmatter
  `version_pin: <git-tag>` (primary, versioned repos) or `fallback_pin:
  <commit-hash>` (no tag yet). Absent by default. A checker validates the pin
  only when the field is present.

## Consequences

- Positive: the human reader gets a precise, familiar folder name and a clean
  identity scheme; parallel worktrees can claim spec subtrees by NNN prefix;
  versioned big-repo doc tracking is supported without burdening the common case.
- Negative: every existing cross-reference to `docs/architecture/...` (READMEs,
  specs, ADRs, master doc, AGENTS.md, system.md) must be updated in one pass -
  a mechanical global rename with a verification grep. The engine's
  `next_number()` must learn to read sub-IDs and increment the branch counter,
  not the global max.
- Follow-up: covered separately by the companion ADR on universal tags + TOC
  roll-up (D4/D5/D6).
