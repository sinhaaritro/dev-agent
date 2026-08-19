# ADR-001: Two-Step Spec Lifecycle (Approval vs. Implementation)

Status: Accepted
Date: 2026-08-18
Source: docs/specs/007-spec-first-lifecycle-core-skill.md

## Context

Spec-first teams need an approved, permanent spec before implementation
starts, so the approval gate belongs at the end of planning rather than at
review. Options considered: keep spec-last promotion at review (the spec as
a post-hoc record), or promote on plan approval and turn review into a
finalize step.

## Decision

Split the lifecycle into two steps: Step 1 approves the draft and promotes
it to docs/specs/ together with its ADRs, then stops; Step 2 is a separate
session or agent that builds from the promoted spec. Phase 3-Review becomes
a finalize step (drift check, checkbox sync, verification evidence) instead
of the birth of the spec.

## Consequences

The spec is an approved contract before any code exists, enabling clean
agent handoff. The spec can drift from the final implementation, so review
must sync the section-4 checkboxes and confirm the build matches section 3
before closing.