# Reference

Living reference docs — the authoritative, lookup surface of current system truth
(living, version-pinable; no DRAFT/APPROVED lifecycle; spec 010 D2). Distinct from
`docs/specs/` (what to build, lifecycle) and `docs/decisions/` (why we chose,
immutable, backlinked).

- `000-modular-agent-orchestration-v7.md` — Master Reference Specification &
  Architectural Blueprint (Version 7), approved, verbatim. Derived specs (e.g.
  `docs/specs/001-...`) refine its points and must reference it here.

ID convention: `<slug>.md` (no numeric prefix; the filename is the single
identity). Display title comes from the filename or H1, never a `name:` field.

Version pin (opt-in, spec 010 D2): `version_pin: <git-tag>` (primary) or
`fallback_pin: <commit-hash>` (when no tag exists). Absent by default; when
present the value must be a real tag / reachable commit.

<!-- TOC:START -->
## Index
- 📁 reference/
  - 📄 [000-modular-agent-orchestration-v7.md](./000-modular-agent-orchestration-v7.md)
<!-- TOC:END -->
