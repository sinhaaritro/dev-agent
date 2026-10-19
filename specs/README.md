# Specs

Permanent functional & technical specs. Promotion pipeline:

- Draft: `specs/temp/draft-plan.md` (gitignored)
- Acceptance: promoted to `specs/<NNN>-<feature-slug>.md` and committed

Naming: `NNN-<feature-slug>.md` (e.g. `001-feature-spec.md`). Sub-documents use
sub-IDs that share the parent `NNN` prefix: `NNN-<letter><NN>` (e.g. `001-A01`),
deeper `NNN-<letter><NN>-<letter><NN>` (e.g. `001-A01-B01`). Parent and child
share the `NNN` so a worktree can claim the subtree.

Every spec carries `tags: [lowercase-kebab, ...]`; the promotion gate runs
`tag-lint` on them.

<!-- TOC:START -->
## Index
  - 📄 [001-SPEC-topic-based-adr.md](./001-SPEC-topic-based-adr.md) — COMPLETED
  - 📄 [002-flow-design.md](./002-flow-design.md)
  - 📄 [002-SPEC-subagent-task-files-full-plan.md](./002-SPEC-subagent-task-files-full-plan.md) — DRAFTED | Date: 2026-09-23
  - 📄 [002-TASK-01-new-template-check.md](./002-TASK-01-new-template-check.md)
  - 📄 [002-TASK-02-compile-purge-sync-accept.md](./002-TASK-02-compile-purge-sync-accept.md)
  - 📄 [002-TASK-03-verify-doctor-hash.md](./002-TASK-03-verify-doctor-hash.md)
  - 📄 [002-TASK-04-coder-contract.md](./002-TASK-04-coder-contract.md)
  - 📄 [002-TASK-05-phase-renumber.md](./002-TASK-05-phase-renumber.md)
  - 📄 [002-TASK-06-run-contract.md](./002-TASK-06-run-contract.md)
  - 📄 [002-TASK-07-branch-commit-guardrail.md](./002-TASK-07-branch-commit-guardrail.md)
  - 📄 [002-TASK-08-spec-builder-template.md](./002-TASK-08-spec-builder-template.md)
  - 📄 [002-TASK-09-docs-and-charts.md](./002-TASK-09-docs-and-charts.md)
  - 📄 [002-TASK-10-slim-skills.md](./002-TASK-10-slim-skills.md)
  - 📄 [002-TASK-11-bootstrap-seeds.md](./002-TASK-11-bootstrap-seeds.md)
  - 📄 [002-TASK-12-task-cleaner.md](./002-TASK-12-task-cleaner.md)
  - 📄 [002-TASK-13-migrate-001-backlog.md](./002-TASK-13-migrate-001-backlog.md)
  - 📄 [002-TASK-14-drift-test-final.md](./002-TASK-14-drift-test-final.md)
  - 📄 [002-TASK-15-update-reference-docs.md](./002-TASK-15-update-reference-docs.md)
  - 📄 [003-REPORT-stop-the-engine-from-knowing-about-docs-readme-md.md](./003-REPORT-stop-the-engine-from-knowing-about-docs-readme-md.md) — REVIEWED
  - 📄 [003-SPEC-stop-the-engine-from-knowing-about-docs-readme-md.md](./003-SPEC-stop-the-engine-from-knowing-about-docs-readme-md.md) — COMPLETED | Date: 2026-09-27
  - 📄 [003-TASK-01-remove-docs-readme-md-machinery-from-pro.md](./003-TASK-01-remove-docs-readme-md-machinery-from-pro.md)
  - 📄 [003-TASK-02-strip-generated-blocks-from-docs-readme-.md](./003-TASK-02-strip-generated-blocks-from-docs-readme-.md)
  - 📄 [003-TASK-03-update-skill-rules-docs.md](./003-TASK-03-update-skill-rules-docs.md)
  - 📄 [003-TASK-04-update-reference-topic-docs.md](./003-TASK-04-update-reference-topic-docs.md)
  - 📄 [003-TASK-05-update-the-regression-tests.md](./003-TASK-05-update-the-regression-tests.md)
  - 📄 [003-TASK-06-make-promote-write-the-nnn-spec-slug-md-.md](./003-TASK-06-make-promote-write-the-nnn-spec-slug-md-.md)
<!-- TOC:END -->

<!-- TAG-INDEX:START -->
<!-- TAG-INDEX:END -->
