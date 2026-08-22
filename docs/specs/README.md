# Specs

Permanent functional & technical specs. Promotion pipeline (Spec V7 §7):

- Draft: `docs/temp/draft-plan.md` (gitignored)
- Acceptance: promoted to `docs/specs/<NNN>-<feature-slug>.md` and committed

Naming: `NNN-<feature-slug>.md` (e.g., `001-feature-spec.md`). Sub-documents use
sub-IDs that share the parent `NNN` prefix: `NNN-<letter><NN>` (e.g. `001-A01`),
deeper `NNN-<letter><NN>-<letter><NN>` (e.g. `001-A01-B01`) — spec 010 D3.
Parent and child share the `NNN` so a worktree can claim the subtree.

Every spec carries `tags: [lowercase-kebab, ...]` (spec 010 D4); the promotion
gate runs `tag-lint` on them.

<!-- TOC:START -->
## Index
- 📁 specs/
  - 📄 [001-map-generator-core-skill.md](./001-map-generator-core-skill.md) — APPROVED | Phase: 2-Build | Date: 2026-08-15
  - 📄 [002-auto-router-core-skill.md](./002-auto-router-core-skill.md) — APPROVED | Phase: 2-Build | Date: 2026-08-15
  - 📄 [003-phase-protocol-core-skill.md](./003-phase-protocol-core-skill.md) — APPROVED | Phase: 2-Build | Date: 2026-08-15
  - 📄 [004-spec-builder-core-skill.md](./004-spec-builder-core-skill.md) — APPROVED | Phase: 2-Build | Date: 2026-08-15
  - 📄 [005-verification-runner-core-skill.md](./005-verification-runner-core-skill.md) — APPROVED | Phase: 2-Build | Date: 2026-08-15
  - 📄 [006-task-cleaner-core-skill.md](./006-task-cleaner-core-skill.md) — APPROVED | Phase: 2-Build | Date: 2026-08-15
  - 📄 [007-spec-first-lifecycle-core-skill.md](./007-spec-first-lifecycle-core-skill.md) — APPROVED | Phase: 2-Build
  - 📄 [008-post-approval-handoff-guard.md](./008-post-approval-handoff-guard.md) — APPROVED | Phase: 2-Build
  - 📄 [009-frontmatter-migration-framework-compaction.md](./009-frontmatter-migration-framework-compaction.md) — APPROVED
  - 📄 [010-docs-architecture-rebuild-reference-rename-id-conventions-tag-governance-toc-roll-up.md](./010-docs-architecture-rebuild-reference-rename-id-conventions-tag-governance-toc-roll-up.md) — APPROVED | Phase: 2-Build
<!-- TOC:END -->
