# Reference

Living reference docs — the authoritative, lookup surface of current system truth
(living, version-pinable; no DRAFT/APPROVED lifecycle; spec 010 D2). Distinct from
`docs/specs/` (what to build, lifecycle) and `docs/decisions/` (why we chose,
immutable, backlinked).

- `000-modular-agent-orchestration-v7.md` — NOT IMPLEMENTED as written.
  Superseded by the aspect-based series `001`-`007` (001 is the entry point);
  kept on disk for history only.

- `001-framework-overview.md` — series entry point: what the framework is,
  the directory map, memory architecture, boot chain, guardrails.
- `002-skill-discovery-and-indexing.md` — MAP.md, snapshot-hash freshness,
  two-stage skill recall.
- `003-triage-lane-taxonomy-and-escalation.md` — lanes D/C/B/A, session
  detection, escalation rules, worked examples.
- `004-phases-gates-and-autonomy.md` — SDLC phases, Socratic gate engine,
  autonomy policy, 4-block response schema.
- `005-docs-architecture-and-spec-lifecycle.md` — docs/ folders, ID/tag
  conventions, spec-first lifecycle, scratchpad GC.
- `006-verification-and-circuit-breakers.md` — verify.py, 3-retry breaker,
  escalation reports.
- `007-parallel-execution-and-worktrees.md` — worktree isolation model
  (INTENT, not yet implemented).

ID convention: `<slug>.md` (no numeric prefix; the filename is the single
identity). Display title comes from the filename or H1, never a `name:` field.

Version pin (opt-in, spec 010 D2): `version_pin: <git-tag>` (primary) or
`fallback_pin: <commit-hash>` (when no tag exists). Absent by default; when
present the value must be a real tag / reachable commit.

<!-- TOC:START -->
## Index
- 📁 reference/
  - 📄 [001-framework-overview.md](./001-framework-overview.md)
  - 📄 [002-skill-discovery-and-indexing.md](./002-skill-discovery-and-indexing.md)
  - 📄 [003-triage-lane-taxonomy-and-escalation.md](./003-triage-lane-taxonomy-and-escalation.md)
  - 📄 [004-phases-gates-and-autonomy.md](./004-phases-gates-and-autonomy.md)
  - 📄 [005-docs-architecture-and-spec-lifecycle.md](./005-docs-architecture-and-spec-lifecycle.md)
  - 📄 [006-verification-and-circuit-breakers.md](./006-verification-and-circuit-breakers.md)
  - 📄 [007-parallel-execution-and-worktrees.md](./007-parallel-execution-and-worktrees.md)
<!-- TOC:END -->
