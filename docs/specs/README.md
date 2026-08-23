# Specs

Permanent functional & technical specs. Promotion pipeline:

- Draft: `docs/temp/draft-plan.md` (gitignored)
- Acceptance: promoted to `docs/specs/<NNN>-<feature-slug>.md` and committed

Naming: `NNN-<feature-slug>.md` (e.g. `001-feature-spec.md`). Sub-documents use
sub-IDs that share the parent `NNN` prefix: `NNN-<letter><NN>` (e.g. `001-A01`),
deeper `NNN-<letter><NN>-<letter><NN>` (e.g. `001-A01-B01`). Parent and child
share the `NNN` so a worktree can claim the subtree.

Every spec carries `tags: [lowercase-kebab, ...]`; the promotion gate runs
`tag-lint` on them.

<!-- TOC:START -->
## Index
<!-- TOC:END -->

<!-- TAG-INDEX:START -->
<!-- TAG-INDEX:END -->
