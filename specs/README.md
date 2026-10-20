# Specs

Permanent functional & technical specs. Promotion pipeline:

- Draft: `specs/temp/draft-plan.md` (gitignored)
- Acceptance: promoted to `specs/<NNN>-SPEC-<slug>.md` and committed

Naming: `NNN-SPEC-<slug>.md` (e.g. `001-SPEC-topic-based-adr.md`). Sub-documents use
sub-IDs that share the parent `NNN` prefix: `NNN-<letter><NN>` (e.g. `001-A01`),
deeper `NNN-<letter><NN>-<letter><NN>` (e.g. `001-A01-B01`). Parent and child
share the `NNN` so a worktree can claim the subtree.

Every spec carries `tags: [lowercase-kebab, ...]`; the promotion gate runs
`tag-lint` on them.

<!-- TOC:START -->
## Index
  - 📄 [001-SPEC-topic-based-adr.md](./001-SPEC-topic-based-adr.md) — COMPLETED
  - 📄 [002-SPEC-subagent-task-files-full-plan.md](./002-SPEC-subagent-task-files-full-plan.md) — COMPILED
  - 📄 [003-SPEC-stop-the-engine-from-knowing-about-docs-readme-md.md](./003-SPEC-stop-the-engine-from-knowing-about-docs-readme-md.md) — COMPLETED | Date: 2026-09-27
  - 📄 [003-REPORT-stop-the-engine-from-knowing-about-docs-readme-md.md](./003-REPORT-stop-the-engine-from-knowing-about-docs-readme-md.md) — REVIEWED
<!-- TOC:END -->
