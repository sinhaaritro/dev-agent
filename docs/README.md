# Docs

Human + AI shared space: the committed knowledge of this repository.

| Folder | Holds | ID convention |
| :--- | :--- | :--- |
| `specs/` | What to build — permanent functional & technical specs with a lifecycle (DRAFT → APPROVED) | `NNN-<slug>.md`, sub-IDs `NNN-<letter><NN>` (spec 010 D3) |
| `specs/temp/` | Ephemeral working memory (gitignored; purged by task-cleaner) | none |
| `docs/001..007-*.md` (reference series) | What is — living, lookup, authoritative docs (no lifecycle) | `NNN-<slug>.md` |
| `docs/<name>.md` (topic docs) | Why we chose — Topic-Based decision docs: one livedoc per subsystem (`## Current State` + `## Decision Log`), revised in place | `<name>.md` or `<name>/` (plain lowercase kebab; decision IDs `<TOPIC>-D<nn>`) |

Topic docs live directly under `docs/`, one per subsystem. The AI routing
index for them is the generated `docs/_topics.md` (rebuilt by
`generate_map.py sync-docs` after any docs/ edit) — it indexes every docs/
file and folder, reference series included; only `_topics.md` itself is
skipped. Humans read the topic files directly. See
`docs/005-docs-architecture-and-spec-lifecycle.md` for the contract.

## Status board

- `specs/` — 001 (topic-based ADR) approved + handed off, in build
- topic docs — `decision-records` seeded (the decision system itself); the many-ADR model is retired
- reference series — 001–007 current

## Frontmatter conventions

Human-curated list (this page is maintained by hand, not by the engine):

- `tags: [lowercase-kebab, ...]` on every doc in `specs/` and the reference
  series — and every topic doc (its `tags:` list is the source of the `covers:`
  line in `docs/_topics.md`) — kept consistent with `promote_spec.py tag-lint`,
  which also runs inside the `check` promotion gate; advisory near-dup
  detection via `tag-suggest`.
- Optional on the reference series only: `version_pin: <git-tag>` or
  `fallback_pin: <commit-hash>` (validated when present).
- The filename is the single identity — no `name:` field anywhere.
