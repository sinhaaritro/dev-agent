# Architectural Decision Record (ADR) Template

The single source of format truth for ADRs. Every ADR filed to `docs/decisions/`
must match this structure, which is why ADR validation and filing mechanics run
through the spec-builder engine (`promote_spec.py adr`) instead of judgment.

 ```text
 ---
 tags: [lowercase-kebab, ...]
 ---
 
 # ADR-<NNN>: <Topic Title>

Status: Accepted
Date: YYYY-MM-DD
Source: docs/specs/<NNN>-<feature-slug>.md (section 2)

## Context

What problem or constraint forced this decision, the options considered, and why
they were rejected. 1-3 sentences.

## Decision

The choice made, stated plainly and without justification.

## Consequences

What this decision enables and what it costs: positive and negative trade-offs,
and any follow-up work it creates.
```

Usage: drafted at `docs/temp/adr-draft-<topic>.md` during the approval step
(Step 1, spec production), one ADR per architectural decision; validated and
filed with `promote_spec.py adr <draft> --source <spec>`. The engine derives the
next `NNN` by scanning `docs/decisions/`, refuses to overwrite an existing ADR
(protected files, system.md section 3), and never edits a filed record.

Rules:

1. ADRs are triggered by the decision, not the lane: any architectural decision
   at any lane (schema, public API, auth/security, new dependency) gets a
   permanent ADR. Lane A mandates one per section-2 decision; Lane B writes one
   only if a decision surfaces during the task.
2. `NNN` numbering is engine-derived, never hand-written.
3. ADRs are written only alongside `APPROVED` promotion (human acceptance).
   Autonomous resolutions stay `PROVISIONAL` and file no ADR until a human
   clears the tag.
4. Never edit or delete an existing ADR without explicit human confirmation.