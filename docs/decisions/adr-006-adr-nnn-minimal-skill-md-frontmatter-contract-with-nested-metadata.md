tags: [frontmatter, sdsc]

# ADR-006: Minimal SKILL.md Frontmatter Contract with Nested Metadata

Status: Accepted
Date: 2026-08-19
Source: docs/specs/009-frontmatter-migration-framework-compaction.md

## Context

SKILL.md files carried flat `version:` and `author:` frontmatter fields that were
not part of the standard skill format, and `scope:` was required on every skill even
though the load-semantic default (on-demand) already covers most of them. Removing
the flat fields (commit 911aef1) left prose references stale and two loading models
in conflict. The options considered: drop version/author entirely (rejected - they
carry release provenance worth keeping), flat dotted keys `metadata.version:`
(rejected - non-standard YAML, hard to read), or a nested `metadata:` block
(standard YAML, one parser extension).

## Decision

The canonical SKILL.md frontmatter contract is: required `name`, `description`,
`tags`, and a nested `metadata` block carrying `version` + `author`; optional
`scope` (`always` only for auto-router and phase-protocol, omitted elsewhere with
the on-demand default applying). The map-generator engine parses one level of
nesting and tolerates legacy flat `version:`/`author:` lines without rendering
them. The whole `.agents/skill-creator/` directory is excluded from this migration
including its validator.

## Consequences

Positive: one unambiguous frontmatter contract; index generation stays
stdlib-only and backward-compatible during migration; the on-demand default removes
redundant `scope` declarations. Negative: the parser accepts two shapes until legacy
skills (skill-creator) are migrated, and `quick_validate.py` will keep rejecting the
new `metadata` key until it is separately updated. Follow-up: migrate
skill-creator and align its validator in a later task; superseded notes on specs
002/003/004 prevent their old unchecked TODOs from re-adding the flat fields.
