# Decisions

Architectural Decision Records (ADRs). Naming: `adr-<NNN>-<topic>.md`
(e.g., `adr-001-database-selection.md`). Flat — ADRs never nest; nesting is
expressed by the backlink graph (`Source:` points at the spec, optional
`Governed-by:` points at a reference doc).

Protected files: ADRs in this directory must not be edited or deleted without
explicit human confirmation (system.md §3).

Every ADR carries `tags: [lowercase-kebab, ...]` (spec 010 D4).

<!-- TOC:START -->
## Index
- 📁 decisions/
  - 📄 [adr-001-two-step-spec-lifecycle-approval-vs-implementation.md](./adr-001-two-step-spec-lifecycle-approval-vs-implementation.md) — Accepted — backlinks: docs/specs/007-spec-first-lifecycle-core-skill.md
  - 📄 [adr-002-adrs-triggered-by-decision-not-lane.md](./adr-002-adrs-triggered-by-decision-not-lane.md) — Accepted — backlinks: docs/specs/007-spec-first-lifecycle-core-skill.md
  - 📄 [adr-003-adr-mandatory-handoff-phase.md](./adr-003-adr-mandatory-handoff-phase.md) — Accepted — backlinks: docs/specs/008-post-approval-handoff-guard.md
  - 📄 [adr-004-adr-engine-recorded-handoff-with-durable-marker.md](./adr-004-adr-engine-recorded-handoff-with-durable-marker.md) — Accepted — backlinks: docs/specs/008-post-approval-handoff-guard.md
  - 📄 [adr-005-adr-lane-scoped-handoff-guard.md](./adr-005-adr-lane-scoped-handoff-guard.md) — Accepted — backlinks: docs/specs/008-post-approval-handoff-guard.md
  - 📄 [adr-006-adr-nnn-minimal-skill-md-frontmatter-contract-with-nested-metadata.md](./adr-006-adr-nnn-minimal-skill-md-frontmatter-contract-with-nested-metadata.md) — Accepted — backlinks: docs/specs/009-frontmatter-migration-framework-compaction.md
  - 📄 [adr-007-docs-reference-rename-id-conventions.md](./adr-007-docs-reference-rename-id-conventions.md) — Accepted — backlinks: docs/specs/010-docs-architecture-rebuild-reference-rename-id-conventions-tag-governance-toc-roll-up.md
  - 📄 [adr-008-universal-tags-deterministic-toc-rollup.md](./adr-008-universal-tags-deterministic-toc-rollup.md) — Accepted — backlinks: docs/specs/010-docs-architecture-rebuild-reference-rename-id-conventions-tag-governance-toc-roll-up.md
<!-- TOC:END -->
